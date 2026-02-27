"""
Suppliers Router
=================
Supplier listing and detail endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from api.deps import get_db
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])
logger = logging.getLogger(__name__)


class SupplierItem(BaseModel):
    """Single supplier item."""
    supplier_uuid: str
    supplier_name: str
    supplier_country: Optional[str] = None
    total_shipments: int = 0
    total_value_usd: Optional[float] = None
    unique_buyers: int = 0
    unique_hs_codes: int = 0
    first_shipment_date: Optional[str] = None
    last_shipment_date: Optional[str] = None


class SuppliersResponse(BaseModel):
    """Response for suppliers listing."""
    items: List[SupplierItem]
    total: int
    limit: int
    offset: int


@router.get("", response_model=SuppliersResponse)
def list_suppliers(
    country: Optional[str] = Query(None, description="Filter by supplier country"),
    hs_code_6: Optional[str] = Query(None, description="Filter by HS code"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db)
):
    """
    List suppliers with aggregated trade statistics.
    
    Data source: organizations_master + global_trades_ledger
    """
    try:
        where_clauses = ["o.type = 'SUPPLIER'"]
        params = []
        
        if country:
            where_clauses.append("o.country_iso = %s")
            params.append(country.upper())
        
        hs_filter = ""
        if hs_code_6:
            hs_filter = "AND g.hs_code_6 = %s"
            params.append(hs_code_6)
        
        where_sql = " AND ".join(where_clauses)
        
        count_query = f"""
            SELECT COUNT(DISTINCT o.org_uuid) 
            FROM organizations_master o
            WHERE {where_sql}
        """
        count_result = db.execute_query(count_query, tuple(params[:1] if country else []))
        total = count_result[0][0] if count_result else 0
        
        all_params = list(params) + [limit, offset]
        
        query = f"""
            SELECT 
                o.org_uuid::text,
                o.name_normalized,
                o.country_iso,
                COALESCE(stats.shipment_count, 0) as total_shipments,
                stats.total_value,
                COALESCE(stats.buyer_count, 0) as unique_buyers,
                COALESCE(stats.hs_count, 0) as unique_hs_codes,
                stats.first_date::text,
                stats.last_date::text
            FROM organizations_master o
            LEFT JOIN LATERAL (
                SELECT 
                    COUNT(*) as shipment_count,
                    SUM(customs_value_usd) as total_value,
                    COUNT(DISTINCT buyer_uuid) as buyer_count,
                    COUNT(DISTINCT hs_code_6) as hs_count,
                    MIN(shipment_date) as first_date,
                    MAX(shipment_date) as last_date
                FROM global_trades_ledger g
                WHERE g.supplier_uuid = o.org_uuid {hs_filter}
            ) stats ON true
            WHERE {where_sql}
            ORDER BY stats.total_value DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(query, tuple(all_params))
        
        items = []
        for row in (results or []):
            items.append(SupplierItem(
                supplier_uuid=row[0],
                supplier_name=row[1] or "Unknown",
                supplier_country=row[2],
                total_shipments=row[3] or 0,
                total_value_usd=float(row[4]) if row[4] else None,
                unique_buyers=row[5] or 0,
                unique_hs_codes=row[6] or 0,
                first_shipment_date=row[7],
                last_shipment_date=row[8]
            ))
        
        return SuppliersResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing suppliers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing suppliers: {str(e)}")
