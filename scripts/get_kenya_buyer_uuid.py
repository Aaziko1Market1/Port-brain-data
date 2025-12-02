"""Get Kenya buyer UUIDs for testing"""
import sys
sys.path.insert(0, '.')
from etl.db_utils import DatabaseManager

db = DatabaseManager('config/db_config.yml')

query = """
SELECT DISTINCT om.org_uuid, om.name_normalized
FROM organizations_master om
JOIN global_trades_ledger g ON om.org_uuid = g.buyer_uuid
WHERE om.name_normalized IN ('SAJ ENTERPRISES', 'TILE AND CARPET CENTRE')
LIMIT 2
"""

rows = db.execute_query(query)
for r in rows:
    print(f"{r[1]}: {r[0]}")

db.close()
