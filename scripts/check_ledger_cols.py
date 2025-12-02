"""Check ledger columns"""
import sys
sys.path.insert(0, '.')
from etl.db_utils import DatabaseManager

db = DatabaseManager('config/db_config.yml')
query = """
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'global_trades_ledger'
ORDER BY column_name
"""
rows = db.execute_query(query)
print("Columns in global_trades_ledger:")
for r in rows:
    print(f"  {r[0]}")
db.close()
