"""
Dashboard Router
=================
Dashboard endpoints for buyer interest and analytics.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field

from api.deps import get_db
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])
logger = logging.getLogger(__name__)


# =====================================================================
# SCHEMAS
# =====================================================================

class BuyerInterestItem(BaseModel):
    """Single buyer interest record."""
    buyer_uuid: str
    buyer_name: str
    buyer_country: Optional[str] = None
    total_value_usd: Optional[float] = None
    total_shipments: int = 0
    active_months: int = 0
    hs_codes_count: int = 0
    risk_level: str = "UNSCORED"
    last_shipment_date: Optional[str] = None


class BuyerInterestResponse(BaseModel):
    """Response for buyer interest endpoint."""
    items: List[BuyerInterestItem]
    total: int
    limit: int
    offset: int


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.get("/buyer-interest", response_model=BuyerInterestResponse)
def get_buyer_interest(
    country: Optional[str] = Query(None, description="Filter by buyer country"),
    hs_code_6: Optional[str] = Query(None, description="Filter by HS code"),
    min_value_usd: Optional[float] = Query(None, description="Minimum total value USD"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get buyer interest dashboard showing active buyers with their metrics.
    
    Returns:
    - Buyer summary with trade volumes
    - Activity metrics (months active, shipment counts)
    - Product diversity (HS codes count)
    - Risk levels
    
    Data source: vw_buyer_360
    """
    try:
        # Build WHERE clauses
        where_clauses = ["1=1"]
        params = []
        
        if country:
            where_clauses.append("buyer_country = %s")
            params.append(country.upper())
        
        if risk_level:
            where_clauses.append("current_risk_level = %s")
            params.append(risk_level.upper())
        
        if min_value_usd is not None:
            where_clauses.append("total_value_usd >= %s")
            params.append(min_value_usd)
        
        # HS code filter requires join with ledger
        hs_join = ""
        if hs_code_6:
            hs_join = """
                AND buyer_uuid IN (
                    SELECT DISTINCT buyer_uuid 
                    FROM global_trades_ledger 
                    WHERE hs_code_6 = %s AND buyer_uuid IS NOT NULL
                )
            """
            params.append(hs_code_6)
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) FROM vw_buyer_360
            WHERE {where_sql} {hs_join}
        """
        count_result = db.execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0
        
        # Fetch data with pagination
        params_with_pagination = params + [limit, offset]
        
        data_query = f"""
            SELECT 
                buyer_uuid::text,
                buyer_name,
                buyer_country,
                total_value_usd,
                total_shipments,
                active_years * 12 as active_months_approx,
                unique_hs_codes,
                current_risk_level,
                last_shipment_date::text
            FROM vw_buyer_360
            WHERE {where_sql} {hs_join}
            ORDER BY total_value_usd DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(data_query, tuple(params_with_pagination))
        
        items = []
        for row in (results or []):
            items.append(BuyerInterestItem(
                buyer_uuid=row[0],
                buyer_name=row[1] or "Unknown",
                buyer_country=row[2],
                total_value_usd=float(row[3]) if row[3] is not None else None,
                total_shipments=row[4] or 0,
                active_months=row[5] or 0,
                hs_codes_count=row[6] or 0,
                risk_level=row[7] or "UNSCORED",
                last_shipment_date=row[8]
            ))
        
        return BuyerInterestResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error fetching buyer interest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching buyer interest: {str(e)}")
