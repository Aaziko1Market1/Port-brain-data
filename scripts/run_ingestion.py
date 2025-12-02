"""
GTI-OS Data Platform - Ingestion Orchestrator Script
Run bulk ingestion of raw files into staging

Usage:
    python scripts/run_ingestion.py
    
    Or with custom configs:
    python scripts/run_ingestion.py --db-config config/db_config.yml --ingest-config config/ingestion_config.yml
"""

import sys
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager
from etl.ingestion import scan_raw_files, FileIngestionEngine
from etl.logging_config import setup_logging, get_logger


def load_ingestion_config(config_path: str) -> Dict[str, Any]:
    """Load ingestion configuration from YAML"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main orchestrator for bulk file ingestion"""
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='GTI-OS Bulk Ingestion')
    parser.add_argument(
        '--db-config',
        default='config/db_config.yml',
        help='Path to database config YAML'
    )
    parser.add_argument(
        '--ingest-config',
        default='config/ingestion_config.yml',
        help='Path to ingestion config YAML'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Scan files only, do not ingest'
    )
    
    args = parser.parse_args()
    
    # Load configs
    try:
        ingest_config = load_ingestion_config(args.ingest_config)
    except FileNotFoundError:
        print(f"ERROR: Ingestion config not found: {args.ingest_config}")
        print("Please copy config/ingestion_config.example.yml to config/ingestion_config.yml")
        return 1
    
    # Setup logging
    log_config = ingest_config.get('logging', {})
    log_file = log_config.get('file', 'logs/ingestion.log')
    log_level = log_config.get('level', 'INFO')
    
    setup_logging(
        log_file=log_file,
        log_level=log_level,
        max_bytes=log_config.get('max_bytes', 10485760),
        backup_count=log_config.get('backup_count', 5)
    )
    
    logger = get_logger(__name__)
    
    # Start ingestion
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("GTI-OS Data Platform - Bulk Ingestion Started")
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(args.db_config)
        logger.info(f"Database connection established")
        
        # Scan for files
        raw_data_root = ingest_config['ingestion']['raw_data_root']
        supported_extensions = ingest_config['ingestion'].get(
            'supported_extensions',
            ['.xlsx', '.xls', '.csv']
        )
        
        logger.info(f"Scanning directory: {raw_data_root}")
        files = scan_raw_files(raw_data_root, supported_extensions)
        
        if not files:
            logger.warning("No files found to ingest")
            return 0
        
        logger.info(f"Found {len(files)} file(s) to process")
        
        # Dry run - just list files
        if args.dry_run:
            logger.info("DRY RUN MODE - Files discovered:")
            for f in files:
                logger.info(f"  - {f}")
            return 0
        
        # Initialize ingestion engine
        chunk_size = ingest_config['ingestion'].get('chunk_size', 50000)
        engine = FileIngestionEngine(db_manager, chunk_size)
        
        # Process each file
        results = {
            'total': len(files),
            'ingested': 0,
            'duplicate': 0,
            'failed': 0,
            'total_rows': 0
        }
        
        for idx, file_path in enumerate(files, 1):
            logger.info(f"\n[{idx}/{len(files)}] Processing: {file_path.name}")
            
            result = engine.ingest_file(file_path)
            
            if result['status'] == 'INGESTED':
                results['ingested'] += 1
                results['total_rows'] += result['rows_ingested']
                logger.info(f"✓ Ingested {result['rows_ingested']} rows")
            
            elif result['status'] == 'DUPLICATE':
                results['duplicate'] += 1
                logger.info(f"⊗ Skipped (already ingested)")
            
            elif result['status'] == 'FAILED':
                results['failed'] += 1
                logger.error(f"✗ Failed: {result['error']}")
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\n" + "=" * 80)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total files processed:  {results['total']}")
        logger.info(f"  ✓ Successfully ingested: {results['ingested']}")
        logger.info(f"  ⊗ Duplicates skipped:    {results['duplicate']}")
        logger.info(f"  ✗ Failed:                {results['failed']}")
        logger.info(f"Total rows ingested:    {results['total_rows']:,}")
        logger.info(f"Duration:               {duration:.2f} seconds")
        logger.info(f"Throughput:             {results['total_rows'] / duration:.0f} rows/sec" if duration > 0 else "N/A")
        logger.info("=" * 80)
        
        # Cleanup
        db_manager.close()
        
        return 0 if results['failed'] == 0 else 1
    
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
