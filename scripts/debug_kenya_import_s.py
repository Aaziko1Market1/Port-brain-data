"""Debug Kenya Import S standardization - check buyer names"""
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='aaziko_trade', user='postgres', password='')
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=== Kenya Import S - First 10 rows with all buyer columns ===")
cur.execute("""
    SELECT std_id, buyer_name_raw, buyer_name_clean, buyer_uuid, hs_code_6, customs_value_usd
    FROM stg_shipments_standardized
    WHERE source_file ILIKE '%Kenya Import S%'
    ORDER BY std_id
    LIMIT 10
""")
for r in cur.fetchall():
    print(f"std_id={r['std_id']}")
    print(f"  buyer_name_raw: {r['buyer_name_raw']}")
    print(f"  buyer_name_clean: {r['buyer_name_clean']}")
    print(f"  buyer_uuid: {r['buyer_uuid']}")
    print(f"  hs_code_6: {r['hs_code_6']}, value: ${r['customs_value_usd']}")
    print()

print("\n=== Check if buyer_uuid is populated ===")
cur.execute("""
    SELECT COUNT(*) as total, 
           COUNT(buyer_uuid) as has_uuid,
           COUNT(buyer_name_raw) as has_raw,
           COUNT(buyer_name_clean) as has_clean
    FROM stg_shipments_standardized
    WHERE source_file ILIKE '%Kenya Import S%'
""")
r = cur.fetchone()
print(f"Total rows: {r['total']}")
print(f"With buyer_uuid: {r['has_uuid']}")
print(f"With buyer_name_raw: {r['has_raw']}")
print(f"With buyer_name_clean: {r['has_clean']}")

print("\n=== Check ledger for Kenya Import S entries ===")
cur.execute("""
    SELECT COUNT(*) as total,
           COUNT(buyer_uuid) as has_uuid
    FROM global_trades_ledger
    WHERE source_file ILIKE '%Kenya Import S%'
""")
r = cur.fetchone()
print(f"Total ledger rows from Kenya Import S: {r['total']}")
print(f"With buyer_uuid: {r['has_uuid']}")

print("\n=== Sample ledger rows with buyer info ===")
cur.execute("""
    SELECT g.transaction_id, g.buyer_uuid, om.name_normalized, g.hs_code_6, g.customs_value_usd
    FROM global_trades_ledger g
    LEFT JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
    WHERE g.source_file ILIKE '%Kenya Import S%'
    AND om.name_normalized ILIKE '%DAVITA%'
""")
rows = cur.fetchall()
print(f"DAVITA ledger rows: {len(rows)}")
for r in rows:
    print(f"  {r}")

print("\n=== Check raw buyer names from standardized ===")
cur.execute("""
    SELECT DISTINCT buyer_name_raw
    FROM stg_shipments_standardized
    WHERE source_file ILIKE '%Kenya Import S%'
    AND buyer_name_raw IS NOT NULL
    LIMIT 10
""")
rows = cur.fetchall()
print(f"Distinct buyer_name_raw: {len(rows)}")
for r in rows:
    print(f"  {r['buyer_name_raw']}")

conn.close()
