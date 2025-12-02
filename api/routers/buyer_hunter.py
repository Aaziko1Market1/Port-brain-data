"""
EPIC 7D - Buyer Hunter Router
==============================
API endpoints for finding best target buyers for a given HS code.

All scoring is deterministic and data-driven.
LLM is NOT used for scoring - only for explanations via separate endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel, Field

from api.deps import get_db
from etl.db_utils import DatabaseManager
from etl.analytics.buyer_hunter import (
    search_target_buyers,
    get_top_target_buyers,
    BuyerHunterResult
)

router = APIRouter(prefix="/api/v1/buyer-hunter", tags=["Buyer Hunter"])
logger = logging.getLogger(__name__)

# Constants
MAX_LIMIT = 200
DEFAULT_LIMIT = 50
TOP_DEFAULT_LIMIT = 20
TOP_MAX_LIMIT = 50


# =====================================================================
# PYDANTIC SCHEMAS
# =====================================================================

class BuyerHunterResultSchema(BaseModel):
    """Schema for a buyer hunter result."""
    buyer_uuid: str
    buyer_name: str
    buyer_country: Optional[str] = None
    destination_country: Optional[str] = None
    total_value_usd_12m: float
    total_shipments_12m: int
    avg_shipment_value_usd: float
    hs_share_pct: float
    months_with_shipments_12m: int
    years_active: int
    classification: str
    website_present: bool
    website_url: Optional[str] = None
    current_risk_level: str
    risk_score: Optional[float] = None
    opportunity_score: float = Field(ge=0, le=100)
    
    # Score breakdown
    volume_score: float
    stability_score: float
    hs_focus_score: float
    risk_score_component: float
    data_quality_score: float


class BuyerHunterSearchResponse(BaseModel):
    """Response for buyer hunter search."""
    items: List[BuyerHunterResultSchema]
    total: int
    limit: int
    offset: int
    hs_code_6: str
    destination_countries: Optional[List[str]] = None
    months_lookback: int
    min_total_value_usd: float
    max_risk_level: str


class BuyerHunterTopResponse(BaseModel):
    """Response for top buyers endpoint."""
    items: List[BuyerHunterResultSchema]
    count: int
    hs_code_6: str
    destination_countries: Optional[List[str]] = None
    months_lookback: int
    max_risk_level: str


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def result_to_schema(result: BuyerHunterResult) -> BuyerHunterResultSchema:
    """Convert BuyerHunterResult dataclass to Pydantic schema."""
    return BuyerHunterResultSchema(
        buyer_uuid=result.buyer_uuid,
        buyer_name=result.buyer_name,
        buyer_country=result.buyer_country,
        destination_country=result.destination_country,
        total_value_usd_12m=result.total_value_usd_12m,
        total_shipments_12m=result.total_shipments_12m,
        avg_shipment_value_usd=result.avg_shipment_value_usd,
        hs_share_pct=result.hs_share_pct,
        months_with_shipments_12m=result.months_with_shipments_12m,
        years_active=result.years_active,
        classification=result.classification,
        website_present=result.website_present,
        website_url=result.website_url,
        current_risk_level=result.current_risk_level,
        risk_score=result.risk_score,
        opportunity_score=result.opportunity_score,
        volume_score=result.volume_score,
        stability_score=result.stability_score,
        hs_focus_score=result.hs_focus_score,
        risk_score_component=result.risk_score_component,
        data_quality_score=result.data_quality_score
    )


def parse_countries(countries_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated country string into list."""
    if not countries_str:
        return None
    countries = [c.strip().upper() for c in countries_str.split(',') if c.strip()]
    return countries if countries else None


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.get("/search", response_model=BuyerHunterSearchResponse)
def search_buyers(
    hs_code_6: str = Query(..., min_length=6, max_length=6, description="6-digit HS code"),
    destination_countries: Optional[str] = Query(
        None, 
        description="Comma-separated destination countries (e.g., 'KENYA,INDIA')"
    ),
    months_lookback: int = Query(12, ge=1, le=60, description="Months to look back"),
    min_total_value_usd: float = Query(50000, ge=0, description="Minimum total value USD"),
    max_risk_level: str = Query(
        "MEDIUM", 
        description="Maximum risk level to include (LOW/MEDIUM/HIGH/CRITICAL/ALL)"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Search for target buyers for a given HS code.
    
    Returns buyers ranked by opportunity score, which is computed based on:
    - Volume (40%): Total trade value in the period
    - Stability (20%): Active months and years
    - HS Focus (15%): Share of this HS code in buyer's total trade
    - Risk (15%): Current risk level
    - Data Quality (10%): Completeness of buyer data
    
    All scoring is deterministic - no LLM involvement.
    """
    # Validate HS code format
    if not hs_code_6.isdigit():
        raise HTTPException(status_code=400, detail="HS code must contain only digits")
    
    # Validate risk level
    valid_risk_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'ALL'}
    if max_risk_level.upper() not in valid_risk_levels:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid max_risk_level. Must be one of: {valid_risk_levels}"
        )
    
    # Parse destination countries
    countries = parse_countries(destination_countries)
    
    try:
        results, total = search_target_buyers(
            db=db,
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            min_total_value_usd=min_total_value_usd,
            max_risk_level=max_risk_level.upper(),
            limit=limit,
            offset=offset
        )
        
        return BuyerHunterSearchResponse(
            items=[result_to_schema(r) for r in results],
            total=total,
            limit=limit,
            offset=offset,
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            min_total_value_usd=min_total_value_usd,
            max_risk_level=max_risk_level.upper()
        )
        
    except Exception as e:
        logger.error(f"Buyer hunter search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/top", response_model=BuyerHunterTopResponse)
def get_top_buyers(
    hs_code_6: str = Query(..., min_length=6, max_length=6, description="6-digit HS code"),
    destination_countries: Optional[str] = Query(
        None, 
        description="Comma-separated destination countries"
    ),
    months_lookback: int = Query(12, ge=1, le=60, description="Months to look back"),
    min_total_value_usd: float = Query(50000, ge=0, description="Minimum total value USD"),
    max_risk_level: str = Query(
        "MEDIUM", 
        description="Maximum risk level (LOW/MEDIUM/HIGH/CRITICAL/ALL)"
    ),
    limit: int = Query(TOP_DEFAULT_LIMIT, ge=1, le=TOP_MAX_LIMIT, description="Number of top buyers"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get top N buyers by opportunity score for a given HS code.
    
    This is a convenience endpoint that always returns buyers sorted by 
    opportunity_score descending. Use this for "Top 20 buyers" queries.
    
    Maximum limit is 50 for this endpoint.
    """
    # Validate HS code format
    if not hs_code_6.isdigit():
        raise HTTPException(status_code=400, detail="HS code must contain only digits")
    
    # Validate risk level
    valid_risk_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'ALL'}
    if max_risk_level.upper() not in valid_risk_levels:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid max_risk_level. Must be one of: {valid_risk_levels}"
        )
    
    # Parse destination countries
    countries = parse_countries(destination_countries)
    
    try:
        results = get_top_target_buyers(
            db=db,
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            min_total_value_usd=min_total_value_usd,
            max_risk_level=max_risk_level.upper(),
            limit=limit
        )
        
        return BuyerHunterTopResponse(
            items=[result_to_schema(r) for r in results],
            count=len(results),
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            max_risk_level=max_risk_level.upper()
        )
        
    except Exception as e:
        logger.error(f"Top buyers query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/search-by-name", response_model=BuyerHunterSearchResponse)
def search_buyers_by_name(
    buyer_name: str = Query(..., min_length=2, description="Buyer name to search for (partial match)"),
    hs_code_6: str = Query(..., min_length=6, max_length=6, description="6-digit HS code"),
    destination_countries: Optional[str] = Query(
        None, 
        description="Comma-separated destination countries (e.g., 'KENYA,INDIA')"
    ),
    months_lookback: int = Query(12, ge=1, le=60, description="Months to look back"),
    min_total_value_usd: float = Query(10000, ge=0, description="Minimum total value USD (default 10k for name search)"),
    max_risk_level: str = Query(
        "ALL", 
        description="Maximum risk level (default ALL for name search)"
    ),
    limit: int = Query(50, ge=1, le=MAX_LIMIT, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Search for specific buyers by name within an HS code + destination context.
    
    This endpoint allows finding buyers who may not appear in the Top 20 due to
    lower volume, but are still valid targets. Uses partial name matching (ILIKE).
    
    Default min_total_value_usd is 10k (lower than /search) to catch smaller buyers.
    Default max_risk_level is ALL to show all matching buyers regardless of risk.
    """
    # Validate HS code format
    if not hs_code_6.isdigit():
        raise HTTPException(status_code=400, detail="HS code must contain only digits")
    
    # Validate risk level
    valid_risk_levels = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'ALL'}
    if max_risk_level.upper() not in valid_risk_levels:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid max_risk_level. Must be one of: {valid_risk_levels}"
        )
    
    # Parse destination countries
    countries = parse_countries(destination_countries)
    
    try:
        # Use the search function with buyer_name filter
        results, total = search_target_buyers(
            db=db,
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            min_total_value_usd=min_total_value_usd,
            max_risk_level=max_risk_level.upper(),
            limit=limit,
            offset=offset,
            buyer_name_filter=buyer_name  # Pass buyer name filter
        )
        
        return BuyerHunterSearchResponse(
            items=[result_to_schema(r) for r in results],
            total=total,
            limit=limit,
            offset=offset,
            hs_code_6=hs_code_6,
            destination_countries=countries,
            months_lookback=months_lookback,
            min_total_value_usd=min_total_value_usd,
            max_risk_level=max_risk_level.upper()
        )
        
    except Exception as e:
        logger.error(f"Buyer name search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/score-breakdown")
def get_score_breakdown():
    """
    Get documentation of the opportunity scoring algorithm (Refined).
    
    Returns the scoring formula breakdown for transparency.
    """
    return {
        "algorithm": "Opportunity Score (0-100) - Refined",
        "version": "7D-R1",
        "components": {
            "volume": {
                "max_points": 40,
                "description": "Based on percentile rank of total_value_usd_12m in result set",
                "formula": "(percentile_rank / 100) * 40",
                "small_cohort_behavior": "When < 5 buyers, uses proportional scaling (20 + ratio * 20)"
            },
            "stability": {
                "max_points": 20,
                "description": "Based on months active (0-12) and years active (1-4+)",
                "formula": "min(months_active, 12) + min(years_active, 4) * 2"
            },
            "hs_focus": {
                "max_points": 15,
                "description": "Share of target HS code in buyer's GLOBAL trade value (not lane-specific)",
                "formula": "min(hs_share_pct / 50, 1) * 15"
            },
            "risk": {
                "max_points": 15,
                "description": "Points based on current risk level (UNKNOWN is between MEDIUM and HIGH)",
                "values": {
                    "LOW": 15,
                    "MEDIUM": 8,
                    "UNKNOWN": 6,
                    "HIGH": 2,
                    "CRITICAL": 0
                }
            },
            "data_quality": {
                "max_points": 10,
                "description": "Classification present, months active >= 3, years active >= 2",
                "breakdown": {
                    "classification_present": 4,
                    "months_active_3plus": 3,
                    "years_active_2plus": 3
                }
            },
            "classification_bump": {
                "max_points": 3,
                "description": "Small tie-breaker bonus for institutional buyer types",
                "values": {
                    "B4": 3,
                    "B5": 3,
                    "B3": 1,
                    "others": 0
                }
            }
        },
        "volume_metrics": {
            "total_value_usd_12m": "Lane-specific (filtered by HS + destination)",
            "hs_share_pct": "Global (this HS value / buyer's total trade value across all HS & destinations)"
        },
        "risk_filter_behavior": {
            "LOW": "Only verified LOW-risk buyers (UNKNOWN excluded)",
            "MEDIUM": "LOW + MEDIUM + UNKNOWN",
            "HIGH": "LOW + MEDIUM + UNKNOWN + HIGH",
            "ALL": "All risk levels including CRITICAL"
        },
        "notes": [
            "All scoring is deterministic - no LLM involvement",
            "Higher scores indicate better target buyers",
            "Risk filters are applied BEFORE scoring",
            "Volume percentile is calculated within the filtered result set",
            "UNKNOWN risk buyers are NOT treated as LOW for filtering purposes",
            "Tiebreaker: when scores are equal, higher volume wins"
        ]
    }
