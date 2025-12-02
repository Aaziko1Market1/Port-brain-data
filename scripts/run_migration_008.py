#!/usr/bin/env python3
"""Run migration 008 to add min/max shipment date columns."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager

def main():
    db = DatabaseManager('config/db_config.yml')
    
    migration_sql = """
    -- Add date coverage columns to file_registry
    ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS min_shipment_date DATE;
    ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS max_shipment_date DATE;
    
    -- Create index for date coverage queries
    CREATE INDEX IF NOT EXISTS idx_fr_shipment_date_range 
        ON file_registry(min_shipment_date, max_shipment_date);
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(migration_sql)
            conn.commit()
    
    print("Migration 008 applied successfully!")
    print("- Added min_shipment_date column")
    print("- Added max_shipment_date column")
    print("- Created index idx_fr_shipment_date_range")

if __name__ == "__main__":
    main()
