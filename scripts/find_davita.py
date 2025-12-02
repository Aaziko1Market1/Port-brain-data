"""Quick search for DAVITA in database"""
import psycopg2

conn = psycopg2.connect(host='localhost', database='aaziko_trade', user='postgres', password='')
cur = conn.cursor()

print("=== DAVITA in stg_shipments_standardized ===")
cur.execute("""
    SELECT buyer_name_clean, hs_code_6, customs_value_usd, destination_country, source_file
    FROM stg_shipments_standardized
    WHERE buyer_name_clean ILIKE '%DAVITA%'
""")
rows = cur.fetchall()
print(f"Found {len(rows)} rows")
for r in rows:
    print(f"  {r}")

print("\n=== DAVITA in organizations_master ===")
cur.execute("""
    SELECT org_uuid, name_normalized, country_iso
    FROM organizations_master
    WHERE name_normalized ILIKE '%DAVITA%'
""")
rows = cur.fetchall()
print(f"Found {len(rows)} rows")
for r in rows:
    print(f"  {r}")

print("\n=== Total Kenya Import Short rows in standardized ===")
cur.execute("""
    SELECT COUNT(*) FROM stg_shipments_standardized
    WHERE source_file ILIKE '%Kenya Import S%'
""")
print(f"  Count: {cur.fetchone()[0]}")

print("\n=== Sample buyers from Kenya Import S file ===")
cur.execute("""
    SELECT DISTINCT buyer_name_clean 
    FROM stg_shipments_standardized
    WHERE source_file ILIKE '%Kenya Import S%'
    LIMIT 20
""")
for r in cur.fetchall():
    print(f"  {r[0]}")

conn.close()
