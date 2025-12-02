"""
FINAL KENYA VALIDATION REPORT
==============================
Cross-validates Excel files against all database layers
Properly handles IMPORT vs EXPORT data
"""

import pandas as pd
import psycopg2
import requests
import os
from collections import defaultdict

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'aaziko_trade',
    'user': 'postgres',
    'password': 'Test@123'
}

API_BASE = "http://localhost:8000/api/v1"

def main():
    print("="*80)
    print("FINAL KENYA VALIDATION REPORT")
    print("="*80)

    # Connect to DB
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Load Kenya Import S (the main file with 1000 rows)
    print("\n[1] Loading Kenya Import S.xlsx...")
    df_import = pd.read_excel('E:/Port Data Brain/data/reference/port_real/Kenya Import S.xlsx')
    df_import.columns = df_import.columns.str.strip().str.upper()

    print(f"    Excel rows: {len(df_import)}")
    print(f"    Excel columns: {list(df_import.columns)[:5]}...")

    # Group by buyer
    buyer_col = 'IMPORTER_NAME'
    value_col = 'TOTALVALUEUSD'
    hs_col = 'HS_CODE'
    origin_col = 'ORIGIN_COUNTRY'
    supplier_col = 'SUPPLIER_NAME'

    excel_buyers = defaultdict(lambda: {
        'excel_shipments': 0,
        'excel_total_usd': 0.0,
        'excel_hs_codes': set(),
        'excel_origins': set(),
        'excel_suppliers': set()
    })

    for idx, row in df_import.iterrows():
        buyer = str(row[buyer_col]).strip().upper()
        if not buyer or buyer == 'NAN':
            continue

        value = float(row[value_col]) if pd.notna(row[value_col]) else 0.0
        excel_buyers[buyer]['excel_shipments'] += 1
        excel_buyers[buyer]['excel_total_usd'] += value

        if pd.notna(row[hs_col]):
            excel_buyers[buyer]['excel_hs_codes'].add(str(row[hs_col]))
        if pd.notna(row[origin_col]):
            excel_buyers[buyer]['excel_origins'].add(str(row[origin_col]).upper())
        if pd.notna(row[supplier_col]):
            excel_buyers[buyer]['excel_suppliers'].add(str(row[supplier_col]).upper())

    print(f"    Unique buyers: {len(excel_buyers)}")
    print(f"    Total value: ${sum(b['excel_total_usd'] for b in excel_buyers.values()):,.2f}")

    # Query database for ALL Kenya imports
    print("\n[2] Querying database...")

    cur.execute("""
        SELECT
            UPPER(buyer_name_raw) as buyer_name,
            COUNT(*) as shipment_count,
            SUM(customs_value_usd) as total_value,
            array_agg(DISTINCT hs_code_6) as hs_codes,
            array_agg(DISTINCT origin_country) as origins,
            array_agg(DISTINCT supplier_name_raw) as suppliers
        FROM stg_shipments_standardized
        WHERE reporting_country = 'KENYA'
        AND direction = 'IMPORT'
        GROUP BY UPPER(buyer_name_raw)
    """)

    db_buyers = {}
    for row in cur.fetchall():
        db_buyers[row[0]] = {
            'db_shipments': row[1],
            'db_total_usd': float(row[2]) if row[2] else 0.0,
            'db_hs_codes': set([x for x in row[3] if x]),
            'db_origins': set([x for x in row[4] if x]),
            'db_suppliers': set([x for x in row[5] if x])
        }

    print(f"    DB buyers: {len(db_buyers)}")
    print(f"    DB total value: ${sum(b['db_total_usd'] for b in db_buyers.values()):,.2f}")

    # Cross-validate
    print("\n[3] Cross-validating...")

    results = []
    issues_summary = defaultdict(int)

    for buyer_name, excel_data in sorted(excel_buyers.items(), key=lambda x: x[1]['excel_total_usd'], reverse=True)[:50]:  # Top 50
        result = {
            'buyer_name': buyer_name,
            'excel_shipments': excel_data['excel_shipments'],
            'excel_total_usd': excel_data['excel_total_usd'],
            'excel_hs_codes': ', '.join(sorted(list(excel_data['excel_hs_codes']))[:3]),
            'excel_origins': ', '.join(sorted(excel_data['excel_origins'])),
        }

        # Check if in DB
        if buyer_name in db_buyers:
            db_data = db_buyers[buyer_name]
            result['db_shipments'] = db_data['db_shipments']
            result['db_total_usd'] = db_data['db_total_usd']
            result['db_hs_codes'] = ', '.join(sorted(list(db_data['db_hs_codes']))[:3])
            result['db_origins'] = ', '.join(sorted(db_data['db_origins']))
            result['difference_usd'] = result['excel_total_usd'] - result['db_total_usd']

            # Check match
            if abs(result['difference_usd']) < 0.01:
                result['value_match'] = 'OK'
            else:
                result['value_match'] = 'MISMATCH'
                issues_summary['WRONG_VALUE'] += 1

            if result['excel_shipments'] == result['db_shipments']:
                result['shipment_match'] = 'OK'
            else:
                result['shipment_match'] = 'MISMATCH'
                issues_summary['WRONG_SHIPMENT_COUNT'] += 1

            result['status'] = 'FOUND_IN_DB'
        else:
            result['db_shipments'] = 0
            result['db_total_usd'] = 0.0
            result['db_hs_codes'] = ''
            result['db_origins'] = ''
            result['difference_usd'] = result['excel_total_usd']
            result['value_match'] = 'MISSING'
            result['shipment_match'] = 'MISSING'
            result['status'] = 'MISSING_FROM_DB'
            issues_summary['MISSING_FROM_DB'] += 1

        # Query organizations_master
        cur.execute("""
            SELECT org_uuid, name_normalized
            FROM organizations_master
            WHERE UPPER(name_normalized) = ANY(%s)
            AND country_iso = 'KENYA'
        """, ([buyer_name] + buyer_name.split()[:2],))  # Try exact + first 2 words

        org_rows = cur.fetchall()
        if org_rows:
            result['uuid'] = str(org_rows[0][0])
            result['name_normalized'] = org_rows[0][1]

            # Query ledger
            cur.execute("""
                SELECT COUNT(*), SUM(customs_value_usd)
                FROM global_trades_ledger
                WHERE buyer_uuid = %s
                AND destination_country = 'KENYA'
            """, (org_rows[0][0],))
            ledger_row = cur.fetchone()
            if ledger_row:
                result['ledger_shipments'] = ledger_row[0]
                result['ledger_total_usd'] = float(ledger_row[1]) if ledger_row[1] else 0.0

            # Query Buyer Hunter API
            try:
                resp = requests.get(f"{API_BASE}/buyer-hunter/search-by-name", params={
                    'buyer_name': buyer_name.split()[0],
                    'hs_code_6': '690721',
                    'destination_countries': 'KENYA'
                }, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    match = next((item for item in data.get('items', []) if item['buyer_uuid'] == result['uuid']), None)
                    if match:
                        result['bh_score'] = match.get('opportunity_score')
                        result['bh_value'] = match.get('total_value_usd_12m')
                        result['appears_in_bh'] = 'YES'
                    else:
                        result['appears_in_bh'] = 'NO'
            except:
                result['appears_in_bh'] = 'API_ERROR'
        else:
            result['uuid'] = 'NOT_FOUND'
            result['name_normalized'] = ''
            result['ledger_shipments'] = 0
            result['ledger_total_usd'] = 0.0
            result['appears_in_bh'] = 'NO_UUID'
            if result['status'] == 'FOUND_IN_DB':
                issues_summary['MISSING_UUID'] += 1

        results.append(result)

    # Save report
    df_report = pd.DataFrame(results)
    output_file = 'E:/Port Data Brain/KENYA_FINAL_VALIDATION.xlsx'
    df_report.to_excel(output_file, index=False, engine='openpyxl')

    print(f"\n[OK] Report saved: {output_file}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    matched = len([r for r in results if r['status'] == 'FOUND_IN_DB'])
    missing = len([r for r in results if r['status'] == 'MISSING_FROM_DB'])

    print(f"Top 50 buyers validated:")
    print(f"  Found in DB: {matched}")
    print(f"  Missing from DB: {missing}")

    if issues_summary:
        print(f"\nIssues found:")
        for issue, count in sorted(issues_summary.items(), key=lambda x: x[1], reverse=True):
            print(f"  {issue}: {count}")

    # Show top 10 buyers
    print(f"\nTop 10 Buyers (by Excel value):")
    for idx, r in enumerate(results[:10], 1):
        status_icon = "[OK]" if r['status'] == 'FOUND_IN_DB' else "[MISSING]"
        print(f"  {idx}. {status_icon} {r['buyer_name']}")
        print(f"      Excel: {r['excel_shipments']} shipments, ${r['excel_total_usd']:,.2f}")
        if r['status'] == 'FOUND_IN_DB':
            print(f"      DB:    {r['db_shipments']} shipments, ${r['db_total_usd']:,.2f}")
            if r.get('uuid') and r['uuid'] != 'NOT_FOUND':
                print(f"      UUID:  {r['uuid']}")
                print(f"      BH:    {r.get('appears_in_bh', 'N/A')}")

    conn.close()

    print("\n" + "="*80)
    print(f"Full report: {output_file}")
    print("="*80)

if __name__ == '__main__':
    main()
