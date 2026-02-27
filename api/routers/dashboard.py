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


class AlertItem(BaseModel):
    """Single alert/notification item."""
    id: str
    type: str
    message: str
    severity: str
    timestamp: str
    buyer_uuid: Optional[str] = None
    is_read: bool = False


class AlertsResponse(BaseModel):
    """Response for alerts endpoint."""
    items: List[AlertItem]
    total: int
    unread_count: int


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_buyers: int = 0
    total_shipments: int = 0
    total_value_usd: float = 0.0
    active_buyers_30d: int = 0
    high_risk_buyers: int = 0
    new_buyers_30d: int = 0
    avg_shipment_value: float = 0.0
    unique_hs_codes: int = 0
    unique_countries: int = 0


class RecentSearchItem(BaseModel):
    """Recent search record."""
    search_id: str
    query: str
    filters: Optional[dict] = None
    result_count: int = 0
    timestamp: str


class RecentSearchesResponse(BaseModel):
    """Response for recent searches."""
    items: List[RecentSearchItem]
    total: int


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


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(
    limit: int = Query(20, ge=1, le=100, description="Number of alerts"),
    unread_only: bool = Query(False, description="Show only unread alerts"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get dashboard alerts and notifications.
    
    Returns recent alerts about high-risk buyers, unusual patterns, etc.
    Currently returns placeholder data - can be enhanced with real alert logic.
    """
    try:
        # For now, return empty alerts (can be enhanced later with real alert detection)
        return AlertsResponse(
            items=[],
            total=0,
            unread_count=0
        )
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: DatabaseManager = Depends(get_db)
):
    """
    Get overall dashboard statistics.
    
    Returns key metrics from vw_buyer_360 and global_trades_ledger.
    """
    try:
        # Get overall stats from vw_buyer_360
        stats_query = """
            SELECT 
                COUNT(DISTINCT buyer_uuid) as total_buyers,
                COALESCE(SUM(total_shipments), 0) as total_shipments,
                COALESCE(SUM(total_value_usd), 0) as total_value_usd,
                COUNT(DISTINCT CASE WHEN current_risk_level IN ('HIGH', 'CRITICAL') THEN buyer_uuid END) as high_risk_buyers,
                COUNT(DISTINCT CASE 
                    WHEN last_shipment_date >= CURRENT_DATE - INTERVAL '30 days' 
                    THEN buyer_uuid 
                END) as active_buyers_30d,
                COALESCE(SUM(unique_hs_codes), 0) as total_hs_codes_sum
            FROM vw_buyer_360
        """
        
        result = db.execute_query(stats_query, ())
        
        if result and result[0]:
            row = result[0]
            total_buyers = row[0] or 0
            total_shipments = row[1] or 0
            total_value_usd = float(row[2]) if row[2] else 0.0
            high_risk_buyers = row[3] or 0
            active_buyers_30d = row[4] or 0
            
            # Calculate average shipment value
            avg_shipment_value = total_value_usd / total_shipments if total_shipments > 0 else 0.0
            
            # Get unique HS codes count from ledger
            hs_query = "SELECT COUNT(DISTINCT hs_code_6) FROM global_trades_ledger WHERE hs_code_6 IS NOT NULL"
            hs_result = db.execute_query(hs_query, ())
            unique_hs_codes = hs_result[0][0] if hs_result and hs_result[0] else 0
            
            # Get unique countries
            country_query = "SELECT COUNT(DISTINCT buyer_country) FROM vw_buyer_360 WHERE buyer_country IS NOT NULL"
            country_result = db.execute_query(country_query, ())
            unique_countries = country_result[0][0] if country_result and country_result[0] else 0
            
            # Get new buyers in last 30 days
            new_buyers_query = """
                SELECT COUNT(DISTINCT buyer_uuid) 
                FROM vw_buyer_360 
                WHERE first_shipment_date >= CURRENT_DATE - INTERVAL '30 days'
            """
            new_buyers_result = db.execute_query(new_buyers_query, ())
            new_buyers_30d = new_buyers_result[0][0] if new_buyers_result and new_buyers_result[0] else 0
            
            return DashboardStats(
                total_buyers=total_buyers,
                total_shipments=total_shipments,
                total_value_usd=total_value_usd,
                active_buyers_30d=active_buyers_30d,
                high_risk_buyers=high_risk_buyers,
                new_buyers_30d=new_buyers_30d,
                avg_shipment_value=avg_shipment_value,
                unique_hs_codes=unique_hs_codes,
                unique_countries=unique_countries
            )
        else:
            return DashboardStats()
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")


@router.get("/recent-searches", response_model=RecentSearchesResponse)
def get_recent_searches(
    limit: int = Query(10, ge=1, le=50, description="Number of recent searches"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get recent search queries.
    
    Returns placeholder data - can be enhanced with search logging.
    """
    try:
        # For now, return empty recent searches (can be enhanced with search logging)
        return RecentSearchesResponse(
            items=[],
            total=0
        )
        
    except Exception as e:
        logger.error(f"Error fetching recent searches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching recent searches: {str(e)}")
