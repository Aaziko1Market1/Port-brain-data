"""
EPIC 7D - Buyer Hunter Scoring Module (Refined)
================================================
Deterministic, data-driven scoring for finding best target buyers
for a given HS code and destination region.

Scoring Algorithm (0-100 points):
- Volume (40 pts): Based on percentile of total_value_usd_12m in result set
  (uses proportional scaling when cohort < 5 buyers)
- Stability (20 pts): Months active (0-12) + years active * 2 (max 8)
- HS Focus (15 pts): Share of HS code in buyer's GLOBAL trade value
- Risk (15 pts): LOW=15, MEDIUM=8, UNKNOWN=6, HIGH=2, CRITICAL=0
- Data Quality (10 pts): Classification present, freshness, history
- Classification Bump (up to +3): B4/B5 get +3, B3 gets +1

Volume Metrics:
- total_value_usd_12m: Filtered by HS code + destination (lane-specific)
- hs_share_pct: This HS value / buyer's GLOBAL trade value (all HS + destinations)

All scoring is deterministic - no LLM involvement.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def _safe_float(value) -> float:
    """Convert value to float, handling None, NaN, and Inf."""
    if value is None:
        return 0.0
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0


def _safe_float_or_none(value) -> Optional[float]:
    """Convert value to float or None, handling NaN and Inf."""
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


@dataclass
class BuyerHunterResult:
    """Result row for buyer hunter search."""
    buyer_uuid: str
    buyer_name: str
    buyer_country: str
    destination_country: str
    total_value_usd_12m: float
    total_shipments_12m: int
    avg_shipment_value_usd: float
    hs_share_pct: float
    months_with_shipments_12m: int
    years_active: int
    classification: str
    website_present: bool
    website_url: Optional[str]
    current_risk_level: str
    risk_score: Optional[float]
    opportunity_score: float
    
    # Score breakdown for transparency
    volume_score: float
    stability_score: float
    hs_focus_score: float
    risk_score_component: float
    data_quality_score: float


def compute_opportunity_scores(
    buyers_data: List[dict],
    max_volume_for_percentile: float = None
) -> List[BuyerHunterResult]:
    """
    Compute opportunity scores for a batch of buyers.
    
    This function is vectorized - it processes all buyers at once
    using list comprehensions and batch calculations.
    
    Args:
        buyers_data: List of dicts with raw buyer data from SQL query
        max_volume_for_percentile: Optional cap for volume percentile calculation
        
    Returns:
        List of BuyerHunterResult with computed scores
    """
    if not buyers_data:
        return []
    
    # Extract volumes for percentile/proportional calculation
    volumes = [b.get('total_value_usd_12m') or 0 for b in buyers_data]
    n_buyers = len(buyers_data)
    
    # TASK 3: Small sample size guard for volume scoring
    use_proportional_volume = n_buyers < 5
    
    if use_proportional_volume:
        # Small cohort: use proportional scaling relative to max
        max_volume = max(volumes) if volumes else 0
    else:
        # Normal path: percentile-based scoring
        sorted_volumes = sorted(volumes)
    
    def get_volume_score(value: float) -> float:
        """Get volume score (0-40) based on cohort size."""
        if value <= 0:
            return 0
        
        if use_proportional_volume:
            # Small cohort: 20-40 pts proportional to max
            if max_volume > 0:
                ratio = value / max_volume
                return 20 + ratio * 20  # 20-40 pts range
            else:
                return 20  # All equal if everything is zero
        else:
            # Normal: percentile-based
            count_below = sum(1 for v in sorted_volumes if v < value)
            percentile = (count_below / n_buyers) * 100
            return (percentile / 100) * 40
    
    results = []
    
    for buyer in buyers_data:
        # Extract values with defaults
        total_value = buyer.get('total_value_usd_12m') or 0
        total_shipments = buyer.get('total_shipments_12m') or 0
        avg_shipment = buyer.get('avg_shipment_value_usd') or 0
        hs_share = buyer.get('hs_share_pct') or 0
        months_active = buyer.get('months_with_shipments_12m') or 0
        years_active = buyer.get('years_active') or 0
        classification = buyer.get('classification') or 'Unknown'
        risk_level = buyer.get('current_risk_level') or 'UNKNOWN'
        risk_score_raw = buyer.get('risk_score')
        
        # Normalize risk level names
        if risk_level in ('UNSCORED', None, ''):
            risk_level = 'UNKNOWN'
        
        # ----- VOLUME SCORE (40 points max) -----
        # Uses proportional scaling for small cohorts, percentile for large
        volume_score = get_volume_score(total_value)
        
        # ----- STABILITY SCORE (20 points max) -----
        # Months active: 0-12 months → 0-12 points
        months_score = min(months_active, 12)  # Cap at 12
        # Years active: 1+ years → up to 8 points
        years_score = min(years_active, 4) * 2  # 4+ years = max 8 points
        stability_score = months_score + years_score
        
        # ----- HS FOCUS SCORE (15 points max) -----
        # Higher HS share = more focused buyer = better target
        # 50%+ share = max points
        hs_focus_score = min(hs_share / 50, 1) * 15
        
        # ----- RISK SCORE (15 points max) -----
        # TASK 1: Adjusted risk mapping with UNKNOWN between MEDIUM and HIGH
        risk_points_map = {
            'LOW': 15,
            'MEDIUM': 8,
            'UNKNOWN': 6,  # Between MEDIUM(8) and HIGH(2)
            'HIGH': 2,
            'CRITICAL': 0,
        }
        risk_score_component = risk_points_map.get(risk_level, 6)  # Default to UNKNOWN
        
        # ----- DATA QUALITY SCORE (10 points max) -----
        quality_score = 0
        # Classification present and not Unknown
        if classification and classification != 'Unknown':
            quality_score += 4
        # Has shipments in recent months (data freshness)
        if months_active >= 3:
            quality_score += 3
        # Multiple years of history (established buyer)
        if years_active >= 2:
            quality_score += 3
        data_quality_score = min(quality_score, 10)
        
        # ----- CLASSIFICATION BUMP (up to +3 bonus) -----
        # TASK 2: Small positive weight for B4/B5 institutional buyers
        classification_bump = 0
        if classification in ('B4', 'B5'):
            classification_bump = 3  # Strong buyer types
        elif classification == 'B3':
            classification_bump = 1  # Moderate buyer
        
        # ----- TOTAL OPPORTUNITY SCORE -----
        opportunity_score = (
            volume_score + 
            stability_score + 
            hs_focus_score + 
            risk_score_component + 
            data_quality_score +
            classification_bump
        )
        
        # Clamp to 0-100
        opportunity_score = max(0, min(100, opportunity_score))
        
        # Include classification bump in data_quality_score for display
        # (keeps the breakdown clean while still showing the boost)
        data_quality_score_display = min(data_quality_score + classification_bump, 13)
        
        # Build result
        result = BuyerHunterResult(
            buyer_uuid=buyer.get('buyer_uuid', ''),
            buyer_name=buyer.get('buyer_name', 'Unknown'),
            buyer_country=buyer.get('buyer_country', ''),
            destination_country=buyer.get('destination_country', ''),
            total_value_usd_12m=total_value,
            total_shipments_12m=total_shipments,
            avg_shipment_value_usd=avg_shipment,
            hs_share_pct=round(hs_share, 2),
            months_with_shipments_12m=months_active,
            years_active=years_active,
            classification=classification,
            website_present=buyer.get('website_present', False),
            website_url=buyer.get('website_url'),
            current_risk_level=risk_level,
            risk_score=risk_score_raw,
            opportunity_score=round(opportunity_score, 1),
            volume_score=round(volume_score, 1),
            stability_score=round(stability_score, 1),
            hs_focus_score=round(hs_focus_score, 1),
            risk_score_component=round(risk_score_component, 1),
            data_quality_score=round(data_quality_score_display, 1)
        )
        
        results.append(result)
    
    # Sort by opportunity score descending, then by volume as tiebreaker
    results.sort(key=lambda x: (x.opportunity_score, x.total_value_usd_12m), reverse=True)
    
    return results


def build_buyer_hunter_query(
    hs_code_6: str,
    destination_countries: Optional[List[str]] = None,
    months_lookback: int = 12,
    min_total_value_usd: float = 50000,
    max_risk_level: str = 'MEDIUM',
    buyer_name_filter: Optional[str] = None
) -> Tuple[str, tuple]:
    """
    Build the SQL query for buyer hunter search.
    
    Returns a parameterized query and parameter tuple.
    All inputs are properly escaped via parameterization.
    """
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=months_lookback * 30)
    
    # Map max_risk_level to allowed levels
    # TASK 1: UNKNOWN (unscored) buyers are NOT treated as LOW
    # - LOW: Only explicitly LOW-risk buyers
    # - MEDIUM: LOW + MEDIUM + UNKNOWN (UNKNOWN is between MEDIUM and HIGH)
    # - HIGH: LOW + MEDIUM + UNKNOWN + HIGH
    # - CRITICAL/ALL: Everything
    risk_level_map = {
        'LOW': ['LOW'],  # Strict: only verified LOW risk
        'MEDIUM': ['LOW', 'MEDIUM', 'UNKNOWN', 'UNSCORED'],  # Include unknown in MEDIUM+
        'HIGH': ['LOW', 'MEDIUM', 'UNKNOWN', 'UNSCORED', 'HIGH'],
        'CRITICAL': ['LOW', 'MEDIUM', 'UNKNOWN', 'UNSCORED', 'HIGH', 'CRITICAL'],
        'ALL': ['LOW', 'MEDIUM', 'UNKNOWN', 'UNSCORED', 'HIGH', 'CRITICAL']
    }
    allowed_risk_levels = risk_level_map.get(max_risk_level.upper(), ['LOW', 'MEDIUM', 'UNKNOWN', 'UNSCORED'])
    
    # Build destination filter
    destination_filter = ""
    params = [hs_code_6, start_date, end_date]
    
    if destination_countries and len(destination_countries) > 0:
        placeholders = ','.join(['%s'] * len(destination_countries))
        destination_filter = f"AND g.destination_country IN ({placeholders})"
        params.extend(destination_countries)
    
    # Add min value and risk level params
    params.append(min_total_value_usd)
    
    # Risk level placeholders
    risk_placeholders = ','.join(['%s'] * len(allowed_risk_levels))
    params.extend(allowed_risk_levels)
    
    query = f"""
    WITH buyer_hs_stats AS (
        -- Aggregate ledger data for the target HS code
        SELECT 
            g.buyer_uuid,
            g.destination_country,
            SUM(g.customs_value_usd) AS total_value_usd_12m,
            COUNT(*) AS total_shipments_12m,
            AVG(g.customs_value_usd) AS avg_shipment_value_usd,
            COUNT(DISTINCT (g.year, g.month)) AS months_with_shipments_12m,
            COUNT(DISTINCT g.year) AS years_active
        FROM global_trades_ledger g
        WHERE g.hs_code_6 = %s
          AND g.shipment_date >= %s
          AND g.shipment_date <= %s
          AND g.buyer_uuid IS NOT NULL
          {destination_filter}
        GROUP BY g.buyer_uuid, g.destination_country
    ),
    
    buyer_total_value AS (
        -- Total value across ALL HS codes for HS share calculation
        SELECT 
            g.buyer_uuid,
            SUM(g.customs_value_usd) AS total_all_hs_value
        FROM global_trades_ledger g
        WHERE g.shipment_date >= %s
          AND g.shipment_date <= %s
          AND g.buyer_uuid IS NOT NULL
        GROUP BY g.buyer_uuid
    ),
    
    buyer_risk AS (
        -- Latest risk score per buyer
        SELECT DISTINCT ON (entity_id)
            entity_id AS buyer_uuid,
            risk_level AS current_risk_level,
            risk_score
        FROM risk_scores
        WHERE entity_type = 'BUYER'
        ORDER BY entity_id, computed_at DESC
    ),
    
    buyer_profile_latest AS (
        -- Latest buyer profile
        SELECT DISTINCT ON (buyer_uuid)
            buyer_uuid,
            persona_label AS classification
        FROM buyer_profile
        ORDER BY buyer_uuid, updated_at DESC
    )
    
    SELECT 
        bhs.buyer_uuid::text,
        om.name_normalized AS buyer_name,
        om.country_iso AS buyer_country,
        bhs.destination_country,
        bhs.total_value_usd_12m,
        bhs.total_shipments_12m,
        bhs.avg_shipment_value_usd,
        CASE 
            WHEN btv.total_all_hs_value > 0 
            THEN (bhs.total_value_usd_12m / btv.total_all_hs_value * 100)
            ELSE 0 
        END AS hs_share_pct,
        bhs.months_with_shipments_12m,
        bhs.years_active,
        COALESCE(bp.classification, 'Unknown') AS classification,
        FALSE AS website_present,
        NULL AS website_url,
        COALESCE(br.current_risk_level, 'UNSCORED') AS current_risk_level,
        br.risk_score
    FROM buyer_hs_stats bhs
    JOIN organizations_master om ON bhs.buyer_uuid = om.org_uuid
    LEFT JOIN buyer_total_value btv ON bhs.buyer_uuid = btv.buyer_uuid
    LEFT JOIN buyer_risk br ON bhs.buyer_uuid = br.buyer_uuid
    LEFT JOIN buyer_profile_latest bp ON bhs.buyer_uuid = bp.buyer_uuid
    WHERE bhs.total_value_usd_12m >= %s
      AND COALESCE(br.current_risk_level, 'UNSCORED') IN ({risk_placeholders})
      --BUYER_NAME_FILTER_PLACEHOLDER--
    ORDER BY bhs.total_value_usd_12m DESC
    """
    
    # Add buyer name filter if provided
    if buyer_name_filter:
        query = query.replace("--BUYER_NAME_FILTER_PLACEHOLDER--", "AND om.name_normalized ILIKE %s")
    else:
        query = query.replace("--BUYER_NAME_FILTER_PLACEHOLDER--", "")
    
    # Insert the date params for buyer_total_value CTE
    # The query has params in this order:
    # 1. hs_code_6
    # 2. start_date (buyer_hs_stats)
    # 3. end_date (buyer_hs_stats)
    # 4. [destination_countries if any]
    # 5. start_date (buyer_total_value) - need to insert
    # 6. end_date (buyer_total_value) - need to insert
    # 7. min_total_value_usd
    # 8. [allowed_risk_levels]
    
    # Rebuild params in correct order
    params_ordered = [
        hs_code_6,          # %s for hs_code_6
        start_date,         # %s for shipment_date >=
        end_date,           # %s for shipment_date <=
    ]
    
    if destination_countries:
        params_ordered.extend(destination_countries)
    
    # Add params for buyer_total_value CTE
    params_ordered.extend([start_date, end_date])
    
    # Add min value
    params_ordered.append(min_total_value_usd)
    
    # Add risk levels
    params_ordered.extend(allowed_risk_levels)
    
    # Add buyer name filter if provided
    if buyer_name_filter:
        params_ordered.append(f'%{buyer_name_filter}%')
    
    return query, tuple(params_ordered)


def search_target_buyers(
    db,
    hs_code_6: str,
    destination_countries: Optional[List[str]] = None,
    months_lookback: int = 12,
    min_total_value_usd: float = 50000,
    max_risk_level: str = 'MEDIUM',
    limit: int = 50,
    offset: int = 0,
    buyer_name_filter: Optional[str] = None
) -> Tuple[List[BuyerHunterResult], int]:
    """
    Search for target buyers for a given HS code.
    
    This is the main entry point for the buyer hunter feature.
    
    Args:
        db: DatabaseManager instance
        hs_code_6: 6-digit HS code to search for
        destination_countries: Optional list of destination countries to filter
        months_lookback: Number of months to look back (default 12)
        min_total_value_usd: Minimum total value threshold (default 50000)
        max_risk_level: Maximum risk level to include (LOW/MEDIUM/HIGH)
        limit: Maximum results to return
        offset: Pagination offset
        buyer_name_filter: Optional buyer name to filter by (partial match)
        
    Returns:
        Tuple of (list of BuyerHunterResult, total count)
    """
    # Build and execute query
    query, params = build_buyer_hunter_query(
        hs_code_6=hs_code_6,
        destination_countries=destination_countries,
        months_lookback=months_lookback,
        min_total_value_usd=min_total_value_usd,
        max_risk_level=max_risk_level,
        buyer_name_filter=buyer_name_filter
    )
    
    logger.debug(f"Buyer Hunter query params: {params}")
    
    # Execute query
    results = db.execute_query(query, params)
    
    if not results:
        return [], 0
    
    # Convert to dicts
    columns = [
        'buyer_uuid', 'buyer_name', 'buyer_country', 'destination_country',
        'total_value_usd_12m', 'total_shipments_12m', 'avg_shipment_value_usd',
        'hs_share_pct', 'months_with_shipments_12m', 'years_active',
        'classification', 'website_present', 'website_url',
        'current_risk_level', 'risk_score'
    ]
    
    buyers_data = []
    for row in results:
        buyer_dict = {}
        for i, col in enumerate(columns):
            value = row[i] if i < len(row) else None
            # Handle numeric conversions with NaN/Inf safety
            if col in ['total_value_usd_12m', 'avg_shipment_value_usd', 'hs_share_pct']:
                buyer_dict[col] = _safe_float(value)
            elif col == 'risk_score':
                buyer_dict[col] = _safe_float_or_none(value)
            elif col in ['total_shipments_12m', 'months_with_shipments_12m', 'years_active']:
                buyer_dict[col] = int(value) if value is not None else 0
            elif col == 'website_present':
                buyer_dict[col] = bool(value) if value is not None else False
            else:
                buyer_dict[col] = value
        buyers_data.append(buyer_dict)
    
    total_count = len(buyers_data)
    
    # Compute scores
    scored_results = compute_opportunity_scores(buyers_data)
    
    # Apply pagination after scoring (results are sorted by score)
    paginated_results = scored_results[offset:offset + limit]
    
    return paginated_results, total_count


def get_top_target_buyers(
    db,
    hs_code_6: str,
    destination_countries: Optional[List[str]] = None,
    months_lookback: int = 12,
    min_total_value_usd: float = 50000,
    max_risk_level: str = 'MEDIUM',
    limit: int = 20
) -> List[BuyerHunterResult]:
    """
    Get top N target buyers by opportunity score.
    
    Convenience method that returns only the top results.
    """
    results, _ = search_target_buyers(
        db=db,
        hs_code_6=hs_code_6,
        destination_countries=destination_countries,
        months_lookback=months_lookback,
        min_total_value_usd=min_total_value_usd,
        max_risk_level=max_risk_level,
        limit=limit,
        offset=0
    )
    return results
