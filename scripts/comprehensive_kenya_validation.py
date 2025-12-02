"""
COMPREHENSIVE KENYA DATA VALIDATION
====================================
Ground truth validation from Excel → Database → API

Validates:
- Excel file totals
- All database layers (raw, standardized, organizations, ledger, profiles)
- API responses (Buyer Hunter, Buyer 360)
- Data accuracy at every stage
"""

import pandas as pd
import psycopg2
import json
import os
from collections import defaultdict
from decimal import Decimal
import requests
from typing import Dict, List, Any, Tuple

# Database credentials
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aaziko_trade',
    'user': 'postgres',
    'password': 'Test@123'
}

# File paths
KENYA_FILES = {
    'import_s': 'E:/Port Data Brain/data/reference/port_real/Kenya Import S.xlsx',
    'import_f': 'E:/Port Data Brain/data/reference/port_real/Kenya Import F.xlsx',
    'export_s': 'E:/Port Data Brain/data/reference/port_real/Kenya Export S.xlsx',
    'export_f': 'E:/Port Data Brain/data/reference/port_real/Kenya Export F.xlsx'
}

# API base URL
API_BASE = "http://localhost:8000/api/v1"

class ValidationReport:
    def __init__(self):
        self.buyers = {}
        self.issues = []

    def add_buyer(self, buyer_name: str, data: dict):
        if buyer_name not in self.buyers:
            self.buyers[buyer_name] = data
        else:
            # Merge data
            for key, value in data.items():
                if key in self.buyers[buyer_name]:
                    if isinstance(value, (int, float)):
                        self.buyers[buyer_name][key] += value
                    elif isinstance(value, list):
                        self.buyers[buyer_name][key].extend(value)
                else:
                    self.buyers[buyer_name][key] = value

    def add_issue(self, buyer_name: str, issue_type: str, details: str):
        self.issues.append({
            'buyer_name': buyer_name,
            'issue_type': issue_type,
            'details': details
        })

    def to_dataframe(self):
        rows = []
        for buyer_name, data in self.buyers.items():
            rows.append(data)
        return pd.DataFrame(rows)


def load_excel_data(file_path: str, file_type: str) -> pd.DataFrame:
    """Load Excel file and extract relevant columns."""
    print(f"\nLoading {file_path}...")

    try:
        # Read Excel
        df = pd.read_excel(file_path)
        print(f"  Loaded {len(df)} rows")
        print(f"  Columns: {list(df.columns)[:10]}...")  # Show first 10 columns

        # Standardize column names
        df.columns = df.columns.str.strip().str.upper()

        return df
    except Exception as e:
        print(f"  ERROR loading file: {e}")
        return pd.DataFrame()


def extract_buyer_data_from_excel(df: pd.DataFrame, file_key: str) -> Dict[str, dict]:
    """Extract buyer data from Excel DataFrame."""
    buyers = defaultdict(lambda: {
        'excel_shipments': 0,
        'excel_total_usd': 0.0,
        'excel_hs_codes': set(),
        'excel_origin_countries': set(),
        'excel_suppliers': set(),
        'excel_months': set(),
        'excel_files': []
    })

    # Map column names (handle variations)
    buyer_col = None
    value_col = None
    hs_col = None
    origin_col = None
    supplier_col = None
    date_col = None

    # Find buyer column
    for col in df.columns:
        if 'IMPORTER' in col or 'BUYER' in col or 'CONSIGNEE' in col:
            buyer_col = col
            break

    # Find value column
    for col in df.columns:
        if 'VALUEUSD' in col or ('VALUE' in col and 'USD' in col):
            value_col = col
            break
        elif 'CIF' in col and 'USD' in col:
            value_col = col
            break
        elif 'TOTALVALUE' in col:
            value_col = col
            break
        elif 'VALUE' in col:
            value_col = col
            break

    # Find HS code column
    for col in df.columns:
        if 'HS' in col or 'HSCODE' in col:
            hs_col = col
            break

    # Find origin column
    for col in df.columns:
        if 'ORIGIN' in col or 'COUNTRY' in col and 'ORIGIN' in col:
            origin_col = col
            break

    # Find supplier column
    for col in df.columns:
        if 'SUPPLIER' in col or 'EXPORTER' in col or 'SHIPPER' in col:
            supplier_col = col
            break

    # Find date column
    for col in df.columns:
        if 'DATE' in col or 'MONTH' in col:
            date_col = col
            break

    print(f"  Detected columns:")
    print(f"    Buyer: {buyer_col}")
    print(f"    Value: {value_col}")
    print(f"    HS Code: {hs_col}")
    print(f"    Origin: {origin_col}")
    print(f"    Supplier: {supplier_col}")
    print(f"    Date: {date_col}")

    if not buyer_col or not value_col:
        print("  WARNING: Could not detect buyer or value column!")
        return {}

    # Process rows
    for idx, row in df.iterrows():
        buyer_name = str(row.get(buyer_col, '')).strip().upper()
        if not buyer_name or buyer_name == 'NAN' or buyer_name == '':
            continue

        value = row.get(value_col, 0)
        try:
            value = float(value)
        except:
            value = 0.0

        buyers[buyer_name]['excel_shipments'] += 1
        buyers[buyer_name]['excel_total_usd'] += value
        buyers[buyer_name]['excel_files'].append(file_key)

        if hs_col and pd.notna(row.get(hs_col)):
            hs_code = str(row.get(hs_col)).strip()
            buyers[buyer_name]['excel_hs_codes'].add(hs_code)

        if origin_col and pd.notna(row.get(origin_col)):
            origin = str(row.get(origin_col)).strip().upper()
            buyers[buyer_name]['excel_origin_countries'].add(origin)

        if supplier_col and pd.notna(row.get(supplier_col)):
            supplier = str(row.get(supplier_col)).strip().upper()
            buyers[buyer_name]['excel_suppliers'].add(supplier)

        if date_col and pd.notna(row.get(date_col)):
            date_val = str(row.get(date_col))
            buyers[buyer_name]['excel_months'].add(date_val)

    print(f"  Found {len(buyers)} unique buyers")
    return dict(buyers)


def query_database_layer(conn, buyer_name: str, layer: str) -> dict:
    """Query a specific database layer for a buyer."""
    cur = conn.cursor()
    result = {}

    try:
        if layer == 'raw':
            # stg_shipments_raw
            cur.execute("""
                SELECT COUNT(*), raw_file_name
                FROM stg_shipments_raw
                WHERE reporting_country = 'KENYA'
                AND direction = 'IMPORT'
                AND UPPER(raw_data->>'IMPORTER_NAME') LIKE %s
                GROUP BY raw_file_name
            """, (f'%{buyer_name}%',))
            rows = cur.fetchall()
            result['raw_count'] = sum(r[0] for r in rows)
            result['raw_files'] = [r[1] for r in rows]

        elif layer == 'standardized':
            # stg_shipments_standardized
            cur.execute("""
                SELECT
                    COUNT(*),
                    SUM(customs_value_usd),
                    array_agg(DISTINCT hs_code_6),
                    array_agg(DISTINCT origin_country),
                    array_agg(DISTINCT supplier_name_raw)
                FROM stg_shipments_standardized
                WHERE reporting_country = 'KENYA'
                AND direction = 'IMPORT'
                AND UPPER(buyer_name_raw) = %s
            """, (buyer_name,))
            row = cur.fetchone()
            if row:
                result['std_count'] = row[0] or 0
                result['std_total_usd'] = float(row[1] or 0)
                result['std_hs_codes'] = [x for x in (row[2] or []) if x]
                result['std_origins'] = [x for x in (row[3] or []) if x]
                result['std_suppliers'] = [x for x in (row[4] or []) if x]

        elif layer == 'organizations':
            # organizations_master
            cur.execute("""
                SELECT org_uuid, name_normalized, org_type, country_iso
                FROM organizations_master
                WHERE UPPER(name_normalized) LIKE %s
                AND country_iso = 'KENYA'
            """, (f'%{buyer_name.split()[0]}%',))  # Match on first word
            rows = cur.fetchall()
            result['org_matches'] = [{
                'uuid': str(r[0]),
                'name': r[1],
                'type': r[2],
                'country': r[3]
            } for r in rows]

        elif layer == 'ledger':
            # global_trades_ledger via organizations_master
            cur.execute("""
                SELECT
                    gtl.buyer_uuid,
                    o.name_normalized,
                    COUNT(*),
                    SUM(gtl.customs_value_usd),
                    array_agg(DISTINCT gtl.hs_code_6),
                    array_agg(DISTINCT gtl.origin_country),
                    array_agg(DISTINCT gtl.supplier_name)
                FROM global_trades_ledger gtl
                JOIN organizations_master o ON gtl.buyer_uuid = o.org_uuid
                WHERE gtl.destination_country = 'KENYA'
                AND UPPER(o.name_normalized) LIKE %s
                GROUP BY gtl.buyer_uuid, o.name_normalized
            """, (f'%{buyer_name.split()[0]}%',))
            rows = cur.fetchall()
            result['ledger_entries'] = [{
                'uuid': str(r[0]),
                'name': r[1],
                'count': r[2],
                'total_usd': float(r[3] or 0),
                'hs_codes': [x for x in (r[4] or []) if x],
                'origins': [x for x in (r[5] or []) if x],
                'suppliers': [x for x in (r[6] or []) if x]
            } for r in rows]

    except Exception as e:
        result['error'] = str(e)

    return result


def query_api(endpoint: str, params: dict = None) -> dict:
    """Query API endpoint."""
    try:
        url = f"{API_BASE}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"HTTP {response.status_code}"}
    except Exception as e:
        return {'error': str(e)}


def validate_all_buyers():
    """Main validation function."""
    print("="*70)
    print("COMPREHENSIVE KENYA DATA VALIDATION")
    print("="*70)

    report = ValidationReport()

    # Step 1: Load all Excel files
    print("\n[STEP 1] Loading Excel Files")
    print("-" * 70)

    all_excel_buyers = {}
    for file_key, file_path in KENYA_FILES.items():
        if not os.path.exists(file_path):
            print(f"WARNING: File not found: {file_path}")
            continue

        df = load_excel_data(file_path, file_key)
        if df.empty:
            continue

        buyers = extract_buyer_data_from_excel(df, file_key)

        # Merge with all_excel_buyers
        for buyer_name, data in buyers.items():
            if buyer_name not in all_excel_buyers:
                all_excel_buyers[buyer_name] = data
            else:
                # Merge data
                all_excel_buyers[buyer_name]['excel_shipments'] += data['excel_shipments']
                all_excel_buyers[buyer_name]['excel_total_usd'] += data['excel_total_usd']
                all_excel_buyers[buyer_name]['excel_hs_codes'].update(data['excel_hs_codes'])
                all_excel_buyers[buyer_name]['excel_origin_countries'].update(data['excel_origin_countries'])
                all_excel_buyers[buyer_name]['excel_suppliers'].update(data['excel_suppliers'])
                all_excel_buyers[buyer_name]['excel_months'].update(data['excel_months'])
                all_excel_buyers[buyer_name]['excel_files'].extend(data['excel_files'])

    print(f"\n[SUMMARY] Found {len(all_excel_buyers)} unique buyers across all Excel files")
    print(f"Total Excel shipments: {sum(b['excel_shipments'] for b in all_excel_buyers.values())}")
    print(f"Total Excel value: ${sum(b['excel_total_usd'] for b in all_excel_buyers.values()):,.2f}")

    # Step 2: Connect to database
    print("\n[STEP 2] Connecting to Database")
    print("-" * 70)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("[OK] Database connection successful")
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return

    # Step 3: Validate each buyer across all layers
    print("\n[STEP 3] Validating Buyers Across All Layers")
    print("-" * 70)

    validation_results = []

    for idx, (buyer_name, excel_data) in enumerate(all_excel_buyers.items(), 1):
        print(f"\n[{idx}/{len(all_excel_buyers)}] {buyer_name}")
        print(f"  Excel: {excel_data['excel_shipments']} shipments, ${excel_data['excel_total_usd']:,.2f}")

        result = {
            'buyer_name_excel': buyer_name,
            'excel_total_usd': excel_data['excel_total_usd'],
            'excel_shipments': excel_data['excel_shipments'],
            'excel_hs_codes': ', '.join(sorted(excel_data['excel_hs_codes'])),
            'excel_origin_countries': ', '.join(sorted(excel_data['excel_origin_countries'])),
            'excel_suppliers': ', '.join(sorted(list(excel_data['excel_suppliers']))[:5]),  # Top 5
            'excel_files': ', '.join(excel_data['excel_files']),
        }

        # Query standardized layer
        std_data = query_database_layer(conn, buyer_name, 'standardized')
        result['std_count'] = std_data.get('std_count', 0)
        result['std_total_usd'] = std_data.get('std_total_usd', 0.0)
        result['std_hs_codes'] = ', '.join(std_data.get('std_hs_codes', []))

        # Check if in standardized
        if result['std_count'] == 0:
            result['issues'] = 'MISSING_FROM_STANDARDIZED'
            report.add_issue(buyer_name, 'MISSING_FROM_STANDARDIZED',
                           f"Buyer in Excel but not in stg_shipments_standardized")
        else:
            # Check value match
            diff = abs(result['excel_total_usd'] - result['std_total_usd'])
            if diff > 0.01:
                result['issues'] = result.get('issues', '') + '; WRONG_VALUE_STANDARDIZED'
                report.add_issue(buyer_name, 'WRONG_VALUE',
                               f"Excel: ${result['excel_total_usd']:,.2f}, Std: ${result['std_total_usd']:,.2f}, Diff: ${diff:,.2f}")

        # Query organizations
        org_data = query_database_layer(conn, buyer_name, 'organizations')
        org_matches = org_data.get('org_matches', [])
        result['org_matches_count'] = len(org_matches)

        if len(org_matches) == 0:
            result['uuid'] = 'NOT_FOUND'
            result['buyer_name_normalized'] = 'NOT_FOUND'
            result['issues'] = result.get('issues', '') + '; MISSING_FROM_ORGANIZATIONS'
            report.add_issue(buyer_name, 'MISSING_FROM_ORGANIZATIONS',
                           f"No UUID assigned in organizations_master")
        elif len(org_matches) > 1:
            result['uuid'] = '; '.join([m['uuid'] for m in org_matches])
            result['buyer_name_normalized'] = '; '.join([m['name'] for m in org_matches])
            result['issues'] = result.get('issues', '') + '; DUPLICATE_UUIDS'
            report.add_issue(buyer_name, 'DUPLICATE_BUYER',
                           f"Multiple UUIDs found: {len(org_matches)}")
        else:
            result['uuid'] = org_matches[0]['uuid']
            result['buyer_name_normalized'] = org_matches[0]['name']

        # Query ledger
        ledger_data = query_database_layer(conn, buyer_name, 'ledger')
        ledger_entries = ledger_data.get('ledger_entries', [])

        if len(ledger_entries) == 0:
            result['ledger_count'] = 0
            result['ledger_total_usd'] = 0.0
            result['issues'] = result.get('issues', '') + '; MISSING_FROM_LEDGER'
            report.add_issue(buyer_name, 'MISSING_FROM_LEDGER',
                           f"Not found in global_trades_ledger")
        else:
            result['ledger_count'] = sum(e['count'] for e in ledger_entries)
            result['ledger_total_usd'] = sum(e['total_usd'] for e in ledger_entries)
            result['ledger_hs_codes'] = ', '.join(set([h for e in ledger_entries for h in e.get('hs_codes', [])]))
            result['ledger_origins'] = ', '.join(set([o for e in ledger_entries for o in e.get('origins', [])]))

            # Check value match
            diff = abs(result['excel_total_usd'] - result['ledger_total_usd'])
            if diff > 0.01:
                result['issues'] = result.get('issues', '') + '; WRONG_VALUE_LEDGER'
                report.add_issue(buyer_name, 'WRONG_VALUE',
                               f"Excel: ${result['excel_total_usd']:,.2f}, Ledger: ${result['ledger_total_usd']:,.2f}, Diff: ${diff:,.2f}")

        # Query Buyer Hunter API (if UUID exists)
        if result.get('uuid') and result['uuid'] != 'NOT_FOUND':
            # Try search by name
            bh_data = query_api('buyer-hunter/search-by-name', {
                'buyer_name': buyer_name.split()[0],  # First word
                'hs_code_6': '690721',  # Common HS code
                'destination_countries': 'KENYA'
            })

            if 'items' in bh_data and len(bh_data['items']) > 0:
                # Find matching buyer
                match = None
                for item in bh_data['items']:
                    if item['buyer_uuid'] == result['uuid']:
                        match = item
                        break

                if match:
                    result['buyer_hunter_value'] = match.get('total_value_usd_12m', 0)
                    result['buyer_hunter_shipments'] = match.get('total_shipments_12m', 0)
                    result['buyer_hunter_score'] = match.get('opportunity_score', 0)
                    result['appears_in_buyer_hunter'] = 'TRUE'
                else:
                    result['appears_in_buyer_hunter'] = 'FALSE'
                    result['issues'] = result.get('issues', '') + '; MISSING_FROM_BUYER_HUNTER'
            else:
                result['appears_in_buyer_hunter'] = 'FALSE'

        # Query Buyer 360 API
        if result.get('uuid') and result['uuid'] != 'NOT_FOUND':
            b360_data = query_api(f'buyers/{result["uuid"]}/360')

            if 'buyer_uuid' in b360_data:
                result['buyer360_total_usd'] = b360_data.get('total_value_usd', 0)
                result['buyer360_shipments'] = b360_data.get('total_shipments', 0)
                result['appears_in_360'] = 'TRUE'
            else:
                result['appears_in_360'] = 'FALSE'
                result['issues'] = result.get('issues', '') + '; MISSING_FROM_360'

        # Final match check
        if not result.get('issues'):
            result['issues'] = 'OK'
            result['matches_excel'] = 'TRUE'
        else:
            result['matches_excel'] = 'FALSE'

        validation_results.append(result)

        print(f"    Std: {result.get('std_count', 0)} rows, ${result.get('std_total_usd', 0):,.2f}")
        print(f"    UUID: {result.get('uuid', 'NOT_FOUND')}")
        print(f"    Ledger: {result.get('ledger_count', 0)} rows, ${result.get('ledger_total_usd', 0):,.2f}")
        print(f"    Issues: {result.get('issues', 'None')}")

    conn.close()

    # Step 4: Generate report
    print("\n[STEP 4] Generating Report")
    print("-" * 70)

    df_report = pd.DataFrame(validation_results)

    # Save to Excel
    output_file = 'E:/Port Data Brain/KENYA_VALIDATION_REPORT.xlsx'
    df_report.to_excel(output_file, index=False, engine='openpyxl')
    print(f"[OK] Report saved to: {output_file}")

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    total_buyers = len(validation_results)
    buyers_ok = len([r for r in validation_results if r.get('issues') == 'OK'])
    buyers_with_issues = total_buyers - buyers_ok

    print(f"Total buyers validated: {total_buyers}")
    print(f"Buyers with NO issues: {buyers_ok} ({buyers_ok/total_buyers*100:.1f}%)")
    print(f"Buyers WITH issues: {buyers_with_issues} ({buyers_with_issues/total_buyers*100:.1f}%)")

    # Issue breakdown
    print(f"\nIssue Breakdown:")
    issue_counts = defaultdict(int)
    for r in validation_results:
        issues = r.get('issues', '').split(';')
        for issue in issues:
            issue = issue.strip()
            if issue and issue != 'OK':
                issue_counts[issue] += 1

    for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {issue}: {count}")

    print("\n" + "="*70)
    print(f"Full report: {output_file}")
    print("="*70)


if __name__ == '__main__':
    validate_all_buyers()
