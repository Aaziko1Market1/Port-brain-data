"""Quick verification of Kenya top 5 buyers via direct SQL"""
import sys
sys.path.insert(0, '.')
from etl.db_utils import DatabaseManager

db = DatabaseManager('config/db_config.yml')

# Direct SQL for top 5 Kenya HS 690721 buyers in ledger
query = """
SELECT 
    om.name_normalized as buyer_name,
    ROUND(SUM(g.customs_value_usd)::numeric, 2) as total_usd,
    COUNT(*) as shipments
FROM global_trades_ledger g
JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
WHERE g.destination_country = 'KENYA'
  AND g.hs_code_6 = '690721'
GROUP BY om.name_normalized
ORDER BY total_usd DESC
LIMIT 5
"""

rows = db.execute_query(query)
print("TOP 5 KENYA HS 690721 BUYERS (from global_trades_ledger):")
print("-" * 70)
print(f"{'Buyer Name':<45} {'Total USD':>15} {'Shipments':>8}")
print("-" * 70)
for r in rows:
    print(f"{r[0]:<45} ${float(r[1]):>14,.2f} {r[2]:>8}")

db.close()
