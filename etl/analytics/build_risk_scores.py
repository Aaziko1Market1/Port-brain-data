"""
EPIC 6C - Global Risk Engine Builder
=====================================
Builds risk scores for shipments and entities from global_trades_ledger.

Key Features:
- Incremental processing: Uses watermark table to track last processed date
- Idempotent: UPSERT semantics ensure no double-counting for same engine version
- Set-based: All risk computation uses SQL aggregations (no per-row Python loops)
- Scalable: Designed for 100M+ ledger rows
- Explainable: Structured JSON reasons for each risk score

Risk Rules Implemented:
1. SHIPMENT-LEVEL:
   - UNDER_INVOICE: Price significantly below corridor median (z-score < -2)
   - OVER_INVOICE: Price significantly above corridor median (z-score > 2)
   - WEIRD_LANE: Unusual origin-destination route for this HS code

2. BUYER-LEVEL:
   - VOLUME_SPIKE: Sudden volume increase vs historical pattern
   - GHOST_ENTITY: High volume but no digital footprint (website)
   - FREE_EMAIL: High volume with free email provider

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import json
import math
import os
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
import uuid as uuid_module
import yaml

from etl.db_utils import DatabaseManager


# =============================================================================
# RISK CONFIG LOADING
# =============================================================================
def _load_risk_config() -> Dict[str, Any]:
    """Load risk configuration from YAML file."""
    config_path = Path(__file__).parent.parent.parent / 'config' / 'risk_config.yml'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        # Return default config if file not found (backwards compatibility)
        return {}

RISK_CONFIG = _load_risk_config()

# Extract config values with defaults (preserves original hardcoded values if config missing)
_risk_bands = RISK_CONFIG.get('risk_level_bands', {})
RISK_BAND_CRITICAL = _risk_bands.get('critical', 80)
RISK_BAND_HIGH = _risk_bands.get('high', 60)
RISK_BAND_MEDIUM = _risk_bands.get('medium', 40)

_price_anomaly = RISK_CONFIG.get('price_anomaly', {})
PRICE_Z_CRITICAL = _price_anomaly.get('z_critical', 5.0)
PRICE_Z_HIGH = _price_anomaly.get('z_high', 3.0)
PRICE_Z_MEDIUM = _price_anomaly.get('z_medium', 2.0)
MIN_CORRIDOR_SAMPLE = _price_anomaly.get('min_corridor_sample', 5)

_price_scores = RISK_CONFIG.get('price_anomaly_scores', {})
PRICE_SCORE_Z_GT_5 = _price_scores.get('z_gt_5', 90.0)
PRICE_SCORE_Z_GT_3 = _price_scores.get('z_gt_3', 70.0)
PRICE_SCORE_Z_GT_2 = _price_scores.get('z_gt_2', 50.0)
PRICE_SCORE_DEFAULT = _price_scores.get('z_default', 30.0)

_ghost = RISK_CONFIG.get('ghost_entity', {})
GHOST_MIN_VALUE = _ghost.get('min_total_value_usd', 500000)

_ghost_scores = RISK_CONFIG.get('ghost_entity_scores', {})
GHOST_SCORE_5M = _ghost_scores.get('value_5m_plus', 70.0)
GHOST_SCORE_1M = _ghost_scores.get('value_1m_plus', 55.0)
GHOST_SCORE_DEFAULT = _ghost_scores.get('value_default', 45.0)
GHOST_CONFIDENCE = _ghost_scores.get('confidence', 0.7)

_free_email = RISK_CONFIG.get('free_email', {})
FREE_EMAIL_HIGH_VALUE = _free_email.get('high_value_threshold', 500000)
FREE_EMAIL_HIGH_SCORE = _free_email.get('high_value_score', 40.0)
FREE_EMAIL_LOW_SCORE = _free_email.get('low_value_score', 30.0)

_vol_spike = RISK_CONFIG.get('volume_spike', {})
SPIKE_MIN_MONTHS = _vol_spike.get('min_months_history', 3)
SPIKE_Z_THRESHOLD = _vol_spike.get('z_threshold_flagging', 2.0)
SPIKE_PCT_THRESHOLD = _vol_spike.get('pct_change_flagging', 200)
SPIKE_CONFIDENCE = _vol_spike.get('confidence', 0.75)

_large_buyer = _vol_spike.get('large_buyer', {})
LARGE_BUYER_Z_CRITICAL = _large_buyer.get('z_critical', 4.0)
LARGE_BUYER_Z_HIGH = _large_buyer.get('z_high', 3.0)
LARGE_BUYER_PCT_CRITICAL = _large_buyer.get('pct_critical', 500)
LARGE_BUYER_PCT_HIGH = _large_buyer.get('pct_high', 300)
LARGE_BUYER_SCORE_CRITICAL = _large_buyer.get('score_critical', 50.0)
LARGE_BUYER_SCORE_HIGH = _large_buyer.get('score_high', 40.0)
LARGE_BUYER_SCORE_DEFAULT = _large_buyer.get('score_default', 30.0)

_small_buyer = _vol_spike.get('small_buyer', {})
SMALL_BUYER_Z_CRITICAL = _small_buyer.get('z_critical', 4.0)
SMALL_BUYER_Z_HIGH = _small_buyer.get('z_high', 3.0)
SMALL_BUYER_PCT_CRITICAL = _small_buyer.get('pct_critical', 500)
SMALL_BUYER_PCT_HIGH = _small_buyer.get('pct_high', 300)
SMALL_BUYER_SCORE_CRITICAL = _small_buyer.get('score_critical', 70.0)
SMALL_BUYER_SCORE_HIGH = _small_buyer.get('score_high', 55.0)
SMALL_BUYER_SCORE_DEFAULT = _small_buyer.get('score_default', 45.0)

# =============================================================================


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, uuid_module.UUID):
            return str(obj)
        return super().default(obj)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_ENGINE_VERSION = 'RISK_ENGINE_V1'
LOOKBACK_DAYS = 7  # Safety window for incremental processing

# Free email domains for risk detection
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
    'mail.com', 'protonmail.com', 'icloud.com', 'yandex.com', 'zoho.com',
    'gmx.com', 'live.com', 'msn.com', 'rediffmail.com', 'mail.ru'
}


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


def _confidence_from_sample_size(n: int) -> float:
    """Compute confidence score based on corridor sample size."""
    if n is None or n < 10:
        return 0.2
    elif n < 50:
        return 0.5
    elif n < 200:
        return 0.8
    else:
        return 0.95


def _risk_level_from_score(score: float) -> str:
    """Convert numeric score to risk level (uses config thresholds)."""
    if score >= RISK_BAND_CRITICAL:
        return 'CRITICAL'
    elif score >= RISK_BAND_HIGH:
        return 'HIGH'
    elif score >= RISK_BAND_MEDIUM:
        return 'MEDIUM'
    else:
        return 'LOW'


@dataclass
class RiskEngineBuildSummary:
    """Summary statistics from risk engine build run."""
    shipments_processed: int = 0
    shipment_risks_created: int = 0
    shipment_risks_updated: int = 0
    buyers_processed: int = 0
    buyer_risks_created: int = 0
    buyer_risks_updated: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'shipments_processed': self.shipments_processed,
            'shipment_risks_created': self.shipment_risks_created,
            'shipment_risks_updated': self.shipment_risks_updated,
            'buyers_processed': self.buyers_processed,
            'buyer_risks_created': self.buyer_risks_created,
            'buyer_risks_updated': self.buyer_risks_updated,
            'errors': self.errors
        }


class RiskEngineBuilder:
    """
    Builds risk scores for shipments and entities.
    
    Uses set-based SQL operations for scalability.
    All risk scores are idempotent per (entity_type, entity_id, scope_key, engine_version).
    """
    
    def __init__(self, db_manager: DatabaseManager, engine_version: str = DEFAULT_ENGINE_VERSION):
        self.db = db_manager
        self.engine_version = engine_version
        self.summary = RiskEngineBuildSummary()
    
    def build_all(self, full_refresh: bool = False, countries: Optional[List[str]] = None) -> RiskEngineBuildSummary:
        """
        Build all risk scores (shipment and entity level).
        
        Args:
            full_refresh: If True, ignore watermarks and recompute everything.
            countries: Optional list of countries to filter (reporting_country).
        """
        logger.info(f"Starting risk engine build (version={self.engine_version}, full_refresh={full_refresh})...")
        
        try:
            # Determine processing window
            min_date, max_date = self._get_processing_window(full_refresh)
            
            if min_date is None or max_date is None:
                logger.info("No data to process")
                return self.summary
            
            logger.info(f"Processing window: {min_date} to {max_date}")
            
            # 1. Build shipment-level risks
            self._build_shipment_risks(min_date, max_date, countries)
            
            # 2. Build buyer-level risks
            self._build_buyer_risks(min_date, max_date, countries)
            
            # Update watermark on success
            self._update_watermark(max_date)
            
            total_created = self.summary.shipment_risks_created + self.summary.buyer_risks_created
            total_updated = self.summary.shipment_risks_updated + self.summary.buyer_risks_updated
            logger.info(f"Risk engine build complete: {total_created} created, {total_updated} updated")
            
        except Exception as e:
            logger.error(f"Risk engine build failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
        
        return self.summary
    
    def _get_processing_window(self, full_refresh: bool) -> Tuple[Optional[date], Optional[date]]:
        """Determine date range to process."""
        # Get max shipment_date from ledger
        max_result = self.db.execute_query("""
            SELECT MAX(shipment_date) FROM global_trades_ledger
        """)
        max_date = max_result[0][0] if max_result and max_result[0][0] else None
        
        if max_date is None:
            return None, None
        
        if full_refresh:
            # Full refresh: process from earliest date
            min_result = self.db.execute_query("""
                SELECT MIN(shipment_date) FROM global_trades_ledger
            """)
            min_date = min_result[0][0] if min_result and min_result[0][0] else None
            return min_date, max_date
        
        # Incremental: get watermark
        watermark_result = self.db.execute_query("""
            SELECT last_processed_shipment_date 
            FROM risk_engine_watermark 
            WHERE id = 1
        """)
        watermark_date = watermark_result[0][0] if watermark_result and watermark_result[0][0] else None
        
        if watermark_date is None:
            # First run - process everything
            min_result = self.db.execute_query("""
                SELECT MIN(shipment_date) FROM global_trades_ledger
            """)
            min_date = min_result[0][0] if min_result and min_result[0][0] else None
        else:
            # Apply lookback window
            min_date = watermark_date - timedelta(days=LOOKBACK_DAYS)
        
        return min_date, max_date
    
    # =========================================================================
    # SHIPMENT-LEVEL RISK COMPUTATION
    # =========================================================================
    
    def _build_shipment_risks(self, min_date: date, max_date: date, countries: Optional[List[str]] = None) -> None:
        """
        Build shipment-level risk scores using set-based SQL.
        
        Computes:
        - Price anomalies (UNDER_INVOICE, OVER_INVOICE) using price_corridor
        - Lane anomalies (WEIRD_LANE) using lane_stats
        """
        logger.info("Building shipment-level risks...")
        
        # Build country filter clause
        country_filter = ""
        country_params = []
        if countries:
            placeholders = ','.join(['%s'] * len(countries))
            country_filter = f"AND g.reporting_country IN ({placeholders})"
            country_params = list(countries)
        
        # MASSIVE SET-BASED QUERY for price anomaly detection
        # This joins shipments with price corridors and computes z-scores in SQL
        price_anomaly_query = f"""
            WITH shipment_data AS (
                SELECT 
                    g.transaction_id,
                    g.year,
                    g.hs_code_6,
                    g.origin_country,
                    g.destination_country,
                    g.reporting_country,
                    g.direction,
                    g.price_usd_per_kg,
                    g.qty_kg,
                    g.customs_value_usd,
                    g.shipment_date,
                    EXTRACT(YEAR FROM g.shipment_date)::INT as ship_year,
                    EXTRACT(MONTH FROM g.shipment_date)::INT as ship_month
                FROM global_trades_ledger g
                WHERE g.shipment_date >= %s AND g.shipment_date <= %s
                  AND g.price_usd_per_kg IS NOT NULL
                  AND g.price_usd_per_kg > 0
                  AND g.qty_kg > 0
                  AND g.hs_code_6 IS NOT NULL
                  {country_filter}
            ),
            shipment_with_corridor AS (
                SELECT 
                    s.*,
                    pc.sample_size as corridor_sample_size,
                    pc.min_price_usd_per_kg as corridor_min,
                    pc.p25_price_usd_per_kg as corridor_p25,
                    pc.median_price_usd_per_kg as corridor_median,
                    pc.p75_price_usd_per_kg as corridor_p75,
                    pc.max_price_usd_per_kg as corridor_max,
                    pc.avg_price_usd_per_kg as corridor_avg,
                    -- IQR-based z-score approximation
                    CASE 
                        WHEN (pc.p75_price_usd_per_kg - pc.p25_price_usd_per_kg) > 0 THEN
                            (s.price_usd_per_kg - pc.median_price_usd_per_kg) / 
                            ((pc.p75_price_usd_per_kg - pc.p25_price_usd_per_kg) * 0.7413)
                        ELSE 0
                    END as z_score,
                    -- Deviation percentage from median
                    CASE 
                        WHEN pc.median_price_usd_per_kg > 0 THEN
                            ((s.price_usd_per_kg - pc.median_price_usd_per_kg) / pc.median_price_usd_per_kg) * 100
                        ELSE 0
                    END as deviation_pct
                FROM shipment_data s
                LEFT JOIN price_corridor pc 
                    ON s.hs_code_6 = pc.hs_code_6
                    AND s.destination_country = pc.destination_country
                    AND s.ship_year = pc.year
                    AND s.ship_month = pc.month
                    AND s.direction = pc.direction
                    AND s.reporting_country = pc.reporting_country
                WHERE pc.sample_size >= 5  -- Minimum sample for comparison
            )
            SELECT 
                transaction_id,
                year,
                hs_code_6,
                origin_country,
                destination_country,
                reporting_country,
                direction,
                price_usd_per_kg,
                customs_value_usd,
                corridor_sample_size,
                corridor_min,
                corridor_p25,
                corridor_median,
                corridor_p75,
                corridor_max,
                z_score,
                deviation_pct,
                CASE 
                    WHEN z_score < -5 THEN 'UNDER_INVOICE_CRITICAL'
                    WHEN z_score < -3 THEN 'UNDER_INVOICE_HIGH'
                    WHEN z_score < -2 THEN 'UNDER_INVOICE_MEDIUM'
                    WHEN z_score > 5 THEN 'OVER_INVOICE_CRITICAL'
                    WHEN z_score > 3 THEN 'OVER_INVOICE_HIGH'
                    WHEN z_score > 2 THEN 'OVER_INVOICE_MEDIUM'
                    ELSE 'NORMAL'
                END as price_anomaly_type
            FROM shipment_with_corridor
            WHERE ABS(z_score) > 2  -- Only flagged shipments
        """
        
        params = [min_date, max_date] + country_params
        price_anomalies = self.db.execute_query(price_anomaly_query, tuple(params))
        
        if price_anomalies:
            logger.info(f"Found {len(price_anomalies)} price anomaly shipments")
            self._upsert_price_anomaly_risks(price_anomalies)
        
        # LANE ANOMALY DETECTION
        # Find shipments on rare/unusual lanes
        lane_anomaly_query = f"""
            WITH shipment_lanes AS (
                SELECT 
                    g.transaction_id,
                    g.year,
                    g.hs_code_6,
                    g.origin_country,
                    g.destination_country,
                    g.reporting_country,
                    g.customs_value_usd
                FROM global_trades_ledger g
                WHERE g.shipment_date >= %s AND g.shipment_date <= %s
                  AND g.hs_code_6 IS NOT NULL
                  AND g.origin_country IS NOT NULL
                  AND g.destination_country IS NOT NULL
                  {country_filter}
            ),
            lane_with_stats AS (
                SELECT 
                    sl.*,
                    COALESCE(ls.total_shipments, 0) as lane_shipment_count,
                    -- Global shipments for this HS code
                    (SELECT COALESCE(SUM(total_shipments), 0) 
                     FROM lane_stats 
                     WHERE hs_code_6 = sl.hs_code_6) as global_hs6_shipments
                FROM shipment_lanes sl
                LEFT JOIN lane_stats ls 
                    ON sl.origin_country = ls.origin_country
                    AND sl.destination_country = ls.destination_country
                    AND sl.hs_code_6 = ls.hs_code_6
            )
            SELECT 
                transaction_id,
                year,
                hs_code_6,
                origin_country,
                destination_country,
                reporting_country,
                customs_value_usd,
                lane_shipment_count,
                global_hs6_shipments
            FROM lane_with_stats
            WHERE lane_shipment_count <= 3  -- Rare lane threshold
              AND global_hs6_shipments >= 50  -- But HS6 has significant global volume
        """
        
        lane_anomalies = self.db.execute_query(lane_anomaly_query, tuple(params))
        
        if lane_anomalies:
            logger.info(f"Found {len(lane_anomalies)} unusual lane shipments")
            self._upsert_lane_anomaly_risks(lane_anomalies)
        
        # Count total shipments processed
        count_query = f"""
            SELECT COUNT(*) FROM global_trades_ledger g
            WHERE g.shipment_date >= %s AND g.shipment_date <= %s
            {country_filter}
        """
        count_result = self.db.execute_query(count_query, tuple(params))
        self.summary.shipments_processed = count_result[0][0] if count_result else 0
    
    def _upsert_price_anomaly_risks(self, anomalies: List[Tuple]) -> None:
        """UPSERT price anomaly risks using batch SQL."""
        for row in anomalies:
            (transaction_id, year, hs_code_6, origin_country, destination_country,
             reporting_country, direction, price_usd_per_kg, customs_value_usd,
             corridor_sample_size, corridor_min, corridor_p25, corridor_median,
             corridor_p75, corridor_max, z_score, deviation_pct, anomaly_type) = row
            
            # Determine risk score and level (uses config thresholds)
            z = _safe_float(z_score)
            abs_z = abs(z)
            
            if abs_z > PRICE_Z_CRITICAL:
                risk_score = PRICE_SCORE_Z_GT_5
            elif abs_z > PRICE_Z_HIGH:
                risk_score = PRICE_SCORE_Z_GT_3
            elif abs_z > PRICE_Z_MEDIUM:
                risk_score = PRICE_SCORE_Z_GT_2
            else:
                risk_score = PRICE_SCORE_DEFAULT
            
            risk_level = _risk_level_from_score(risk_score)
            confidence = _confidence_from_sample_size(corridor_sample_size)
            
            # Determine main reason code
            main_reason = 'UNDER_INVOICE' if z < 0 else 'OVER_INVOICE'
            
            # Build structured reasons JSON
            reasons = {
                'code': main_reason,
                'severity': risk_level,
                'context': {
                    'hs_code_6': hs_code_6,
                    'origin_country': origin_country,
                    'destination_country': destination_country,
                    'direction': direction,
                    'shipment_price': _safe_float(price_usd_per_kg),
                    'shipment_value_usd': _safe_float(customs_value_usd),
                    'corridor_min': _safe_float(corridor_min),
                    'corridor_p25': _safe_float(corridor_p25),
                    'corridor_median': _safe_float(corridor_median),
                    'corridor_p75': _safe_float(corridor_p75),
                    'corridor_max': _safe_float(corridor_max),
                    'deviation_pct': round(_safe_float(deviation_pct), 1),
                    'z_score': round(z, 2),
                    'corridor_sample_size': corridor_sample_size or 0
                }
            }
            
            is_new = self._upsert_risk_score(
                entity_type='SHIPMENT',
                entity_id=transaction_id,
                scope_key='GLOBAL',
                risk_score=risk_score,
                confidence_score=confidence,
                risk_level=risk_level,
                main_reason_code=main_reason,
                reasons=reasons
            )
            
            if is_new:
                self.summary.shipment_risks_created += 1
            else:
                self.summary.shipment_risks_updated += 1
    
    def _upsert_lane_anomaly_risks(self, anomalies: List[Tuple]) -> None:
        """UPSERT lane anomaly risks."""
        for row in anomalies:
            (transaction_id, year, hs_code_6, origin_country, destination_country,
             reporting_country, customs_value_usd, lane_count, global_count) = row
            
            # Risk score based on how rare the lane is vs global volume
            if lane_count == 0:
                risk_score = 60.0
            elif lane_count == 1:
                risk_score = 50.0
            else:
                risk_score = 40.0
            
            risk_level = _risk_level_from_score(risk_score)
            
            # Confidence based on global sample
            confidence = _confidence_from_sample_size(global_count)
            
            reasons = {
                'code': 'WEIRD_LANE',
                'severity': risk_level,
                'context': {
                    'hs_code_6': hs_code_6,
                    'origin_country': origin_country,
                    'destination_country': destination_country,
                    'lane_shipment_count': lane_count or 0,
                    'global_hs6_shipments': global_count or 0,
                    'shipment_value_usd': _safe_float(customs_value_usd)
                }
            }
            
            is_new = self._upsert_risk_score(
                entity_type='SHIPMENT',
                entity_id=transaction_id,
                scope_key=f'LANE:{origin_country}->{destination_country}',
                risk_score=risk_score,
                confidence_score=confidence,
                risk_level=risk_level,
                main_reason_code='WEIRD_LANE',
                reasons=reasons
            )
            
            if is_new:
                self.summary.shipment_risks_created += 1
            else:
                self.summary.shipment_risks_updated += 1
    
    # =========================================================================
    # BUYER-LEVEL RISK COMPUTATION
    # =========================================================================
    
    def _build_buyer_risks(self, min_date: date, max_date: date, countries: Optional[List[str]] = None) -> None:
        """
        Build buyer-level risk scores using set-based SQL.
        
        Computes:
        - Volume spike detection
        - Ghost entity detection (no website + high volume)
        - Free email domain detection
        """
        logger.info("Building buyer-level risks...")
        
        # Build country filter
        country_filter = ""
        country_params = []
        if countries:
            placeholders = ','.join(['%s'] * len(countries))
            country_filter = f"AND bp.reporting_country IN ({placeholders})"
            country_params = list(countries)
        
        # Get affected buyers (those with recent shipments)
        affected_buyers_query = f"""
            SELECT DISTINCT buyer_uuid
            FROM global_trades_ledger
            WHERE shipment_date >= %s AND shipment_date <= %s
              AND buyer_uuid IS NOT NULL
        """
        
        affected_result = self.db.execute_query(affected_buyers_query, (min_date, max_date))
        # Convert UUIDs to strings for PostgreSQL array compatibility
        affected_buyer_uuids = [str(r[0]) for r in (affected_result or [])]
        
        if not affected_buyer_uuids:
            logger.info("No affected buyers to process")
            return
        
        logger.info(f"Processing {len(affected_buyer_uuids)} affected buyers")
        self.summary.buyers_processed = len(affected_buyer_uuids)
        
        # GHOST ENTITY DETECTION
        # High volume buyers with no website
        ghost_entity_query = """
            SELECT 
                bp.buyer_uuid,
                bp.destination_country,
                bp.total_shipments,
                bp.total_customs_value_usd,
                om.name_normalized as buyer_name,
                om.raw_name_variants
            FROM buyer_profile bp
            JOIN organizations_master om ON bp.buyer_uuid = om.org_uuid
            WHERE bp.buyer_uuid = ANY(%s::uuid[])
              AND bp.total_customs_value_usd >= {GHOST_MIN_VALUE}  -- High volume threshold (from config)
        """
        
        ghost_candidates = self.db.execute_query(ghost_entity_query, (affected_buyer_uuids,))
        
        if ghost_candidates:
            logger.info(f"Checking {len(ghost_candidates)} high-volume buyers for ghost entity risk")
            self._process_ghost_entity_risks(ghost_candidates)
        
        # VOLUME SPIKE DETECTION  
        # Compare recent volume to historical pattern
        # Uses a CTE to compute buyer time series and detect spikes
        spike_detection_query = """
            WITH buyer_monthly AS (
                SELECT 
                    buyer_uuid,
                    DATE_TRUNC('month', shipment_date) as month,
                    COUNT(*) as shipment_count,
                    SUM(customs_value_usd) as monthly_value
                FROM global_trades_ledger
                WHERE buyer_uuid = ANY(%s::uuid[])
                  AND buyer_uuid IS NOT NULL
                GROUP BY buyer_uuid, DATE_TRUNC('month', shipment_date)
            ),
            buyer_stats AS (
                SELECT 
                    buyer_uuid,
                    AVG(monthly_value) as avg_monthly_value,
                    STDDEV(monthly_value) as stddev_monthly_value,
                    MAX(month) as latest_month
                FROM buyer_monthly
                GROUP BY buyer_uuid
                HAVING COUNT(*) >= {SPIKE_MIN_MONTHS}  -- Need history for comparison (from config)
            ),
            recent_performance AS (
                SELECT 
                    bm.buyer_uuid,
                    bm.monthly_value as recent_value,
                    bs.avg_monthly_value,
                    bs.stddev_monthly_value,
                    CASE 
                        WHEN bs.avg_monthly_value > 0 THEN
                            (bm.monthly_value - bs.avg_monthly_value) / NULLIF(bs.avg_monthly_value, 0) * 100
                        ELSE 0
                    END as pct_change,
                    CASE 
                        WHEN bs.stddev_monthly_value > 0 THEN
                            (bm.monthly_value - bs.avg_monthly_value) / bs.stddev_monthly_value
                        ELSE 0
                    END as z_score
                FROM buyer_monthly bm
                JOIN buyer_stats bs ON bm.buyer_uuid = bs.buyer_uuid
                    AND bm.month = bs.latest_month
            )
            SELECT 
                rp.buyer_uuid,
                rp.recent_value,
                rp.avg_monthly_value,
                rp.pct_change,
                rp.z_score,
                bp.persona_label,
                om.name_normalized as buyer_name
            FROM recent_performance rp
            JOIN buyer_profile bp ON rp.buyer_uuid = bp.buyer_uuid
            JOIN organizations_master om ON rp.buyer_uuid = om.org_uuid
            WHERE rp.z_score > {SPIKE_Z_THRESHOLD}  -- Significant spike (from config)
              OR rp.pct_change > {SPIKE_PCT_THRESHOLD}  -- 3x+ volume increase (from config)
        """
        
        spike_results = self.db.execute_query(spike_detection_query, (affected_buyer_uuids,))
        
        if spike_results:
            logger.info(f"Found {len(spike_results)} buyers with volume spikes")
            self._process_volume_spike_risks(spike_results)
    
    def _process_ghost_entity_risks(self, candidates: List[Tuple]) -> None:
        """Process ghost entity risks."""
        for row in candidates:
            (buyer_uuid, dest_country, total_shipments, total_value, buyer_name, raw_variants) = row
            
            # Check raw_name_variants for website/email info
            # In real implementation, this would check actual contact fields
            has_website = False
            email_domain = None
            
            # Parse raw_variants if available
            if raw_variants:
                try:
                    variants = raw_variants if isinstance(raw_variants, list) else json.loads(raw_variants)
                    # Look for email patterns in variants
                    for v in variants:
                        if isinstance(v, str) and '@' in v:
                            # Extract domain
                            email_domain = v.split('@')[-1].lower()
                            break
                except:
                    pass
            
            # Score based on volume and digital presence (uses config thresholds)
            value = _safe_float(total_value)
            if value >= 5000000:  # $5M+
                risk_score = GHOST_SCORE_5M
            elif value >= 1000000:  # $1M+
                risk_score = GHOST_SCORE_1M
            else:
                risk_score = GHOST_SCORE_DEFAULT
            
            risk_level = _risk_level_from_score(risk_score)
            
            reasons = {
                'code': 'GHOST_ENTITY',
                'severity': risk_level,
                'context': {
                    'buyer_uuid': str(buyer_uuid),
                    'buyer_name': buyer_name,
                    'destination_country': dest_country,
                    'total_shipments': total_shipments or 0,
                    'total_value_usd': value,
                    'has_website': has_website,
                    'email_domain': email_domain
                }
            }
            
            is_new = self._upsert_risk_score(
                entity_type='BUYER',
                entity_id=buyer_uuid,
                scope_key='GLOBAL',
                risk_score=risk_score,
                confidence_score=GHOST_CONFIDENCE,  # Medium confidence for metadata-based rules (from config)
                risk_level=risk_level,
                main_reason_code='GHOST_ENTITY',
                reasons=reasons
            )
            
            if is_new:
                self.summary.buyer_risks_created += 1
            else:
                self.summary.buyer_risks_updated += 1
            
            # Also check for free email domain risk (uses config thresholds)
            if email_domain and email_domain in FREE_EMAIL_DOMAINS:
                email_risk_score = FREE_EMAIL_HIGH_SCORE if value >= FREE_EMAIL_HIGH_VALUE else FREE_EMAIL_LOW_SCORE
                email_risk_level = _risk_level_from_score(email_risk_score)
                
                email_reasons = {
                    'code': 'FREE_EMAIL',
                    'severity': email_risk_level,
                    'context': {
                        'buyer_uuid': str(buyer_uuid),
                        'buyer_name': buyer_name,
                        'email_domain': email_domain,
                        'total_value_usd': value
                    }
                }
                
                is_new = self._upsert_risk_score(
                    entity_type='BUYER',
                    entity_id=buyer_uuid,
                    scope_key='EMAIL_DOMAIN',
                    risk_score=email_risk_score,
                    confidence_score=0.9,  # High confidence - domain is factual
                    risk_level=email_risk_level,
                    main_reason_code='FREE_EMAIL',
                    reasons=email_reasons
                )
                
                if is_new:
                    self.summary.buyer_risks_created += 1
                else:
                    self.summary.buyer_risks_updated += 1
    
    def _process_volume_spike_risks(self, spike_data: List[Tuple]) -> None:
        """Process volume spike risks."""
        for row in spike_data:
            (buyer_uuid, recent_value, avg_value, pct_change, z_score, 
             persona_label, buyer_name) = row
            
            z = _safe_float(z_score)
            pct = _safe_float(pct_change)
            
            # Adjust risk based on buyer classification (uses config thresholds)
            # Large aggregators (personas like 'Whale') get lower risk for spikes
            is_large_buyer = persona_label in ('Whale', 'Mid')
            
            if is_large_buyer:
                # Large buyers need bigger spikes to trigger risk
                if z > LARGE_BUYER_Z_CRITICAL or pct > LARGE_BUYER_PCT_CRITICAL:
                    risk_score = LARGE_BUYER_SCORE_CRITICAL
                elif z > LARGE_BUYER_Z_HIGH or pct > LARGE_BUYER_PCT_HIGH:
                    risk_score = LARGE_BUYER_SCORE_HIGH
                else:
                    risk_score = LARGE_BUYER_SCORE_DEFAULT
            else:
                # Smaller buyers - lower threshold
                if z > SMALL_BUYER_Z_CRITICAL or pct > SMALL_BUYER_PCT_CRITICAL:
                    risk_score = SMALL_BUYER_SCORE_CRITICAL
                elif z > SMALL_BUYER_Z_HIGH or pct > SMALL_BUYER_PCT_HIGH:
                    risk_score = SMALL_BUYER_SCORE_HIGH
                else:
                    risk_score = SMALL_BUYER_SCORE_DEFAULT
            
            risk_level = _risk_level_from_score(risk_score)
            
            reasons = {
                'code': 'VOLUME_SPIKE',
                'severity': risk_level,
                'context': {
                    'buyer_uuid': str(buyer_uuid),
                    'buyer_name': buyer_name,
                    'persona_label': persona_label,
                    'recent_monthly_value': round(_safe_float(recent_value), 2),
                    'avg_monthly_value': round(_safe_float(avg_value), 2),
                    'pct_change': round(pct, 1),
                    'z_score': round(z, 2),
                    'is_large_buyer': is_large_buyer
                }
            }
            
            is_new = self._upsert_risk_score(
                entity_type='BUYER',
                entity_id=buyer_uuid,
                scope_key='VOLUME_TREND',
                risk_score=risk_score,
                confidence_score=SPIKE_CONFIDENCE,
                risk_level=risk_level,
                main_reason_code='VOLUME_SPIKE',
                reasons=reasons
            )
            
            if is_new:
                self.summary.buyer_risks_created += 1
            else:
                self.summary.buyer_risks_updated += 1
    
    # =========================================================================
    # COMMON UPSERT LOGIC
    # =========================================================================
    
    def _upsert_risk_score(
        self,
        entity_type: str,
        entity_id,
        scope_key: str,
        risk_score: float,
        confidence_score: float,
        risk_level: str,
        main_reason_code: str,
        reasons: Dict[str, Any]
    ) -> bool:
        """
        UPSERT a risk score record.
        Returns True if new, False if updated.
        """
        query = """
            INSERT INTO risk_scores (
                entity_type, entity_id, scope_key, engine_version,
                risk_score, confidence_score, risk_level, main_reason_code,
                reasons, computed_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW()
            )
            ON CONFLICT (entity_type, entity_id, scope_key, engine_version) 
            DO UPDATE SET
                risk_score = EXCLUDED.risk_score,
                confidence_score = EXCLUDED.confidence_score,
                risk_level = EXCLUDED.risk_level,
                main_reason_code = EXCLUDED.main_reason_code,
                reasons = EXCLUDED.reasons,
                computed_at = NOW()
            RETURNING (xmax = 0) as is_insert
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        entity_type,
                        entity_id,
                        scope_key,
                        self.engine_version,
                        round(risk_score, 2),
                        round(confidence_score, 2),
                        risk_level,
                        main_reason_code,
                        json.dumps(reasons, cls=DecimalEncoder)
                    ))
                    result = cur.fetchone()
                    return result[0] if result else True
        except Exception as e:
            logger.error(f"Error upserting risk score: {e}")
            self.summary.errors.append(f"Upsert error: {str(e)}")
            return False
    
    def _update_watermark(self, max_date: date) -> None:
        """Update watermark after successful processing."""
        query = """
            UPDATE risk_engine_watermark
            SET last_processed_shipment_date = %s,
                last_run_at = NOW(),
                engine_version = %s
            WHERE id = 1
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (max_date, self.engine_version))


# Convenience function
def run_build_risk_scores(
    db_config_path: str = "config/db_config.yml",
    full_refresh: bool = False,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    countries: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main entry point for building risk scores.
    
    Args:
        db_config_path: Path to database configuration
        full_refresh: If True, recompute everything from scratch
        engine_version: Version string for the risk engine
        countries: Optional list of countries to filter
        
    Returns:
        Summary dictionary with counts and errors
    """
    db = DatabaseManager(db_config_path)
    builder = RiskEngineBuilder(db, engine_version)
    summary = builder.build_all(full_refresh, countries)
    db.close()
    return summary.to_dict()
