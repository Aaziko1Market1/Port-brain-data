"""Verify trade history endpoint accuracy"""
import sys
import requests
sys.path.insert(0, '.')
from etl.db_utils import DatabaseManager

SAJ_UUID = "96769b86-0645-4f6d-a0a3-c1f9fb2b96c8"

# Get API response
resp = requests.get(f"http://localhost:8000/api/v1/buyers/{SAJ_UUID}/trade-history")
data = resp.json()

api_total = sum(m['total_value_usd'] for m in data['months'])
api_shipments = sum(m['shipment_count'] for m in data['months'])

print("=" * 60)
print("TRADE HISTORY API VERIFICATION")
print("=" * 60)
print(f"Buyer: {data['buyer_name']}")
print(f"Total months: {data['total_months']}")
print()
print("Monthly breakdown:")
for m in data['months']:
    print(f"  {m['year']}-{m['month']:02d}: ${m['total_value_usd']:,.2f}, {m['shipment_count']} shipments, origin: {m['top_origin_country']}")

print()
print(f"API sum of months: ${api_total:,.2f}")
print(f"API sum shipments: {api_shipments}")

# Compare with direct DB query
db = DatabaseManager('config/db_config.yml')
query = """
SELECT SUM(customs_value_usd), COUNT(*)
FROM global_trades_ledger
WHERE buyer_uuid = %s::uuid
"""
result = db.execute_query(query, (SAJ_UUID,))
db_total = float(result[0][0]) if result and result[0][0] else 0
db_count = result[0][1] if result else 0

print()
print(f"Direct DB total:   ${db_total:,.2f}")
print(f"Direct DB count:   {db_count}")

print()
diff = abs(api_total - db_total)
print(f"Difference: ${diff:.2f}")
if diff < 0.01:
    print("✅ MATCH - API total equals DB total")
else:
    print("❌ MISMATCH")

db.close()
