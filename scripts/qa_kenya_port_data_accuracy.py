"""
Kenya Port Data 100% Accuracy QA Script
========================================
Validates that all Kenya Excel files match database values within tolerance.

Checks:
1. Row counts: Excel vs DB (staging, ledger)
2. Value totals: Excel vs DB (within $0.01 tolerance)
3. Per-buyer validation for key buyers (DAVITA, MARBLE INN, etc.)
4. HS code aggregates match

Exit code:
- 0: All checks pass
- 1: One or more checks failed
"""

import sys
import os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Any

import pandas as pd

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ['DB_CONFIG_PATH'] = 'config/db_config.yml'

from etl.db_utils import DatabaseManager

# Tolerance for value comparisons (USD)
VALUE_TOLERANCE = 0.01

# Kenya Excel files to validate
KENYA_FILES = {
    'import_short': {
        'path': 'data/raw/kenya/import/2023/01/Kenya Import S.xlsx',
        'header_row': 0,
        'value_col': 'TOTALVALUEUSD',
        'buyer_col': 'IMPORTER_NAME',
        'hs_col': 'HS_CODE',
        'db_file_name': 'Kenya Import S.xlsx'
    },
    'import_full': {
        'path': 'data/raw/kenya/import/2023/01/Kenya Import F.xlsx',
        'header_row': 5,
        'value_col': 'TOTAL_VALUE_USD',
        'buyer_col': 'IMPORTER_NAME',
        'hs_col': 'HS_CODE',
        'db_file_name': 'Kenya Import F.xlsx'
    },
    'export_short': {
        'path': 'data/raw/kenya/export/2023/01/Kenya Export S.xlsx',
        'header_row': 0,
        'value_col': 'TOTALVALUE',
        'buyer_col': 'BUYER_NAME',
        'hs_col': 'HS_CODE',
        'db_file_name': 'Kenya Export S.xlsx'
    },
    'export_full': {
        'path': 'data/raw/kenya/export/2023/01/Kenya Export F.xlsx',
        'header_row': 5,
        'value_col': 'TOTAL_VALUE_USD',
        'buyer_col': 'BUYER_NAME',
        'hs_col': 'HS_CODE',
        'db_file_name': 'Kenya Export F.xlsx'
    }
}

# Key buyers to validate (importer name, expected HS code, expected value range)
KEY_BUYERS_IMPORT = [
    {
        'name': 'DAVITA SOLUTIONS LIMITED',
        'search_pattern': 'DAVITA',
        'hs_code': '6907210000',
        'expected_value_min': 56000,
        'expected_value_max': 57000,
        'expected_shipments': 2
    },
    {
        'name': 'MARBLE INN DEVELOPERS LIMITED',
        'search_pattern': 'MARBLE INN',
        'hs_code': '6907210000',
        'expected_value_min': 130000,
        'expected_value_max': 131000,
        'expected_shipments': 5
    }
]


class KenyaQAResult:
    """Container for QA results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.results = []
    
    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.results.append(('PASS', test_name, details))
        print(f"  ✓ {test_name}" + (f": {details}" if details else ""))
    
    def add_fail(self, test_name: str, details: str):
        self.failed += 1
        self.errors.append((test_name, details))
        self.results.append(('FAIL', test_name, details))
        print(f"  ✗ {test_name}: {details}")
    
    def is_success(self) -> bool:
        return self.failed == 0


def load_excel_file(file_config: dict) -> pd.DataFrame:
    """Load Excel file with proper settings"""
    path = file_config['path']
    if not os.path.exists(path):
        raise FileNotFoundError(f"Excel file not found: {path}")
    
    df = pd.read_excel(path, header=file_config['header_row'])
    return df


def get_db_file_stats(db: DatabaseManager, source_file: str) -> Dict[str, Any]:
    """Get standardized and ledger stats for a file from DB"""
    # Standardized stats
    std_result = db.execute_query("""
        SELECT COUNT(*) as rows, COALESCE(SUM(customs_value_usd), 0) as total_value
        FROM stg_shipments_standardized
        WHERE source_file = %s
    """, (source_file,))
    
    std_rows = std_result[0][0] if std_result else 0
    std_value = float(std_result[0][1]) if std_result else 0.0
    
    # Ledger stats
    ledger_result = db.execute_query("""
        SELECT COUNT(*) as rows, COALESCE(SUM(customs_value_usd), 0) as total_value
        FROM global_trades_ledger
        WHERE source_file = %s
    """, (source_file,))
    
    ledger_rows = ledger_result[0][0] if ledger_result else 0
    ledger_value = float(ledger_result[0][1]) if ledger_result else 0.0
    
    return {
        'std_rows': std_rows,
        'std_value': std_value,
        'ledger_rows': ledger_rows,
        'ledger_value': ledger_value
    }


def get_buyer_stats_from_db(db: DatabaseManager, buyer_pattern: str, destination: str = 'KENYA') -> Dict[str, Any]:
    """Get buyer stats from ledger"""
    result = db.execute_query("""
        SELECT 
            om.name_normalized as buyer_name,
            SUM(g.customs_value_usd) as total_value,
            COUNT(*) as shipments
        FROM global_trades_ledger g
        JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
        WHERE om.name_normalized ILIKE %s
        AND g.destination_country = %s
        GROUP BY om.name_normalized
    """, (f'%{buyer_pattern}%', destination))
    
    if result:
        return {
            'buyer_name': result[0][0],
            'total_value': float(result[0][1]),
            'shipments': result[0][2]
        }
    return None


def validate_file(db: DatabaseManager, file_key: str, file_config: dict, qa: KenyaQAResult):
    """Validate a single Kenya file"""
    print(f"\n--- Validating: {file_config['db_file_name']} ---")
    
    # Load Excel
    try:
        df = load_excel_file(file_config)
    except FileNotFoundError as e:
        qa.add_fail(f"{file_key}_file_exists", str(e))
        return
    
    excel_rows = len(df)
    excel_value = df[file_config['value_col']].sum()
    
    # Get DB stats
    db_stats = get_db_file_stats(db, file_config['db_file_name'])
    
    # 1. Row count check - Standardized
    if excel_rows == db_stats['std_rows']:
        qa.add_pass(f"{file_key}_std_row_count", f"{excel_rows} rows")
    else:
        qa.add_fail(f"{file_key}_std_row_count", 
                   f"Excel={excel_rows}, DB_STD={db_stats['std_rows']}")
    
    # 2. Row count check - Ledger
    if excel_rows == db_stats['ledger_rows']:
        qa.add_pass(f"{file_key}_ledger_row_count", f"{excel_rows} rows")
    else:
        qa.add_fail(f"{file_key}_ledger_row_count", 
                   f"Excel={excel_rows}, DB_LEDGER={db_stats['ledger_rows']}")
    
    # 3. Value check - Standardized
    value_diff_std = abs(excel_value - db_stats['std_value'])
    if value_diff_std <= VALUE_TOLERANCE:
        qa.add_pass(f"{file_key}_std_value", f"${excel_value:,.2f} (diff=${value_diff_std:.4f})")
    else:
        qa.add_fail(f"{file_key}_std_value", 
                   f"Excel=${excel_value:,.2f}, DB_STD=${db_stats['std_value']:,.2f}, diff=${value_diff_std:.2f}")
    
    # 4. Value check - Ledger
    value_diff_ledger = abs(excel_value - db_stats['ledger_value'])
    if value_diff_ledger <= VALUE_TOLERANCE:
        qa.add_pass(f"{file_key}_ledger_value", f"${excel_value:,.2f} (diff=${value_diff_ledger:.4f})")
    else:
        qa.add_fail(f"{file_key}_ledger_value", 
                   f"Excel=${excel_value:,.2f}, DB_LEDGER=${db_stats['ledger_value']:,.2f}, diff=${value_diff_ledger:.2f}")
    
    # Print summary
    print(f"  Excel: {excel_rows} rows, ${excel_value:,.2f}")
    print(f"  DB STD: {db_stats['std_rows']} rows, ${db_stats['std_value']:,.2f}")
    print(f"  DB Ledger: {db_stats['ledger_rows']} rows, ${db_stats['ledger_value']:,.2f}")


def validate_key_buyers(db: DatabaseManager, qa: KenyaQAResult):
    """Validate key buyers exist and have correct values"""
    print(f"\n--- Validating Key Buyers ---")
    
    for buyer in KEY_BUYERS_IMPORT:
        buyer_stats = get_buyer_stats_from_db(db, buyer['search_pattern'])
        
        if buyer_stats is None:
            qa.add_fail(f"buyer_{buyer['search_pattern']}_exists", 
                       f"{buyer['name']} NOT FOUND in ledger")
            continue
        
        # Check value in range
        if buyer['expected_value_min'] <= buyer_stats['total_value'] <= buyer['expected_value_max']:
            qa.add_pass(f"buyer_{buyer['search_pattern']}_value", 
                       f"${buyer_stats['total_value']:,.2f} (expected ${buyer['expected_value_min']:,}-${buyer['expected_value_max']:,})")
        else:
            qa.add_fail(f"buyer_{buyer['search_pattern']}_value", 
                       f"${buyer_stats['total_value']:,.2f} not in range ${buyer['expected_value_min']:,}-${buyer['expected_value_max']:,}")
        
        # Check shipment count
        if buyer_stats['shipments'] == buyer['expected_shipments']:
            qa.add_pass(f"buyer_{buyer['search_pattern']}_shipments", 
                       f"{buyer_stats['shipments']} shipments")
        else:
            qa.add_fail(f"buyer_{buyer['search_pattern']}_shipments", 
                       f"DB={buyer_stats['shipments']}, Expected={buyer['expected_shipments']}")
        
        print(f"  {buyer_stats['buyer_name']}: ${buyer_stats['total_value']:,.2f}, {buyer_stats['shipments']} shipments")


def validate_hs_690721_totals(db: DatabaseManager, qa: KenyaQAResult):
    """Validate HS 690721 (tiles) totals for Kenya imports"""
    print(f"\n--- Validating HS 690721 (Tiles) ---")
    
    # Load Excel to get expected totals
    df = pd.read_excel(KENYA_FILES['import_short']['path'], header=0)
    
    # Filter for HS 690721
    hs_690721_rows = df[df['HS_CODE'].astype(str).str.startswith('690721')]
    excel_count = len(hs_690721_rows)
    excel_value = hs_690721_rows['TOTALVALUEUSD'].sum()
    excel_buyers = hs_690721_rows['IMPORTER_NAME'].nunique()
    
    # Get DB stats
    db_result = db.execute_query("""
        SELECT 
            COUNT(*) as rows,
            COALESCE(SUM(customs_value_usd), 0) as total_value,
            COUNT(DISTINCT buyer_uuid) as buyers
        FROM global_trades_ledger
        WHERE hs_code_6 = '690721'
        AND destination_country = 'KENYA'
        AND source_file = 'Kenya Import S.xlsx'
    """)
    
    db_rows = db_result[0][0] if db_result else 0
    db_value = float(db_result[0][1]) if db_result else 0.0
    db_buyers = db_result[0][2] if db_result else 0
    
    # Row count check
    if excel_count == db_rows:
        qa.add_pass("hs_690721_row_count", f"{excel_count} rows")
    else:
        qa.add_fail("hs_690721_row_count", f"Excel={excel_count}, DB={db_rows}")
    
    # Value check
    value_diff = abs(excel_value - db_value)
    if value_diff <= VALUE_TOLERANCE:
        qa.add_pass("hs_690721_value", f"${excel_value:,.2f}")
    else:
        qa.add_fail("hs_690721_value", f"Excel=${excel_value:,.2f}, DB=${db_value:,.2f}, diff=${value_diff:.2f}")
    
    # Buyer count check
    if excel_buyers == db_buyers:
        qa.add_pass("hs_690721_buyer_count", f"{excel_buyers} unique buyers")
    else:
        qa.add_fail("hs_690721_buyer_count", f"Excel={excel_buyers}, DB={db_buyers}")
    
    print(f"  Excel: {excel_count} rows, ${excel_value:,.2f}, {excel_buyers} buyers")
    print(f"  DB: {db_rows} rows, ${db_value:,.2f}, {db_buyers} buyers")


def main():
    print("=" * 70)
    print("KENYA PORT DATA 100% ACCURACY QA")
    print("=" * 70)
    
    qa = KenyaQAResult()
    db = DatabaseManager('config/db_config.yml')
    
    try:
        # Validate each file
        for file_key, file_config in KENYA_FILES.items():
            validate_file(db, file_key, file_config, qa)
        
        # Validate key buyers
        validate_key_buyers(db, qa)
        
        # Validate HS 690721 specifically
        validate_hs_690721_totals(db, qa)
        
    finally:
        db.close()
    
    # Summary
    print("\n" + "=" * 70)
    print(f"QA SUMMARY: {qa.passed} passed, {qa.failed} failed")
    print("=" * 70)
    
    if qa.failed > 0:
        print("\nFAILED TESTS:")
        for test_name, details in qa.errors:
            print(f"  - {test_name}: {details}")
        print("\n❌ KENYA QA FAILED - Fix issues before proceeding")
        return 1
    else:
        print("\n✅ KENYA QA PASSED - All values match within tolerance")
        return 0


if __name__ == "__main__":
    sys.exit(main())
