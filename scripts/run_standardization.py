"""
GTI-OS Data Platform - Standardization Orchestrator Script
Run standardization pipeline to normalize raw data

Usage:
    python scripts/run_standardization.py
    
    Or with custom configs:
    python scripts/run_standardization.py --db-config config/db_config.yml --limit 50000
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager
from etl.standardization.standardize_shipments import standardize_staging_rows
from etl.logging_config import setup_logging, get_logger
from etl.pipeline_tracking import track_pipeline_run, update_run_metrics


def main():
    """Main orchestrator for standardization"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='GTI-OS Standardization Pipeline')
    parser.add_argument(
        '--db-config',
        default='config/db_config.yml',
        help='Path to database config YAML'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of rows to process (for testing)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(
        log_file='logs/standardization.log',
        log_level=args.log_level
    )
    
    logger = get_logger(__name__)
    
    # Start standardization
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("GTI-OS Data Platform - Standardization Pipeline Started")
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # Check database connection
        db_manager = DatabaseManager(args.db_config)
        logger.info("Database connection established")
        
        # Check for raw data
        raw_count = db_manager.get_table_row_count('stg_shipments_raw')
        logger.info(f"Raw rows in staging: {raw_count:,}")
        
        if raw_count == 0:
            logger.warning("No raw data found. Run ingestion first:")
            logger.warning("  python scripts/run_ingestion.py")
            return 1
        
        # Check for already standardized data
        std_count = db_manager.get_table_row_count('stg_shipments_standardized')
        logger.info(f"Already standardized rows: {std_count:,}")
        
        unstandardized = raw_count - std_count
        logger.info(f"Rows to standardize: {unstandardized:,}")
        
        db_manager.close()
        
        if unstandardized == 0:
            logger.info("All rows already standardized!")
            return 0
        
        # Run standardization with pipeline tracking
        logger.info("\nStarting standardization process...")
        
        db = DatabaseManager(args.db_config)
        countries = ['INDIA', 'KENYA', 'INDONESIA']
        
        with track_pipeline_run(db, 'standardization', countries=countries) as run_id:
            summary = standardize_staging_rows(
                db_config_path=args.db_config,
                limit=args.limit
            )
            
            # Update run metrics
            update_run_metrics(
                db, run_id,
                rows_processed=summary.get('total_rows_standardized', 0),
                rows_created=summary.get('total_rows_standardized', 0),
                rows_skipped=summary.get('groups_skipped', 0)
            )
        
        db.close()
        
        # Print summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("STANDARDIZATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Groups processed:          {summary['groups_processed']}")
        logger.info(f"Groups skipped:            {summary['groups_skipped']}")
        logger.info(f"Total rows standardized:   {summary['total_rows_standardized']:,}")
        logger.info(f"Duration:                  {duration:.2f} seconds")
        
        if summary['total_rows_standardized'] > 0:
            throughput = summary['total_rows_standardized'] / duration
            logger.info(f"Throughput:                {throughput:.0f} rows/sec")
        
        if summary['errors']:
            logger.warning(f"\nErrors encountered: {len(summary['errors'])}")
            for error in summary['errors']:
                logger.warning(f"  - {error}")
        
        logger.info("=" * 80)
        
        # Verification queries
        logger.info("\nVerification SQL queries:")
        logger.info("  SELECT COUNT(*) FROM stg_shipments_standardized;")
        logger.info("  SELECT hs_code_raw, hs_code_6, qty_raw, qty_kg, price_usd_per_kg")
        logger.info("  FROM stg_shipments_standardized LIMIT 10;")
        
        return 0 if not summary['errors'] else 1
    
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("\nMissing mapping configuration file.")
        logger.error("Create YAML configs in config/ folder:")
        logger.error("  - config/india_export.yml")
        logger.error("  - config/kenya_import.yml")
        logger.error("  - etc.")
        return 1
    
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
