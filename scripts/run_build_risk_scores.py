#!/usr/bin/env python
"""
EPIC 6C - Build Risk Scores Orchestration Script
=================================================
CLI script to build risk scores from global_trades_ledger.

This script:
1. Reads from global_trades_ledger and analytics tables
2. Computes shipment-level risks (price anomalies, lane anomalies)
3. Computes buyer-level risks (volume spikes, ghost entities, free email)
4. Uses incremental processing by default (watermark-based)
5. Supports full refresh mode for initial setup or corrections
6. Integrates with pipeline_runs for Control Tower visibility

Usage:
    python scripts/run_build_risk_scores.py
    python scripts/run_build_risk_scores.py --full-refresh
    python scripts/run_build_risk_scores.py --countries INDIA KENYA
    python scripts/run_build_risk_scores.py --engine-version RISK_ENGINE_V2

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.analytics.build_risk_scores import (
    RiskEngineBuilder, 
    run_build_risk_scores,
    DEFAULT_ENGINE_VERSION
)
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
    print("  GTI-OS Data Platform - EPIC 6C: Global Risk Engine")
    print("  Shipment & Entity Risk Analysis")
    print("=" * 70)
    print()


def print_summary(result: dict, elapsed_seconds: float):
    """Print a formatted summary of the build results."""
    print()
    print("=" * 70)
    print("  RISK ENGINE BUILD SUMMARY")
    print("=" * 70)
    print()
    
    # Shipment-level stats
    print("  SHIPMENT-LEVEL RISKS:")
    print(f"    Shipments analyzed:   {result.get('shipments_processed', 0):,}")
    print(f"    Risks created:        {result.get('shipment_risks_created', 0):,}")
    print(f"    Risks updated:        {result.get('shipment_risks_updated', 0):,}")
    print()
    
    # Buyer-level stats
    print("  BUYER-LEVEL RISKS:")
    print(f"    Buyers analyzed:      {result.get('buyers_processed', 0):,}")
    print(f"    Risks created:        {result.get('buyer_risks_created', 0):,}")
    print(f"    Risks updated:        {result.get('buyer_risks_updated', 0):,}")
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
    total_created = (
        result.get('shipment_risks_created', 0) + 
        result.get('buyer_risks_created', 0)
    )
    total_updated = (
        result.get('shipment_risks_updated', 0) + 
        result.get('buyer_risks_updated', 0)
    )
    
    if errors:
        print("  STATUS: COMPLETED WITH ERRORS")
    elif total_created == 0 and total_updated == 0:
        print("  STATUS: NO RISKS TO UPDATE (data is current)")
    else:
        print(f"  STATUS: SUCCESS ({total_created} created, {total_updated} updated)")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the risk engine builder."""
    parser = argparse.ArgumentParser(
        description='EPIC 6C: Build Risk Scores',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Incremental build (default)
  %(prog)s --full-refresh               # Rebuild all risk scores from scratch
  %(prog)s --countries INDIA KENYA      # Only process specific countries
  %(prog)s --engine-version V2          # Use custom engine version

Risk Rules Computed:
  SHIPMENT-LEVEL:
    - UNDER_INVOICE: Price below corridor (z < -2)
    - OVER_INVOICE: Price above corridor (z > 2)
    - WEIRD_LANE: Unusual trade route

  BUYER-LEVEL:
    - VOLUME_SPIKE: Sudden volume increase
    - GHOST_ENTITY: High volume, no digital presence
    - FREE_EMAIL: High volume with free email provider
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/db_config.yml',
        help='Path to database configuration file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--full-refresh',
        action='store_true',
        help='Rebuild all risk scores from scratch (ignore watermarks)'
    )
    
    parser.add_argument(
        '--countries',
        nargs='+',
        help='Optional: Only process specific reporting countries'
    )
    
    parser.add_argument(
        '--engine-version',
        default=DEFAULT_ENGINE_VERSION,
        help=f'Risk engine version string (default: {DEFAULT_ENGINE_VERSION})'
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging(args.log_level)
    print_banner()
    
    # Verify config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Log configuration
    mode = "FULL REFRESH" if args.full_refresh else "INCREMENTAL"
    countries_str = ", ".join(args.countries) if args.countries else "ALL"
    
    logger.info("Configuration:")
    logger.info(f"  Database config: {args.config}")
    logger.info(f"  Mode: {mode}")
    logger.info(f"  Engine version: {args.engine_version}")
    logger.info(f"  Countries: {countries_str}")
    
    # Run risk engine with pipeline tracking
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        
        metadata = {
            'mode': mode, 
            'engine_version': args.engine_version,
            'countries': args.countries or 'ALL'
        }
        
        with track_pipeline_run(db, 'risk_engine', countries=args.countries, metadata=metadata) as run_id:
            builder = RiskEngineBuilder(db, args.engine_version)
            builder.build_all(args.full_refresh, args.countries)
            
            result = builder.summary.to_dict()
            
            # Update run metrics
            total_processed = result.get('shipments_processed', 0) + result.get('buyers_processed', 0)
            total_created = result.get('shipment_risks_created', 0) + result.get('buyer_risks_created', 0)
            total_updated = result.get('shipment_risks_updated', 0) + result.get('buyer_risks_updated', 0)
            
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
        logger.error(f"Risk engine build failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  RISK ENGINE BUILD FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
