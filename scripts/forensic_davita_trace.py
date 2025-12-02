"""
FORENSIC TRACE: DAVITA SOLUTIONS LIMITED - Kenya HS 690721
Complete pipeline trace for missing buyer in Buyer Hunter
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'aaziko_trade'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', '')
    )

def run_forensic_trace():
    conn = get_connection()
    conn.autocommit = True  # Prevent transaction issues
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("FORENSIC TRACE: DAVITA SOLUTIONS LIMITED")
    print("Country: KENYA | HS: 690721 | Expected Value: ~$56,108 USD")
    print("=" * 80)
    
    # ================================================================
    # STEP 1: CONFIRM INGESTION FROM KENYA IMPORT S FILE
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 1: INGESTION VERIFICATION")
    print("=" * 60)
    
    # Check mapping_registry for Kenya Import Short
    print("\n### 1.1 MAPPING_REGISTRY CHECK ###")
    cur.execute("""
        SELECT mapping_id, reporting_country, direction, source_format, 
               config_key, yaml_path, status, sample_file_path
        FROM mapping_registry
        WHERE reporting_country = 'KENYA' 
          AND direction = 'IMPORT' 
          AND source_format = 'SHORT'
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  Mapping ID: {r['mapping_id']}")
            print(f"  Config: {r['config_key']}")
            print(f"  YAML: {r['yaml_path']}")
            print(f"  Status: {r['status']}")
            print(f"  Sample: {r['sample_file_path']}")
    else:
        print("  ⚠️ NO MAPPING_REGISTRY ENTRY for KENYA IMPORT SHORT")
    
    # ================================================================
    # STEP 2: VERIFY STANDARDIZATION
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 2: STANDARDIZATION VERIFICATION")
    print("=" * 60)
    
    print("\n### 2.1 DAVITA IN STG_SHIPMENTS_STANDARDIZED ###")
    cur.execute("""
        SELECT std_id, reporting_country, direction,
               destination_country, origin_country,
               hs_code_6, customs_value_usd, qty_kg, qty_unit_raw,
               buyer_name_clean, buyer_uuid, source_file
        FROM stg_shipments_standardized
        WHERE reporting_country = 'KENYA'
          AND direction = 'IMPORT'
          AND hs_code_6 = '690721'
          AND buyer_name_clean ILIKE '%DAVITA%'
        ORDER BY std_id
    """)
    rows = cur.fetchall()
    
    if rows:
        total_value = 0
        print(f"  Found {len(rows)} standardized rows for DAVITA:")
        for r in rows:
            print(f"    std_id: {r['std_id']}")
            print(f"    HS: {r['hs_code_6']}, Value: ${r['customs_value_usd']}")
            print(f"    Dest: {r['destination_country']}, Origin: {r['origin_country']}")
            print(f"    Buyer: {r['buyer_name_clean']}, UUID: {r['buyer_uuid']}")
            print(f"    Source: {r['source_file']}")
            print()
            if r['customs_value_usd']:
                total_value += float(r['customs_value_usd'])
        print(f"  TOTAL VALUE: ${total_value:,.2f}")
        if abs(total_value - 56108.48) < 1000:
            print("  ✅ Value matches expected ~$56,108")
        else:
            print(f"  ⚠️ Value mismatch! Expected ~$56,108, got ${total_value:,.2f}")
    else:
        print("  ⚠️ NO DAVITA ROWS IN stg_shipments_standardized for HS 690721")
        # Try broader search
        cur.execute("""
            SELECT DISTINCT buyer_name_clean 
            FROM stg_shipments_standardized
            WHERE buyer_name_clean ILIKE '%DAVITA%'
            LIMIT 10
        """)
        alt_rows = cur.fetchall()
        if alt_rows:
            print("  Alternative DAVITA matches found:")
            for r in alt_rows:
                print(f"    - {r['buyer_name_clean']}")
    
    # ================================================================
    # STEP 3: VERIFY IDENTITY RESOLUTION
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 3: IDENTITY RESOLUTION VERIFICATION")
    print("=" * 60)
    
    print("\n### 3.1 DAVITA IN ORGANIZATIONS_MASTER ###")
    cur.execute("""
        SELECT org_uuid, name_normalized, name_raw, country_iso, org_type
        FROM organizations_master
        WHERE name_normalized ILIKE '%DAVITA%'
           OR name_raw ILIKE '%DAVITA%'
    """)
    rows = cur.fetchall()
    
    davita_uuid = None
    if rows:
        print(f"  Found {len(rows)} org(s) matching DAVITA:")
        for r in rows:
            print(f"    UUID: {r['org_uuid']}")
            print(f"    Normalized: {r['name_normalized']}")
            print(f"    Raw: {r['name_raw']}")
            print(f"    Country: {r['country_iso']}")
            print(f"    Type: {r['org_type']}")
            davita_uuid = r['org_uuid']
    else:
        print("  ⚠️ NO DAVITA IN organizations_master")
    
    # ================================================================
    # STEP 4: VERIFY LEDGER
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 4: LEDGER VERIFICATION")
    print("=" * 60)
    
    print("\n### 4.1 DAVITA IN GLOBAL_TRADES_LEDGER ###")
    cur.execute("""
        SELECT g.buyer_uuid, om.name_normalized as buyer_name,
               SUM(g.customs_value_usd) AS total_value_usd,
               COUNT(*) AS shipment_count,
               MIN(g.shipment_date) AS first_date,
               MAX(g.shipment_date) AS last_date
        FROM global_trades_ledger g
        JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
        WHERE g.reporting_country = 'KENYA'
          AND g.destination_country = 'KENYA'
          AND g.hs_code_6 = '690721'
          AND om.name_normalized ILIKE '%DAVITA%'
        GROUP BY g.buyer_uuid, om.name_normalized
    """)
    rows = cur.fetchall()
    
    if rows:
        print(f"  Found DAVITA in ledger:")
        for r in rows:
            print(f"    UUID: {r['buyer_uuid']}")
            print(f"    Name: {r['buyer_name']}")
            print(f"    Total Value: ${r['total_value_usd']:,.2f}")
            print(f"    Shipments: {r['shipment_count']}")
            print(f"    Date Range: {r['first_date']} to {r['last_date']}")
            davita_uuid = r['buyer_uuid']
    else:
        print("  ⚠️ NO DAVITA IN global_trades_ledger for HS 690721 Kenya")
        # Broader search - check if DAVITA exists anywhere in ledger
        cur.execute("""
            SELECT g.buyer_uuid, om.name_normalized as buyer_name, g.hs_code_6, 
                   g.destination_country, SUM(g.customs_value_usd) as val
            FROM global_trades_ledger g
            JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
            WHERE om.name_normalized ILIKE '%DAVITA%'
            GROUP BY g.buyer_uuid, om.name_normalized, g.hs_code_6, g.destination_country
        """)
        alt_rows = cur.fetchall()
        if alt_rows:
            print("  Alternative DAVITA entries in ledger:")
            for r in alt_rows:
                print(f"    {r['buyer_name']} - HS {r['hs_code_6']} - {r['destination_country']} - ${r['val']}")
        else:
            print("  NO DAVITA ENTRIES ANYWHERE IN LEDGER")
    
    # ================================================================
    # STEP 5: VERIFY BUYER PROFILE
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 5: BUYER PROFILE VERIFICATION")
    print("=" * 60)
    
    print("\n### 5.1 DAVITA IN BUYER_PROFILE ###")
    cur.execute("""
        SELECT bp.buyer_uuid, om.name_normalized as buyer_name,
               bp.destination_country,
               bp.total_customs_value_usd,
               bp.total_shipments,
               bp.last_shipment_date,
               bp.persona_label
        FROM buyer_profile bp
        JOIN organizations_master om ON bp.buyer_uuid = om.org_uuid
        WHERE om.name_normalized ILIKE '%DAVITA%'
    """)
    rows = cur.fetchall()
    
    if rows:
        print(f"  Found DAVITA profile:")
        for r in rows:
            print(f"    UUID: {r['buyer_uuid']}")
            print(f"    Name: {r['buyer_name']}")
            print(f"    Destination: {r['destination_country']}")
            print(f"    Total Value: ${r['total_customs_value_usd'] or 0:,.2f}")
            print(f"    Shipments: {r['total_shipments']}")
            print(f"    Last Shipment: {r['last_shipment_date']}")
            print(f"    Persona: {r['persona_label']}")
    else:
        print("  ⚠️ NO DAVITA IN buyer_profile")
    
    # ================================================================
    # STEP 6: VERIFY BUYER HUNTER OPPORTUNITY
    # ================================================================
    print("\n" + "=" * 60)
    print("STEP 6: BUYER HUNTER OPPORTUNITY VERIFICATION")
    print("=" * 60)
    
    print("\n### 6.1 BUYER HUNTER QUERY SIMULATION ###")
    # Simulate the buyer hunter query
    cur.execute("""
        WITH buyer_hs_stats AS (
            SELECT 
                g.buyer_uuid,
                g.destination_country,
                SUM(g.customs_value_usd) AS total_value_usd_12m,
                COUNT(*) AS total_shipments_12m
            FROM global_trades_ledger g
            WHERE g.hs_code_6 = '690721'
              AND g.destination_country = 'KENYA'
              AND g.buyer_uuid IS NOT NULL
            GROUP BY g.buyer_uuid, g.destination_country
        )
        SELECT 
            bhs.buyer_uuid::text,
            om.name_normalized AS buyer_name,
            bhs.total_value_usd_12m,
            bhs.total_shipments_12m
        FROM buyer_hs_stats bhs
        JOIN organizations_master om ON bhs.buyer_uuid = om.org_uuid
        WHERE om.name_normalized ILIKE '%DAVITA%'
        ORDER BY bhs.total_value_usd_12m DESC
    """)
    rows = cur.fetchall()
    
    if rows:
        print(f"  DAVITA in Buyer Hunter aggregation:")
        for r in rows:
            print(f"    UUID: {r['buyer_uuid']}")
            print(f"    Name: {r['buyer_name']}")
            print(f"    12m Value: ${r['total_value_usd_12m']:,.2f}")
            print(f"    12m Shipments: {r['total_shipments_12m']}")
            
            # Check if it meets threshold
            if r['total_value_usd_12m'] >= 50000:
                print("    ✅ Meets $50K threshold")
            else:
                print(f"    ⚠️ BELOW $50K threshold! Value: ${r['total_value_usd_12m']:,.2f}")
    else:
        print("  ⚠️ DAVITA NOT FOUND in Buyer Hunter aggregation")
    
    # Check total buyers for this HS/country
    print("\n### 6.2 ALL BUYERS FOR HS 690721 KENYA (sorted by value) ###")
    cur.execute("""
        WITH buyer_hs_stats AS (
            SELECT 
                g.buyer_uuid,
                g.destination_country,
                SUM(g.customs_value_usd) AS total_value_usd_12m,
                COUNT(*) AS total_shipments_12m
            FROM global_trades_ledger g
            WHERE g.hs_code_6 = '690721'
              AND g.destination_country = 'KENYA'
              AND g.buyer_uuid IS NOT NULL
            GROUP BY g.buyer_uuid, g.destination_country
        )
        SELECT 
            bhs.buyer_uuid::text,
            om.name_normalized AS buyer_name,
            bhs.total_value_usd_12m,
            bhs.total_shipments_12m
        FROM buyer_hs_stats bhs
        JOIN organizations_master om ON bhs.buyer_uuid = om.org_uuid
        ORDER BY bhs.total_value_usd_12m DESC
    """)
    rows = cur.fetchall()
    
    print(f"  Total buyers found: {len(rows)}")
    davita_rank = None
    for i, r in enumerate(rows):
        if 'DAVITA' in (r['buyer_name'] or '').upper():
            davita_rank = i + 1
            print(f"  >>> DAVITA RANK: #{davita_rank} with ${r['total_value_usd_12m']:,.2f}")
    
    # Show top 30 to see where DAVITA falls
    print("\n  TOP 30 BUYERS:")
    for i, r in enumerate(rows[:30]):
        marker = " <<<" if 'DAVITA' in (r['buyer_name'] or '').upper() else ""
        meets_threshold = "✓" if r['total_value_usd_12m'] >= 50000 else "✗"
        print(f"    {i+1}. [{meets_threshold}] {r['buyer_name']}: ${r['total_value_usd_12m']:,.2f} ({r['total_shipments_12m']} shipments){marker}")
    
    if davita_rank:
        if davita_rank > 20:
            print(f"\n  ⚠️ DAVITA is at rank #{davita_rank} - outside default TOP 20 limit!")
            print("  This is a PAGINATION/LIMIT issue, not a data issue.")
        else:
            print(f"\n  ✅ DAVITA is at rank #{davita_rank} - within TOP 20")
    else:
        print("\n  ⚠️ DAVITA NOT FOUND in buyer ranking!")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("FORENSIC TRACE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_forensic_trace()
