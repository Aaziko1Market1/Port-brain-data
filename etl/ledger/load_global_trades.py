"""
EPIC 4 - Global Trades Ledger Loader
=====================================
Populates the global_trades_ledger fact table from standardized shipments.

Key Features:
- Incremental loading (only new rows)
- Idempotent operation via std_id tracking
- Batch-based processing
- Support for filtering by country/direction

Natural Key Strategy:
- Uses `std_id` from stg_shipments_standardized as the unique identifier
- Adds `std_id` column to global_trades_ledger with unique constraint
- Uses LEFT JOIN anti-pattern to find unloaded rows

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

from etl.db_utils import DatabaseManager

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BATCH_SIZE = 10000
SUPPORTED_COUNTRIES = ('INDIA', 'KENYA', 'INDONESIA')


@dataclass
class LedgerLoadSummary:
    """Summary statistics from ledger loading"""
    rows_loaded: int = 0
    batches_processed: int = 0
    countries_processed: List[str] = field(default_factory=list)
    directions_processed: List[str] = field(default_factory=list)
    rows_by_country_direction: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rows_loaded': self.rows_loaded,
            'batches_processed': self.batches_processed,
            'countries_processed': self.countries_processed,
            'directions_processed': self.directions_processed,
            'rows_by_country_direction': self.rows_by_country_direction,
            'errors': self.errors
        }


class GlobalTradesLoader:
    """
    Loads standardized shipments into global_trades_ledger.
    
    Process:
    1. Ensure std_id column exists in ledger (schema migration)
    2. Find standardized rows not yet in ledger
    3. Map fields from staging to ledger format
    4. Bulk insert with generated transaction_id
    5. Track progress via std_id
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        batch_size: int = DEFAULT_BATCH_SIZE,
        country_filters: Optional[List[str]] = None,
        direction_filters: Optional[List[str]] = None
    ):
        self.db_manager = db_manager
        self.batch_size = batch_size
        self.country_filters = country_filters
        self.direction_filters = direction_filters
        self.summary = LedgerLoadSummary()
    
    def run(self) -> LedgerLoadSummary:
        """
        Execute the ledger loading pipeline.
        
        Returns:
            LedgerLoadSummary with statistics
        """
        logger.info("=" * 60)
        logger.info("EPIC 4: Global Trades Ledger Loader - Starting")
        logger.info("=" * 60)
        
        try:
            # Step 1: Ensure schema is ready (add std_id column if needed)
            logger.info("Step 1: Ensuring schema compatibility...")
            self._ensure_schema()
            
            # Step 2: Get candidate counts
            logger.info("Step 2: Counting candidate rows...")
            candidates_count = self._count_candidates()
            logger.info(f"  Found {candidates_count} candidate rows to load")
            
            if candidates_count == 0:
                logger.info("No new rows to load. Ledger is up to date.")
                return self.summary
            
            # Step 3: Process in batches
            logger.info(f"Step 3: Loading rows in batches of {self.batch_size}...")
            self._load_batches()
            
            logger.info("=" * 60)
            logger.info("Ledger Loading Complete!")
            logger.info(f"  Rows loaded: {self.summary.rows_loaded}")
            logger.info(f"  Batches processed: {self.summary.batches_processed}")
            logger.info(f"  Countries: {self.summary.countries_processed}")
            logger.info(f"  Directions: {self.summary.directions_processed}")
            for key, count in self.summary.rows_by_country_direction.items():
                logger.info(f"    {key}: {count}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Ledger loading failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
        
        return self.summary
    
    def _ensure_schema(self) -> None:
        """
        Ensure global_trades_ledger has std_id column for tracking.
        This is a safe, idempotent schema modification.
        """
        # Check if std_id column exists
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'global_trades_ledger' 
              AND column_name = 'std_id'
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(check_query)
                if cur.fetchone() is None:
                    # Add std_id column
                    logger.info("  Adding std_id column to global_trades_ledger...")
                    cur.execute("""
                        ALTER TABLE global_trades_ledger 
                        ADD COLUMN std_id BIGINT
                    """)
                    
                    # Create unique index for idempotency
                    logger.info("  Creating unique index on std_id...")
                    cur.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_gtl_std_id 
                        ON global_trades_ledger(std_id) 
                        WHERE std_id IS NOT NULL
                    """)
                    
                    logger.info("  Schema migration complete.")
                else:
                    logger.info("  Schema already compatible (std_id exists).")
    
    def _build_where_clause(self) -> Tuple[str, List]:
        """Build WHERE clause based on filters."""
        conditions = []
        params = []
        
        # Always filter to supported countries if no explicit filter
        if self.country_filters:
            conditions.append("s.reporting_country = ANY(%s)")
            params.append(self.country_filters)
        else:
            conditions.append("s.reporting_country = ANY(%s)")
            params.append(list(SUPPORTED_COUNTRIES))
        
        if self.direction_filters:
            conditions.append("s.direction = ANY(%s)")
            params.append(self.direction_filters)
        
        # Required fields for ledger (NOT NULL constraints)
        # Use COALESCE for dates - fallback to export_date, import_date, or standardized_at
        # shipment_date handled via COALESCE in SELECT
        conditions.append("s.origin_country IS NOT NULL")
        conditions.append("s.destination_country IS NOT NULL")
        conditions.append("s.hs_code_6 IS NOT NULL")
        # year/month can be derived from shipment_date fallback
        
        where_clause = " AND ".join(conditions)
        return where_clause, params
    
    def _count_candidates(self) -> int:
        """Count rows eligible for loading."""
        where_clause, params = self._build_where_clause()
        
        query = f"""
            SELECT COUNT(*)
            FROM stg_shipments_standardized s
            LEFT JOIN global_trades_ledger g ON s.std_id = g.std_id
            WHERE g.std_id IS NULL
              AND {where_clause}
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                count = cur.fetchone()[0]
        
        return count
    
    def _load_batches(self) -> None:
        """Load all candidates in batches."""
        where_clause, params = self._build_where_clause()
        
        # Query to get candidate rows
        # Use COALESCE for dates - fallback to export_date, import_date, or standardized_at::date
        select_query = f"""
            SELECT 
                s.std_id,
                s.reporting_country,
                s.direction,
                s.origin_country,
                s.destination_country,
                s.export_date,
                s.import_date,
                COALESCE(s.shipment_date, s.export_date, s.import_date, s.standardized_at::date) AS shipment_date,
                COALESCE(s.year, EXTRACT(YEAR FROM COALESCE(s.shipment_date, s.export_date, s.import_date, s.standardized_at))::int) AS year,
                COALESCE(s.month, EXTRACT(MONTH FROM COALESCE(s.shipment_date, s.export_date, s.import_date, s.standardized_at))::int) AS month,
                s.buyer_uuid,
                s.supplier_uuid,
                s.hs_code_raw,
                s.hs_code_6,
                s.goods_description,
                s.qty_raw,
                s.qty_unit_raw,
                s.qty_kg,
                s.fob_usd,
                s.cif_usd,
                s.customs_value_usd,
                s.price_usd_per_kg,
                s.teu,
                s.vessel_name,
                s.container_id,
                s.port_loading,
                s.port_unloading,
                s.record_grain,
                s.source_format,
                s.source_file
            FROM stg_shipments_standardized s
            LEFT JOIN global_trades_ledger g ON s.std_id = g.std_id
            WHERE g.std_id IS NULL
              AND {where_clause}
            ORDER BY s.std_id
            LIMIT %s
        """
        
        # Insert query
        insert_query = """
            INSERT INTO global_trades_ledger (
                transaction_id,
                std_id,
                reporting_country,
                direction,
                origin_country,
                destination_country,
                export_date,
                import_date,
                shipment_date,
                year,
                month,
                buyer_uuid,
                supplier_uuid,
                hs_code_raw,
                hs_code_6,
                goods_description,
                qty_kg,
                qty_unit,
                fob_usd,
                cif_usd,
                customs_value_usd,
                price_usd_per_kg,
                teu,
                vessel_name,
                container_id,
                port_loading,
                port_unloading,
                record_grain,
                source_format,
                source_file,
                created_at
            ) VALUES %s
        """
        
        countries_seen = set()
        directions_seen = set()
        
        while True:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Fetch batch
                    cur.execute(select_query, params + [self.batch_size])
                    rows = cur.fetchall()
                    
                    if not rows:
                        break
                    
                    # Transform rows for insert
                    insert_data = []
                    for row in rows:
                        (std_id, reporting_country, direction, origin_country,
                         destination_country, export_date, import_date, shipment_date,
                         year, month, buyer_uuid, supplier_uuid, hs_code_raw,
                         hs_code_6, goods_description, qty_raw, qty_unit_raw, qty_kg,
                         fob_usd, cif_usd, customs_value_usd, price_usd_per_kg,
                         teu, vessel_name, container_id, port_loading, port_unloading,
                         record_grain, source_format, source_file) = row
                        
                        # Generate UUID for transaction
                        transaction_id = str(uuid.uuid4())
                        
                        # Track countries/directions
                        countries_seen.add(reporting_country)
                        directions_seen.add(direction)
                        key = f"{reporting_country}/{direction}"
                        self.summary.rows_by_country_direction[key] = \
                            self.summary.rows_by_country_direction.get(key, 0) + 1
                        
                        insert_data.append((
                            transaction_id,
                            std_id,
                            reporting_country,
                            direction,
                            origin_country,
                            destination_country,
                            export_date,
                            import_date,
                            shipment_date,
                            year,
                            month,
                            str(buyer_uuid) if buyer_uuid else None,
                            str(supplier_uuid) if supplier_uuid else None,
                            hs_code_raw,
                            hs_code_6,
                            goods_description,
                            qty_kg,
                            qty_unit_raw,  # qty_unit in ledger = qty_unit_raw from staging
                            fob_usd,
                            cif_usd,
                            customs_value_usd,
                            price_usd_per_kg,
                            teu,
                            vessel_name,
                            container_id,
                            port_loading,
                            port_unloading,
                            record_grain,
                            source_format,
                            source_file,
                            datetime.now()
                        ))
                    
                    # Bulk insert
                    execute_values(
                        cur,
                        insert_query,
                        insert_data,
                        template="""(
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )"""
                    )
                    
                    batch_count = len(rows)
                    self.summary.rows_loaded += batch_count
                    self.summary.batches_processed += 1
                    
                    logger.info(f"  Batch {self.summary.batches_processed}: "
                               f"loaded {batch_count} rows "
                               f"(total: {self.summary.rows_loaded})")
        
        self.summary.countries_processed = list(countries_seen)
        self.summary.directions_processed = list(directions_seen)


def load_global_trades(
    db_config_path: str = "config/db_config.yml",
    batch_size: int = DEFAULT_BATCH_SIZE,
    country_filters: Optional[List[str]] = None,
    direction_filters: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main entry point for global trades ledger loading.
    
    Args:
        db_config_path: Path to database configuration file
        batch_size: Number of records to process per batch
        country_filters: List of countries to process (default: INDIA, KENYA)
        direction_filters: List of directions to process (default: all)
        
    Returns:
        Summary dictionary with loading statistics
    """
    logger.info("Initializing Global Trades Ledger Loader")
    logger.info(f"  Config: {db_config_path}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Country filters: {country_filters or 'all supported'}")
    logger.info(f"  Direction filters: {direction_filters or 'all'}")
    
    db_manager = DatabaseManager(db_config_path)
    
    try:
        loader = GlobalTradesLoader(
            db_manager=db_manager,
            batch_size=batch_size,
            country_filters=country_filters,
            direction_filters=direction_filters
        )
        
        summary = loader.run()
        return summary.to_dict()
        
    finally:
        db_manager.close()


# CLI entrypoint
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='EPIC 4: Global Trades Ledger Loader')
    parser.add_argument('--config', default='config/db_config.yml', help='Database config path')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size')
    parser.add_argument('--countries', nargs='+', help='Countries to process')
    parser.add_argument('--directions', nargs='+', help='Directions to process')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    result = load_global_trades(
        db_config_path=args.config,
        batch_size=args.batch_size,
        country_filters=args.countries,
        direction_filters=args.directions
    )
    
    print("\n" + "=" * 60)
    print("Global Trades Ledger Loading Summary")
    print("=" * 60)
    for key, value in result.items():
        print(f"  {key}: {value}")
