"""
GTI-OS Data Platform - Database Setup Script
Creates database and applies schema

Usage:
    python scripts/setup_database.py
    
    Or with custom config:
    python scripts/setup_database.py --config config/db_config.yml
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import create_database_if_not_exists, apply_schema
from etl.logging_config import setup_logging, get_logger


def main():
    """Setup database and apply schema"""
    
    parser = argparse.ArgumentParser(description='GTI-OS Database Setup')
    parser.add_argument(
        '--config',
        default='config/db_config.yml',
        help='Path to database config YAML'
    )
    parser.add_argument(
        '--schema',
        default='db/schema_v1.sql',
        help='Path to schema SQL file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level='INFO')
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("GTI-OS Data Platform - Database Setup")
    logger.info("=" * 80)
    
    try:
        # Create database if not exists
        logger.info("Step 1: Creating database 'aaziko_trade' if not exists...")
        create_database_if_not_exists(args.config, 'aaziko_trade')
        
        # Apply schema
        logger.info(f"Step 2: Applying schema from {args.schema}...")
        apply_schema(args.config, args.schema)
        
        logger.info("=" * 80)
        logger.info("✓ Database setup completed successfully!")
        logger.info("=" * 80)
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Database setup failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
