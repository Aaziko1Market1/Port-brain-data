"""
EPIC 7B - Pydantic Response Schemas
====================================
Type-safe response models for the Control Tower API.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum


# =====================================================================
# ENUMS
# =====================================================================

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNSCORED = "UNSCORED"


class Direction(str, Enum):
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"


# =====================================================================
# HEALTH & META SCHEMAS
# =====================================================================

class PipelineRunInfo(BaseModel):
    """Last run info for a pipeline."""
    pipeline_name: str
    last_run_at: Optional[datetime] = None
    status: Optional[str] = None
    rows_processed: Optional[int] = None


class HealthStatus(BaseModel):
    """Health check response."""
    status: str = Field(description="Overall API status")
    db: str = Field(description="Database connection status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GlobalStats(BaseModel):
    """Global platform statistics."""
    total_shipments: int
    total_buyers: int
    total_suppliers: int
    total_countries: int
    total_hs_codes: int
    ledger_date_range: Optional[Dict[str, str]] = None
    last_pipeline_runs: List[PipelineRunInfo] = []


# =====================================================================
# BUYER SCHEMAS
# =====================================================================

class HsCodeSummary(BaseModel):
    """HS code summary within a buyer's portfolio."""
    hs_code_6: str
    value_usd: Optional[float] = None
    share_pct: Optional[float] = None


class CountrySummary(BaseModel):
    """Country summary for buyer origins/destinations."""
    country: str
    value_usd: Optional[float] = None
    share_pct: Optional[float] = None


class BuyerSummary(BaseModel):
    """Summary view of a buyer for list endpoints."""
    buyer_uuid: str
    buyer_name: str
    buyer_country: Optional[str] = None
    buyer_classification: Optional[str] = None
    total_shipments: int = 0
    total_value_usd: Optional[float] = None
    current_risk_level: str = "UNSCORED"
    current_risk_score: Optional[float] = None
    has_ghost_flag: bool = False
    first_shipment_date: Optional[date] = None
    last_shipment_date: Optional[date] = None


class Buyer360(BaseModel):
    """Full 360-degree view of a buyer."""
    # Identity
    buyer_uuid: str
    buyer_name: str
    buyer_country: Optional[str] = None
    buyer_classification: Optional[str] = None
    
    # Volume metrics
    total_shipments: int = 0
    total_value_usd: Optional[float] = None
    total_qty_kg: Optional[float] = None
    total_teu: Optional[float] = None
    
    # Activity
    first_shipment_date: Optional[date] = None
    last_shipment_date: Optional[date] = None
    active_years: int = 0
    
    # Diversity
    unique_hs_codes: int = 0
    unique_origin_countries: int = 0
    unique_suppliers: int = 0
    
    # Product mix
    top_hs_codes: List[HsCodeSummary] = []
    top_origin_countries: List[CountrySummary] = []
    
    # Risk
    current_risk_level: str = "UNSCORED"
    current_risk_score: Optional[float] = None
    current_confidence_score: Optional[float] = None
    current_main_reason_code: Optional[str] = None
    has_ghost_flag: bool = False
    risk_engine_version: Optional[str] = None
    
    # Metadata
    last_profile_updated_at: Optional[datetime] = None
    last_risk_scored_at: Optional[datetime] = None


class BuyerListResponse(BaseModel):
    """Paginated list of buyers."""
    items: List[BuyerSummary]
    total: int
    limit: int
    offset: int


class TradeMonth(BaseModel):
    """Monthly trade data for a buyer."""
    year: int
    month: int
    total_value_usd: float = 0.0
    total_volume_kg: Optional[float] = None
    shipment_count: int = 0
    top_origin_country: Optional[str] = None
    top_supplier: Optional[str] = None


class BuyerTradeHistoryResponse(BaseModel):
    """Buyer monthly trade history response."""
    buyer_uuid: str
    buyer_name: str
    currency: str = "USD"
    total_months: int = 0
    months: List[TradeMonth] = []


# =====================================================================
# HS DASHBOARD SCHEMAS
# =====================================================================

class HsDashboardRecord(BaseModel):
    """HS code dashboard record for a country/direction/period."""
    hs_code_6: str
    reporting_country: str
    direction: str
    year: int
    month: int
    
    # Volume metrics
    shipment_count: int = 0
    unique_buyers: int = 0
    unique_suppliers: int = 0
    total_value_usd: Optional[float] = None
    total_qty_kg: Optional[float] = None
    avg_price_usd_per_kg: Optional[float] = None
    avg_value_per_shipment_usd: Optional[float] = None
    
    # Market share
    value_share_pct: Optional[float] = None
    
    # Risk
    high_risk_shipments: int = 0
    high_risk_buyers: int = 0
    high_risk_shipment_pct: Optional[float] = None


class MonthlyTrend(BaseModel):
    """Monthly trend data point."""
    year: int
    month: int
    shipment_count: int = 0
    total_value_usd: Optional[float] = None
    avg_price_usd_per_kg: Optional[float] = None


class HsDashboardResponse(BaseModel):
    """HS dashboard response with aggregates and trends."""
    hs_code_6: str
    reporting_country: Optional[str] = None
    direction: Optional[str] = None
    
    # Aggregated totals
    total_shipments: int = 0
    total_value_usd: Optional[float] = None
    total_qty_kg: Optional[float] = None
    avg_price_usd_per_kg: Optional[float] = None
    unique_buyers: int = 0
    unique_suppliers: int = 0
    
    # Risk summary
    high_risk_shipments: int = 0
    high_risk_pct: Optional[float] = None
    
    # Monthly breakdown
    monthly_data: List[HsDashboardRecord] = []
    monthly_trend: List[MonthlyTrend] = []


# =====================================================================
# RISK SCHEMAS
# =====================================================================

class RiskShipmentRecord(BaseModel):
    """Risk record for a shipment."""
    entity_id: str  # transaction_id
    risk_score: float
    risk_level: str
    confidence_score: Optional[float] = None
    main_reason_code: str
    scope_key: Optional[str] = None
    
    # Shipment context (from ledger join)
    hs_code_6: Optional[str] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    customs_value_usd: Optional[float] = None
    price_usd_per_kg: Optional[float] = None
    shipment_date: Optional[date] = None
    
    # Reason details
    reasons: Optional[Dict[str, Any]] = None
    computed_at: Optional[datetime] = None


class RiskBuyerRecord(BaseModel):
    """Risk record for a buyer."""
    entity_id: str  # buyer_uuid
    buyer_name: Optional[str] = None
    buyer_country: Optional[str] = None
    
    risk_score: float
    risk_level: str
    confidence_score: Optional[float] = None
    main_reason_code: str
    scope_key: Optional[str] = None
    
    # Volume context
    total_value_usd: Optional[float] = None
    total_shipments: Optional[int] = None
    
    # Reason details
    reasons: Optional[Dict[str, Any]] = None
    computed_at: Optional[datetime] = None


class RiskShipmentListResponse(BaseModel):
    """Paginated list of risky shipments."""
    items: List[RiskShipmentRecord]
    total: int
    limit: int
    offset: int


class RiskBuyerListResponse(BaseModel):
    """Paginated list of risky buyers."""
    items: List[RiskBuyerRecord]
    total: int
    limit: int
    offset: int


# =====================================================================
# ERROR SCHEMAS
# =====================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int
