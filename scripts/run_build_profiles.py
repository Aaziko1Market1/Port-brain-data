#!/usr/bin/env python
"""
EPIC 6A - Build Profiles Orchestration Script
==============================================
CLI script to build buyer and exporter profiles from global_trades_ledger.

This script:
1. Reads from global_trades_ledger (respects partitioning)
2. Computes aggregated profiles for buyers and exporters
3. Uses incremental processing by default (only new/changed data)
4. Supports full rebuild mode for initial setup or corrections
5. Integrates with pipeline_runs for Control Tower visibility

Usage:
    python scripts/run_build_profiles.py
    python scripts/run_build_profiles.py --full-rebuild
    python scripts/run_build_profiles.py --buyers-only
    python scripts/run_build_profiles.py --exporters-only

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.analytics.build_profiles import ProfileBuilder, run_build_profiles
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
    print("  GTI-OS Data Platform - EPIC 6A: Build Profiles")
    print("  Buyer & Exporter Profile Generation")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the profile build results."""
    print()
    print("=" * 70)
    print("  PROFILE BUILD SUMMARY")
    print("=" * 70)
    print()
    
    # Buyer stats
    print("  BUYER PROFILES:")
    print(f"    Processed:    {result.get('buyers_processed', 0):,}")
    print(f"    Created:      {result.get('buyers_created', 0):,}")
    print(f"    Updated:      {result.get('buyers_updated', 0):,}")
    print()
    
    # Exporter stats
    print("  EXPORTER PROFILES:")
    print(f"    Processed:    {result.get('exporters_processed', 0):,}")
    print(f"    Created:      {result.get('exporters_created', 0):,}")
    print(f"    Updated:      {result.get('exporters_updated', 0):,}")
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
    total_processed = result.get('buyers_processed', 0) + result.get('exporters_processed', 0)
    total_created = result.get('buyers_created', 0) + result.get('exporters_created', 0)
    total_updated = result.get('buyers_updated', 0) + result.get('exporters_updated', 0)
    
    if errors:
        print("  STATUS: COMPLETED WITH ERRORS")
    elif total_processed == 0:
        print("  STATUS: NO PROFILES TO UPDATE (data is current)")
    else:
        print(f"  STATUS: SUCCESS ({total_created} created, {total_updated} updated)")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the profile builder."""
    parser = argparse.ArgumentParser(
        description='EPIC 6A: Build Buyer & Exporter Profiles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Incremental build (default)
  %(prog)s --full-rebuild       # Rebuild all profiles from scratch
  %(prog)s --buyers-only        # Only build buyer profiles
  %(prog)s --exporters-only     # Only build exporter profiles

The profile builder will:
  1. Query global_trades_ledger for buyer/exporter data
  2. Compute aggregated metrics (shipments, values, top HS codes, etc.)
  3. Assign persona labels (buyers) and scores (exporters)
  4. UPSERT profiles into buyer_profile and exporter_profile tables
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
        help='Rebuild all profiles from scratch (ignore incremental markers)'
    )
    
    parser.add_argument(
        '--buyers-only',
        action='store_true',
        help='Only build buyer profiles'
    )
    
    parser.add_argument(
        '--exporters-only',
        action='store_true',
        help='Only build exporter profiles'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate mutually exclusive options
    if args.buyers_only and args.exporters_only:
        print("Error: Cannot specify both --buyers-only and --exporters-only")
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
    if args.buyers_only:
        scope = "BUYERS ONLY"
    elif args.exporters_only:
        scope = "EXPORTERS ONLY"
    
    logger.info("Configuration:")
    logger.info(f"  Database config: {args.config}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Scope: {scope}")
    
    # Run profile builder with pipeline tracking
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        
        with track_pipeline_run(db, 'build_profiles', metadata={'mode': mode, 'scope': scope}) as run_id:
            builder = ProfileBuilder(db)
            
            if args.buyers_only:
                builder._build_buyer_profiles(args.full_rebuild)
                builder._update_markers()
            elif args.exporters_only:
                builder._build_exporter_profiles(args.full_rebuild)
                builder._update_markers()
            else:
                builder.build_all(args.full_rebuild)
            
            result = builder.summary.to_dict()
            
            # Update run metrics
            total_processed = result.get('buyers_processed', 0) + result.get('exporters_processed', 0)
            total_created = result.get('buyers_created', 0) + result.get('exporters_created', 0)
            total_updated = result.get('buyers_updated', 0) + result.get('exporters_updated', 0)
            
            update_run_metrics(
                db, run_id,
                rows_processed=total_processed,
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
        logger.error(f"Profile build failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  PROFILE BUILD FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
