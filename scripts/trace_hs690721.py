"""
HS 690721 Kenya Data Trace Script
Traces exactly where Buyer Hunter is reading tile data for Kenya
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

def run_trace():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("HS 690721 (TILES) - KENYA DATA TRACE")
    print("=" * 80)
    
    # 1. Check global_trades_ledger
    print("\n### 1. GLOBAL_TRADES_LEDGER - HS 690721 Kenya ###")
    cur.execute("""
        SELECT 
            reporting_country,
            direction,
            destination_country,
            COUNT(*) as row_count,
            SUM(customs_value_usd) as total_value_usd,
            MIN(shipment_date) as min_date,
            MAX(shipment_date) as max_date
        FROM global_trades_ledger 
        WHERE hs_code_6 = '690721' 
        AND (destination_country ILIKE '%kenya%' OR reporting_country ILIKE '%kenya%')
        GROUP BY reporting_country, direction, destination_country
        ORDER BY row_count DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  reporting_country: {r['reporting_country']}, direction: {r['direction']}, "
                  f"destination: {r['destination_country']}, rows: {r['row_count']}, "
                  f"value_usd: {r['total_value_usd']}, dates: {r['min_date']} to {r['max_date']}")
    else:
        print("  NO ROWS FOUND")
    
    # 2. Check source files for HS 690721 Kenya
    print("\n### 2. SOURCE FILES for HS 690721 Kenya ###")
    cur.execute("""
        SELECT DISTINCT source_file, source_format, COUNT(*) as rows
        FROM global_trades_ledger 
        WHERE hs_code_6 = '690721' 
        AND (destination_country ILIKE '%kenya%' OR reporting_country ILIKE '%kenya%')
        GROUP BY source_file, source_format
        ORDER BY rows DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  source_file: {r['source_file']}, format: {r['source_format']}, rows: {r['rows']}")
    else:
        print("  NO SOURCE FILES FOUND")
    
    # 3. Check stg_shipments_standardized
    print("\n### 3. STG_SHIPMENTS_STANDARDIZED - HS 690721 Kenya ###")
    cur.execute("""
        SELECT 
            reporting_country,
            direction,
            destination_country,
            COUNT(*) as row_count,
            SUM(customs_value_usd) as total_value_usd
        FROM stg_shipments_standardized 
        WHERE hs_code_6 = '690721' 
        AND (destination_country ILIKE '%kenya%' OR reporting_country ILIKE '%kenya%')
        GROUP BY reporting_country, direction, destination_country
        ORDER BY row_count DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  reporting_country: {r['reporting_country']}, direction: {r['direction']}, "
                  f"destination: {r['destination_country']}, rows: {r['row_count']}, value: {r['total_value_usd']}")
    else:
        print("  NO ROWS FOUND")
    
    # 4. Check ALL HS 690721 data globally (to see where it's coming from)
    print("\n### 4. ALL HS 690721 DATA GLOBALLY (top sources) ###")
    cur.execute("""
        SELECT 
            reporting_country,
            direction,
            destination_country,
            COUNT(*) as row_count,
            SUM(customs_value_usd) as total_value_usd
        FROM global_trades_ledger 
        WHERE hs_code_6 = '690721'
        GROUP BY reporting_country, direction, destination_country
        ORDER BY row_count DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {r['reporting_country']} -> {r['destination_country']} ({r['direction']}): "
                  f"{r['row_count']} rows, ${r['total_value_usd']}")
    else:
        print("  NO HS 690721 DATA FOUND GLOBALLY")
    
    # 5. Check mapping_registry for Kenya
    print("\n### 5. MAPPING_REGISTRY - Kenya entries ###")
    cur.execute("""
        SELECT * FROM mapping_registry 
        WHERE reporting_country ILIKE '%kenya%' OR sample_file_path ILIKE '%kenya%'
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {dict(r)}")
    else:
        print("  NO KENYA ENTRIES IN MAPPING_REGISTRY")
    
    # 6. Check what Buyer Hunter API would return
    print("\n### 6. BUYER HUNTER VIEW - vw_buyer_360 for Kenya ###")
    try:
        cur.execute("""
            SELECT 
                buyer_name,
                country,
                total_shipments,
                total_value_usd,
                top_hs_codes
            FROM vw_buyer_360 
            WHERE country ILIKE '%kenya%'
            ORDER BY total_value_usd DESC NULLS LAST
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"  {r['buyer_name']}: {r['country']}, shipments: {r['total_shipments']}, "
                      f"value: {r['total_value_usd']}, hs: {r['top_hs_codes']}")
        else:
            print("  NO KENYA BUYERS IN vw_buyer_360")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 7. Check buyer_profile for Kenya
    print("\n### 7. BUYER_PROFILE - Kenya entries ###")
    cur.execute("""
        SELECT 
            buyer_name_clean,
            country,
            total_shipments,
            total_value_usd,
            top_hs_codes
        FROM buyer_profile 
        WHERE country ILIKE '%kenya%'
        ORDER BY total_value_usd DESC NULLS LAST
        LIMIT 10
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  {r['buyer_name_clean']}: {r['country']}, shipments: {r['total_shipments']}, "
                  f"value: {r['total_value_usd']}, hs: {r['top_hs_codes']}")
    else:
        print("  NO KENYA BUYERS IN buyer_profile")
    
    # 8. Check all tables for any Kenya data
    print("\n### 8. ALL KENYA DATA IN LEDGER (any HS) ###")
    cur.execute("""
        SELECT 
            hs_code_6,
            COUNT(*) as row_count,
            SUM(customs_value_usd) as total_value
        FROM global_trades_ledger 
        WHERE reporting_country ILIKE '%kenya%' OR destination_country ILIKE '%kenya%'
        GROUP BY hs_code_6
        ORDER BY row_count DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  HS {r['hs_code_6']}: {r['row_count']} rows, ${r['total_value']}")
    else:
        print("  NO KENYA DATA IN LEDGER AT ALL")
    
    # 9. Check price_corridor for Kenya
    print("\n### 9. PRICE_CORRIDOR - Kenya entries ###")
    try:
        cur.execute("""
            SELECT * FROM price_corridor 
            WHERE country ILIKE '%kenya%'
            LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            for r in rows:
                print(f"  {dict(r)}")
        else:
            print("  NO KENYA ENTRIES IN price_corridor")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # 10. List all distinct source files in ledger
    print("\n### 10. ALL DISTINCT SOURCE FILES IN LEDGER ###")
    cur.execute("""
        SELECT DISTINCT source_file, COUNT(*) as rows
        FROM global_trades_ledger
        GROUP BY source_file
        ORDER BY source_file
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"  {r['source_file']}: {r['rows']} rows")
    
    conn.close()
    print("\n" + "=" * 80)
    print("TRACE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_trace()
