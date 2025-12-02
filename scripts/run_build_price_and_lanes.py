#!/usr/bin/env python
"""
EPIC 6B - Build Price Corridors & Lane Stats Orchestration Script
==================================================================
CLI script to build price corridor and lane statistics from global_trades_ledger.

This script:
1. Reads from global_trades_ledger (respects partitioning)
2. Computes price corridors (percentiles per HS6/country/month)
3. Computes lane stats (origin->destination aggregates per HS6)
4. Uses incremental processing by default (watermark-based)
5. Supports full rebuild mode for initial setup or corrections
6. Integrates with pipeline_runs for Control Tower visibility

Usage:
    python scripts/run_build_price_and_lanes.py
    python scripts/run_build_price_and_lanes.py --full-rebuild
    python scripts/run_build_price_and_lanes.py --corridors-only
    python scripts/run_build_price_and_lanes.py --lanes-only

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.analytics.build_price_and_lanes import PriceAndLanesBuilder, run_build_price_and_lanes
from etl.db_utils import DatabaseManager
from etl.pipeline_tracking import track_pipeline_run, update_run_metrics


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
    print("  GTI-OS Data Platform - EPIC 6B: Price Corridors & Lane Stats")
    print("  Market Price Intelligence & Trade Lane Analysis")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the build results."""
    print()
    print("=" * 70)
    print("  PRICE & LANES BUILD SUMMARY")
    print("=" * 70)
    print()
    
    # Ledger stats
    print("  LEDGER DATA:")
    print(f"    Rows processed:       {result.get('ledger_rows_processed', 0):,}")
    print()
    
    # Price corridor stats
    print("  PRICE CORRIDORS:")
    print(f"    Created:              {result.get('corridor_records_created', 0):,}")
    print(f"    Updated:              {result.get('corridor_records_updated', 0):,}")
    print()
    
    # Lane stats
    print("  LANE STATS:")
    print(f"    Created:              {result.get('lane_records_created', 0):,}")
    print(f"    Updated:              {result.get('lane_records_updated', 0):,}")
    print()
    
    # Errors
    errors = result.get('errors', [])
    if errors:
        print("  ERRORS:")
        for error in errors[:10]:  # Show max 10 errors
            print(f"    - {error}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more errors")
        print()
    
    # Timing
    print(f"  ELAPSED TIME: {elapsed_seconds:.2f} seconds")
    print()
    print("=" * 70)
    
    # Status
    total_records = (
        result.get('corridor_records_created', 0) + 
        result.get('corridor_records_updated', 0) +
        result.get('lane_records_created', 0) + 
        result.get('lane_records_updated', 0)
    )
    
    if errors:
        print("  STATUS: COMPLETED WITH ERRORS")
    elif total_records == 0:
        print("  STATUS: NO RECORDS TO UPDATE (data is current)")
    else:
        print(f"  STATUS: SUCCESS ({total_records} records processed)")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the price & lanes builder."""
    parser = argparse.ArgumentParser(
        description='EPIC 6B: Build Price Corridors & Lane Stats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Incremental build (default)
  %(prog)s --full-rebuild       # Rebuild all records from scratch
  %(prog)s --corridors-only     # Only build price corridors
  %(prog)s --lanes-only         # Only build lane stats

The builder will:
  1. Query global_trades_ledger for shipments with valid prices
  2. Compute price percentiles (min, p25, median, p75, max) per corridor
  3. Compute lane aggregates (shipments, value, TEU) per trade route
  4. UPSERT records into price_corridor and lane_stats tables
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/db_config.yml',
        help='Path to database configuration file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--full-rebuild',
        action='store_true',
        help='Rebuild all records from scratch (ignore watermarks)'
    )
    
    parser.add_argument(
        '--corridors-only',
        action='store_true',
        help='Only build price corridors'
    )
    
    parser.add_argument(
        '--lanes-only',
        action='store_true',
        help='Only build lane stats'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.corridors_only and args.lanes_only:
        print("Error: Cannot specify both --corridors-only and --lanes-only")
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
    mode = "FULL REBUILD" if args.full_rebuild else "INCREMENTAL"
    scope = "ALL"
    if args.corridors_only:
        scope = "CORRIDORS ONLY"
    elif args.lanes_only:
        scope = "LANES ONLY"
    
    logger.info("Configuration:")
    logger.info(f"  Database config: {args.config}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Scope: {scope}")
    
    # Run builder with pipeline tracking
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        
        with track_pipeline_run(db, 'build_price_and_lanes', metadata={'mode': mode, 'scope': scope}) as run_id:
            builder = PriceAndLanesBuilder(db)
            
            if args.corridors_only:
                # Build corridors only
                min_date, max_date = builder._get_processing_window(args.full_rebuild)
                if min_date and max_date:
                    builder._build_price_corridors(min_date, max_date, args.full_rebuild)
                    builder._update_watermarks(max_date)
            elif args.lanes_only:
                # Build lanes only
                min_date, max_date = builder._get_processing_window(args.full_rebuild)
                if min_date and max_date:
                    builder._build_lane_stats(min_date, max_date, args.full_rebuild)
                    builder._update_watermarks(max_date)
            else:
                # Build all
                builder.build_all(args.full_rebuild)
            
            result = builder.summary.to_dict()
            
            # Update run metrics
            total_created = result.get('corridor_records_created', 0) + result.get('lane_records_created', 0)
            total_updated = result.get('corridor_records_updated', 0) + result.get('lane_records_updated', 0)
            
            update_run_metrics(
                db, run_id,
                rows_processed=result.get('ledger_rows_processed', 0),
                rows_created=total_created,
                rows_updated=total_updated
            )
        
        db.close()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print_summary(result, elapsed)
        
        # Exit code based on errors
        if result.get('errors'):
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Price & lanes build failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  BUILD FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
