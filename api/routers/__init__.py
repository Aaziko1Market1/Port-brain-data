"""
API Routers Package
"""
from .health import router as health_router
from .buyers import router as buyers_router
from .hs_dashboard import router as hs_dashboard_router
from .risk import router as risk_router
from .ai import router as ai_router
from .buyer_hunter import router as buyer_hunter_router
from .admin_upload import router as admin_upload_router
from .dashboard import router as dashboard_router

__all__ = [
    'health_router',
    'buyers_router', 
    'hs_dashboard_router',
    'risk_router',
    'ai_router',
    'buyer_hunter_router',
    'admin_upload_router',
    'dashboard_router'
]
