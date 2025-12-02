"""
QA Tool: Basic Country Data Verification
==========================================
Simple, trustworthy script to verify Excel -> DB data accuracy.

Usage:
    python scripts/qa_country_basic_check.py --country KENYA --direction IMPORT --hs 690721

Features:
- Loads Excel file
- Extracts top N buyers
- Compares against stg_shipments_standardized
- Compares against global_trades_ledger
- Reports exact matches and mismatches

Design Principles:
- Simple SQL with exact matching (no fuzzy LIKE)
- Validate against known buyers first
- Show sample rows for any mismatch
"""

import argparse
import sys
import pandas as pd
import psycopg2
from pathlib import Path
from typing import List, Dict, Tuple

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aaziko_trade',
    'user': 'postgres',
    'password': 'Test@123'
}

# File mapping
FILE_MAP = {
    ('KENYA', 'IMPORT'): 'data/reference/port_real/Kenya Import S.xlsx',
    ('KENYA', 'EXPORT'): 'data/reference/port_real/Kenya Export S.xlsx',
}

COLUMN_MAP = {
    'buyer': ['IMPORTER_NAME', 'BUYER_NAME', 'CONSIGNEE_NAME'],
    'value': ['TOTALVALUEUSD', 'TOTALVALUE', 'VALUE_USD', 'CIF_USD'],
    'hs': ['HS_CODE', 'HS6', 'HS_CODE_6']
}


def find_column(df: pd.DataFrame, col_type: str) -> str:
    """Find actual column name from possible variants."""
    df_cols_upper = [c.upper() for c in df.columns]
    for variant in COLUMN_MAP[col_type]:
        if variant in df_cols_upper:
            idx = df_cols_upper.index(variant)
            return df.columns[idx]
    raise ValueError(f"Could not find {col_type} column in {list(df.columns)}")


def load_excel_data(country: str, direction: str, hs_code: str = None, top_n: int = 10) -> List[Dict]:
    """Load and aggregate Excel data for top N buyers."""

    file_key = (country.upper(), direction.upper())
    if file_key not in FILE_MAP:
        raise ValueError(f"No Excel file configured for {file_key}")

    file_path = FILE_MAP[file_key]
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    print(f"[1/4] Loading Excel: {file_path}")
    df = pd.read_excel(file_path)
    df.columns = df.columns.str.strip().str.upper()

    # Find columns
    buyer_col = find_column(df, 'buyer')
    value_col = find_column(df, 'value')
    hs_col = find_column(df, 'hs')

    # Filter by HS if specified
    if hs_code:
        df = df[df[hs_col].astype(str).str.startswith(hs_code)]

    print(f"      Rows: {len(df)}")
    print(f"      Buyer col: {buyer_col}")
    print(f"      Value col: {value_col}")

    # Aggregate by buyer
    buyer_stats = df.groupby(buyer_col).agg({
        value_col: 'sum',
        hs_col: 'count'
    }).rename(columns={value_col: 'excel_total_usd', hs_col: 'excel_shipments'})

    buyer_stats = buyer_stats.sort_values('excel_total_usd', ascending=False).head(top_n)

    results = []
    for buyer_name, row in buyer_stats.iterrows():
        results.append({
            'buyer_name_excel': str(buyer_name).strip(),
            'excel_total_usd': float(row['excel_total_usd']),
            'excel_shipments': int(row['excel_shipments'])
        })

    return results


def verify_standardized(conn, buyers: List[Dict], country: str, direction: str, hs_code: str = None) -> None:
    """Verify buyers in stg_shipments_standardized."""

    print(f"\n[2/4] Verifying in stg_shipments_standardized...")
    cur = conn.cursor()

    for buyer_data in buyers:
        buyer_name = buyer_data['buyer_name_excel'].upper()

        # Build query with exact match
        query = """
            SELECT
                buyer_name_raw,
                buyer_uuid,
                COUNT(*) as shipment_count,
                SUM(customs_value_usd) as total_value_usd
            FROM stg_shipments_standardized
            WHERE reporting_country = %s
            AND direction = %s
            AND UPPER(buyer_name_raw) = %s
        """

        params = [country.upper(), direction.upper(), buyer_name]

        if hs_code:
            query += " AND hs_code_6 = %s"
            params.append(hs_code)

        query += " GROUP BY buyer_name_raw, buyer_uuid"

        cur.execute(query, params)
        result = cur.fetchone()

        if result:
            buyer_data['std_buyer_name'] = result[0]
            buyer_data['std_buyer_uuid'] = str(result[1])
            buyer_data['std_shipments'] = result[2]
            buyer_data['std_total_usd'] = float(result[3])
            buyer_data['std_status'] = 'FOUND'

            # Check for mismatches
            value_diff = abs(buyer_data['excel_total_usd'] - buyer_data['std_total_usd'])
            shipment_diff = abs(buyer_data['excel_shipments'] - buyer_data['std_shipments'])

            if value_diff > 0.01:
                buyer_data['std_status'] = 'VALUE_MISMATCH'
            elif shipment_diff > 0:
                buyer_data['std_status'] = 'COUNT_MISMATCH'
            else:
                buyer_data['std_status'] = 'OK'
        else:
            buyer_data['std_status'] = 'NOT_FOUND'
            buyer_data['std_buyer_name'] = None
            buyer_data['std_buyer_uuid'] = None
            buyer_data['std_shipments'] = 0
            buyer_data['std_total_usd'] = 0.0


def verify_ledger(conn, buyers: List[Dict], country: str, hs_code: str = None) -> None:
    """Verify buyers in global_trades_ledger."""

    print(f"\n[3/4] Verifying in global_trades_ledger...")
    cur = conn.cursor()

    for buyer_data in buyers:
        if not buyer_data.get('std_buyer_uuid'):
            buyer_data['ledger_status'] = 'NO_UUID'
            buyer_data['ledger_shipments'] = 0
            buyer_data['ledger_total_usd'] = 0.0
            continue

        # Query ledger by UUID
        query = """
            SELECT
                COUNT(*) as shipment_count,
                SUM(customs_value_usd) as total_value_usd
            FROM global_trades_ledger
            WHERE buyer_uuid = %s
            AND destination_country = %s
        """

        params = [buyer_data['std_buyer_uuid'], country.upper()]

        if hs_code:
            query += " AND hs_code_6 = %s"
            params.append(hs_code)

        cur.execute(query, params)
        result = cur.fetchone()

        if result and result[0] > 0:
            buyer_data['ledger_shipments'] = result[0]
            buyer_data['ledger_total_usd'] = float(result[1])

            # Check for mismatches
            value_diff = abs(buyer_data['excel_total_usd'] - buyer_data['ledger_total_usd'])
            shipment_diff = abs(buyer_data['excel_shipments'] - buyer_data['ledger_shipments'])

            if value_diff > 0.01:
                buyer_data['ledger_status'] = 'VALUE_MISMATCH'
            elif shipment_diff > 0:
                buyer_data['ledger_status'] = 'COUNT_MISMATCH'
            else:
                buyer_data['ledger_status'] = 'OK'
        else:
            buyer_data['ledger_status'] = 'NOT_FOUND'
            buyer_data['ledger_shipments'] = 0
            buyer_data['ledger_total_usd'] = 0.0


def print_report(buyers: List[Dict]) -> None:
    """Print comparison report."""

    print(f"\n[4/4] COMPARISON REPORT")
    print("="*120)
    print(f"{'Buyer Name':<40} {'Excel $':<15} {'Std $':<15} {'Ledger $':<15} {'Status':<20}")
    print("-"*120)

    for b in buyers:
        excel_val = f"${b['excel_total_usd']:,.0f}"
        std_val = f"${b['std_total_usd']:,.0f}" if b.get('std_total_usd') else 'N/A'
        ledger_val = f"${b['ledger_total_usd']:,.0f}" if b.get('ledger_total_usd') else 'N/A'

        # Determine overall status
        if b['std_status'] == 'OK' and b.get('ledger_status') == 'OK':
            status = '[OK]'
        elif b['std_status'] == 'NOT_FOUND':
            status = '[MISSING_STD]'
        elif b.get('ledger_status') == 'NOT_FOUND':
            status = '[MISSING_LEDGER]'
        elif b['std_status'] == 'VALUE_MISMATCH' or b.get('ledger_status') == 'VALUE_MISMATCH':
            status = '[VALUE_DIFF]'
        elif b['std_status'] == 'COUNT_MISMATCH' or b.get('ledger_status') == 'COUNT_MISMATCH':
            status = '[COUNT_DIFF]'
        else:
            status = '[CHECK]'

        buyer_short = b['buyer_name_excel'][:38] if len(b['buyer_name_excel']) > 38 else b['buyer_name_excel']
        print(f"{buyer_short:<40} {excel_val:<15} {std_val:<15} {ledger_val:<15} {status:<20}")

    # Summary
    print("\nSUMMARY:")
    ok_count = sum(1 for b in buyers if b['std_status'] == 'OK' and b.get('ledger_status') == 'OK')
    print(f"  Total buyers checked: {len(buyers)}")
    print(f"  Perfect matches: {ok_count}")
    print(f"  Issues found: {len(buyers) - ok_count}")


def main():
    parser = argparse.ArgumentParser(description='QA Country Data Verification')
    parser.add_argument('--country', required=True, help='Country name (e.g. KENYA)')
    parser.add_argument('--direction', required=True, choices=['IMPORT', 'EXPORT'], help='Trade direction')
    parser.add_argument('--hs', help='HS code filter (e.g. 690721)')
    parser.add_argument('--top', type=int, default=10, help='Number of top buyers to check (default: 10)')

    args = parser.parse_args()

    print("="*120)
    print("QA COUNTRY BASIC CHECK")
    print("="*120)
    print(f"Country: {args.country}")
    print(f"Direction: {args.direction}")
    print(f"HS Code: {args.hs or 'ALL'}")
    print(f"Top N: {args.top}")
    print()

    try:
        # Load Excel
        buyers = load_excel_data(args.country, args.direction, args.hs, args.top)

        # Connect to DB
        conn = psycopg2.connect(**DB_CONFIG)

        # Verify standardized
        verify_standardized(conn, buyers, args.country, args.direction, args.hs)

        # Verify ledger
        verify_ledger(conn, buyers, args.country, args.hs)

        # Print report
        print_report(buyers)

        conn.close()

        # Exit code based on results
        issues = sum(1 for b in buyers if not (b['std_status'] == 'OK' and b.get('ledger_status') == 'OK'))
        sys.exit(1 if issues > 0 else 0)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == '__main__':
    main()
