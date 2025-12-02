"""
EPIC 5 - Global Mirror Algorithm Core Engine
=============================================
Matches export shipments with hidden/unknown buyers to corresponding
import shipments in the destination country to infer the true final buyer.

Key Features:
- Hidden buyer detection via name patterns (TO ORDER, BANK, L/C, etc.)
- Multi-criteria matching: HS6, qty tolerance, date window, vessel, container
- Tie-breaking logic to avoid ambiguous matches
- Idempotent operation with unique constraint on export_transaction_id
- Batch-oriented, set-based SQL approach for performance
- Respects year-based partitioning of global_trades_ledger

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from etl.db_utils import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class MirrorConfig:
    """Configuration for the mirror matching algorithm."""
    # Matching thresholds
    min_score: int = 70              # Minimum score to accept a match
    qty_tolerance_pct: float = 5.0   # ±5% quantity tolerance
    min_lag_days: int = 15           # Minimum days between export and import
    max_lag_days: int = 45           # Maximum days between export and import
    score_tie_delta: int = 5         # Max score difference to consider a tie
    
    # Scoring weights (must sum to 100 for full match)
    score_hs6_match: int = 40        # HS6 exact match (required)
    score_qty_match: int = 25        # Quantity within tolerance
    score_date_match: int = 20       # Date within window
    score_container_match: int = 10  # Container ID exact match
    score_vessel_match: int = 5      # Vessel name exact match
    
    # Processing
    batch_size: int = 5000           # Exports to process per batch
    country_filters: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'min_score': self.min_score,
            'qty_tolerance_pct': self.qty_tolerance_pct,
            'min_lag_days': self.min_lag_days,
            'max_lag_days': self.max_lag_days,
            'score_tie_delta': self.score_tie_delta,
            'batch_size': self.batch_size,
            'country_filters': self.country_filters
        }


@dataclass 
class MirrorSummary:
    """Summary statistics from mirror algorithm run."""
    exports_scanned: int = 0
    exports_eligible: int = 0
    candidate_pairs_evaluated: int = 0
    matches_accepted: int = 0
    matches_skipped_ambiguous: int = 0
    matches_skipped_low_score: int = 0
    matches_skipped_no_candidates: int = 0
    score_distribution: Dict[str, int] = field(default_factory=dict)
    top_routes: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'exports_scanned': self.exports_scanned,
            'exports_eligible': self.exports_eligible,
            'candidate_pairs_evaluated': self.candidate_pairs_evaluated,
            'matches_accepted': self.matches_accepted,
            'matches_skipped_ambiguous': self.matches_skipped_ambiguous,
            'matches_skipped_low_score': self.matches_skipped_low_score,
            'matches_skipped_no_candidates': self.matches_skipped_no_candidates,
            'score_distribution': self.score_distribution,
            'top_routes': self.top_routes,
            'errors': self.errors
        }


class MirrorAlgorithm:
    """
    Global Mirror Algorithm for inferring hidden buyers.
    
    Process:
    1. Identify eligible exports (hidden buyer pattern)
    2. For each eligible export, find candidate imports
    3. Score each (export, import) pair
    4. Select best match if unambiguous and above threshold
    5. Update export with inferred buyer_uuid
    6. Log match in mirror_match_log
    """
    
    HIDDEN_BUYER_PATTERNS = [
        'TO THE ORDER',
        'TO ORDER',
        'BANK',
        'L/C',
        'LETTER OF CREDIT',
        'SHIPPER ORDER',
        'ORDER OF SHIPPER'
    ]
    
    def __init__(self, db_manager: DatabaseManager, config: MirrorConfig):
        self.db_manager = db_manager
        self.config = config
        self.summary = MirrorSummary()
    
    def run(self) -> MirrorSummary:
        """Execute the mirror matching algorithm."""
        logger.info("=" * 60)
        logger.info("EPIC 5: Global Mirror Algorithm - Starting")
        logger.info("=" * 60)
        logger.info(f"Configuration: {self.config.to_dict()}")
        
        try:
            # Step 1: Ensure schema is ready
            logger.info("Step 1: Ensuring schema compatibility...")
            self._ensure_schema()
            
            # Step 2: Get count of eligible exports
            logger.info("Step 2: Counting eligible exports (hidden buyers)...")
            eligible_count = self._count_eligible_exports()
            self.summary.exports_eligible = eligible_count
            logger.info(f"  Found {eligible_count} eligible exports with hidden buyers")
            
            if eligible_count == 0:
                logger.info("No eligible exports found. Mirror algorithm complete.")
                return self.summary
            
            # Step 3: Process in batches
            logger.info(f"Step 3: Processing exports in batches of {self.config.batch_size}...")
            self._process_batches()
            
            # Step 4: Compute summary statistics
            logger.info("Step 4: Computing summary statistics...")
            self._compute_statistics()
            
            logger.info("=" * 60)
            logger.info("Mirror Algorithm Complete!")
            logger.info(f"  Exports scanned: {self.summary.exports_scanned}")
            logger.info(f"  Exports eligible: {self.summary.exports_eligible}")
            logger.info(f"  Matches accepted: {self.summary.matches_accepted}")
            logger.info(f"  Matches skipped (ambiguous): {self.summary.matches_skipped_ambiguous}")
            logger.info(f"  Matches skipped (low score): {self.summary.matches_skipped_low_score}")
            logger.info(f"  Matches skipped (no candidates): {self.summary.matches_skipped_no_candidates}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Mirror algorithm failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
        
        return self.summary
    
    def _ensure_schema(self) -> None:
        """Ensure required columns and indexes exist."""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if hidden_buyer_flag exists
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'stg_shipments_standardized'
                      AND column_name = 'hidden_buyer_flag'
                """)
                if not cur.fetchone():
                    logger.info("  Adding hidden_buyer_flag column...")
                    cur.execute("""
                        ALTER TABLE stg_shipments_standardized 
                        ADD COLUMN hidden_buyer_flag BOOLEAN DEFAULT FALSE
                    """)
                    
                    # Update flags
                    cur.execute("""
                        UPDATE stg_shipments_standardized
                        SET hidden_buyer_flag = TRUE
                        WHERE buyer_name_raw IS NULL 
                           OR TRIM(buyer_name_raw) = ''
                           OR UPPER(buyer_name_raw) LIKE '%TO THE ORDER%'
                           OR UPPER(buyer_name_raw) LIKE '%TO ORDER%'
                           OR UPPER(buyer_name_raw) LIKE '%BANK%'
                           OR UPPER(buyer_name_raw) LIKE '%L/C%'
                           OR UPPER(buyer_name_raw) LIKE '%LETTER OF CREDIT%'
                    """)
                    logger.info(f"    Flagged {cur.rowcount} rows with hidden buyers")
                
                # Check for mirror_matched_at column
                cur.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'global_trades_ledger'
                      AND column_name = 'mirror_matched_at'
                """)
                if not cur.fetchone():
                    logger.info("  Adding mirror_matched_at column...")
                    cur.execute("""
                        ALTER TABLE global_trades_ledger 
                        ADD COLUMN mirror_matched_at TIMESTAMPTZ
                    """)
                
                logger.info("  Schema ready.")
    
    def _count_eligible_exports(self) -> int:
        """Count exports with hidden buyers that haven't been matched yet."""
        country_filter = ""
        params = []
        
        if self.config.country_filters:
            country_filter = "AND g.reporting_country = ANY(%s)"
            params.append(self.config.country_filters)
        
        query = f"""
            SELECT COUNT(*)
            FROM global_trades_ledger g
            JOIN stg_shipments_standardized s ON g.std_id = s.std_id
            WHERE g.direction = 'EXPORT'
              AND s.hidden_buyer_flag = TRUE
              AND g.mirror_matched_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM mirror_match_log m 
                  WHERE m.export_transaction_id = g.transaction_id
              )
              {country_filter}
        """
        
        result = self.db_manager.execute_query(query, tuple(params) if params else None)
        return result[0][0] if result else 0
    
    def _process_batches(self) -> None:
        """Process eligible exports in batches."""
        country_filter = ""
        params = []
        
        if self.config.country_filters:
            country_filter = "AND g.reporting_country = ANY(%s)"
            params.append(self.config.country_filters)
        
        offset = 0
        batch_num = 0
        
        while True:
            batch_num += 1
            
            # Fetch batch of eligible exports
            export_query = f"""
                SELECT 
                    g.transaction_id,
                    g.std_id,
                    g.year,
                    g.reporting_country,
                    g.origin_country,
                    g.destination_country,
                    g.hs_code_6,
                    g.qty_kg,
                    g.shipment_date,
                    g.vessel_name,
                    g.container_id
                FROM global_trades_ledger g
                JOIN stg_shipments_standardized s ON g.std_id = s.std_id
                WHERE g.direction = 'EXPORT'
                  AND s.hidden_buyer_flag = TRUE
                  AND g.mirror_matched_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM mirror_match_log m 
                      WHERE m.export_transaction_id = g.transaction_id
                  )
                  {country_filter}
                ORDER BY g.transaction_id
                LIMIT %s OFFSET %s
            """
            
            query_params = list(params) + [self.config.batch_size, offset]
            exports = self.db_manager.execute_query(export_query, tuple(query_params))
            
            if not exports:
                break
            
            logger.info(f"  Batch {batch_num}: Processing {len(exports)} exports...")
            self.summary.exports_scanned += len(exports)
            
            # Process each export in this batch
            matches_in_batch = 0
            for export_row in exports:
                matched = self._process_single_export(export_row)
                if matched:
                    matches_in_batch += 1
            
            logger.info(f"  Batch {batch_num}: {matches_in_batch} matches accepted")
            offset += self.config.batch_size
    
    def _process_single_export(self, export_row: Tuple) -> bool:
        """
        Process a single export to find matching import.
        
        Returns True if a match was accepted.
        """
        (transaction_id, std_id, year, reporting_country, origin_country,
         destination_country, hs_code_6, qty_kg, shipment_date,
         vessel_name, container_id) = export_row
        
        # Find candidate imports
        candidates = self._find_candidates(
            origin_country=origin_country or reporting_country,
            destination_country=destination_country,
            hs_code_6=hs_code_6,
            qty_kg=qty_kg,
            export_date=shipment_date,
            vessel_name=vessel_name,
            container_id=container_id
        )
        
        if not candidates:
            self.summary.matches_skipped_no_candidates += 1
            return False
        
        self.summary.candidate_pairs_evaluated += len(candidates)
        
        # Score candidates
        scored_candidates = []
        for candidate in candidates:
            score, criteria = self._compute_score(
                export_row=export_row,
                import_row=candidate
            )
            scored_candidates.append((candidate, score, criteria))
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Get best candidate
        best_candidate, best_score, best_criteria = scored_candidates[0]
        
        # Check minimum score threshold
        if best_score < self.config.min_score:
            self.summary.matches_skipped_low_score += 1
            return False
        
        # Check for ties/ambiguity
        if len(scored_candidates) > 1:
            second_best_score = scored_candidates[1][1]
            if best_score - second_best_score <= self.config.score_tie_delta:
                # Ambiguous - skip
                self.summary.matches_skipped_ambiguous += 1
                logger.debug(
                    f"Ambiguous match for export {transaction_id}: "
                    f"scores {best_score} vs {second_best_score}"
                )
                return False
        
        # Accept match
        self._record_match(
            export_transaction_id=transaction_id,
            export_year=year,
            import_row=best_candidate,
            match_score=best_score,
            criteria=best_criteria
        )
        
        self.summary.matches_accepted += 1
        
        # Update score distribution
        score_bucket = f"{(best_score // 10) * 10}-{(best_score // 10) * 10 + 9}"
        self.summary.score_distribution[score_bucket] = \
            self.summary.score_distribution.get(score_bucket, 0) + 1
        
        return True
    
    def _find_candidates(
        self,
        origin_country: str,
        destination_country: str,
        hs_code_6: str,
        qty_kg: Optional[float],
        export_date,
        vessel_name: Optional[str],
        container_id: Optional[str]
    ) -> List[Tuple]:
        """Find candidate import shipments for matching."""
        
        # Build query for candidate imports
        # Must match on: destination country (as reporting_country), origin, HS6
        # Filter by: date window, qty tolerance
        
        query = """
            SELECT 
                i.transaction_id,
                i.std_id,
                i.year,
                i.reporting_country,
                i.origin_country,
                i.destination_country,
                i.hs_code_6,
                i.qty_kg,
                i.shipment_date,
                i.vessel_name,
                i.container_id,
                i.buyer_uuid
            FROM global_trades_ledger i
            WHERE i.direction = 'IMPORT'
              AND i.reporting_country = %s  -- Import is reported by destination country
              AND i.origin_country = %s
              AND i.hs_code_6 = %s
              AND i.buyer_uuid IS NOT NULL  -- Must have a buyer to infer
              AND i.shipment_date >= %s::date + INTERVAL '%s days'
              AND i.shipment_date <= %s::date + INTERVAL '%s days'
        """
        
        params = [
            destination_country,
            origin_country,
            hs_code_6,
            export_date,
            self.config.min_lag_days,
            export_date,
            self.config.max_lag_days
        ]
        
        # Add quantity filter if qty_kg is available
        if qty_kg is not None and float(qty_kg) > 0:
            qty_kg_float = float(qty_kg)
            qty_tolerance = qty_kg_float * (self.config.qty_tolerance_pct / 100.0)
            query += """
              AND i.qty_kg IS NOT NULL
              AND i.qty_kg BETWEEN %s AND %s
            """
            params.extend([qty_kg_float - qty_tolerance, qty_kg_float + qty_tolerance])
        
        query += " LIMIT 100"  # Cap candidates to avoid runaway queries
        
        results = self.db_manager.execute_query(query, tuple(params))
        return results if results else []
    
    def _compute_score(
        self,
        export_row: Tuple,
        import_row: Tuple
    ) -> Tuple[int, Dict]:
        """
        Compute match score between export and import.
        
        Returns (score, criteria_dict).
        """
        (_, _, _, _, e_origin, e_dest, e_hs6, e_qty, e_date,
         e_vessel, e_container) = export_row
        
        (_, _, _, _, i_origin, i_dest, i_hs6, i_qty, i_date,
         i_vessel, i_container, _) = import_row
        
        score = 0
        criteria = {}
        
        # HS6 match (required, always true if we got here)
        criteria['hs6_match'] = (e_hs6 == i_hs6)
        if criteria['hs6_match']:
            score += self.config.score_hs6_match
        
        # Quantity match
        if e_qty and i_qty and e_qty > 0:
            qty_diff_pct = abs(i_qty - e_qty) / e_qty * 100
            criteria['qty_diff_pct'] = round(qty_diff_pct, 2)
            criteria['qty_match'] = qty_diff_pct <= self.config.qty_tolerance_pct
            if criteria['qty_match']:
                score += self.config.score_qty_match
        else:
            criteria['qty_match'] = None
            criteria['qty_diff_pct'] = None
        
        # Date match
        if e_date and i_date:
            date_diff = (i_date - e_date).days
            criteria['date_diff_days'] = date_diff
            criteria['date_match'] = (
                self.config.min_lag_days <= date_diff <= self.config.max_lag_days
            )
            if criteria['date_match']:
                score += self.config.score_date_match
        else:
            criteria['date_match'] = None
            criteria['date_diff_days'] = None
        
        # Container ID match
        if e_container and i_container:
            container_clean_e = str(e_container).strip().upper()
            container_clean_i = str(i_container).strip().upper()
            criteria['container_match'] = (container_clean_e == container_clean_i)
            if criteria['container_match']:
                score += self.config.score_container_match
        else:
            criteria['container_match'] = None
        
        # Vessel name match
        if e_vessel and i_vessel:
            vessel_clean_e = str(e_vessel).strip().upper()
            vessel_clean_i = str(i_vessel).strip().upper()
            criteria['vessel_match'] = (vessel_clean_e == vessel_clean_i)
            if criteria['vessel_match']:
                score += self.config.score_vessel_match
        else:
            criteria['vessel_match'] = None
        
        criteria['total_score'] = score
        return score, criteria
    
    def _record_match(
        self,
        export_transaction_id: str,
        export_year: int,
        import_row: Tuple,
        match_score: int,
        criteria: Dict
    ) -> None:
        """Record match in mirror_match_log and update export."""
        import_transaction_id = import_row[0]
        import_year = import_row[2]
        buyer_uuid = import_row[11]  # buyer_uuid from import
        
        criteria['decision'] = 'accepted'
        criteria_json = json.dumps(criteria)
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Insert into mirror_match_log
                cur.execute("""
                    INSERT INTO mirror_match_log (
                        export_transaction_id,
                        export_year,
                        import_transaction_id,
                        import_year,
                        match_score,
                        criteria_used,
                        matched_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, NOW())
                    ON CONFLICT (export_transaction_id) DO NOTHING
                """, (
                    str(export_transaction_id),
                    export_year,
                    str(import_transaction_id),
                    import_year,
                    match_score,
                    criteria_json
                ))
                
                # Update export with inferred buyer
                # Note: We use (transaction_id, year) for partitioned table
                cur.execute("""
                    UPDATE global_trades_ledger
                    SET buyer_uuid = %s,
                        mirror_matched_at = NOW()
                    WHERE transaction_id = %s AND year = %s
                      AND mirror_matched_at IS NULL
                """, (str(buyer_uuid), str(export_transaction_id), export_year))
    
    def _compute_statistics(self) -> None:
        """Compute summary statistics after processing."""
        # Get top routes by match count
        query = """
            SELECT 
                e.origin_country,
                e.destination_country,
                e.hs_code_6,
                COUNT(*) as match_count
            FROM mirror_match_log m
            JOIN global_trades_ledger e 
                ON m.export_transaction_id = e.transaction_id 
                AND m.export_year = e.year
            GROUP BY e.origin_country, e.destination_country, e.hs_code_6
            ORDER BY match_count DESC
            LIMIT 5
        """
        
        results = self.db_manager.execute_query(query)
        if results:
            self.summary.top_routes = [
                {
                    'origin': r[0],
                    'destination': r[1],
                    'hs_code_6': r[2],
                    'match_count': r[3]
                }
                for r in results
            ]


def run_mirror_algorithm(
    db_config_path: str = "config/db_config.yml",
    min_score: int = 70,
    qty_tolerance_pct: float = 5.0,
    min_lag_days: int = 15,
    max_lag_days: int = 45,
    batch_size: int = 5000,
    country_filters: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main entry point for mirror algorithm.
    
    Args:
        db_config_path: Path to database configuration
        min_score: Minimum score to accept a match (default 70)
        qty_tolerance_pct: Quantity tolerance percentage (default 5%)
        min_lag_days: Minimum days between export and import (default 15)
        max_lag_days: Maximum days between export and import (default 45)
        batch_size: Exports to process per batch (default 5000)
        country_filters: List of countries to process (default: all)
        
    Returns:
        Summary dictionary with matching statistics
    """
    logger.info("Initializing Mirror Algorithm")
    logger.info(f"  Config: {db_config_path}")
    logger.info(f"  Min score: {min_score}")
    logger.info(f"  Qty tolerance: ±{qty_tolerance_pct}%")
    logger.info(f"  Date window: {min_lag_days}-{max_lag_days} days")
    logger.info(f"  Countries: {country_filters or 'all'}")
    
    db_manager = DatabaseManager(db_config_path)
    
    config = MirrorConfig(
        min_score=min_score,
        qty_tolerance_pct=qty_tolerance_pct,
        min_lag_days=min_lag_days,
        max_lag_days=max_lag_days,
        batch_size=batch_size,
        country_filters=country_filters
    )
    
    try:
        algorithm = MirrorAlgorithm(db_manager, config)
        summary = algorithm.run()
        return summary.to_dict()
    finally:
        db_manager.close()
