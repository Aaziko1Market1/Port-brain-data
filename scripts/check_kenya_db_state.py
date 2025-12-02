"""
Check current Kenya data state in database
"""
import sys
sys.path.insert(0, '.')

from etl.db_utils import DatabaseManager

def main():
    db = DatabaseManager('config/db_config.yml')
    
    print("=" * 70)
    print("KENYA DATA - DATABASE STATE")
    print("=" * 70)
    
    # File Registry
    print("\n1. FILE REGISTRY (Kenya files)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT file_name, status, total_rows, direction, source_format
        FROM file_registry 
        WHERE reporting_country = 'KENYA'
        ORDER BY file_name
    """)
    print(f"Total Kenya files in registry: {len(rows)}")
    for r in rows:
        print(f"  {r[0]}: status={r[1]}, rows={r[2]}, dir={r[3]}, fmt={r[4]}")
    
    # Raw staging
    print("\n2. STG_SHIPMENTS_RAW (Kenya)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT raw_file_name, COUNT(*) as rows, direction, source_format
        FROM stg_shipments_raw 
        WHERE reporting_country = 'KENYA'
        GROUP BY raw_file_name, direction, source_format
        ORDER BY raw_file_name
    """)
    print(f"Total Kenya raw entries by file: {len(rows)}")
    total_raw = 0
    for r in rows:
        print(f"  {r[0]}: {r[1]} rows, dir={r[2]}, fmt={r[3]}")
        total_raw += r[1]
    print(f"Total raw rows: {total_raw}")
    
    # Standardized staging
    print("\n3. STG_SHIPMENTS_STANDARDIZED (Kenya)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT source_file, COUNT(*) as rows, SUM(customs_value_usd) as total_value
        FROM stg_shipments_standardized 
        WHERE reporting_country = 'KENYA'
        GROUP BY source_file
        ORDER BY source_file
    """)
    print(f"Standardized files: {len(rows)}")
    total_std = 0
    total_value_std = 0
    for r in rows:
        val = r[2] or 0
        print(f"  {r[0]}: {r[1]} rows, ${val:,.2f}")
        total_std += r[1]
        total_value_std += val
    print(f"Total standardized rows: {total_std}")
    print(f"Total standardized value: ${total_value_std:,.2f}")
    
    # Global Trades Ledger
    print("\n4. GLOBAL_TRADES_LEDGER (Kenya)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT source_file, COUNT(*) as rows, SUM(customs_value_usd) as total_value, direction
        FROM global_trades_ledger 
        WHERE reporting_country = 'KENYA'
        GROUP BY source_file, direction
        ORDER BY source_file
    """)
    print(f"Ledger files: {len(rows)}")
    total_ledger = 0
    total_value_ledger = 0
    for r in rows:
        val = r[2] or 0
        print(f"  {r[0]}: {r[1]} rows, ${val:,.2f}, dir={r[3]}")
        total_ledger += r[1]
        total_value_ledger += val
    print(f"Total ledger rows: {total_ledger}")
    print(f"Total ledger value: ${total_value_ledger:,.2f}")
    
    # Buyers from Ledger for Kenya
    print("\n5. BUYER STATS from LEDGER (Kenya destination)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT 
            COUNT(DISTINCT buyer_uuid) as buyers, 
            SUM(customs_value_usd) as total_value,
            COUNT(*) as transactions
        FROM global_trades_ledger 
        WHERE destination_country = 'KENYA'
        AND buyer_uuid IS NOT NULL
    """)
    if rows:
        print(f"Total Kenya buyers (with UUID): {rows[0][0]}")
        print(f"Total buyer value: ${rows[0][1] or 0:,.2f}")
        print(f"Total transactions: {rows[0][2]}")
    
    # Check for DAVITA and MARBLE INN in ledger
    print("\n6. KEY BUYERS CHECK (from Ledger)")
    print("-" * 50)
    
    # DAVITA
    davita = db.execute_query("""
        SELECT 
            om.name_normalized as buyer_name, 
            SUM(g.customs_value_usd) as total_value,
            COUNT(*) as shipments,
            g.destination_country
        FROM global_trades_ledger g
        JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
        WHERE om.name_normalized ILIKE '%DAVITA%' 
        AND g.destination_country = 'KENYA'
        GROUP BY om.name_normalized, g.destination_country
    """)
    if davita:
        print(f"DAVITA found in ledger:")
        for d in davita:
            print(f"  {d[0]}: ${d[1]:,.2f}, {d[2]} shipments")
    else:
        print("DAVITA NOT FOUND in ledger for Kenya")
    
    # MARBLE INN
    marble = db.execute_query("""
        SELECT 
            om.name_normalized as buyer_name, 
            SUM(g.customs_value_usd) as total_value,
            COUNT(*) as shipments,
            g.destination_country
        FROM global_trades_ledger g
        JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
        WHERE om.name_normalized ILIKE '%MARBLE INN%' 
        AND g.destination_country = 'KENYA'
        GROUP BY om.name_normalized, g.destination_country
    """)
    if marble:
        print(f"MARBLE INN found in ledger:")
        for m in marble:
            print(f"  {m[0]}: ${m[1]:,.2f}, {m[2]} shipments")
    else:
        print("MARBLE INN NOT FOUND in ledger for Kenya")
    
    # Organizations master
    print("\n7. ORGANIZATIONS_MASTER (Kenya buyers)")
    print("-" * 50)
    rows = db.execute_query("""
        SELECT COUNT(*) FROM organizations_master 
        WHERE country_iso = 'KENYA' AND type IN ('BUYER', 'MIXED')
    """)
    print(f"Kenya organizations (BUYER/MIXED): {rows[0][0] if rows else 0}")
    
    db.close()
    print("\n" + "=" * 70)
    print("DATABASE CHECK COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
