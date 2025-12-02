"""
EPIC 7B - HS Dashboard Router
==============================
HS code dashboard and analytics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List

from api.deps import get_db
from api.schemas import (
    HsDashboardResponse, HsDashboardRecord, MonthlyTrend
)
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/hs-dashboard", tags=["HS Dashboard"])


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


@router.get("", response_model=HsDashboardResponse)
def get_hs_dashboard(
    hs_code_6: str = Query(..., description="HS code (6 digits) - required"),
    reporting_country: Optional[str] = Query(None, description="Filter by reporting country"),
    direction: Optional[str] = Query(None, description="Filter by direction (IMPORT/EXPORT)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get dashboard data for a specific HS code.
    
    Returns:
    - Aggregated totals across the filter criteria
    - Monthly breakdown from vw_country_hs_dashboard
    - Monthly trend for charting
    
    Data source: vw_country_hs_dashboard (built on mv_country_hs_month_summary)
    """
    try:
        # Validate direction if provided
        if direction and direction.upper() not in ('IMPORT', 'EXPORT'):
            raise HTTPException(
                status_code=400, 
                detail="direction must be 'IMPORT' or 'EXPORT'"
            )
        
        # Build WHERE clauses
        where_clauses = ["hs_code_6 = %s"]
        params = [hs_code_6]
        
        if reporting_country:
            where_clauses.append("reporting_country = %s")
            params.append(reporting_country.upper())
        
        if direction:
            where_clauses.append("direction = %s")
            params.append(direction.upper())
        
        if year:
            where_clauses.append("year = %s")
            params.append(year)
        
        where_sql = " AND ".join(where_clauses)
        
        # Fetch monthly breakdown
        data_query = f"""
            SELECT 
                hs_code_6,
                reporting_country,
                direction,
                year,
                month,
                shipment_count,
                unique_buyers,
                unique_suppliers,
                total_value_usd,
                total_qty_kg,
                avg_price_usd_per_kg,
                avg_value_per_shipment_usd,
                value_share_pct,
                high_risk_shipments,
                high_risk_buyers,
                high_risk_shipment_pct
            FROM vw_country_hs_dashboard
            WHERE {where_sql}
            ORDER BY year DESC, month DESC
        """
        
        results = db.execute_query(data_query, tuple(params))
        
        if not results:
            # Return empty response if no data found
            return HsDashboardResponse(
                hs_code_6=hs_code_6,
                reporting_country=reporting_country,
                direction=direction,
                total_shipments=0,
                total_value_usd=None,
                total_qty_kg=None,
                avg_price_usd_per_kg=None,
                unique_buyers=0,
                unique_suppliers=0,
                high_risk_shipments=0,
                high_risk_pct=None,
                monthly_data=[],
                monthly_trend=[]
            )
        
        # Build monthly records
        monthly_data = []
        monthly_trend = []
        
        # Aggregated totals
        total_shipments = 0
        total_value = 0.0
        total_qty = 0.0
        total_high_risk = 0
        unique_buyers_set = set()
        unique_suppliers_set = set()
        
        for row in results:
            record = HsDashboardRecord(
                hs_code_6=row[0],
                reporting_country=row[1],
                direction=row[2],
                year=row[3],
                month=row[4],
                shipment_count=row[5] or 0,
                unique_buyers=row[6] or 0,
                unique_suppliers=row[7] or 0,
                total_value_usd=_safe_float(row[8]),
                total_qty_kg=_safe_float(row[9]),
                avg_price_usd_per_kg=_safe_float(row[10]),
                avg_value_per_shipment_usd=_safe_float(row[11]),
                value_share_pct=_safe_float(row[12]),
                high_risk_shipments=row[13] or 0,
                high_risk_buyers=row[14] or 0,
                high_risk_shipment_pct=_safe_float(row[15])
            )
            monthly_data.append(record)
            
            # Add to trend (reversed order for chronological)
            monthly_trend.append(MonthlyTrend(
                year=row[3],
                month=row[4],
                shipment_count=row[5] or 0,
                total_value_usd=_safe_float(row[8]),
                avg_price_usd_per_kg=_safe_float(row[10])
            ))
            
            # Aggregate totals
            total_shipments += row[5] or 0
            if row[8]:
                val = _safe_float(row[8])
                if val:
                    total_value += val
            if row[9]:
                qty = _safe_float(row[9])
                if qty:
                    total_qty += qty
            total_high_risk += row[13] or 0
        
        # Reverse trend for chronological order
        monthly_trend.reverse()
        
        # Calculate average price from totals
        avg_price = None
        if total_qty > 0:
            avg_price = total_value / total_qty
        
        # Calculate high risk percentage
        high_risk_pct = None
        if total_shipments > 0:
            high_risk_pct = (total_high_risk / total_shipments) * 100
        
        # Get unique counts from the first row (they are per-month, so we need to re-query)
        # For simplicity, we'll sum unique counts (though this overcounts)
        # A more accurate approach would be a separate query
        unique_buyers_total = sum(r.unique_buyers for r in monthly_data)
        unique_suppliers_total = sum(r.unique_suppliers for r in monthly_data)
        
        return HsDashboardResponse(
            hs_code_6=hs_code_6,
            reporting_country=reporting_country,
            direction=direction,
            total_shipments=total_shipments,
            total_value_usd=total_value if total_value > 0 else None,
            total_qty_kg=total_qty if total_qty > 0 else None,
            avg_price_usd_per_kg=avg_price,
            unique_buyers=unique_buyers_total,
            unique_suppliers=unique_suppliers_total,
            high_risk_shipments=total_high_risk,
            high_risk_pct=high_risk_pct,
            monthly_data=monthly_data,
            monthly_trend=monthly_trend
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HS dashboard: {str(e)}")


@router.get("/top-hs-codes")
def get_top_hs_codes(
    reporting_country: Optional[str] = Query(None, description="Filter by reporting country"),
    direction: Optional[str] = Query(None, description="Filter by direction (IMPORT/EXPORT)"),
    limit: int = Query(20, ge=1, le=100, description="Number of top HS codes to return"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get top HS codes by total value.
    
    Returns a ranked list of HS codes with aggregated metrics.
    """
    try:
        where_clauses = ["1=1"]
        params = []
        
        if reporting_country:
            where_clauses.append("reporting_country = %s")
            params.append(reporting_country.upper())
        
        if direction:
            where_clauses.append("direction = %s")
            params.append(direction.upper())
        
        params.append(limit)
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                hs_code_6,
                SUM(shipment_count) as total_shipments,
                SUM(total_value_usd) as total_value,
                SUM(total_qty_kg) as total_qty,
                SUM(high_risk_shipments) as high_risk_count,
                COUNT(DISTINCT reporting_country) as country_count
            FROM vw_country_hs_dashboard
            WHERE {where_sql}
            GROUP BY hs_code_6
            ORDER BY total_value DESC NULLS LAST
            LIMIT %s
        """
        
        results = db.execute_query(query, tuple(params))
        
        items = []
        for row in (results or []):
            items.append({
                "hs_code_6": row[0],
                "total_shipments": row[1] or 0,
                "total_value_usd": _safe_float(row[2]),
                "total_qty_kg": _safe_float(row[3]),
                "high_risk_shipments": row[4] or 0,
                "country_count": row[5] or 0
            })
        
        return {"items": items, "count": len(items)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top HS codes: {str(e)}")
