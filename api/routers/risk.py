"""
EPIC 7B - Risk Router
======================
Risk insights and top risky entities endpoints.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from api.deps import get_db
from api.schemas import (
    RiskShipmentRecord, RiskBuyerRecord,
    RiskShipmentListResponse, RiskBuyerListResponse
)
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/risk", tags=["Risk"])

# Constants
MAX_LIMIT = 200
DEFAULT_LIMIT = 50


def _safe_float(value) -> Optional[float]:
    """Safely convert to float, handling NaN and None."""
    if value is None:
        return None
    try:
        f = float(value)
        import math
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except:
        return None


def _parse_reasons(value) -> Optional[dict]:
    """Parse reasons JSONB from database."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return None
    return None


@router.get("/top-shipments", response_model=RiskShipmentListResponse)
def get_top_risky_shipments(
    level: Optional[str] = Query(
        "HIGH,CRITICAL", 
        description="Comma-separated risk levels (e.g., HIGH,CRITICAL)"
    ),
    main_reason: Optional[str] = Query(None, description="Filter by main reason code"),
    hs_code_6: Optional[str] = Query(None, description="Filter by HS code"),
    reporting_country: Optional[str] = Query(None, description="Filter by reporting country"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get top risky shipments.
    
    Returns shipment-level risk scores joined with ledger data.
    Default: HIGH and CRITICAL risk levels.
    """
    try:
        # Parse risk levels
        risk_levels = [l.strip().upper() for l in level.split(",")] if level else ["HIGH", "CRITICAL"]
        valid_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        
        for rl in risk_levels:
            if rl not in valid_levels:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid risk level: {rl}. Must be one of {valid_levels}"
                )
        
        # Build WHERE clauses
        where_clauses = ["rs.entity_type = 'SHIPMENT'"]
        params = []
        
        # Risk levels filter using ANY array
        level_placeholders = ",".join(["%s"] * len(risk_levels))
        where_clauses.append(f"rs.risk_level IN ({level_placeholders})")
        params.extend(risk_levels)
        
        if main_reason:
            where_clauses.append("rs.main_reason_code = %s")
            params.append(main_reason.upper())
        
        if hs_code_6:
            where_clauses.append("g.hs_code_6 = %s")
            params.append(hs_code_6)
        
        if reporting_country:
            where_clauses.append("g.reporting_country = %s")
            params.append(reporting_country.upper())
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) 
            FROM risk_scores rs
            LEFT JOIN global_trades_ledger g ON rs.entity_id = g.transaction_id
            WHERE {where_sql}
        """
        count_result = db.execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0
        
        # Fetch data with pagination
        params_with_pagination = params + [limit, offset]
        
        data_query = f"""
            SELECT 
                rs.entity_id::text,
                rs.risk_score,
                rs.risk_level,
                rs.confidence_score,
                rs.main_reason_code,
                rs.scope_key,
                g.hs_code_6,
                g.origin_country,
                g.destination_country,
                g.customs_value_usd,
                g.price_usd_per_kg,
                g.shipment_date,
                rs.reasons,
                rs.computed_at
            FROM risk_scores rs
            LEFT JOIN global_trades_ledger g ON rs.entity_id = g.transaction_id
            WHERE {where_sql}
            ORDER BY rs.risk_score DESC, rs.computed_at DESC
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(data_query, tuple(params_with_pagination))
        
        items = []
        for row in (results or []):
            items.append(RiskShipmentRecord(
                entity_id=row[0],
                risk_score=_safe_float(row[1]) or 0,
                risk_level=row[2],
                confidence_score=_safe_float(row[3]),
                main_reason_code=row[4],
                scope_key=row[5],
                hs_code_6=row[6],
                origin_country=row[7],
                destination_country=row[8],
                customs_value_usd=_safe_float(row[9]),
                price_usd_per_kg=_safe_float(row[10]),
                shipment_date=row[11],
                reasons=_parse_reasons(row[12]),
                computed_at=row[13]
            ))
        
        return RiskShipmentListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching risky shipments: {str(e)}")


@router.get("/top-buyers", response_model=RiskBuyerListResponse)
def get_top_risky_buyers(
    level: Optional[str] = Query(
        "HIGH,CRITICAL", 
        description="Comma-separated risk levels (e.g., HIGH,CRITICAL)"
    ),
    main_reason: Optional[str] = Query(None, description="Filter by main reason code"),
    min_value_usd: Optional[float] = Query(None, description="Minimum buyer total value USD"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get top risky buyers.
    
    Returns buyer-level risk scores joined with buyer 360 data.
    Default: HIGH and CRITICAL risk levels.
    """
    try:
        # Parse risk levels
        risk_levels = [l.strip().upper() for l in level.split(",")] if level else ["HIGH", "CRITICAL"]
        valid_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        
        for rl in risk_levels:
            if rl not in valid_levels:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid risk level: {rl}. Must be one of {valid_levels}"
                )
        
        # Build WHERE clauses
        where_clauses = ["rs.entity_type = 'BUYER'"]
        params = []
        
        # Risk levels filter
        level_placeholders = ",".join(["%s"] * len(risk_levels))
        where_clauses.append(f"rs.risk_level IN ({level_placeholders})")
        params.extend(risk_levels)
        
        if main_reason:
            where_clauses.append("rs.main_reason_code = %s")
            params.append(main_reason.upper())
        
        if min_value_usd is not None:
            where_clauses.append("b.total_value_usd >= %s")
            params.append(min_value_usd)
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) 
            FROM risk_scores rs
            LEFT JOIN vw_buyer_360 b ON rs.entity_id = b.buyer_uuid
            WHERE {where_sql}
        """
        count_result = db.execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0
        
        # Fetch data with pagination
        params_with_pagination = params + [limit, offset]
        
        data_query = f"""
            SELECT 
                rs.entity_id::text,
                b.buyer_name,
                b.buyer_country,
                rs.risk_score,
                rs.risk_level,
                rs.confidence_score,
                rs.main_reason_code,
                rs.scope_key,
                b.total_value_usd,
                b.total_shipments,
                rs.reasons,
                rs.computed_at
            FROM risk_scores rs
            LEFT JOIN vw_buyer_360 b ON rs.entity_id = b.buyer_uuid
            WHERE {where_sql}
            ORDER BY rs.risk_score DESC, b.total_value_usd DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(data_query, tuple(params_with_pagination))
        
        items = []
        for row in (results or []):
            items.append(RiskBuyerRecord(
                entity_id=row[0],
                buyer_name=row[1],
                buyer_country=row[2],
                risk_score=_safe_float(row[3]) or 0,
                risk_level=row[4],
                confidence_score=_safe_float(row[5]),
                main_reason_code=row[6],
                scope_key=row[7],
                total_value_usd=_safe_float(row[8]),
                total_shipments=row[9],
                reasons=_parse_reasons(row[10]),
                computed_at=row[11]
            ))
        
        return RiskBuyerListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching risky buyers: {str(e)}")


@router.get("/summary")
def get_risk_summary(
    db: DatabaseManager = Depends(get_db)
):
    """
    Get overall risk summary statistics.
    
    Returns counts by risk level and entity type.
    """
    try:
        query = """
            SELECT 
                entity_type,
                risk_level,
                COUNT(*) as count
            FROM risk_scores
            GROUP BY entity_type, risk_level
            ORDER BY entity_type, 
                CASE risk_level 
                    WHEN 'CRITICAL' THEN 1 
                    WHEN 'HIGH' THEN 2 
                    WHEN 'MEDIUM' THEN 3 
                    WHEN 'LOW' THEN 4 
                    ELSE 5 
                END
        """
        
        results = db.execute_query(query)
        
        summary = {
            "SHIPMENT": {},
            "BUYER": {},
            "totals": {"SHIPMENT": 0, "BUYER": 0}
        }
        
        for row in (results or []):
            entity_type, risk_level, count = row
            if entity_type in summary:
                summary[entity_type][risk_level] = count
                summary["totals"][entity_type] += count
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching risk summary: {str(e)}")
