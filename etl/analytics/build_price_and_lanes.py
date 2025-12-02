"""
EPIC 6B - Price Corridor & Lane Stats Builder
==============================================
Builds aggregated price corridors and trade lane statistics from global_trades_ledger.

Key Features:
- Incremental processing: Uses watermark table to track last processed date
- Idempotent: UPSERT semantics ensure no double-counting
- Respects partitioning: Queries ledger by year filters
- Pipeline tracking: Integrates with pipeline_runs table

Incremental Strategy:
    We use "analytics_watermarks" table to track max_shipment_date processed.
    On each run:
    1. Get current watermark (last processed shipment_date)
    2. Find max(shipment_date) in ledger
    3. Process shipments between watermark and max date
    4. UPSERT into price_corridor and lane_stats
    5. Update watermark

Grain:
    price_corridor: (hs_code_6, destination_country, year, month, direction, reporting_country)
    lane_stats: (origin_country, destination_country, hs_code_6)

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import json
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta

from etl.db_utils import DatabaseManager

logger = logging.getLogger(__name__)


def _safe_float(value, default=0.0) -> float:
    """Convert value to float, replacing NaN/None with default."""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


@dataclass
class PriceLanesBuildSummary:
    """Summary statistics from price/lanes build run."""
    ledger_rows_processed: int = 0
    corridor_records_created: int = 0
    corridor_records_updated: int = 0
    lane_records_created: int = 0
    lane_records_updated: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ledger_rows_processed': self.ledger_rows_processed,
            'corridor_records_created': self.corridor_records_created,
            'corridor_records_updated': self.corridor_records_updated,
            'lane_records_created': self.lane_records_created,
            'lane_records_updated': self.lane_records_updated,
            'errors': self.errors
        }


class PriceAndLanesBuilder:
    """
    Builds price corridors and lane statistics from global_trades_ledger.
    
    Price Corridor grain: (hs_code_6, destination_country, year, month, direction, reporting_country)
    Lane Stats grain: (origin_country, destination_country, hs_code_6)
    """
    
    # Lookback window in days for safety (rebuild recent data to catch late arrivals)
    LOOKBACK_DAYS = 7
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.summary = PriceLanesBuildSummary()
    
    def build_all(self, full_rebuild: bool = False) -> PriceLanesBuildSummary:
        """
        Build both price corridors and lane stats.
        
        Args:
            full_rebuild: If True, ignore watermarks and recompute everything.
                         If False (default), only process incrementally.
        """
        logger.info("Starting price corridor and lane stats build...")
        
        try:
            # Determine date range to process
            min_date, max_date = self._get_processing_window(full_rebuild)
            
            if min_date is None or max_date is None:
                logger.info("No data to process")
                return self.summary
            
            logger.info(f"Processing window: {min_date} to {max_date}")
            
            # Get count of ledger rows in window
            count_result = self.db.execute_query("""
                SELECT COUNT(*) 
                FROM global_trades_ledger 
                WHERE shipment_date >= %s AND shipment_date <= %s
                  AND price_usd_per_kg IS NOT NULL
                  AND qty_kg > 0
            """, (min_date, max_date))
            self.summary.ledger_rows_processed = count_result[0][0] if count_result else 0
            
            logger.info(f"Found {self.summary.ledger_rows_processed} qualifying ledger rows")
            
            # Build price corridors
            self._build_price_corridors(min_date, max_date, full_rebuild)
            
            # Build lane stats
            self._build_lane_stats(min_date, max_date, full_rebuild)
            
            # Update watermarks
            self._update_watermarks(max_date)
            
            logger.info(f"Build complete: corridors={self.summary.corridor_records_created + self.summary.corridor_records_updated}, "
                       f"lanes={self.summary.lane_records_created + self.summary.lane_records_updated}")
            
        except Exception as e:
            logger.error(f"Price/lanes build failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
        
        return self.summary
    
    def _get_processing_window(self, full_rebuild: bool) -> Tuple[Optional[date], Optional[date]]:
        """
        Determine the date range to process.
        
        Returns (min_date, max_date) tuple.
        For incremental: min_date = watermark - lookback, max_date = max ledger date
        For full rebuild: min_date = min ledger date, max_date = max ledger date
        """
        # Get max shipment_date from ledger
        max_result = self.db.execute_query("""
            SELECT MAX(shipment_date) FROM global_trades_ledger
            WHERE price_usd_per_kg IS NOT NULL AND qty_kg > 0
        """)
        max_ledger_date = max_result[0][0] if max_result and max_result[0][0] else None
        
        if max_ledger_date is None:
            return None, None
        
        if full_rebuild:
            # Get min date from ledger for full rebuild
            min_result = self.db.execute_query("""
                SELECT MIN(shipment_date) FROM global_trades_ledger
                WHERE price_usd_per_kg IS NOT NULL AND qty_kg > 0
            """)
            min_ledger_date = min_result[0][0] if min_result and min_result[0][0] else None
            return min_ledger_date, max_ledger_date
        
        # Incremental: get watermarks
        # Use the older of the two watermarks as our starting point
        watermark_result = self.db.execute_query("""
            SELECT MIN(max_shipment_date) 
            FROM analytics_watermarks 
            WHERE analytics_name IN ('price_corridor', 'lane_stats')
        """)
        watermark_date = watermark_result[0][0] if watermark_result and watermark_result[0][0] else None
        
        if watermark_date is None:
            # No watermark = first run, process everything
            min_result = self.db.execute_query("""
                SELECT MIN(shipment_date) FROM global_trades_ledger
                WHERE price_usd_per_kg IS NOT NULL AND qty_kg > 0
            """)
            min_date = min_result[0][0] if min_result and min_result[0][0] else None
        else:
            # Apply lookback window for safety
            min_date = watermark_date - timedelta(days=self.LOOKBACK_DAYS)
        
        return min_date, max_ledger_date
    
    def _build_price_corridors(self, min_date: date, max_date: date, full_rebuild: bool) -> None:
        """
        Build price corridor statistics.
        
        Computes min, p25, median, p75, max, avg prices per grain.
        Only includes shipments with valid price_usd_per_kg and qty_kg > 0.
        """
        logger.info("Building price corridors...")
        
        # SQL to compute price corridors using percentile functions
        # We compute corridors for all affected (hs_code_6, destination_country, year, month, direction, reporting_country) combinations
        query = """
            WITH price_data AS (
                SELECT 
                    hs_code_6,
                    destination_country,
                    EXTRACT(YEAR FROM shipment_date)::INT as year,
                    EXTRACT(MONTH FROM shipment_date)::INT as month,
                    direction,
                    reporting_country,
                    price_usd_per_kg,
                    shipment_date
                FROM global_trades_ledger
                WHERE shipment_date >= %s AND shipment_date <= %s
                  AND price_usd_per_kg IS NOT NULL
                  AND price_usd_per_kg > 0
                  AND qty_kg > 0
                  AND hs_code_6 IS NOT NULL
                  AND destination_country IS NOT NULL
            )
            SELECT 
                hs_code_6,
                destination_country,
                year,
                month,
                direction,
                reporting_country,
                COUNT(*) as sample_size,
                MIN(price_usd_per_kg) as min_price,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_usd_per_kg) as p25_price,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price_usd_per_kg) as median_price,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_usd_per_kg) as p75_price,
                MAX(price_usd_per_kg) as max_price,
                AVG(price_usd_per_kg) as avg_price,
                MAX(shipment_date) as last_shipment_date
            FROM price_data
            GROUP BY hs_code_6, destination_country, year, month, direction, reporting_country
        """
        
        results = self.db.execute_query(query, (min_date, max_date))
        
        if not results:
            logger.info("No price corridor data to process")
            return
        
        logger.info(f"Processing {len(results)} price corridor records")
        
        # UPSERT each corridor record
        for row in results:
            try:
                is_new = self._upsert_price_corridor(row)
                if is_new:
                    self.summary.corridor_records_created += 1
                else:
                    self.summary.corridor_records_updated += 1
            except Exception as e:
                logger.error(f"Error upserting corridor: {e}")
                self.summary.errors.append(f"Corridor error: {str(e)}")
    
    def _upsert_price_corridor(self, row: Tuple) -> bool:
        """
        UPSERT a price corridor record.
        Returns True if new record, False if updated.
        """
        (hs_code_6, destination_country, year, month, direction, reporting_country,
         sample_size, min_price, p25_price, median_price, p75_price, max_price,
         avg_price, last_shipment_date) = row
        
        query = """
            INSERT INTO price_corridor (
                hs_code_6, destination_country, year, month, direction, reporting_country,
                sample_size, min_price_usd_per_kg, p25_price_usd_per_kg, median_price_usd_per_kg,
                p75_price_usd_per_kg, max_price_usd_per_kg, avg_price_usd_per_kg,
                last_ledger_shipment_date, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (hs_code_6, destination_country, year, month, direction, reporting_country) 
            DO UPDATE SET
                sample_size = EXCLUDED.sample_size,
                min_price_usd_per_kg = EXCLUDED.min_price_usd_per_kg,
                p25_price_usd_per_kg = EXCLUDED.p25_price_usd_per_kg,
                median_price_usd_per_kg = EXCLUDED.median_price_usd_per_kg,
                p75_price_usd_per_kg = EXCLUDED.p75_price_usd_per_kg,
                max_price_usd_per_kg = EXCLUDED.max_price_usd_per_kg,
                avg_price_usd_per_kg = EXCLUDED.avg_price_usd_per_kg,
                last_ledger_shipment_date = EXCLUDED.last_ledger_shipment_date,
                updated_at = NOW()
            RETURNING (xmax = 0) as is_insert
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    hs_code_6, destination_country, year, month, direction, reporting_country,
                    sample_size,
                    _safe_float(min_price) if min_price else None,
                    _safe_float(p25_price) if p25_price else None,
                    _safe_float(median_price) if median_price else None,
                    _safe_float(p75_price) if p75_price else None,
                    _safe_float(max_price) if max_price else None,
                    _safe_float(avg_price) if avg_price else None,
                    last_shipment_date
                ))
                result = cur.fetchone()
                return result[0] if result else True
    
    def _build_lane_stats(self, min_date: date, max_date: date, full_rebuild: bool) -> None:
        """
        Build lane statistics.
        
        Aggregates shipment data by (origin_country, destination_country, hs_code_6).
        For lanes, we need to FULLY recompute affected lanes since the grain
        doesn't include time - any update to a lane requires full recalc.
        """
        logger.info("Building lane stats...")
        
        # First, identify which lanes are affected by the date window
        affected_lanes_query = """
            SELECT DISTINCT origin_country, destination_country, hs_code_6
            FROM global_trades_ledger
            WHERE shipment_date >= %s AND shipment_date <= %s
              AND origin_country IS NOT NULL
              AND destination_country IS NOT NULL
              AND hs_code_6 IS NOT NULL
        """
        
        affected_lanes = self.db.execute_query(affected_lanes_query, (min_date, max_date))
        
        if not affected_lanes:
            logger.info("No lane stats to process")
            return
        
        logger.info(f"Processing {len(affected_lanes)} affected lanes")
        
        # For each affected lane, FULLY recompute stats from entire ledger
        for lane in affected_lanes:
            origin_country, destination_country, hs_code_6 = lane
            try:
                lane_data = self._compute_lane_stats(origin_country, destination_country, hs_code_6)
                if lane_data:
                    is_new = self._upsert_lane_stats(lane_data)
                    if is_new:
                        self.summary.lane_records_created += 1
                    else:
                        self.summary.lane_records_updated += 1
            except Exception as e:
                logger.error(f"Error computing lane {origin_country}->{destination_country} HS:{hs_code_6}: {e}")
                self.summary.errors.append(f"Lane error: {str(e)}")
    
    def _compute_lane_stats(self, origin_country: str, destination_country: str, hs_code_6: str) -> Optional[Dict]:
        """
        Compute full lane statistics for a specific lane.
        Returns dict with all lane metrics.
        """
        # Main aggregation query for the lane
        main_query = """
            SELECT 
                COUNT(*) as total_shipments,
                COALESCE(SUM(teu), 0) as total_teu,
                COALESCE(SUM(customs_value_usd), 0) as total_customs_value_usd,
                COALESCE(SUM(qty_kg), 0) as total_qty_kg,
                CASE WHEN SUM(qty_kg) > 0 
                     THEN SUM(customs_value_usd) / NULLIF(SUM(qty_kg), 0)
                     ELSE NULL END as avg_price_usd_per_kg,
                MIN(shipment_date) as first_shipment_date,
                MAX(shipment_date) as last_shipment_date,
                ARRAY_AGG(DISTINCT reporting_country) as reporting_countries
            FROM global_trades_ledger
            WHERE origin_country = %s
              AND destination_country = %s
              AND hs_code_6 = %s
        """
        
        result = self.db.execute_query(main_query, (origin_country, destination_country, hs_code_6))
        
        if not result or result[0][0] == 0:
            return None
        
        row = result[0]
        
        # Get top carriers (using vessel_name as surrogate)
        carriers_query = """
            SELECT 
                COALESCE(vessel_name, 'Unknown') as carrier_name,
                COUNT(*) as shipments,
                COALESCE(SUM(teu), 0) as total_teu,
                COALESCE(SUM(customs_value_usd), 0) as total_value_usd
            FROM global_trades_ledger
            WHERE origin_country = %s
              AND destination_country = %s
              AND hs_code_6 = %s
            GROUP BY vessel_name
            ORDER BY total_value_usd DESC
            LIMIT 5
        """
        
        carriers_result = self.db.execute_query(carriers_query, (origin_country, destination_country, hs_code_6))
        
        top_carriers = [
            {
                'carrier_name': r[0],
                'shipments': r[1],
                'total_teu': _safe_float(r[2]),
                'total_value_usd': _safe_float(r[3])
            }
            for r in (carriers_result or [])
        ]
        
        # Format reporting_countries as list
        reporting_countries = list(row[7]) if row[7] else []
        
        return {
            'origin_country': origin_country,
            'destination_country': destination_country,
            'hs_code_6': hs_code_6,
            'total_shipments': row[0],
            'total_teu': _safe_float(row[1]),
            'total_customs_value_usd': _safe_float(row[2]),
            'total_qty_kg': _safe_float(row[3]),
            'avg_price_usd_per_kg': _safe_float(row[4]) if row[4] else None,
            'first_shipment_date': row[5],
            'last_shipment_date': row[6],
            'top_carriers': top_carriers,
            'reporting_countries': reporting_countries
        }
    
    def _upsert_lane_stats(self, data: Dict) -> bool:
        """
        UPSERT a lane stats record.
        Returns True if new record, False if updated.
        """
        query = """
            INSERT INTO lane_stats (
                origin_country, destination_country, hs_code_6,
                total_shipments, total_teu, total_customs_value_usd, total_qty_kg,
                avg_price_usd_per_kg, first_shipment_date, last_shipment_date,
                top_carriers, reporting_countries, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW()
            )
            ON CONFLICT (origin_country, destination_country, hs_code_6) 
            DO UPDATE SET
                total_shipments = EXCLUDED.total_shipments,
                total_teu = EXCLUDED.total_teu,
                total_customs_value_usd = EXCLUDED.total_customs_value_usd,
                total_qty_kg = EXCLUDED.total_qty_kg,
                avg_price_usd_per_kg = EXCLUDED.avg_price_usd_per_kg,
                first_shipment_date = EXCLUDED.first_shipment_date,
                last_shipment_date = EXCLUDED.last_shipment_date,
                top_carriers = EXCLUDED.top_carriers,
                reporting_countries = EXCLUDED.reporting_countries,
                updated_at = NOW()
            RETURNING (xmax = 0) as is_insert
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    data['origin_country'],
                    data['destination_country'],
                    data['hs_code_6'],
                    data['total_shipments'],
                    data['total_teu'],
                    data['total_customs_value_usd'],
                    data['total_qty_kg'],
                    data['avg_price_usd_per_kg'],
                    data['first_shipment_date'],
                    data['last_shipment_date'],
                    json.dumps(data['top_carriers']),
                    json.dumps(data['reporting_countries'])
                ))
                result = cur.fetchone()
                return result[0] if result else True
    
    def _update_watermarks(self, max_date: date) -> None:
        """Update analytics watermarks to the processed date."""
        query = """
            UPDATE analytics_watermarks
            SET max_shipment_date = %s,
                updated_at = NOW()
            WHERE analytics_name IN ('price_corridor', 'lane_stats')
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (max_date,))


# Convenience function
def run_build_price_and_lanes(
    db_config_path: str = "config/db_config.yml",
    full_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for building price corridors and lane stats.
    
    Args:
        db_config_path: Path to database configuration
        full_rebuild: If True, recompute everything from scratch
        
    Returns:
        Summary dictionary with counts and errors
    """
    db = DatabaseManager(db_config_path)
    builder = PriceAndLanesBuilder(db)
    summary = builder.build_all(full_rebuild)
    db.close()
    return summary.to_dict()
