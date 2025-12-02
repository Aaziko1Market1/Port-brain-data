"""
Test script for Kenya Import Full standardization
Runs ingestion and standardization for Kenya Import F.xlsx files
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager
from etl.ingestion.ingest_files import FileIngestionEngine
from etl.standardization.standardize_shipments import standardize_staging_rows
from etl.logging_config import setup_logging, get_logger

# Setup logging
setup_logging(log_level='INFO')
logger = get_logger(__name__)


def main():
    """Run Kenya Import Full test"""
    
    logger.info("=" * 80)
    logger.info("Kenya Import Full - End-to-End Test")
    logger.info("=" * 80)
    
    # Database config
    db_config_path = 'config/db_config.yml'
    
    # Kenya Import Full file
    kenya_file = Path('data/raw/kenya/import/2023/01/Kenya Import F.xlsx')
    
    if not kenya_file.exists():
        logger.error(f"Kenya Import F.xlsx not found at: {kenya_file}")
        logger.error("Please ensure the file exists before running this test")
        return 1
    
    # Step 1: Ingest
    logger.info("\n" + "=" * 80)
    logger.info("STEP 1: Ingesting Kenya Import F.xlsx")
    logger.info("=" * 80)
    
    db_manager = DatabaseManager(db_config_path)
    ingestion_engine = FileIngestionEngine(db_manager, chunk_size=50000)
    
    result = ingestion_engine.ingest_file(kenya_file)
    
    logger.info(f"Ingestion result: {result['status']}")
    logger.info(f"Rows ingested: {result.get('rows_ingested', 0)}")
    logger.info(f"File ID: {result.get('file_id', 'N/A')}")
    
    if result['status'] != 'INGESTED' and result['status'] != 'DUPLICATE':
        logger.error(f"Ingestion failed: {result.get('error')}")
        db_manager.close()
        return 1
    
    db_manager.close()
    
    # Step 2: Standardize
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: Standardizing Kenya Import Full data")
    logger.info("=" * 80)
    
    summary = standardize_staging_rows(db_config_path, limit=None)
    
    logger.info(f"Groups processed: {summary['groups_processed']}")
    logger.info(f"Groups skipped: {summary['groups_skipped']}")
    logger.info(f"Total rows standardized: {summary['total_rows_standardized']}")
    
    if summary['errors']:
        logger.warning(f"Errors encountered: {summary['errors']}")
    
    # Step 3: Verification queries
    logger.info("\n" + "=" * 80)
    logger.info("STEP 3: Running verification queries")
    logger.info("=" * 80)
    logger.info("Run the following command to verify:")
    logger.info('psql -U postgres -d aaziko_trade -f db\\epic2_verification_queries.sql')
    logger.info("\nOr run specific Kenya queries:")
    logger.info('psql -U postgres -d aaziko_trade -c "SELECT * FROM stg_shipments_standardized WHERE reporting_country=\'KENYA\' AND direction=\'IMPORT\' AND source_format=\'FULL\' LIMIT 10;"')
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ Kenya Import Full test completed successfully!")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
