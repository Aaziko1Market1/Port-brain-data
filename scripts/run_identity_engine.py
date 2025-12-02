#!/usr/bin/env python
"""
EPIC 3 - Identity Engine Orchestration Script
==============================================
CLI script to run the organization identity resolution pipeline.

This script:
1. Reads database configuration
2. Runs the identity resolution engine
3. Logs comprehensive statistics
4. Outputs a summary of results

Usage:
    python scripts/run_identity_engine.py
    python scripts/run_identity_engine.py --batch-size 10000
    python scripts/run_identity_engine.py --log-level DEBUG
    python scripts/run_identity_engine.py --no-fuzzy
    python scripts/run_identity_engine.py --fuzzy-threshold 0.85

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.identity.resolve_organizations import run_identity_resolution
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
    print("  GTI-OS Data Platform - EPIC 3: Identity Engine")
    print("  Organization Resolution Pipeline")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the resolution results."""
    print()
    print("=" * 70)
    print("  IDENTITY RESOLUTION SUMMARY")
    print("=" * 70)
    print()
    
    # Organizations processed
    print("  ORGANIZATIONS PROCESSED:")
    print(f"    Distinct Buyers:     {result.get('total_buyers_processed', 0):,}")
    print(f"    Distinct Suppliers:  {result.get('total_suppliers_processed', 0):,}")
    print()
    
    # Matching results
    print("  MATCHING RESULTS:")
    print(f"    Exact Matches:       {result.get('existing_orgs_matched_exact', 0):,}")
    print(f"    Fuzzy Matches:       {result.get('existing_orgs_matched_fuzzy', 0):,}")
    print(f"    New Orgs Created:    {result.get('new_organizations_created', 0):,}")
    print(f"    Type → MIXED:        {result.get('type_updates_to_mixed', 0):,}")
    print()
    
    # Shipment updates
    print("  SHIPMENTS UPDATED:")
    print(f"    With buyer_uuid:     {result.get('shipments_updated_buyer_uuid', 0):,}")
    print(f"    With supplier_uuid:  {result.get('shipments_updated_supplier_uuid', 0):,}")
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
        total_processed = (
            result.get('total_buyers_processed', 0) + 
            result.get('total_suppliers_processed', 0)
        )
        if total_processed == 0:
            print("  STATUS: NO NEW ORGANIZATIONS TO PROCESS")
        else:
            print("  STATUS: SUCCESS")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the identity engine."""
    parser = argparse.ArgumentParser(
        description='EPIC 3: Identity Resolution Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run with defaults
  %(prog)s --batch-size 10000        # Larger batch size
  %(prog)s --log-level DEBUG         # Verbose logging
  %(prog)s --no-fuzzy                # Disable fuzzy matching
  %(prog)s --fuzzy-threshold 0.85    # Stricter fuzzy matching

The identity engine will:
  1. Extract buyer/supplier names from standardized shipments lacking UUIDs
  2. Normalize names for matching
  3. Match against existing organizations (exact, then fuzzy)
  4. Create new organizations for unmatched names
  5. Update type to MIXED for orgs in both roles
  6. Write UUIDs back to shipments
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
        default=5000,
        help='Number of records to process per batch (default: 5000)'
    )
    
    parser.add_argument(
        '--no-fuzzy', 
        action='store_true',
        help='Disable fuzzy matching (only use exact matches)'
    )
    
    parser.add_argument(
        '--fuzzy-threshold', 
        type=float, 
        default=0.8,
        help='Similarity threshold for fuzzy matching, 0.0-1.0 (default: 0.8)'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.fuzzy_threshold < 0.0 or args.fuzzy_threshold > 1.0:
        print("Error: --fuzzy-threshold must be between 0.0 and 1.0")
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
    logger.info(f"  Batch size: {args.batch_size:,}")
    logger.info(f"  Fuzzy matching: {'disabled' if args.no_fuzzy else 'enabled'}")
    if not args.no_fuzzy:
        logger.info(f"  Fuzzy threshold: {args.fuzzy_threshold}")
    
    # Run identity resolution
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        countries = ['INDIA', 'KENYA', 'INDONESIA']
        
        with track_pipeline_run(db, 'identity', countries=countries) as run_id:
            result = run_identity_resolution(
                db_config_path=args.config,
                batch_size=args.batch_size,
                enable_fuzzy=not args.no_fuzzy,
                fuzzy_threshold=args.fuzzy_threshold
            )
            
            # Update run metrics
            total_orgs = (
                result.get('total_buyers_processed', 0) + 
                result.get('total_suppliers_processed', 0)
            )
            update_run_metrics(
                db, run_id,
                rows_processed=total_orgs,
                rows_created=result.get('new_organizations_created', 0),
                rows_updated=(
                    result.get('shipments_updated_buyer_uuid', 0) +
                    result.get('shipments_updated_supplier_uuid', 0)
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
        logger.error(f"Identity resolution failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  IDENTITY RESOLUTION FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
