"""
Products Router
================
Products/HS codes endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from api.deps import get_db
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/products", tags=["Products"])
logger = logging.getLogger(__name__)


# =====================================================================
# SCHEMAS
# =====================================================================

class ProductItem(BaseModel):
    """Product/HS code item."""
    hs_code_6: str
    hs_description: Optional[str] = None
    total_shipments: int = 0
    total_value_usd: Optional[float] = None
    unique_buyers: int = 0
    avg_shipment_value: Optional[float] = None
    top_buyer_country: Optional[str] = None


class ProductsResponse(BaseModel):
    """Response for products listing."""
    items: List[ProductItem]
    total: int
    limit: int
    offset: int


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.get("", response_model=ProductsResponse)
def list_products(
    country: Optional[str] = Query(None, description="Filter by buyer country"),
    hs_code_6: Optional[str] = Query(None, description="Filter by specific HS code"),
    min_value_usd: Optional[float] = Query(None, description="Minimum total value USD"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: DatabaseManager = Depends(get_db)
):
    """
    List products (HS codes) with trade statistics.
    
    Returns aggregated HS code data from global_trades_ledger.
    """
    try:
        # Build WHERE clauses
        where_clauses = ["hs_code_6 IS NOT NULL"]
        params = []
        
        if country:
            where_clauses.append("destination_country = %s")
            params.append(country.upper())
        
        if hs_code_6:
            where_clauses.append("hs_code_6 = %s")
            params.append(hs_code_6)
        
        where_sql = " AND ".join(where_clauses)
        
        # Count total unique HS codes
        count_query = f"""
            SELECT COUNT(DISTINCT hs_code_6) 
            FROM global_trades_ledger
            WHERE {where_sql}
        """
        count_result = db.execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0
        
        # Fetch aggregated data with pagination
        params_with_pagination = params + [limit, offset]
        
        data_query = f"""
            SELECT 
                hs_code_6,
                NULL as hs_description,
                COUNT(*) as total_shipments,
                SUM(customs_value_usd) as total_value_usd,
                COUNT(DISTINCT buyer_uuid) as unique_buyers,
                AVG(customs_value_usd) as avg_shipment_value,
                (
                    SELECT destination_country 
                    FROM global_trades_ledger l2 
                    WHERE l2.hs_code_6 = l1.hs_code_6 
                      AND l2.destination_country IS NOT NULL
                    GROUP BY destination_country 
                    ORDER BY SUM(customs_value_usd) DESC 
                    LIMIT 1
                ) as top_buyer_country
            FROM global_trades_ledger l1
            WHERE {where_sql}
            GROUP BY hs_code_6
            HAVING SUM(customs_value_usd) >= %s
            ORDER BY SUM(customs_value_usd) DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        # Add min_value_usd filter
        min_value = min_value_usd if min_value_usd is not None else 0.0
        params_with_pagination = params + [min_value, limit, offset]
        
        results = db.execute_query(data_query, tuple(params_with_pagination))
        
        items = []
        for row in (results or []):
            items.append(ProductItem(
                hs_code_6=row[0],
                hs_description=row[1],
                total_shipments=row[2] or 0,
                total_value_usd=float(row[3]) if row[3] is not None else None,
                unique_buyers=row[4] or 0,
                avg_shipment_value=float(row[5]) if row[5] is not None else None,
                top_buyer_country=row[6]
            ))
        
        return ProductsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing products: {str(e)}")
