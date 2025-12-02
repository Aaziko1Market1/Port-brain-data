#!/usr/bin/env python
"""
EPIC 4 - Global Trades Ledger Loader Orchestration Script
==========================================================
CLI script to populate global_trades_ledger from standardized shipments.

This script:
1. Reads database configuration
2. Runs the ledger loading pipeline
3. Logs comprehensive statistics
4. Outputs a summary of results

Usage:
    python scripts/run_ledger_loader.py
    python scripts/run_ledger_loader.py --batch-size 20000
    python scripts/run_ledger_loader.py --countries INDIA KENYA
    python scripts/run_ledger_loader.py --directions EXPORT IMPORT
    python scripts/run_ledger_loader.py --log-level DEBUG

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.ledger.load_global_trades import load_global_trades
from etl.db_utils import DatabaseManager
from etl.pipeline_tracking import track_pipeline_run, update_run_metrics

# Configure logging
def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Configure logging with consistent format."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def print_banner():
    """Print the application banner."""
    print()
    print("=" * 70)
    print("  GTI-OS Data Platform - EPIC 4: Global Trades Ledger Loader")
    print("  Fact Table Population Pipeline")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the loading results."""
    print()
    print("=" * 70)
    print("  GLOBAL TRADES LEDGER LOADING SUMMARY")
    print("=" * 70)
    print()
    
    # Overall stats
    print("  OVERALL STATISTICS:")
    print(f"    Rows loaded:         {result.get('rows_loaded', 0):,}")
    print(f"    Batches processed:   {result.get('batches_processed', 0):,}")
    print()
    
    # Countries and directions
    print("  COVERAGE:")
    print(f"    Countries processed: {result.get('countries_processed', [])}")
    print(f"    Directions processed: {result.get('directions_processed', [])}")
    print()
    
    # Per country/direction breakdown
    rows_by_cd = result.get('rows_by_country_direction', {})
    if rows_by_cd:
        print("  ROWS BY COUNTRY/DIRECTION:")
        for key, count in sorted(rows_by_cd.items()):
            print(f"    {key}: {count:,}")
        print()
    
    # Errors
    errors = result.get('errors', [])
    if errors:
        print("  ERRORS:")
        for error in errors:
            print(f"    - {error}")
        print()
    
    # Timing
    print(f"  ELAPSED TIME: {elapsed_seconds:.2f} seconds")
    print()
    print("=" * 70)
    
    # Status
    if errors:
        print("  STATUS: COMPLETED WITH ERRORS")
    else:
        rows_loaded = result.get('rows_loaded', 0)
        if rows_loaded == 0:
            print("  STATUS: NO NEW ROWS TO LOAD (LEDGER UP TO DATE)")
        else:
            print("  STATUS: SUCCESS")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the ledger loader."""
    parser = argparse.ArgumentParser(
        description='EPIC 4: Global Trades Ledger Loader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with defaults
  %(prog)s --batch-size 20000                 # Larger batch size
  %(prog)s --countries INDIA KENYA            # Filter by countries
  %(prog)s --directions EXPORT                # Export only
  %(prog)s --log-level DEBUG                  # Verbose logging

The ledger loader will:
  1. Find standardized rows not yet in global_trades_ledger
  2. Map fields from staging to ledger format
  3. Generate transaction UUIDs
  4. Bulk insert into global_trades_ledger
  5. Track loaded rows via std_id for idempotency
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/db_config.yml',
        help='Path to database configuration file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=10000,
        help='Number of records to process per batch (default: 10000)'
    )
    
    parser.add_argument(
        '--countries', 
        nargs='+',
        metavar='COUNTRY',
        help='Countries to process (default: INDIA, KENYA)'
    )
    
    parser.add_argument(
        '--directions', 
        nargs='+',
        metavar='DIRECTION',
        choices=['EXPORT', 'IMPORT'],
        help='Directions to process (default: all)'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch_size < 1:
        print("Error: --batch-size must be positive")
        sys.exit(1)
    
    # Setup
    logger = setup_logging(args.log_level)
    print_banner()
    
    # Verify config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  Database config: {args.config}")
    logger.info(f"  Batch size: {args.batch_size:,}")
    logger.info(f"  Countries: {args.countries or 'all supported (INDIA, KENYA)'}")
    logger.info(f"  Directions: {args.directions or 'all'}")
    
    # Run ledger loading
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        countries = args.countries or ['INDIA', 'KENYA', 'INDONESIA']
        
        with track_pipeline_run(db, 'ledger', countries=countries, directions=args.directions) as run_id:
            result = load_global_trades(
                db_config_path=args.config,
                batch_size=args.batch_size,
                country_filters=args.countries,
                direction_filters=args.directions
            )
            
            # Update run metrics
            update_run_metrics(
                db, run_id,
                rows_processed=result.get('rows_loaded', 0),
                rows_created=result.get('rows_loaded', 0)
            )
        
        db.close()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print_summary(result, elapsed)
        
        # Exit code based on errors
        if result.get('errors'):
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Ledger loading failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  LEDGER LOADING FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
