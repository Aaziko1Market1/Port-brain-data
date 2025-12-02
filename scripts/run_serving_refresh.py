#!/usr/bin/env python
"""
EPIC 7A - Serving Views Refresh Script
=======================================
Refreshes materialized views for the LLM/API serving layer.

This script:
1. Refreshes mv_country_hs_month_summary (concurrently by default)
2. Logs to pipeline_runs for Control Tower visibility
3. Reports row counts and timing

Usage:
    python scripts/run_serving_refresh.py
    python scripts/run_serving_refresh.py --no-concurrent
    python scripts/run_serving_refresh.py --log-level DEBUG

Part of GTI-OS Data Platform Architecture v1.0
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    print("  GTI-OS Data Platform - EPIC 7A: Serving Views Refresh")
    print("  LLM/API Serving Layer Maintenance")
    print("=" * 70)
    print()


def get_view_stats(db: DatabaseManager) -> dict:
    """Get row counts and stats from serving views."""
    stats = {}
    
    # Materialized view count
    result = db.execute_query("SELECT COUNT(*) FROM mv_country_hs_month_summary")
    stats['mv_country_hs_month_summary'] = result[0][0] if result else 0
    
    # Dashboard view count (same as MV)
    stats['vw_country_hs_dashboard'] = stats['mv_country_hs_month_summary']
    
    # Buyer 360 count
    result = db.execute_query("SELECT COUNT(*) FROM vw_buyer_360")
    stats['vw_buyer_360'] = result[0][0] if result else 0
    
    # Country count in MV
    result = db.execute_query("""
        SELECT COUNT(DISTINCT reporting_country) 
        FROM mv_country_hs_month_summary
    """)
    stats['unique_countries'] = result[0][0] if result else 0
    
    # HS code count in MV
    result = db.execute_query("""
        SELECT COUNT(DISTINCT hs_code_6) 
        FROM mv_country_hs_month_summary
    """)
    stats['unique_hs_codes'] = result[0][0] if result else 0
    
    # Year-month combos
    result = db.execute_query("""
        SELECT COUNT(DISTINCT (year, month)) 
        FROM mv_country_hs_month_summary
    """)
    stats['unique_year_months'] = result[0][0] if result else 0
    
    return stats


def refresh_materialized_views(db: DatabaseManager, concurrent: bool = True) -> dict:
    """
    Refresh all materialized views in the serving layer.
    
    Args:
        db: DatabaseManager instance
        concurrent: If True, use CONCURRENTLY (requires unique index)
        
    Returns:
        Dictionary with refresh results
    """
    logger = logging.getLogger(__name__)
    results = {
        'refreshed': [],
        'errors': []
    }
    
    # List of materialized views to refresh
    materialized_views = [
        'mv_country_hs_month_summary'
    ]
    
    for mv_name in materialized_views:
        try:
            if concurrent:
                logger.info(f"Refreshing {mv_name} (CONCURRENTLY)...")
                refresh_sql = f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv_name}"
            else:
                logger.info(f"Refreshing {mv_name}...")
                refresh_sql = f"REFRESH MATERIALIZED VIEW {mv_name}"
            
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(refresh_sql)
            
            results['refreshed'].append(mv_name)
            logger.info(f"  ✓ {mv_name} refreshed successfully")
            
        except Exception as e:
            error_msg = f"{mv_name}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"  ✗ Failed to refresh {mv_name}: {e}")
            
            # If CONCURRENTLY failed, try without it
            if concurrent and 'cannot refresh' in str(e).lower():
                logger.info(f"  Retrying {mv_name} without CONCURRENTLY...")
                try:
                    with db.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(f"REFRESH MATERIALIZED VIEW {mv_name}")
                    results['refreshed'].append(mv_name)
                    results['errors'].pop()  # Remove the error
                    logger.info(f"  ✓ {mv_name} refreshed successfully (non-concurrent)")
                except Exception as e2:
                    results['errors'].append(f"{mv_name} (retry): {str(e2)}")
                    logger.error(f"  ✗ Retry failed: {e2}")
    
    return results


def print_summary(stats: dict, refresh_results: dict, elapsed_seconds: float):
    """Print a formatted summary of the refresh results."""
    print()
    print("=" * 70)
    print("  SERVING VIEWS REFRESH SUMMARY")
    print("=" * 70)
    print()
    
    # View counts
    print("  VIEW ROW COUNTS:")
    print(f"    mv_country_hs_month_summary:  {stats.get('mv_country_hs_month_summary', 0):,}")
    print(f"    vw_country_hs_dashboard:      {stats.get('vw_country_hs_dashboard', 0):,}")
    print(f"    vw_buyer_360:                 {stats.get('vw_buyer_360', 0):,}")
    print()
    
    # Dashboard coverage
    print("  DASHBOARD COVERAGE:")
    print(f"    Unique countries:     {stats.get('unique_countries', 0)}")
    print(f"    Unique HS codes:      {stats.get('unique_hs_codes', 0):,}")
    print(f"    Year-month periods:   {stats.get('unique_year_months', 0)}")
    print()
    
    # Refresh results
    print("  REFRESH RESULTS:")
    print(f"    Views refreshed:      {len(refresh_results.get('refreshed', []))}")
    if refresh_results.get('errors'):
        print(f"    Errors:               {len(refresh_results['errors'])}")
        for err in refresh_results['errors'][:5]:
            print(f"      - {err}")
    print()
    
    # Timing
    print(f"  ELAPSED TIME: {elapsed_seconds:.2f} seconds")
    print()
    print("=" * 70)
    
    # Status
    if refresh_results.get('errors'):
        print("  STATUS: COMPLETED WITH ERRORS")
    else:
        print("  STATUS: SUCCESS")
    
    print("=" * 70)
    print()


def main():
    """Main entry point for the serving refresh script."""
    parser = argparse.ArgumentParser(
        description='EPIC 7A: Refresh Serving Views',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Refresh with CONCURRENTLY (default)
  %(prog)s --no-concurrent     # Refresh without CONCURRENTLY (for empty MVs)
  %(prog)s --log-level DEBUG   # Verbose logging

Materialized Views Refreshed:
  - mv_country_hs_month_summary (Country/HS/Month aggregates)

Views (no refresh needed):
  - vw_buyer_360 (Buyer 360 intelligence)
  - vw_country_hs_dashboard (Dashboard layer on MV)
        """
    )
    
    parser.add_argument(
        '--config', 
        default='config/db_config.yml',
        help='Path to database configuration file (default: config/db_config.yml)'
    )
    
    parser.add_argument(
        '--no-concurrent',
        action='store_true',
        help='Use non-concurrent refresh (required for first refresh or empty MVs)'
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
    concurrent = not args.no_concurrent
    logger.info("Configuration:")
    logger.info(f"  Database config: {args.config}")
    logger.info(f"  Concurrent refresh: {concurrent}")
    
    # Run refresh with pipeline tracking
    start_time = datetime.now()
    
    try:
        db = DatabaseManager(args.config)
        
        metadata = {
            'concurrent': concurrent,
            'views_refreshed': ['mv_country_hs_month_summary']
        }
        
        with track_pipeline_run(db, 'serving_views', metadata=metadata) as run_id:
            # Refresh materialized views
            refresh_results = refresh_materialized_views(db, concurrent=concurrent)
            
            # Get stats after refresh
            stats = get_view_stats(db)
            
            # Update run metrics
            total_rows = stats.get('mv_country_hs_month_summary', 0)
            update_run_metrics(
                db, run_id,
                rows_processed=total_rows,
                metadata={
                    'buyer_360_count': stats.get('vw_buyer_360', 0),
                    'unique_countries': stats.get('unique_countries', 0),
                    'unique_hs_codes': stats.get('unique_hs_codes', 0)
                }
            )
        
        db.close()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print_summary(stats, refresh_results, elapsed)
        
        # Exit code based on errors
        if refresh_results.get('errors'):
            sys.exit(1)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Serving refresh failed: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        print()
        print("=" * 70)
        print(f"  SERVING REFRESH FAILED")
        print(f"  Error: {e}")
        print(f"  Elapsed: {elapsed:.2f} seconds")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
