#!/usr/bin/env python3
"""
EPIC 8 - Synthetic Ledger Data Generator
=========================================
Generates large-scale synthetic trade data for performance testing.

SAFETY:
- Uses test-only countries (TESTLAND, FAKISTAN, etc.) to avoid mixing with real data
- Uses years 2020-2021 by default (before real Kenya/India data from 2023+)
- All synthetic data can be identified and wiped safely

Usage:
    python scripts/simulate_large_ledger.py --rows 1000000
    python scripts/simulate_large_ledger.py --rows 100000 --start-year 2020 --end-year 2021
    python scripts/simulate_large_ledger.py --wipe-simulated  # Remove all synthetic data
"""

import argparse
import logging
import os
import random
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path
from io import StringIO

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# SYNTHETIC DATA CONSTANTS
# ============================================================================

# Test-only countries (clearly fake, won't conflict with real data)
SYNTHETIC_COUNTRIES = [
    'TESTLAND', 'FAKISTAN', 'DEMOCR', 'SYNTHIA', 'MOCKOVIA',
    'PERF_NORTH', 'PERF_SOUTH', 'PERF_EAST', 'PERF_WEST', 'LOADTEST'
]

# Realistic HS code patterns (6-digit)
SYNTHETIC_HS_CODES = [
    '010101', '020110', '030211', '040110', '050100',
    '060110', '070110', '080111', '090111', '100110',
    '610910', '620110', '630110', '640110', '650100',
    '690710', '690721', '690890', '691110', '691200',
    '720110', '730110', '740110', '750110', '760110',
    '841110', '842110', '843110', '844110', '845110',
    '850110', '851110', '852110', '853110', '854110',
    '870110', '871110', '880110', '890110', '900110',
]

# Realistic buyer/supplier name patterns
BUYER_PATTERNS = [
    'TEST IMPORTS LTD', 'PERF TRADING CO', 'SYNTHETIC GOODS INC',
    'LOAD TEST ENTERPRISES', 'BENCHMARK SUPPLIES', 'SCALE TEST CORP',
    'MOCK INDUSTRIES', 'FAKE DISTRIBUTORS', 'DEMO TRADERS',
    'VOLUME TEST LLC', 'STRESS TEST IMPORTS', 'CAPACITY TRADERS'
]

SUPPLIER_PATTERNS = [
    'TEST EXPORTS PVT', 'PERF MANUFACTURING', 'SYNTHETIC PRODUCERS',
    'LOAD TEST FACTORY', 'BENCHMARK MAKERS', 'SCALE TEST MILLS',
    'MOCK FABRICATORS', 'FAKE PRODUCERS', 'DEMO SUPPLIERS',
    'VOLUME TEST EXPORTS', 'STRESS TEST FACTORY', 'CAPACITY EXPORTS'
]

# Ports
PORTS = [
    'TEST_PORT_A', 'TEST_PORT_B', 'TEST_PORT_C', 'PERF_PORT_1', 'PERF_PORT_2',
    'MOCK_HARBOR', 'SYNTHETIC_DOCK', 'LOAD_PORT', 'BENCH_PORT', 'SCALE_PORT'
]

# Minimum std_id offset (to avoid collision with real data)
DEFAULT_STD_ID_OFFSET = 10_000_000


def get_next_std_id_offset(db: DatabaseManager) -> int:
    """Get the next safe std_id offset by checking existing synthetic data."""
    query = """
        SELECT COALESCE(MAX(std_id), 0) + 1 
        FROM global_trades_ledger 
        WHERE std_id >= %s
    """
    result = db.execute_query(query, (DEFAULT_STD_ID_OFFSET,))
    if result and result[0][0]:
        return max(result[0][0], DEFAULT_STD_ID_OFFSET)
    return DEFAULT_STD_ID_OFFSET


def get_ledger_columns(db: DatabaseManager) -> list:
    """Introspect the global_trades_ledger schema to get column list."""
    query = """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'global_trades_ledger'
        ORDER BY ordinal_position
    """
    result = db.execute_query(query)
    return [(r[0], r[1], r[2]) for r in result]


def generate_synthetic_row(
    row_index: int,
    year: int,
    month: int,
    reporting_country: str,
    std_id_offset: int
) -> dict:
    """Generate a single synthetic ledger row."""
    
    # Generate dates within the year/month
    day = random.randint(1, 28)  # Safe for all months
    shipment_date = date(year, month, day)
    
    # Random destination (different from reporting)
    dest_countries = [c for c in SYNTHETIC_COUNTRIES if c != reporting_country]
    destination_country = random.choice(dest_countries)
    origin_country = random.choice(dest_countries)
    
    # Random quantities and values
    qty_kg = random.uniform(100, 50000)
    price_per_kg = random.uniform(0.5, 100)
    customs_value = qty_kg * price_per_kg
    
    # Random TEU
    teu = random.choice([0.5, 1, 2, 4, 6, 8]) if random.random() > 0.3 else None
    
    return {
        'transaction_id': str(uuid.uuid4()),
        'std_id': std_id_offset + row_index,
        'reporting_country': reporting_country,
        'direction': random.choice(['EXPORT', 'IMPORT']),
        'origin_country': origin_country,
        'destination_country': destination_country,
        'export_date': shipment_date if random.random() > 0.5 else None,
        'import_date': shipment_date if random.random() > 0.5 else None,
        'shipment_date': shipment_date,
        'year': year,
        'month': month,
        'buyer_uuid': str(uuid.uuid4()),
        'supplier_uuid': str(uuid.uuid4()),
        'hs_code_raw': random.choice(SYNTHETIC_HS_CODES),
        'hs_code_6': random.choice(SYNTHETIC_HS_CODES),
        'goods_description': f"SYNTHETIC GOODS - PERF TEST ITEM {row_index % 1000}",
        'qty_raw': qty_kg,
        'qty_kg': qty_kg,
        'qty_unit': 'KGS',
        'fob_usd': customs_value * 0.9,
        'cif_usd': customs_value * 1.1,
        'customs_value_usd': customs_value,
        'price_usd_per_kg': price_per_kg,
        'teu': teu,
        'vessel_name': f"TEST_VESSEL_{random.randint(1, 100)}",
        'container_id': f"PERF{random.randint(10000000, 99999999)}",
        'port_loading': random.choice(PORTS),
        'port_unloading': random.choice(PORTS),
        'record_grain': 'LINE_ITEM',
        'source_format': 'SYNTHETIC',
        'source_file': f'synthetic_perf_test_{year}_{month}.csv'
    }


def generate_batch(
    start_index: int,
    batch_size: int,
    years: list,
    months: list,
    countries: list,
    std_id_offset: int
) -> list:
    """Generate a batch of synthetic rows."""
    rows = []
    for i in range(batch_size):
        row_idx = start_index + i
        year = random.choice(years)
        month = random.choice(months)
        country = random.choice(countries)
        rows.append(generate_synthetic_row(row_idx, year, month, country, std_id_offset))
    return rows


def insert_batch_copy(db: DatabaseManager, rows: list):
    """Insert batch using COPY for maximum performance."""
    if not rows:
        return 0
    
    # Column order matching the INSERT
    columns = [
        'transaction_id', 'std_id', 'reporting_country', 'direction',
        'origin_country', 'destination_country', 'export_date', 'import_date',
        'shipment_date', 'year', 'month', 'buyer_uuid', 'supplier_uuid',
        'hs_code_raw', 'hs_code_6', 'goods_description', 'qty_raw', 'qty_kg',
        'qty_unit', 'fob_usd', 'cif_usd', 'customs_value_usd', 'price_usd_per_kg',
        'teu', 'vessel_name', 'container_id', 'port_loading', 'port_unloading',
        'record_grain', 'source_format', 'source_file'
    ]
    
    # Build COPY data as tab-separated values
    buffer = StringIO()
    for row in rows:
        values = []
        for col in columns:
            val = row.get(col)
            if val is None:
                values.append('\\N')
            elif isinstance(val, date):
                values.append(str(val))
            else:
                values.append(str(val))
        buffer.write('\t'.join(values) + '\n')
    
    buffer.seek(0)
    
    # Use context manager for connection
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.copy_from(
                buffer,
                'global_trades_ledger',
                columns=columns,
                null='\\N'
            )
            return len(rows)
        finally:
            cursor.close()


def insert_batch_sql(db: DatabaseManager, rows: list):
    """Insert batch using multi-row INSERT (fallback)."""
    if not rows:
        return 0
    
    columns = [
        'transaction_id', 'std_id', 'reporting_country', 'direction',
        'origin_country', 'destination_country', 'export_date', 'import_date',
        'shipment_date', 'year', 'month', 'buyer_uuid', 'supplier_uuid',
        'hs_code_raw', 'hs_code_6', 'goods_description', 'qty_raw', 'qty_kg',
        'qty_unit', 'fob_usd', 'cif_usd', 'customs_value_usd', 'price_usd_per_kg',
        'teu', 'vessel_name', 'container_id', 'port_loading', 'port_unloading',
        'record_grain', 'source_format', 'source_file'
    ]
    
    # Build values
    placeholders = []
    params = []
    for row in rows:
        row_placeholders = []
        for col in columns:
            params.append(row.get(col))
            row_placeholders.append('%s')
        placeholders.append(f"({', '.join(row_placeholders)})")
    
    query = f"""
        INSERT INTO global_trades_ledger ({', '.join(columns)})
        VALUES {', '.join(placeholders)}
        ON CONFLICT (transaction_id, year) DO NOTHING
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.rowcount
        finally:
            cursor.close()


def get_current_ledger_stats(db: DatabaseManager) -> dict:
    """Get current ledger statistics."""
    query = """
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT reporting_country) as countries,
            MIN(shipment_date) as min_date,
            MAX(shipment_date) as max_date,
            COUNT(*) FILTER (WHERE source_format = 'SYNTHETIC') as synthetic_rows
        FROM global_trades_ledger
    """
    result = db.execute_query(query)
    if result:
        return {
            'total_rows': result[0][0],
            'countries': result[0][1],
            'min_date': result[0][2],
            'max_date': result[0][3],
            'synthetic_rows': result[0][4] or 0
        }
    return {'total_rows': 0, 'countries': 0, 'min_date': None, 'max_date': None, 'synthetic_rows': 0}


def wipe_synthetic_data(db: DatabaseManager, dry_run: bool = False) -> int:
    """Delete all synthetic data from the ledger."""
    
    # Count first
    count_query = """
        SELECT COUNT(*) FROM global_trades_ledger
        WHERE source_format = 'SYNTHETIC'
           OR reporting_country IN ('TESTLAND', 'FAKISTAN', 'DEMOCR', 'SYNTHIA', 'MOCKOVIA',
                                   'PERF_NORTH', 'PERF_SOUTH', 'PERF_EAST', 'PERF_WEST', 'LOADTEST')
    """
    result = db.execute_query(count_query)
    count = result[0][0] if result else 0
    
    if dry_run:
        logger.info(f"[DRY RUN] Would delete {count:,} synthetic rows")
        return count
    
    if count == 0:
        logger.info("No synthetic data to delete")
        return 0
    
    # Delete synthetic data
    delete_query = """
        DELETE FROM global_trades_ledger
        WHERE source_format = 'SYNTHETIC'
           OR reporting_country IN ('TESTLAND', 'FAKISTAN', 'DEMOCR', 'SYNTHIA', 'MOCKOVIA',
                                   'PERF_NORTH', 'PERF_SOUTH', 'PERF_EAST', 'PERF_WEST', 'LOADTEST')
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            logger.info(f"Deleting {count:,} synthetic rows...")
            cursor.execute(delete_query)
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted:,} synthetic rows")
            return deleted
        finally:
            cursor.close()


def generate_synthetic_data(
    db: DatabaseManager,
    total_rows: int,
    start_year: int,
    end_year: int,
    countries: list,
    batch_size: int = 10000
):
    """Generate and insert synthetic ledger data."""
    
    years = list(range(start_year, end_year + 1))
    months = list(range(1, 13))
    
    # Get next safe std_id offset (to avoid collisions with existing data)
    std_id_offset = get_next_std_id_offset(db)
    
    logger.info(f"Generating {total_rows:,} synthetic rows...")
    logger.info(f"Years: {start_year} - {end_year}")
    logger.info(f"Countries: {', '.join(countries)}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info(f"Starting std_id: {std_id_offset:,}")
    
    # Get starting stats
    before_stats = get_current_ledger_stats(db)
    logger.info(f"Current ledger: {before_stats['total_rows']:,} rows ({before_stats['synthetic_rows']:,} synthetic)")
    
    start_time = time.time()
    rows_inserted = 0
    batches = 0
    
    try:
        while rows_inserted < total_rows:
            remaining = total_rows - rows_inserted
            current_batch_size = min(batch_size, remaining)
            
            # Generate batch
            batch = generate_batch(
                start_index=rows_inserted,
                batch_size=current_batch_size,
                years=years,
                months=months,
                countries=countries,
                std_id_offset=std_id_offset
            )
            
            # Insert using COPY (faster) or fallback to SQL
            try:
                inserted = insert_batch_copy(db, batch)
            except Exception as e:
                logger.warning(f"COPY failed, falling back to SQL INSERT: {e}")
                inserted = insert_batch_sql(db, batch)
            
            rows_inserted += inserted
            batches += 1
            
            # Progress update every 10 batches
            if batches % 10 == 0:
                elapsed = time.time() - start_time
                rate = rows_inserted / elapsed if elapsed > 0 else 0
                pct = (rows_inserted / total_rows) * 100
                logger.info(f"Progress: {rows_inserted:,}/{total_rows:,} ({pct:.1f}%) - {rate:.0f} rows/sec")
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    
    elapsed = time.time() - start_time
    
    # Get final stats
    after_stats = get_current_ledger_stats(db)
    
    # Print summary
    print("\n" + "=" * 70)
    print("  SYNTHETIC DATA GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n  Rows Requested:    {total_rows:,}")
    print(f"  Rows Inserted:     {rows_inserted:,}")
    print(f"  Batches:           {batches}")
    print(f"  Elapsed Time:      {elapsed:.1f} seconds")
    print(f"  Rate:              {rows_inserted / elapsed:.0f} rows/second")
    print(f"\n  Years:             {start_year} - {end_year}")
    print(f"  Countries:         {', '.join(countries)}")
    print(f"\n  Ledger Before:     {before_stats['total_rows']:,} rows")
    print(f"  Ledger After:      {after_stats['total_rows']:,} rows")
    print(f"  Synthetic Total:   {after_stats['synthetic_rows']:,} rows")
    print(f"\n  Date Range:        {after_stats['min_date']} to {after_stats['max_date']}")
    print("=" * 70 + "\n")
    
    return rows_inserted


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic ledger data for performance testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1M synthetic rows
  python scripts/simulate_large_ledger.py --rows 1000000

  # Generate 100K rows for specific years
  python scripts/simulate_large_ledger.py --rows 100000 --start-year 2020 --end-year 2021

  # Preview what would be deleted (dry run)
  python scripts/simulate_large_ledger.py --wipe-simulated --dry-run

  # Actually delete all synthetic data
  python scripts/simulate_large_ledger.py --wipe-simulated
        """
    )
    
    parser.add_argument('--rows', type=int, default=100000,
                       help='Number of synthetic rows to generate (default: 100000)')
    parser.add_argument('--start-year', type=int, default=2020,
                       help='Start year for synthetic data (default: 2020)')
    parser.add_argument('--end-year', type=int, default=2021,
                       help='End year for synthetic data (default: 2021)')
    parser.add_argument('--reporting-countries', type=str, default=None,
                       help='Comma-separated list of reporting countries (default: TESTLAND,FAKISTAN,DEMOCR)')
    parser.add_argument('--batch-size', type=int, default=10000,
                       help='Batch size for inserts (default: 10000)')
    parser.add_argument('--wipe-simulated', action='store_true',
                       help='Delete all synthetic data instead of generating')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without executing (for --wipe-simulated)')
    
    args = parser.parse_args()
    
    # Initialize database
    config_path = os.environ.get('DB_CONFIG_PATH', 'config/db_config.yml')
    db = DatabaseManager(config_path)
    
    if args.wipe_simulated:
        # Delete synthetic data
        deleted = wipe_synthetic_data(db, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"\nDeleted {deleted:,} synthetic rows")
        return 0
    
    # Parse countries
    if args.reporting_countries:
        countries = [c.strip().upper() for c in args.reporting_countries.split(',')]
    else:
        countries = SYNTHETIC_COUNTRIES[:3]  # Default: TESTLAND, FAKISTAN, DEMOCR
    
    # Generate data
    rows = generate_synthetic_data(
        db=db,
        total_rows=args.rows,
        start_year=args.start_year,
        end_year=args.end_year,
        countries=countries,
        batch_size=args.batch_size
    )
    
    return 0 if rows > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
