"""Debug Buyer Hunter - why is DAVITA not showing?"""
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal

conn = psycopg2.connect(host='localhost', database='aaziko_trade', user='postgres', password='')
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("BUYER HUNTER SIMULATION - HS 690721, KENYA")
print("=" * 60)

# Simulate the actual Buyer Hunter query
print("\n=== 1. Basic aggregation (like Buyer Hunter) ===")
cur.execute("""
    WITH buyer_hs_stats AS (
        SELECT 
            g.buyer_uuid,
            SUM(g.customs_value_usd) AS total_value_usd_12m,
            COUNT(*) AS total_shipments_12m
        FROM global_trades_ledger g
        WHERE g.hs_code_6 = '690721'
          AND g.destination_country = 'KENYA'
          AND g.buyer_uuid IS NOT NULL
        GROUP BY g.buyer_uuid
    )
    SELECT 
        bhs.buyer_uuid::text,
        om.name_normalized AS buyer_name,
        bhs.total_value_usd_12m,
        bhs.total_shipments_12m,
        RANK() OVER (ORDER BY bhs.total_value_usd_12m DESC) as rank
    FROM buyer_hs_stats bhs
    JOIN organizations_master om ON bhs.buyer_uuid = om.org_uuid
    ORDER BY bhs.total_value_usd_12m DESC
""")
rows = cur.fetchall()
print(f"Total buyers: {len(rows)}")

davita_found = False
for r in rows:
    if 'DAVITA' in (r['buyer_name'] or '').upper():
        davita_found = True
        print(f"\n>>> DAVITA FOUND at rank #{r['rank']}:")
        print(f"    UUID: {r['buyer_uuid']}")
        print(f"    Name: {r['buyer_name']}")
        print(f"    Value: ${r['total_value_usd_12m']:,.2f}")
        print(f"    Shipments: {r['total_shipments_12m']}")

if not davita_found:
    print("\n>>> DAVITA NOT IN RESULTS")

# Show top 30
print("\n=== 2. Top 30 buyers ===")
for r in rows[:30]:
    marker = " <<<" if 'DAVITA' in (r['buyer_name'] or '').upper() else ""
    print(f"  #{r['rank']}. {r['buyer_name']}: ${r['total_value_usd_12m']:,.2f}{marker}")

# Check buyer_profile for DAVITA
print("\n=== 3. DAVITA in buyer_profile ===")
cur.execute("""
    SELECT bp.*, om.name_normalized
    FROM buyer_profile bp
    JOIN organizations_master om ON bp.buyer_uuid = om.org_uuid
    WHERE om.name_normalized ILIKE '%DAVITA%'
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  UUID: {r['buyer_uuid']}")
        print(f"  Name: {r['name_normalized']}")
        print(f"  Dest: {r.get('destination_country')}")
        print(f"  Total Value: ${r.get('total_customs_value_usd') or 0:,.2f}")
else:
    print("  NOT FOUND IN buyer_profile!")

# Check risk_scores for DAVITA
print("\n=== 4. DAVITA risk_score ===")
cur.execute("""
    SELECT * FROM risk_scores
    WHERE entity_uuid = 'd55e818c-2582-4bb9-a32c-dc4c9c9ac365'
""")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"  Risk Score: {r.get('risk_score')}")
        print(f"  Risk Level: {r.get('risk_level')}")
else:
    print("  NO RISK SCORE FOUND")

conn.close()
