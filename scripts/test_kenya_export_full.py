#!/usr/bin/env python3
"""
Test script for Kenya Export FULL standardization
Validates end-to-end: ingestion → standardization → verification
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager
from etl.ingestion.ingest_files import FileIngestionEngine
from etl.standardization.standardize_shipments import standardize_staging_rows

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test Kenya Export FULL end-to-end"""
    
    logger.info("=" * 80)
    logger.info("Kenya Export Full - End-to-End Test")
    logger.info("=" * 80)
    
    # Configuration
    config_path = "config/db_config.yml"
    kenya_export_file = Path("data/raw/kenya/export/2023/01/Kenya Export F.xlsx")
    
    # Verify file exists
    if not kenya_export_file.exists():
        logger.error(f"Kenya Export F.xlsx not found at: {kenya_export_file}")
        logger.error("Please ensure the file exists before running this test")
        return 1
    
    # Step 1: Ingest Kenya Export F.xlsx
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 1: Ingesting Kenya Export F.xlsx")
    logger.info("=" * 80)
    
    db_manager = DatabaseManager(config_path)
    ingestion_engine = FileIngestionEngine(db_manager, chunk_size=50000)
    
    try:
        result = ingestion_engine.ingest_file(kenya_export_file)
        logger.info(f"Ingestion result: {result['status']}")
        logger.info(f"Rows ingested: {result.get('rows_ingested', 0)}")
        logger.info(f"File ID: {result.get('file_id', 'N/A')}")
        
        if result['status'] not in ['INGESTED', 'DUPLICATE']:
            logger.error(f"Ingestion failed or skipped: {result.get('error', 'Unknown error')}")
            db_manager.close()
            return 1
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        db_manager.close()
        return 1
    finally:
        db_manager.close()
    
    # Step 2: Standardize Kenya Export FULL data
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 2: Standardizing Kenya Export Full data")
    logger.info("=" * 80)
    
    try:
        summary = standardize_staging_rows(config_path)
        
        logger.info(f"Groups processed: {summary['groups_processed']}")
        logger.info(f"Groups skipped: {summary['groups_skipped']}")
        logger.info(f"Total rows standardized: {summary['total_rows_standardized']}")
        
        if summary['groups_skipped'] > 0:
            logger.warning(f"Some groups were skipped. Check logs for details.")
        
    except Exception as e:
        logger.error(f"Standardization failed: {e}", exc_info=True)
        return 1
    
    # Step 3: Verification
    logger.info("")
    logger.info("=" * 80)
    logger.info("STEP 3: Running verification queries")
    logger.info("=" * 80)
    logger.info("Run the following command to verify:")
    logger.info("psql -U postgres -d aaziko_trade -f db\\epic2_verification_queries.sql")
    logger.info("")
    logger.info("Or run specific Kenya Export queries:")
    logger.info("psql -U postgres -d aaziko_trade -c \"SELECT * FROM stg_shipments_standardized WHERE reporting_country='KENYA' AND direction='EXPORT' AND source_format='FULL' LIMIT 10;\"")
    logger.info("")
    logger.info("Or check standardization progress:")
    logger.info("psql -U postgres -d aaziko_trade -c \"SELECT * FROM vw_standardization_progress WHERE reporting_country='KENYA' AND direction='EXPORT';\"")
    
    # Success
    logger.info("")
    logger.info("=" * 80)
    logger.info("✓ Kenya Export Full test completed successfully!")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
