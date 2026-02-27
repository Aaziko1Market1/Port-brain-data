"""
EPIC 7B - Buyers Router
========================
Buyer 360 and buyer list endpoints.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID

from api.deps import get_db
from api.schemas import (
    BuyerSummary, Buyer360, BuyerListResponse,
    HsCodeSummary, CountrySummary,
    TradeMonth, BuyerTradeHistoryResponse
)
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1/buyers", tags=["Buyers"])

# Constants
MAX_LIMIT = 200
DEFAULT_LIMIT = 50


def _parse_jsonb(value) -> list:
    """Parse JSONB value from database."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return []
    if isinstance(value, list):
        return value
    return []


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


@router.get("/hs-codes")
def list_buyer_hs_codes(
    limit: int = Query(100, ge=1, le=500, description="Number of HS codes"),
    country: Optional[str] = Query(None, description="Filter by buyer country"),
    db: DatabaseManager = Depends(get_db)
):
    """List HS codes traded by buyers with aggregated stats."""
    try:
        where_clause = "WHERE hs_code_6 IS NOT NULL"
        params = []
        if country:
            where_clause += " AND destination_country = %s"
            params.append(country.upper())
        
        query = f"""
            SELECT 
                hs_code_6,
                goods_description,
                COUNT(*) as shipment_count,
                SUM(customs_value_usd) as total_value,
                COUNT(DISTINCT buyer_uuid) as buyer_count,
                COUNT(DISTINCT destination_country) as country_count
            FROM global_trades_ledger
            {where_clause}
            GROUP BY hs_code_6, goods_description
            ORDER BY SUM(customs_value_usd) DESC NULLS LAST
            LIMIT %s
        """
        params.append(limit)
        results = db.execute_query(query, tuple(params))
        
        items = []
        for row in (results or []):
            items.append({
                "hs_code_6": row[0],
                "description": row[1] or "",
                "shipment_count": row[2] or 0,
                "total_value_usd": float(row[3]) if row[3] else 0,
                "buyer_count": row[4] or 0,
                "country_count": row[5] or 0
            })
        return {"items": items, "total": len(items), "limit": limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing HS codes: {str(e)}")


@router.get("", response_model=BuyerListResponse)
def list_buyers(
    country: Optional[str] = Query(None, description="Filter by buyer country"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (LOW/MEDIUM/HIGH/CRITICAL)"),
    hs_code_6: Optional[str] = Query(None, description="Filter buyers trading this HS code"),
    min_value_usd: Optional[float] = Query(None, description="Minimum total value USD"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: DatabaseManager = Depends(get_db)
):
    """
    List buyers with optional filters.
    
    Returns paginated buyer summaries from vw_buyer_360.
    """
    try:
        # Build WHERE clauses with parameterized queries
        where_clauses = ["1=1"]  # Always true base
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
        
        # If filtering by HS code, need to check ledger
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
        # Add limit and offset params
        params_with_pagination = params + [limit, offset]
        
        data_query = f"""
            SELECT 
                buyer_uuid::text,
                buyer_name,
                buyer_country,
                buyer_classification,
                total_shipments,
                total_value_usd,
                current_risk_level,
                current_risk_score,
                has_ghost_flag,
                first_shipment_date,
                last_shipment_date
            FROM vw_buyer_360
            WHERE {where_sql} {hs_join}
            ORDER BY total_value_usd DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        
        results = db.execute_query(data_query, tuple(params_with_pagination))
        
        items = []
        for row in (results or []):
            items.append(BuyerSummary(
                buyer_uuid=row[0],
                buyer_name=row[1] or "Unknown",
                buyer_country=row[2],
                buyer_classification=row[3],
                total_shipments=row[4] or 0,
                total_value_usd=_safe_float(row[5]),
                current_risk_level=row[6] or "UNSCORED",
                current_risk_score=_safe_float(row[7]),
                has_ghost_flag=row[8] or False,
                first_shipment_date=row[9],
                last_shipment_date=row[10]
            ))
        
        return BuyerListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing buyers: {str(e)}")


@router.get("/{buyer_uuid}/360", response_model=Buyer360)
def get_buyer_360(
    buyer_uuid: str,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get full 360-degree view for a specific buyer.
    
    Returns complete buyer intelligence including:
    - Identity and profile
    - Volume metrics
    - Product mix (top HS codes)
    - Origin countries
    - Risk snapshot
    """
    try:
        # Validate UUID format
        try:
            UUID(buyer_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
        
        # Fetch from vw_buyer_360
        query = """
            SELECT 
                buyer_uuid::text,
                buyer_name,
                buyer_country,
                buyer_classification,
                total_shipments,
                total_value_usd,
                total_qty_kg,
                total_teu,
                first_shipment_date,
                last_shipment_date,
                active_years,
                unique_hs_codes,
                unique_origin_countries,
                unique_suppliers,
                top_hs6,
                top_origin_countries,
                current_risk_level,
                current_risk_score,
                current_confidence_score,
                current_main_reason_code,
                has_ghost_flag,
                risk_engine_version,
                last_profile_updated_at,
                last_risk_scored_at
            FROM vw_buyer_360
            WHERE buyer_uuid = %s::uuid
        """
        
        result = db.execute_query(query, (buyer_uuid,))
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_uuid}")
        
        row = result[0]
        
        # Parse top HS codes
        top_hs_raw = _parse_jsonb(row[14])
        top_hs_codes = []
        for item in top_hs_raw:
            if isinstance(item, dict):
                top_hs_codes.append(HsCodeSummary(
                    hs_code_6=item.get('hs_code_6', ''),
                    value_usd=_safe_float(item.get('value_usd')),
                    share_pct=_safe_float(item.get('share_pct'))
                ))
        
        # Parse top origin countries
        top_origins_raw = _parse_jsonb(row[15])
        top_origin_countries = []
        for item in top_origins_raw:
            if isinstance(item, dict):
                top_origin_countries.append(CountrySummary(
                    country=item.get('origin_country', ''),
                    value_usd=_safe_float(item.get('value_usd')),
                    share_pct=_safe_float(item.get('share_pct'))
                ))
        
        return Buyer360(
            buyer_uuid=row[0],
            buyer_name=row[1] or "Unknown",
            buyer_country=row[2],
            buyer_classification=row[3],
            total_shipments=row[4] or 0,
            total_value_usd=_safe_float(row[5]),
            total_qty_kg=_safe_float(row[6]),
            total_teu=_safe_float(row[7]),
            first_shipment_date=row[8],
            last_shipment_date=row[9],
            active_years=row[10] or 0,
            unique_hs_codes=row[11] or 0,
            unique_origin_countries=row[12] or 0,
            unique_suppliers=row[13] or 0,
            top_hs_codes=top_hs_codes,
            top_origin_countries=top_origin_countries,
            current_risk_level=row[16] or "UNSCORED",
            current_risk_score=_safe_float(row[17]),
            current_confidence_score=_safe_float(row[18]),
            current_main_reason_code=row[19],
            has_ghost_flag=row[20] or False,
            risk_engine_version=row[21],
            last_profile_updated_at=row[22],
            last_risk_scored_at=row[23]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching buyer 360: {str(e)}")


@router.get("/{buyer_uuid}/trade-history", response_model=BuyerTradeHistoryResponse)
def get_buyer_trade_history(
    buyer_uuid: str,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get monthly trade history for a specific buyer.
    
    Returns chronological monthly aggregates including:
    - Total value (USD)
    - Total volume (kg)
    - Shipment count
    - Top origin country per month
    - Top supplier per month
    """
    try:
        # Validate UUID format
        try:
            UUID(buyer_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
        
        # First get buyer name
        name_query = """
            SELECT name_normalized 
            FROM organizations_master 
            WHERE org_uuid = %s::uuid
        """
        name_result = db.execute_query(name_query, (buyer_uuid,))
        if not name_result:
            raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_uuid}")
        
        buyer_name = name_result[0][0] or "Unknown"
        
        # Get monthly trade history from ledger
        # Using window functions to get top origin/supplier per month
        history_query = """
            WITH monthly_base AS (
                SELECT 
                    EXTRACT(YEAR FROM shipment_date)::int as year,
                    EXTRACT(MONTH FROM shipment_date)::int as month,
                    SUM(customs_value_usd) as total_value_usd,
                    SUM(qty_kg) as total_volume_kg,
                    COUNT(*) as shipment_count
                FROM global_trades_ledger
                WHERE buyer_uuid = %s::uuid
                  AND shipment_date IS NOT NULL
                GROUP BY 
                    EXTRACT(YEAR FROM shipment_date),
                    EXTRACT(MONTH FROM shipment_date)
            ),
            top_origins AS (
                SELECT DISTINCT ON (year, month)
                    EXTRACT(YEAR FROM shipment_date)::int as year,
                    EXTRACT(MONTH FROM shipment_date)::int as month,
                    origin_country
                FROM global_trades_ledger
                WHERE buyer_uuid = %s::uuid
                  AND shipment_date IS NOT NULL
                  AND origin_country IS NOT NULL
                GROUP BY 
                    EXTRACT(YEAR FROM shipment_date),
                    EXTRACT(MONTH FROM shipment_date),
                    origin_country
                ORDER BY year, month, SUM(customs_value_usd) DESC
            )
            SELECT 
                mb.year, 
                mb.month, 
                mb.total_value_usd, 
                mb.total_volume_kg, 
                mb.shipment_count,
                toc.origin_country as top_origin_country,
                NULL as top_supplier
            FROM monthly_base mb
            LEFT JOIN top_origins toc ON mb.year = toc.year AND mb.month = toc.month
            ORDER BY mb.year, mb.month
        """
        
        results = db.execute_query(history_query, (buyer_uuid, buyer_uuid))
        
        months = []
        for row in (results or []):
            months.append(TradeMonth(
                year=row[0],
                month=row[1],
                total_value_usd=_safe_float(row[2]) or 0.0,
                total_volume_kg=_safe_float(row[3]),
                shipment_count=row[4] or 0,
                top_origin_country=row[5],
                top_supplier=row[6]
            ))
        
        return BuyerTradeHistoryResponse(
            buyer_uuid=buyer_uuid,
            buyer_name=buyer_name,
            currency="USD",
            total_months=len(months),
            months=months
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trade history: {str(e)}")


@router.get("/{buyer_uuid}/suppliers")
def get_buyer_suppliers(
    buyer_uuid: str,
    limit: int = Query(10, ge=1, le=100),
    db: DatabaseManager = Depends(get_db)
):
    """Get suppliers that have traded with this buyer."""
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    try:
        query = """
            SELECT 
                g.supplier_uuid::text,
                o.name_normalized as supplier_name,
                o.country_iso as supplier_country,
                COUNT(*) as shipment_count,
                SUM(g.customs_value_usd) as total_value_usd,
                MAX(g.shipment_date)::text as last_shipment_date
            FROM global_trades_ledger g
            LEFT JOIN organizations_master o ON g.supplier_uuid = o.org_uuid
            WHERE g.buyer_uuid = %s::uuid AND g.supplier_uuid IS NOT NULL
            GROUP BY g.supplier_uuid, o.name_normalized, o.country_iso
            ORDER BY SUM(g.customs_value_usd) DESC NULLS LAST
            LIMIT %s
        """
        results = db.execute_query(query, (buyer_uuid, limit))
        items = []
        for row in (results or []):
            items.append({
                "supplier_uuid": row[0],
                "supplier_name": row[1] or "Unknown",
                "supplier_country": row[2],
                "shipment_count": row[3] or 0,
                "total_value_usd": float(row[4]) if row[4] else 0,
                "last_shipment_date": row[5]
            })
        return {"items": items, "total": len(items), "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching buyer suppliers: {str(e)}")


@router.get("/{buyer_uuid}/shipments")
def get_buyer_shipments(
    buyer_uuid: str,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DatabaseManager = Depends(get_db)
):
    """Get individual shipment records for a buyer."""
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    try:
        count_query = "SELECT COUNT(*) FROM global_trades_ledger WHERE buyer_uuid = %s::uuid"
        count_result = db.execute_query(count_query, (buyer_uuid,))
        total = count_result[0][0] if count_result else 0

        query = """
            SELECT 
                transaction_id::text,
                shipment_date::text,
                origin_country,
                destination_country,
                hs_code_6,
                goods_description,
                qty_kg,
                customs_value_usd,
                price_usd_per_kg,
                supplier_uuid::text,
                vessel_name,
                port_loading,
                port_unloading
            FROM global_trades_ledger
            WHERE buyer_uuid = %s::uuid
            ORDER BY shipment_date DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        results = db.execute_query(query, (buyer_uuid, limit, offset))
        items = []
        for row in (results or []):
            items.append({
                "transaction_id": row[0],
                "shipment_date": row[1],
                "origin_country": row[2],
                "destination_country": row[3],
                "hs_code_6": row[4],
                "goods_description": row[5],
                "qty_kg": float(row[6]) if row[6] else None,
                "customs_value_usd": float(row[7]) if row[7] else None,
                "price_usd_per_kg": float(row[8]) if row[8] else None,
                "supplier_uuid": row[9],
                "vessel_name": row[10],
                "port_loading": row[11],
                "port_unloading": row[12]
            })
        return {"items": items, "total": total, "limit": limit, "offset": offset}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching buyer shipments: {str(e)}")


@router.get("/{buyer_uuid}/similar")
def get_similar_buyers(
    buyer_uuid: str,
    limit: int = Query(5, ge=1, le=20),
    db: DatabaseManager = Depends(get_db)
):
    """Find buyers similar to this one based on HS codes and countries."""
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    try:
        query = """
            WITH target_hs AS (
                SELECT DISTINCT hs_code_6
                FROM global_trades_ledger 
                WHERE buyer_uuid = %s::uuid AND hs_code_6 IS NOT NULL
            )
            SELECT 
                b.buyer_uuid::text,
                b.buyer_name,
                b.buyer_country,
                b.total_shipments,
                b.total_value_usd,
                b.current_risk_level
            FROM vw_buyer_360 b
            WHERE b.buyer_uuid != %s::uuid
              AND b.buyer_uuid IN (
                  SELECT DISTINCT g2.buyer_uuid
                  FROM global_trades_ledger g2
                  WHERE g2.hs_code_6 IN (SELECT hs_code_6 FROM target_hs)
                    AND g2.buyer_uuid != %s::uuid
              )
            ORDER BY b.total_value_usd DESC NULLS LAST
            LIMIT %s
        """
        results = db.execute_query(query, (buyer_uuid, buyer_uuid, buyer_uuid, limit))
        items = []
        for row in (results or []):
            items.append({
                "buyer_uuid": row[0],
                "buyer_name": row[1] or "Unknown",
                "buyer_country": row[2],
                "total_shipments": row[3] or 0,
                "total_value_usd": float(row[4]) if row[4] else 0,
                "risk_level": row[5] or "UNSCORED"
            })
        return {"items": items, "total": len(items), "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching similar buyers: {str(e)}")


@router.get("/{buyer_uuid}/business-profile")
def get_buyer_business_profile(
    buyer_uuid: str,
    db: DatabaseManager = Depends(get_db)
):
    """Get business profile for a buyer - aggregated trade intelligence."""
    try:
        UUID(buyer_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid buyer UUID format")
    try:
        query = """
            SELECT 
                b.buyer_uuid::text,
                b.buyer_name,
                b.buyer_country,
                b.buyer_classification,
                b.total_shipments,
                b.total_value_usd,
                b.total_qty_kg,
                b.first_shipment_date::text,
                b.last_shipment_date::text,
                b.active_years,
                b.unique_hs_codes,
                b.unique_origin_countries,
                b.unique_suppliers,
                b.current_risk_level,
                b.current_risk_score,
                b.top_hs6,
                b.top_origin_countries
            FROM vw_buyer_360 b
            WHERE b.buyer_uuid = %s::uuid
        """
        result = db.execute_query(query, (buyer_uuid,))
        if not result:
            raise HTTPException(status_code=404, detail=f"Buyer not found: {buyer_uuid}")
        
        row = result[0]
        top_hs = _parse_jsonb(row[15])
        top_countries = _parse_jsonb(row[16])
        
        # Get top suppliers
        supplier_query = """
            SELECT 
                o.name_normalized,
                o.country_iso,
                COUNT(*) as shipments,
                SUM(g.customs_value_usd) as value
            FROM global_trades_ledger g
            JOIN organizations_master o ON g.supplier_uuid = o.org_uuid
            WHERE g.buyer_uuid = %s::uuid
            GROUP BY o.name_normalized, o.country_iso
            ORDER BY SUM(g.customs_value_usd) DESC NULLS LAST
            LIMIT 5
        """
        supplier_results = db.execute_query(supplier_query, (buyer_uuid,))
        top_suppliers = []
        for s in (supplier_results or []):
            top_suppliers.append({
                "name": s[0] or "Unknown",
                "country": s[1],
                "shipments": s[2] or 0,
                "value_usd": float(s[3]) if s[3] else 0
            })
        
        avg_value = float(row[5]) / int(row[4]) if row[4] and int(row[4]) > 0 else 0
        
        return {
            "buyer_uuid": row[0],
            "buyer_name": row[1] or "Unknown",
            "buyer_country": row[2],
            "classification": row[3] or "Unknown",
            "total_shipments": row[4] or 0,
            "total_value_usd": float(row[5]) if row[5] else 0,
            "total_qty_kg": float(row[6]) if row[6] else 0,
            "avg_shipment_value": avg_value,
            "first_shipment_date": row[7],
            "last_shipment_date": row[8],
            "active_years": row[9] or 0,
            "unique_hs_codes": row[10] or 0,
            "unique_origin_countries": row[11] or 0,
            "unique_suppliers": row[12] or 0,
            "risk_level": row[13] or "UNSCORED",
            "risk_score": _safe_float(row[14]),
            "top_hs_codes": top_hs,
            "top_origin_countries": top_countries,
            "top_suppliers": top_suppliers
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching business profile: {str(e)}")
