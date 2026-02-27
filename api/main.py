"""
EPIC 7B - GTI-OS Control Tower API
====================================
Read-only HTTP API for Buyer 360, HS Dashboard, and Risk insights.

This API provides:
- Health check and platform statistics
- Buyer intelligence (list, 360 view)
- HS code dashboard analytics
- Risk insights (shipments, buyers)

All endpoints are READ-ONLY and use parameterized SQL queries.

Usage:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Or via the entrypoint script:
    python scripts/run_api.py
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import __version__
from api.deps import shutdown_db
from api.routers import (
    health_router,
    buyers_router,
    hs_dashboard_router,
    risk_router,
    ai_router,
    buyer_hunter_router,
    admin_upload_router,
    dashboard_router,
    products_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    """
    # Startup
    logger.info("GTI-OS Control Tower API starting up...")
    yield
    # Shutdown
    logger.info("GTI-OS Control Tower API shutting down...")
    shutdown_db()


# Create FastAPI app
app = FastAPI(
    title="Aaziko GTI-OS Control Tower API",
    description="""
## GTI-OS Global Trade Intelligence Platform - Control Tower API

A read-only API layer providing access to:

- **Buyer 360**: Complete buyer intelligence with volumes, risk, and product mix
- **HS Dashboard**: Country/HS code analytics from materialized views
- **Risk Insights**: Top risky shipments and buyers from the risk engine

### Data Sources

All data comes from pre-computed serving views (EPIC 7A):
- `vw_buyer_360` - Buyer intelligence
- `vw_country_hs_dashboard` - HS code dashboards
- `risk_scores` - Risk assessments

### Key Features

- ✅ Read-only (no inserts/updates/deletes)
- ✅ Parameterized SQL (SQL injection safe)
- ✅ Pagination support
- ✅ Optimized for large datasets (100M+ rows)
- ✅ AI Co-Pilot for intelligent explanations (EPIC 7C)
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware (configure origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Read-only API + AI endpoints
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "status_code": 500
        }
    )


# Include routers
app.include_router(health_router)
app.include_router(buyers_router)
app.include_router(hs_dashboard_router)
app.include_router(risk_router)
app.include_router(ai_router)
app.include_router(buyer_hunter_router)
app.include_router(admin_upload_router)
app.include_router(dashboard_router)
app.include_router(products_router)


# Root endpoint
@app.get("/", tags=["Root"])
def root():
    """
    API root - returns welcome message and links.
    """
    return {
        "message": "Welcome to GTI-OS Control Tower API",
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": "/api/v1/health",
            "stats": "/api/v1/meta/stats",
            "buyers": "/api/v1/buyers",
            "hs_dashboard": "/api/v1/hs-dashboard",
            "risk_shipments": "/api/v1/risk/top-shipments",
            "risk_buyers": "/api/v1/risk/top-buyers",
            "ai_status": "/api/v1/ai/status",
            "ai_explain_buyer": "/api/v1/ai/explain-buyer/{buyer_uuid}"
        }
    }


@app.get("/api/v1", tags=["Root"])
def api_v1_root():
    """
    API v1 root - returns available endpoints.
    """
    return {
        "api_version": "v1",
        "endpoints": [
            {"path": "/api/v1/health", "method": "GET", "description": "Health check"},
            {"path": "/api/v1/meta/stats", "method": "GET", "description": "Global statistics"},
            {"path": "/api/v1/buyers", "method": "GET", "description": "List buyers with filters"},
            {"path": "/api/v1/buyers/{buyer_uuid}/360", "method": "GET", "description": "Buyer 360 view"},
            {"path": "/api/v1/hs-dashboard", "method": "GET", "description": "HS code dashboard"},
            {"path": "/api/v1/hs-dashboard/top-hs-codes", "method": "GET", "description": "Top HS codes"},
            {"path": "/api/v1/risk/top-shipments", "method": "GET", "description": "Top risky shipments"},
            {"path": "/api/v1/risk/top-buyers", "method": "GET", "description": "Top risky buyers"},
            {"path": "/api/v1/risk/summary", "method": "GET", "description": "Risk summary stats"},
            {"path": "/api/v1/ai/status", "method": "GET", "description": "AI Co-Pilot status"},
            {"path": "/api/v1/ai/explain-buyer/{uuid}", "method": "POST", "description": "AI buyer explanation"},
            {"path": "/api/v1/ai/ask-buyer/{uuid}", "method": "POST", "description": "Ask AI about buyer"}
        ]
    }
