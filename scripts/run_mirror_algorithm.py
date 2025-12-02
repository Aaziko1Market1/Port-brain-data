#!/usr/bin/env python
"""
EPIC 5 - Global Mirror Algorithm Orchestration Script
======================================================
CLI script to run the mirror matching algorithm for inferring hidden buyers.

This script:
1. Identifies exports with hidden/unknown buyers
2. Matches them to corresponding imports in destination country
3. Infers the true buyer from the matched import
4. Updates the export with the inferred buyer_uuid
5. Logs matches in mirror_match_log

Usage:
    python scripts/run_mirror_algorithm.py
    python scripts/run_mirror_algorithm.py --countries INDIA KENYA
    python scripts/run_mirror_algorithm.py --min-score 75 --qty-tolerance 10
    python scripts/run_mirror_algorithm.py --min-lag-days 10 --max-lag-days 60

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.mirror.mirror_algorithm import run_mirror_algorithm
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
    print("  GTI-OS Data Platform - EPIC 5: Global Mirror Algorithm")
    print("  Hidden Buyer Inference via Export-Import Matching")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the matching results."""
    print()
    print("=" * 70)
    print("  MIRROR ALGORITHM SUMMARY")
    print("=" * 70)
    print()
    
    # Overall stats
    print("  EXPORT ANALYSIS:")
    print(f"    Exports scanned:           {result.get('exports_scanned', 0):,}")
    print(f"    Exports eligible (hidden): {result.get('exports_eligible', 0):,}")
    print()
    
    # Matching stats
    print("  MATCHING RESULTS:")
    print(f"    Candidate pairs evaluated: {result.get('candidate_pairs_evaluated', 0):,}")
    print(f"    Matches accepted:          {result.get('matches_accepted', 0):,}")
    print(f"    Skipped (ambiguous):       {result.get('matches_skipped_ambiguous', 0):,}")
    print(f"    Skipped (low score):       {result.get('matches_skipped_low_score', 0):,}")
    print(f"    Skipped (no candidates):   {result.get('matches_skipped_no_candidates', 0):,}")
    print()
    
    # Score distribution
    score_dist = result.get('score_distribution', {})
    if score_dist:
        print("  SCORE DISTRIBUTION:")
        for bucket in sorted(score_dist.keys()):
            print(f"    {bucket}: {score_dist[bucket]:,} matches")
        print()
    
    # Top routes
    top_routes = result.get('top_routes', [])
    if top_routes:
        print("  TOP 5 ROUTES BY MATCH COUNT:")
        for route in top_routes:
            print(f"    {route['origin']} -> {route['destination']} "
                  f"(HS:{route['hs_code_6']}): {route['match_count']} matches")
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
        matches = result.get('matches_accepted', 0)
        if matches == 0:
            print("  STATUS: NO MATCHES FOUND")
        else:
            print(f"  STATUS: SUCCESS ({matches} buyers inferred)")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the mirror algorithm."""
    parser = argparse.ArgumentParser(
        description='EPIC 5: Global Mirror Algorithm',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with defaults
  %(prog)s --countries INDIA KENYA            # Filter by countries
  %(prog)s --min-score 75                     # Stricter matching
  %(prog)s --qty-tolerance 10                 # ±10%% quantity tolerance
  %(prog)s --min-lag-days 10 --max-lag-days 60  # Custom date window

The mirror algorithm will:
  1. Identify exports with hidden buyers (TO ORDER, BANK, etc.)
  2. Find matching imports in destination country (by HS6, qty, date)
  3. Score each (export, import) pair
  4. Accept unambiguous matches above the minimum score
  5. Update export with inferred buyer_uuid from matched import
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/db_config.yml',
        help='Path to database configuration file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--countries', 
        nargs='+',
        metavar='COUNTRY',
        help='Countries to process (default: all)'
    )
    
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=5000,
        help='Number of exports to process per batch (default: 5000)'
    )
    
    parser.add_argument(
        '--min-score', 
        type=int, 
        default=70,
        help='Minimum score to accept a match, 0-100 (default: 70)'
    )
    
    parser.add_argument(
        '--qty-tolerance', 
        type=float, 
        default=5.0,
        help='Quantity tolerance in percentage (default: 5.0 for ±5%%)'
    )
    
    parser.add_argument(
        '--min-lag-days', 
        type=int, 
        default=15,
        help='Minimum days between export and import (default: 15)'
    )
    
    parser.add_argument(
        '--max-lag-days', 
        type=int, 
        default=45,
        help='Maximum days between export and import (default: 45)'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min_score < 0 or args.min_score > 100:
        print("Error: --min-score must be between 0 and 100")
        sys.exit(1)
    
    if args.qty_tolerance < 0:
        print("Error: --qty-tolerance must be non-negative")
        sys.exit(1)
    
    if args.min_lag_days < 0 or args.max_lag_days < args.min_lag_days:
        print("Error: Invalid lag days (min must be >= 0 and <= max)")
        sys.exit(1)
    
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
    logger.info(f"  Countries: {args.countries or 'all'}")
    logger.info(f"  Batch size: {args.batch_size:,}")
    logger.info(f"  Min score: {args.min_score}")
    logger.info(f"  Qty tolerance: ±{args.qty_tolerance}%")
    logger.info(f"  Date window: {args.min_lag_days}-{args.max_lag_days} days")
    
    # Run mirror algorithm with pipeline tracking
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        countries = args.countries or ['INDIA', 'KENYA', 'INDONESIA']
        
        with track_pipeline_run(db, 'mirror_algorithm', countries=countries) as run_id:
            result = run_mirror_algorithm(
                db_config_path=args.config,
                min_score=args.min_score,
                qty_tolerance_pct=args.qty_tolerance,
                min_lag_days=args.min_lag_days,
                max_lag_days=args.max_lag_days,
                batch_size=args.batch_size,
                country_filters=args.countries
            )
            
            # Update run metrics
            update_run_metrics(
                db, run_id,
                rows_processed=result.get('exports_scanned', 0),
                rows_created=result.get('matches_accepted', 0),
                rows_updated=result.get('matches_accepted', 0),
                rows_skipped=(
                    result.get('matches_skipped_ambiguous', 0) +
                    result.get('matches_skipped_low_score', 0) +
                    result.get('matches_skipped_no_candidates', 0)
                )
            )
        
        db.close()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print_summary(result, elapsed)
        
        # Exit code based on errors
        if result.get('errors'):
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Mirror algorithm failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  MIRROR ALGORITHM FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
