"""
GTI-OS Data Platform - Verify Setup Script
Check database connectivity and table existence

Usage:
    python scripts/verify_setup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager
from etl.logging_config import setup_logging, get_logger


EXPECTED_TABLES = [
    'file_registry',
    'stg_shipments_raw',
    'stg_shipments_standardized',
    'organizations_master',
    'global_trades_ledger',
    'product_taxonomy',
    'buyer_profile',
    'exporter_profile',
    'price_corridor',
    'lane_stats',
    'risk_scores',
    'mirror_match_log',
    'demand_trends',
    'country_opportunity_scores',
    'product_bundle_stats'
]


def main():
    """Verify database setup"""
    
    setup_logging(log_level='INFO')
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("GTI-OS Data Platform - Setup Verification")
    logger.info("=" * 80)
    
    try:
        # Connect to database
        db_manager = DatabaseManager('config/db_config.yml')
        logger.info("✓ Database connection successful")
        
        # Check tables
        logger.info("\nChecking tables...")
        missing_tables = []
        existing_tables = []
        
        for table in EXPECTED_TABLES:
            exists = db_manager.table_exists(table)
            if exists:
                row_count = db_manager.get_table_row_count(table)
                existing_tables.append((table, row_count))
                logger.info(f"  ✓ {table:<35} ({row_count:>10,} rows)")
            else:
                missing_tables.append(table)
                logger.warning(f"  ✗ {table:<35} NOT FOUND")
        
        # Check views
        logger.info("\nChecking LLM views...")
        views = [
            'vw_global_shipments_for_llm',
            'vw_buyer_profile_for_llm',
            'vw_exporter_profile_for_llm',
            'vw_price_corridor_for_llm',
            'vw_lane_stats_for_llm',
            'vw_risk_scores_for_llm',
            'vw_country_opportunity_for_llm'
        ]
        
        for view in views:
            exists = db_manager.table_exists(view)
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {view}")
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Tables found:    {len(existing_tables)}/{len(EXPECTED_TABLES)}")
        logger.info(f"Missing tables:  {len(missing_tables)}")
        
        if missing_tables:
            logger.warning(f"\nMissing tables: {', '.join(missing_tables)}")
            logger.warning("Run: python scripts/setup_database.py")
        else:
            logger.info("\n✓ All expected tables exist!")
        
        logger.info("=" * 80)
        
        db_manager.close()
        
        return 0 if not missing_tables else 1
    
    except Exception as e:
        logger.error(f"✗ Verification failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
