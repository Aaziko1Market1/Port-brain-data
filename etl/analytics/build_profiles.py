"""
EPIC 6A - Buyer & Exporter Profile Builder
==========================================
Builds aggregated profiles from global_trades_ledger data.

Key Features:
- Incremental processing: Only recomputes affected profiles based on new/changed data
- Idempotent: UPSERT semantics ensure no double-counting
- Respects partitioning: Queries ledger by year/reporting_country
- Pipeline tracking: Integrates with pipeline_runs table

Incremental Strategy:
    We use a "marker table" (profile_build_markers) to track the last processed date.
    On each run:
    1. Find shipments with created_at > last_processed_date
    2. Get distinct buyer_uuid/supplier_uuid from those shipments
    3. FULLY recompute profiles for those affected entities only
    4. UPSERT into profile tables
    5. Update marker to current timestamp

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import json
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal

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
class ProfileBuildSummary:
    """Summary statistics from profile build run."""
    buyers_processed: int = 0
    buyers_created: int = 0
    buyers_updated: int = 0
    exporters_processed: int = 0
    exporters_created: int = 0
    exporters_updated: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'buyers_processed': self.buyers_processed,
            'buyers_created': self.buyers_created,
            'buyers_updated': self.buyers_updated,
            'exporters_processed': self.exporters_processed,
            'exporters_created': self.exporters_created,
            'exporters_updated': self.exporters_updated,
            'errors': self.errors
        }


class ProfileBuilder:
    """
    Builds buyer and exporter profiles from global_trades_ledger.
    
    Profile grain:
    - buyer_profile: (buyer_uuid, destination_country)
    - exporter_profile: (supplier_uuid, origin_country)
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.summary = ProfileBuildSummary()
    
    def build_all(self, full_rebuild: bool = False) -> ProfileBuildSummary:
        """
        Build both buyer and exporter profiles.
        
        Args:
            full_rebuild: If True, ignore markers and recompute all profiles.
                         If False (default), only process incrementally.
        """
        logger.info("Starting profile build...")
        
        try:
            # Build buyer profiles
            self._build_buyer_profiles(full_rebuild)
            
            # Build exporter profiles
            self._build_exporter_profiles(full_rebuild)
            
            # Update markers
            self._update_markers()
            
            logger.info(f"Profile build complete: "
                       f"buyers={self.summary.buyers_processed}, "
                       f"exporters={self.summary.exporters_processed}")
            
        except Exception as e:
            logger.error(f"Profile build failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
        
        return self.summary
    
    def _build_buyer_profiles(self, full_rebuild: bool = False) -> None:
        """Build/update buyer profiles."""
        logger.info("Building buyer profiles...")
        
        # Get affected buyer_uuid + destination_country combinations
        if full_rebuild:
            affected_query = """
                SELECT DISTINCT buyer_uuid, destination_country
                FROM global_trades_ledger
                WHERE buyer_uuid IS NOT NULL
                  AND direction = 'IMPORT'
            """
            affected = self.db.execute_query(affected_query)
        else:
            # Incremental: find entities with new shipments since last marker
            affected_query = """
                WITH last_marker AS (
                    SELECT COALESCE(last_processed_date, '1900-01-01'::date) as cutoff
                    FROM profile_build_markers
                    WHERE profile_type = 'buyer'
                )
                SELECT DISTINCT g.buyer_uuid, g.destination_country
                FROM global_trades_ledger g, last_marker m
                WHERE g.buyer_uuid IS NOT NULL
                  AND g.direction = 'IMPORT'
                  AND g.created_at::date > m.cutoff
            """
            affected = self.db.execute_query(affected_query)
        
        if not affected:
            logger.info("No buyer profiles to update")
            return
        
        logger.info(f"Found {len(affected)} buyer+destination combinations to process")
        self.summary.buyers_processed = len(affected)
        
        # Process in batches
        batch_size = 500
        for i in range(0, len(affected), batch_size):
            batch = affected[i:i+batch_size]
            self._process_buyer_batch(batch)
    
    def _process_buyer_batch(self, batch: List[Tuple]) -> None:
        """Process a batch of buyer profiles."""
        for buyer_uuid, destination_country in batch:
            try:
                # Compute full profile for this buyer+destination
                profile_data = self._compute_buyer_profile(buyer_uuid, destination_country)
                
                if profile_data:
                    # UPSERT into buyer_profile
                    is_new = self._upsert_buyer_profile(profile_data)
                    if is_new:
                        self.summary.buyers_created += 1
                    else:
                        self.summary.buyers_updated += 1
                        
            except Exception as e:
                logger.error(f"Error processing buyer {buyer_uuid}: {e}")
                self.summary.errors.append(f"Buyer {buyer_uuid}: {str(e)}")
    
    def _compute_buyer_profile(self, buyer_uuid: str, destination_country: str) -> Optional[Dict]:
        """Compute aggregated profile for a buyer in a destination country."""
        
        # Main aggregation query
        query = """
            SELECT 
                %s::uuid as buyer_uuid,
                %s as destination_country,
                MIN(shipment_date) as first_shipment_date,
                MAX(shipment_date) as last_shipment_date,
                COUNT(*) as total_shipments,
                COALESCE(SUM(customs_value_usd), 0) as total_customs_value_usd,
                COALESCE(SUM(qty_kg), 0) as total_qty_kg,
                CASE 
                    WHEN SUM(qty_kg) > 0 THEN SUM(customs_value_usd) / NULLIF(SUM(qty_kg), 0)
                    ELSE NULL
                END as avg_price_usd_per_kg,
                COUNT(DISTINCT hs_code_6) as unique_hs6_count,
                MAX(reporting_country) as reporting_country
            FROM global_trades_ledger
            WHERE buyer_uuid = %s
              AND destination_country = %s
              AND direction = 'IMPORT'
        """
        
        result = self.db.execute_query(query, (buyer_uuid, destination_country, buyer_uuid, destination_country))
        
        if not result or result[0][4] == 0:  # No shipments
            return None
        
        row = result[0]
        
        # Get top HS codes
        top_hs_query = """
            SELECT 
                hs_code_6,
                COALESCE(SUM(customs_value_usd), 0) as total_value_usd,
                COUNT(*) as shipments
            FROM global_trades_ledger
            WHERE buyer_uuid = %s
              AND destination_country = %s
              AND direction = 'IMPORT'
              AND hs_code_6 IS NOT NULL
            GROUP BY hs_code_6
            ORDER BY total_value_usd DESC
            LIMIT 5
        """
        top_hs = self.db.execute_query(top_hs_query, (buyer_uuid, destination_country))
        top_hs_codes = [
            {'hs_code_6': r[0], 'total_value_usd': _safe_float(r[1]), 'shipments': r[2]}
            for r in (top_hs or [])
        ]
        
        # Get top suppliers
        top_suppliers_query = """
            SELECT 
                g.supplier_uuid,
                COALESCE(o.name_normalized, 'Unknown') as supplier_name,
                COALESCE(SUM(g.customs_value_usd), 0) as total_value_usd
            FROM global_trades_ledger g
            LEFT JOIN organizations_master o ON g.supplier_uuid = o.org_uuid
            WHERE g.buyer_uuid = %s
              AND g.destination_country = %s
              AND g.direction = 'IMPORT'
              AND g.supplier_uuid IS NOT NULL
            GROUP BY g.supplier_uuid, o.name_normalized
            ORDER BY total_value_usd DESC
            LIMIT 5
        """
        top_suppliers = self.db.execute_query(top_suppliers_query, (buyer_uuid, destination_country))
        top_suppliers_json = [
            {'supplier_uuid': str(r[0]), 'supplier_name': r[1], 'total_value_usd': _safe_float(r[2])}
            for r in (top_suppliers or [])
        ]
        
        # Compute 12-month growth (if sufficient data)
        growth_12m = self._compute_growth_12m(buyer_uuid, destination_country, 'buyer')
        
        # Compute persona label
        persona = self._compute_buyer_persona(
            total_value=_safe_float(row[5]),
            total_shipments=row[4],
            growth_12m=growth_12m
        )
        
        return {
            'buyer_uuid': buyer_uuid,
            'destination_country': destination_country,
            'first_shipment_date': row[2],
            'last_shipment_date': row[3],
            'total_shipments': row[4],
            'total_customs_value_usd': _safe_float(row[5]),
            'total_qty_kg': _safe_float(row[6]),
            'avg_price_usd_per_kg': _safe_float(row[7]) if row[7] else None,
            'unique_hs6_count': row[8],
            'top_hs_codes': top_hs_codes,
            'top_suppliers': top_suppliers_json,
            'growth_12m': growth_12m,
            'persona_label': persona,
            'reporting_country': row[9]
        }
    
    def _compute_growth_12m(self, entity_uuid: str, country: str, entity_type: str) -> Optional[float]:
        """Compute 12-month YoY growth for an entity."""
        if entity_type == 'buyer':
            query = """
                WITH period_values AS (
                    SELECT 
                        CASE WHEN shipment_date >= CURRENT_DATE - INTERVAL '12 months' 
                             AND shipment_date < CURRENT_DATE THEN 'current'
                             WHEN shipment_date >= CURRENT_DATE - INTERVAL '24 months'
                             AND shipment_date < CURRENT_DATE - INTERVAL '12 months' THEN 'previous'
                        END as period,
                        SUM(customs_value_usd) as total_value
                    FROM global_trades_ledger
                    WHERE buyer_uuid = %s
                      AND destination_country = %s
                      AND direction = 'IMPORT'
                      AND shipment_date >= CURRENT_DATE - INTERVAL '24 months'
                    GROUP BY period
                )
                SELECT 
                    MAX(CASE WHEN period = 'current' THEN total_value END) as current_value,
                    MAX(CASE WHEN period = 'previous' THEN total_value END) as previous_value
                FROM period_values
            """
            params = (entity_uuid, country)
        else:
            query = """
                WITH period_values AS (
                    SELECT 
                        CASE WHEN shipment_date >= CURRENT_DATE - INTERVAL '12 months' 
                             AND shipment_date < CURRENT_DATE THEN 'current'
                             WHEN shipment_date >= CURRENT_DATE - INTERVAL '24 months'
                             AND shipment_date < CURRENT_DATE - INTERVAL '12 months' THEN 'previous'
                        END as period,
                        SUM(customs_value_usd) as total_value
                    FROM global_trades_ledger
                    WHERE supplier_uuid = %s
                      AND origin_country = %s
                      AND direction = 'EXPORT'
                      AND shipment_date >= CURRENT_DATE - INTERVAL '24 months'
                    GROUP BY period
                )
                SELECT 
                    MAX(CASE WHEN period = 'current' THEN total_value END) as current_value,
                    MAX(CASE WHEN period = 'previous' THEN total_value END) as previous_value
                FROM period_values
            """
            params = (entity_uuid, country)
        
        result = self.db.execute_query(query, params)
        
        if not result or not result[0][0] or not result[0][1]:
            return None
        
        current_val = float(result[0][0])
        previous_val = float(result[0][1])
        
        if previous_val == 0:
            return None
        
        growth = ((current_val - previous_val) / previous_val) * 100
        return round(growth, 2)
    
    def _compute_buyer_persona(self, total_value: float, total_shipments: int, growth_12m: Optional[float]) -> str:
        """Assign a persona label to a buyer based on simple rules."""
        # Rule-based persona assignment
        if total_value >= 1_000_000:  # $1M+
            return 'Whale'
        elif total_value >= 100_000:  # $100K+
            if growth_12m and growth_12m > 50:
                return 'Growing'
            return 'Mid'
        elif total_value >= 10_000:  # $10K+
            if growth_12m and growth_12m > 100:
                return 'Growing'
            return 'Value'
        else:
            if total_shipments <= 2:
                return 'New'
            return 'Small'
    
    def _upsert_buyer_profile(self, data: Dict) -> bool:
        """UPSERT buyer profile. Returns True if new, False if updated."""
        query = """
            INSERT INTO buyer_profile (
                buyer_uuid, destination_country, first_shipment_date, last_shipment_date,
                total_shipments, total_customs_value_usd, total_qty_kg, avg_price_usd_per_kg,
                unique_hs6_count, top_hs_codes, top_suppliers, growth_12m, persona_label,
                reporting_country, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, NOW()
            )
            ON CONFLICT (buyer_uuid, destination_country) DO UPDATE SET
                first_shipment_date = EXCLUDED.first_shipment_date,
                last_shipment_date = EXCLUDED.last_shipment_date,
                total_shipments = EXCLUDED.total_shipments,
                total_customs_value_usd = EXCLUDED.total_customs_value_usd,
                total_qty_kg = EXCLUDED.total_qty_kg,
                avg_price_usd_per_kg = EXCLUDED.avg_price_usd_per_kg,
                unique_hs6_count = EXCLUDED.unique_hs6_count,
                top_hs_codes = EXCLUDED.top_hs_codes,
                top_suppliers = EXCLUDED.top_suppliers,
                growth_12m = EXCLUDED.growth_12m,
                persona_label = EXCLUDED.persona_label,
                reporting_country = EXCLUDED.reporting_country,
                updated_at = NOW()
            RETURNING (xmax = 0) as is_insert
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    data['buyer_uuid'],
                    data['destination_country'],
                    data['first_shipment_date'],
                    data['last_shipment_date'],
                    data['total_shipments'],
                    data['total_customs_value_usd'],
                    data['total_qty_kg'],
                    data['avg_price_usd_per_kg'],
                    data['unique_hs6_count'],
                    json.dumps(data['top_hs_codes']),
                    json.dumps(data['top_suppliers']),
                    data['growth_12m'],
                    data['persona_label'],
                    data['reporting_country']
                ))
                result = cur.fetchone()
                return result[0] if result else True
    
    def _build_exporter_profiles(self, full_rebuild: bool = False) -> None:
        """Build/update exporter profiles."""
        logger.info("Building exporter profiles...")
        
        # Get affected supplier_uuid + origin_country combinations
        if full_rebuild:
            affected_query = """
                SELECT DISTINCT supplier_uuid, origin_country
                FROM global_trades_ledger
                WHERE supplier_uuid IS NOT NULL
                  AND direction = 'EXPORT'
            """
            affected = self.db.execute_query(affected_query)
        else:
            # Incremental: find entities with new shipments since last marker
            affected_query = """
                WITH last_marker AS (
                    SELECT COALESCE(last_processed_date, '1900-01-01'::date) as cutoff
                    FROM profile_build_markers
                    WHERE profile_type = 'exporter'
                )
                SELECT DISTINCT g.supplier_uuid, g.origin_country
                FROM global_trades_ledger g, last_marker m
                WHERE g.supplier_uuid IS NOT NULL
                  AND g.direction = 'EXPORT'
                  AND g.created_at::date > m.cutoff
            """
            affected = self.db.execute_query(affected_query)
        
        if not affected:
            logger.info("No exporter profiles to update")
            return
        
        logger.info(f"Found {len(affected)} supplier+origin combinations to process")
        self.summary.exporters_processed = len(affected)
        
        # Process in batches
        batch_size = 500
        for i in range(0, len(affected), batch_size):
            batch = affected[i:i+batch_size]
            self._process_exporter_batch(batch)
    
    def _process_exporter_batch(self, batch: List[Tuple]) -> None:
        """Process a batch of exporter profiles."""
        for supplier_uuid, origin_country in batch:
            try:
                # Compute full profile for this supplier+origin
                profile_data = self._compute_exporter_profile(supplier_uuid, origin_country)
                
                if profile_data:
                    # UPSERT into exporter_profile
                    is_new = self._upsert_exporter_profile(profile_data)
                    if is_new:
                        self.summary.exporters_created += 1
                    else:
                        self.summary.exporters_updated += 1
                        
            except Exception as e:
                logger.error(f"Error processing exporter {supplier_uuid}: {e}")
                self.summary.errors.append(f"Exporter {supplier_uuid}: {str(e)}")
    
    def _compute_exporter_profile(self, supplier_uuid: str, origin_country: str) -> Optional[Dict]:
        """Compute aggregated profile for an exporter in an origin country."""
        
        # Main aggregation query
        query = """
            SELECT 
                %s::uuid as supplier_uuid,
                %s as origin_country,
                MIN(shipment_date) as first_shipment_date,
                MAX(shipment_date) as last_shipment_date,
                COUNT(*) as total_shipments,
                COALESCE(SUM(customs_value_usd), 0) as total_customs_value_usd,
                COALESCE(SUM(qty_kg), 0) as total_qty_kg,
                CASE 
                    WHEN SUM(qty_kg) > 0 THEN SUM(customs_value_usd) / NULLIF(SUM(qty_kg), 0)
                    ELSE NULL
                END as avg_price_usd_per_kg,
                COUNT(DISTINCT hs_code_6) as unique_hs6_count,
                MAX(reporting_country) as reporting_country
            FROM global_trades_ledger
            WHERE supplier_uuid = %s
              AND origin_country = %s
              AND direction = 'EXPORT'
        """
        
        result = self.db.execute_query(query, (supplier_uuid, origin_country, supplier_uuid, origin_country))
        
        if not result or result[0][4] == 0:  # No shipments
            return None
        
        row = result[0]
        
        # Get top HS codes
        top_hs_query = """
            SELECT 
                hs_code_6,
                COALESCE(SUM(customs_value_usd), 0) as total_value_usd,
                COUNT(*) as shipments
            FROM global_trades_ledger
            WHERE supplier_uuid = %s
              AND origin_country = %s
              AND direction = 'EXPORT'
              AND hs_code_6 IS NOT NULL
            GROUP BY hs_code_6
            ORDER BY total_value_usd DESC
            LIMIT 5
        """
        top_hs = self.db.execute_query(top_hs_query, (supplier_uuid, origin_country))
        top_hs_codes = [
            {'hs_code_6': r[0], 'total_value_usd': _safe_float(r[1]), 'shipments': r[2]}
            for r in (top_hs or [])
        ]
        
        # Get top buyers
        top_buyers_query = """
            SELECT 
                g.buyer_uuid,
                COALESCE(o.name_normalized, 'Unknown') as buyer_name,
                COALESCE(SUM(g.customs_value_usd), 0) as total_value_usd
            FROM global_trades_ledger g
            LEFT JOIN organizations_master o ON g.buyer_uuid = o.org_uuid
            WHERE g.supplier_uuid = %s
              AND g.origin_country = %s
              AND g.direction = 'EXPORT'
              AND g.buyer_uuid IS NOT NULL
            GROUP BY g.buyer_uuid, o.name_normalized
            ORDER BY total_value_usd DESC
            LIMIT 5
        """
        top_buyers = self.db.execute_query(top_buyers_query, (supplier_uuid, origin_country))
        top_buyers_json = [
            {'buyer_uuid': str(r[0]), 'buyer_name': r[1], 'total_value_usd': _safe_float(r[2])}
            for r in (top_buyers or [])
        ]
        
        # Compute stability score (0-100)
        stability = self._compute_stability_score(supplier_uuid, origin_country)
        
        # Compute onboarding score (0-100)
        onboarding = self._compute_onboarding_score(
            total_shipments=row[4],
            first_date=row[2],
            last_date=row[3]
        )
        
        return {
            'supplier_uuid': supplier_uuid,
            'origin_country': origin_country,
            'first_shipment_date': row[2],
            'last_shipment_date': row[3],
            'total_shipments': row[4],
            'total_customs_value_usd': _safe_float(row[5]),
            'total_qty_kg': _safe_float(row[6]),
            'avg_price_usd_per_kg': _safe_float(row[7]) if row[7] else None,
            'unique_hs6_count': row[8],
            'top_hs_codes': top_hs_codes,
            'top_buyers': top_buyers_json,
            'stability_score': stability,
            'onboarding_score': onboarding,
            'reporting_country': row[9]
        }
    
    def _compute_stability_score(self, supplier_uuid: str, origin_country: str) -> float:
        """
        Compute stability score (0-100) based on shipment consistency.
        Higher = more stable/reliable supplier.
        """
        # Get monthly shipment counts for last 12 months
        query = """
            SELECT 
                COUNT(DISTINCT month) as active_months,
                SUM(monthly_count) as total_shipments,
                STDDEV(monthly_count) as shipment_stddev
            FROM (
                SELECT DATE_TRUNC('month', shipment_date) as month, COUNT(*) as monthly_count
                FROM global_trades_ledger
                WHERE supplier_uuid = %s
                  AND origin_country = %s
                  AND direction = 'EXPORT'
                  AND shipment_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', shipment_date)
            ) monthly
        """
        
        result = self.db.execute_query(query, (supplier_uuid, origin_country))
        
        if not result or not result[0][0]:
            return 50.0  # Default neutral score
        
        # Convert all values to float to avoid Decimal arithmetic issues
        active_months = float(result[0][0]) if result[0][0] else 0
        total_shipments = float(result[0][1]) if result[0][1] else 0
        stddev = float(result[0][2]) if result[0][2] else 0
        
        # Score based on:
        # - Active months (up to 12) = 50 points max
        # - Low variance = 50 points max
        month_score = min(active_months / 12.0 * 50.0, 50.0)
        
        # Lower stddev = higher score
        if total_shipments > 0 and stddev is not None:
            avg_monthly = total_shipments / max(active_months, 1.0)
            cv = stddev / avg_monthly if avg_monthly > 0 else 1.0  # Coefficient of variation
            variance_score = max(0.0, 50.0 - (cv * 25.0))  # Higher CV = lower score
        else:
            variance_score = 25.0  # Neutral
        
        return round(month_score + variance_score, 2)
    
    def _compute_onboarding_score(self, total_shipments: int, first_date, last_date) -> float:
        """
        Compute onboarding score (0-100) based on trading readiness.
        Higher = better candidate for new business.
        """
        score = 50.0  # Base score
        
        # Bonus for shipment volume
        if total_shipments >= 100:
            score += 20
        elif total_shipments >= 50:
            score += 15
        elif total_shipments >= 20:
            score += 10
        elif total_shipments >= 5:
            score += 5
        
        # Bonus for recent activity
        if last_date:
            days_since_last = (date.today() - last_date).days
            if days_since_last <= 30:
                score += 20
            elif days_since_last <= 90:
                score += 15
            elif days_since_last <= 180:
                score += 10
        
        # Bonus for track record length
        if first_date and last_date:
            track_record_days = (last_date - first_date).days
            if track_record_days >= 365:
                score += 10
            elif track_record_days >= 180:
                score += 5
        
        return min(score, 100.0)
    
    def _upsert_exporter_profile(self, data: Dict) -> bool:
        """UPSERT exporter profile. Returns True if new, False if updated."""
        query = """
            INSERT INTO exporter_profile (
                supplier_uuid, origin_country, first_shipment_date, last_shipment_date,
                total_shipments, total_customs_value_usd, total_qty_kg, avg_price_usd_per_kg,
                unique_hs6_count, top_hs_codes, top_buyers, stability_score, onboarding_score,
                reporting_country, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, NOW()
            )
            ON CONFLICT (supplier_uuid, origin_country) DO UPDATE SET
                first_shipment_date = EXCLUDED.first_shipment_date,
                last_shipment_date = EXCLUDED.last_shipment_date,
                total_shipments = EXCLUDED.total_shipments,
                total_customs_value_usd = EXCLUDED.total_customs_value_usd,
                total_qty_kg = EXCLUDED.total_qty_kg,
                avg_price_usd_per_kg = EXCLUDED.avg_price_usd_per_kg,
                unique_hs6_count = EXCLUDED.unique_hs6_count,
                top_hs_codes = EXCLUDED.top_hs_codes,
                top_buyers = EXCLUDED.top_buyers,
                stability_score = EXCLUDED.stability_score,
                onboarding_score = EXCLUDED.onboarding_score,
                reporting_country = EXCLUDED.reporting_country,
                updated_at = NOW()
            RETURNING (xmax = 0) as is_insert
        """
        
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (
                    data['supplier_uuid'],
                    data['origin_country'],
                    data['first_shipment_date'],
                    data['last_shipment_date'],
                    data['total_shipments'],
                    data['total_customs_value_usd'],
                    data['total_qty_kg'],
                    data['avg_price_usd_per_kg'],
                    data['unique_hs6_count'],
                    json.dumps(data['top_hs_codes']),
                    json.dumps(data['top_buyers']),
                    data['stability_score'],
                    data['onboarding_score'],
                    data['reporting_country']
                ))
                result = cur.fetchone()
                return result[0] if result else True
    
    def _update_markers(self) -> None:
        """Update build markers to current date."""
        query = """
            UPDATE profile_build_markers
            SET last_processed_date = CURRENT_DATE,
                last_processed_at = NOW()
            WHERE profile_type IN ('buyer', 'exporter')
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)


# Convenience functions
def build_buyer_profiles(db_config_path: str = "config/db_config.yml", full_rebuild: bool = False) -> Dict:
    """Build buyer profiles only."""
    db = DatabaseManager(db_config_path)
    builder = ProfileBuilder(db)
    builder._build_buyer_profiles(full_rebuild)
    builder._update_markers()
    db.close()
    return builder.summary.to_dict()


def build_exporter_profiles(db_config_path: str = "config/db_config.yml", full_rebuild: bool = False) -> Dict:
    """Build exporter profiles only."""
    db = DatabaseManager(db_config_path)
    builder = ProfileBuilder(db)
    builder._build_exporter_profiles(full_rebuild)
    builder._update_markers()
    db.close()
    return builder.summary.to_dict()


def run_build_profiles(
    db_config_path: str = "config/db_config.yml",
    full_rebuild: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for building all profiles.
    
    Args:
        db_config_path: Path to database configuration
        full_rebuild: If True, recompute all profiles from scratch
        
    Returns:
        Summary dictionary with counts and errors
    """
    db = DatabaseManager(db_config_path)
    builder = ProfileBuilder(db)
    summary = builder.build_all(full_rebuild)
    db.close()
    return summary.to_dict()
