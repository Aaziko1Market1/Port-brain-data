"""Dump risk_scores summary for before/after comparison"""
import sys
sys.path.insert(0, '.')
from etl.db_utils import DatabaseManager

db = DatabaseManager('config/db_config.yml')

print("=" * 70)
print("RISK SCORES SUMMARY")
print("=" * 70)

# Total counts by entity_type
query1 = """
SELECT entity_type, risk_level, COUNT(*) 
FROM risk_scores 
GROUP BY entity_type, risk_level 
ORDER BY entity_type, risk_level
"""
rows = db.execute_query(query1)
print("\n1. COUNT BY ENTITY_TYPE + RISK_LEVEL:")
for r in rows:
    print(f"  {r[0]:<12} {r[1]:<10} {r[2]:>6}")

# Sample Kenya buyers
query2 = """
SELECT 
    om.name_normalized as buyer_name,
    rs.risk_level,
    rs.risk_score,
    rs.main_reason_code
FROM risk_scores rs
JOIN organizations_master om ON rs.entity_id = om.org_uuid
WHERE rs.entity_type = 'BUYER'
  AND om.name_normalized IN ('SAJ ENTERPRISES', 'TILE AND CARPET CENTRE')
ORDER BY om.name_normalized, rs.main_reason_code
"""
rows = db.execute_query(query2)
print("\n2. KENYA SAMPLE BUYERS:")
for r in rows:
    print(f"  {r[0]:<30} {r[1]:<10} {r[2]:>5.1f} {r[3]}")

# Total records
query3 = "SELECT COUNT(*) FROM risk_scores"
total = db.execute_query(query3)[0][0]
print(f"\n3. TOTAL RISK RECORDS: {total}")

db.close()
