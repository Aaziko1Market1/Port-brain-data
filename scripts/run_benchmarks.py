#!/usr/bin/env python3
"""
EPIC 8 - Performance Benchmark Runner
======================================
Runs benchmark queries against the GTI-OS database and reports timings.

Usage:
    python scripts/run_benchmarks.py                    # Run all benchmarks
    python scripts/run_benchmarks.py --mode small      # Real data only (~11k rows)
    python scripts/run_benchmarks.py --mode large      # With synthetic data
    python scripts/run_benchmarks.py --iterations 5    # Run 5 iterations per query
    python scripts/run_benchmarks.py --explain         # Show EXPLAIN ANALYZE for slow queries
"""

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark query."""
    name: str
    query: str
    rows_returned: int
    min_time_ms: float
    max_time_ms: float
    avg_time_ms: float
    iterations: int
    error: Optional[str] = None


def load_benchmark_queries(sql_file: Path) -> List[Tuple[str, str]]:
    """Load benchmark queries from SQL file.
    
    Expected format:
    -- query_name
    SELECT ...;
    
    Returns list of (name, query) tuples.
    """
    queries = []
    current_name = None
    current_query_lines = []
    
    with open(sql_file, 'r') as f:
        content = f.read()
    
    # Find all query blocks
    # Pattern: -- query_name\n followed by SQL until next -- query_name or end
    pattern = r'^-- (\w+)\n((?:(?!^-- \w+)[\s\S])*)'
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines and comment-only lines (not query names)
        if not line or (line.startswith('--') and not re.match(r'^-- \w+$', line)):
            continue
        
        # Check if this is a query name marker (-- name with single word)
        match = re.match(r'^-- (\w+)$', line)
        if match:
            # Save previous query if exists
            if current_name and current_query_lines:
                query = ' '.join(current_query_lines).strip()
                if query:
                    queries.append((current_name, query))
            
            # Start new query
            current_name = match.group(1)
            current_query_lines = []
        elif current_name:
            # Add line to current query
            current_query_lines.append(line)
    
    # Save last query
    if current_name and current_query_lines:
        query = ' '.join(current_query_lines).strip()
        if query:
            queries.append((current_name, query))
    
    return queries


def run_single_benchmark(
    db: DatabaseManager, 
    name: str, 
    query: str, 
    iterations: int = 3
) -> BenchmarkResult:
    """Run a single benchmark query multiple times and collect timing stats."""
    
    times = []
    rows = 0
    error = None
    
    # Warm up run (discard timing)
    try:
        result = db.execute_query(query)
        rows = len(result) if result else 0
    except Exception as e:
        return BenchmarkResult(
            name=name,
            query=query,
            rows_returned=0,
            min_time_ms=0,
            max_time_ms=0,
            avg_time_ms=0,
            iterations=0,
            error=str(e)
        )
    
    # Timed runs
    for i in range(iterations):
        start = time.perf_counter()
        try:
            result = db.execute_query(query)
            rows = len(result) if result else 0
        except Exception as e:
            error = str(e)
            break
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)
    
    if not times:
        return BenchmarkResult(
            name=name,
            query=query,
            rows_returned=rows,
            min_time_ms=0,
            max_time_ms=0,
            avg_time_ms=0,
            iterations=0,
            error=error
        )
    
    return BenchmarkResult(
        name=name,
        query=query,
        rows_returned=rows,
        min_time_ms=min(times),
        max_time_ms=max(times),
        avg_time_ms=sum(times) / len(times),
        iterations=len(times),
        error=error
    )


def get_explain_analyze(db: DatabaseManager, query: str) -> str:
    """Get EXPLAIN ANALYZE output for a query."""
    explain_query = f"EXPLAIN ANALYZE {query}"
    try:
        result = db.execute_query(explain_query)
        return '\n'.join([row[0] for row in result])
    except Exception as e:
        return f"EXPLAIN failed: {e}"


def get_dataset_stats(db: DatabaseManager) -> dict:
    """Get current dataset statistics."""
    query = """
        SELECT 
            COUNT(*) as total_rows,
            COUNT(*) FILTER (WHERE source_format = 'SYNTHETIC') as synthetic_rows,
            COUNT(*) FILTER (WHERE source_format != 'SYNTHETIC' OR source_format IS NULL) as real_rows,
            COUNT(DISTINCT reporting_country) as countries,
            MIN(year) as min_year,
            MAX(year) as max_year
        FROM global_trades_ledger
    """
    result = db.execute_query(query)
    if result:
        return {
            'total_rows': result[0][0],
            'synthetic_rows': result[0][1] or 0,
            'real_rows': result[0][2] or 0,
            'countries': result[0][3],
            'min_year': result[0][4],
            'max_year': result[0][5]
        }
    return {}


def print_results(
    results: List[BenchmarkResult], 
    stats: dict, 
    mode: str,
    show_explain: bool = False,
    db: DatabaseManager = None
):
    """Print benchmark results in a formatted table."""
    
    print("\n" + "=" * 90)
    print("  EPIC 8 - PERFORMANCE BENCHMARK RESULTS")
    print("=" * 90)
    
    # Dataset info
    print(f"\n  Mode:           {mode.upper()}")
    print(f"  Total Rows:     {stats.get('total_rows', 0):,}")
    print(f"  Real Rows:      {stats.get('real_rows', 0):,}")
    print(f"  Synthetic Rows: {stats.get('synthetic_rows', 0):,}")
    print(f"  Countries:      {stats.get('countries', 0)}")
    print(f"  Year Range:     {stats.get('min_year')} - {stats.get('max_year')}")
    
    # Results table header
    print("\n" + "-" * 90)
    print(f"  {'Query Name':<30} {'Rows':>10} {'Min (ms)':>12} {'Avg (ms)':>12} {'Max (ms)':>12} {'Status':<10}")
    print("-" * 90)
    
    slow_queries = []
    
    for r in results:
        if r.error:
            status = "ERROR"
        elif r.avg_time_ms > 2000:
            status = "SLOW!"
            slow_queries.append(r)
        elif r.avg_time_ms > 500:
            status = "WARN"
        else:
            status = "OK"
        
        print(f"  {r.name:<30} {r.rows_returned:>10,} {r.min_time_ms:>12.1f} {r.avg_time_ms:>12.1f} {r.max_time_ms:>12.1f} {status:<10}")
        
        if r.error:
            print(f"      Error: {r.error[:60]}...")
    
    print("-" * 90)
    
    # Summary
    total_time = sum(r.avg_time_ms for r in results if not r.error)
    passed = sum(1 for r in results if not r.error and r.avg_time_ms <= 2000)
    failed = len(results) - passed
    
    print(f"\n  Total Queries:  {len(results)}")
    print(f"  Passed (<2s):   {passed}")
    print(f"  Failed/Slow:    {failed}")
    print(f"  Total Time:     {total_time:.0f} ms")
    
    # Show EXPLAIN for slow queries
    if show_explain and slow_queries and db:
        print("\n" + "=" * 90)
        print("  EXPLAIN ANALYZE FOR SLOW QUERIES")
        print("=" * 90)
        
        for r in slow_queries:
            print(f"\n  Query: {r.name} (avg: {r.avg_time_ms:.0f}ms)")
            print("-" * 60)
            explain = get_explain_analyze(db, r.query)
            for line in explain.split('\n')[:20]:  # Limit output
                print(f"    {line}")
            if len(explain.split('\n')) > 20:
                print("    ... (truncated)")
    
    print("\n" + "=" * 90)
    
    return slow_queries


def run_benchmarks(
    db: DatabaseManager,
    sql_file: Path,
    iterations: int = 3,
    mode: str = 'auto',
    show_explain: bool = False
) -> List[BenchmarkResult]:
    """Run all benchmark queries and return results."""
    
    # Load queries
    queries = load_benchmark_queries(sql_file)
    logger.info(f"Loaded {len(queries)} benchmark queries from {sql_file}")
    
    # Get dataset stats
    stats = get_dataset_stats(db)
    
    # Auto-detect mode
    if mode == 'auto':
        if stats.get('synthetic_rows', 0) > 0:
            mode = 'large'
        else:
            mode = 'small'
    
    logger.info(f"Running benchmarks in {mode} mode...")
    logger.info(f"Dataset: {stats.get('total_rows', 0):,} rows ({stats.get('synthetic_rows', 0):,} synthetic)")
    
    # Run benchmarks
    results = []
    for name, query in queries:
        logger.info(f"Running: {name}...")
        result = run_single_benchmark(db, name, query, iterations=iterations)
        results.append(result)
        
        if result.error:
            logger.warning(f"  {name}: ERROR - {result.error[:50]}")
        else:
            logger.info(f"  {name}: {result.avg_time_ms:.1f}ms avg ({result.rows_returned} rows)")
    
    # Print results
    slow_queries = print_results(results, stats, mode, show_explain=show_explain, db=db)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run GTI-OS performance benchmarks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks with default settings
  python scripts/run_benchmarks.py

  # Run with more iterations for accuracy
  python scripts/run_benchmarks.py --iterations 5

  # Show EXPLAIN ANALYZE for slow queries
  python scripts/run_benchmarks.py --explain

  # Specify mode explicitly
  python scripts/run_benchmarks.py --mode large
        """
    )
    
    parser.add_argument('--mode', choices=['small', 'large', 'auto'], default='auto',
                       help='Benchmark mode: small (real data only), large (with synthetic), auto (detect)')
    parser.add_argument('--iterations', type=int, default=3,
                       help='Number of iterations per query (default: 3)')
    parser.add_argument('--explain', action='store_true',
                       help='Show EXPLAIN ANALYZE for queries taking > 2s')
    parser.add_argument('--sql-file', type=str, default='db/benchmark_queries.sql',
                       help='Path to SQL file with benchmark queries')
    
    args = parser.parse_args()
    
    # Resolve SQL file path
    sql_file = Path(args.sql_file)
    if not sql_file.is_absolute():
        sql_file = Path(__file__).parent.parent / sql_file
    
    if not sql_file.exists():
        logger.error(f"SQL file not found: {sql_file}")
        return 1
    
    # Initialize database
    config_path = os.environ.get('DB_CONFIG_PATH', 'config/db_config.yml')
    db = DatabaseManager(config_path)
    
    # Run benchmarks
    results = run_benchmarks(
        db=db,
        sql_file=sql_file,
        iterations=args.iterations,
        mode=args.mode,
        show_explain=args.explain
    )
    
    # Return exit code based on results
    slow_count = sum(1 for r in results if not r.error and r.avg_time_ms > 2000)
    error_count = sum(1 for r in results if r.error)
    
    if error_count > 0:
        return 2  # Errors occurred
    elif slow_count > 0:
        return 1  # Some queries are slow
    else:
        return 0  # All queries passed


if __name__ == '__main__':
    sys.exit(main())
