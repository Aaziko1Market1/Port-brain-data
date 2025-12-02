"""
EPIC 7B - Health & Meta Router
===============================
Health check and platform statistics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Optional

from api.deps import get_db, check_db_health
from api.schemas import HealthStatus, GlobalStats, PipelineRunInfo
from api import __version__
from etl.db_utils import DatabaseManager

router = APIRouter(prefix="/api/v1", tags=["Health & Meta"])


@router.get("/health", response_model=HealthStatus)
def health_check(db: DatabaseManager = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns API status and database connectivity.
    """
    db_healthy = check_db_health(db)
    
    return HealthStatus(
        status="ok" if db_healthy else "degraded",
        db="ok" if db_healthy else "error",
        version=__version__,
        timestamp=datetime.utcnow()
    )


@router.get("/meta/stats", response_model=GlobalStats)
def get_global_stats(db: DatabaseManager = Depends(get_db)):
    """
    Get global platform statistics.
    
    Returns:
    - Total shipments, buyers, suppliers, countries
    - Last pipeline run status for each pipeline
    """
    try:
        # Total shipments
        result = db.execute_query("SELECT COUNT(*) FROM global_trades_ledger")
        total_shipments = result[0][0] if result else 0
        
        # Total buyers (from organizations_master with BUYER type)
        result = db.execute_query("""
            SELECT COUNT(DISTINCT org_uuid) 
            FROM organizations_master 
            WHERE type IN ('BUYER', 'MIXED')
        """)
        total_buyers = result[0][0] if result else 0
        
        # Total suppliers
        result = db.execute_query("""
            SELECT COUNT(DISTINCT org_uuid) 
            FROM organizations_master 
            WHERE type IN ('SUPPLIER', 'MIXED')
        """)
        total_suppliers = result[0][0] if result else 0
        
        # Total distinct countries in ledger
        result = db.execute_query("""
            SELECT COUNT(DISTINCT reporting_country) FROM global_trades_ledger
        """)
        total_countries = result[0][0] if result else 0
        
        # Total distinct HS codes
        result = db.execute_query("""
            SELECT COUNT(DISTINCT hs_code_6) FROM global_trades_ledger 
            WHERE hs_code_6 IS NOT NULL
        """)
        total_hs_codes = result[0][0] if result else 0
        
        # Date range
        result = db.execute_query("""
            SELECT MIN(shipment_date), MAX(shipment_date) FROM global_trades_ledger
        """)
        date_range = None
        if result and result[0][0]:
            date_range = {
                "min": str(result[0][0]),
                "max": str(result[0][1])
            }
        
        # Last pipeline runs
        result = db.execute_query("""
            SELECT DISTINCT ON (pipeline_name)
                pipeline_name,
                started_at,
                status,
                rows_processed
            FROM pipeline_runs
            ORDER BY pipeline_name, started_at DESC
        """)
        
        pipeline_runs = []
        for row in (result or []):
            pipeline_runs.append(PipelineRunInfo(
                pipeline_name=row[0],
                last_run_at=row[1],
                status=row[2],
                rows_processed=row[3]
            ))
        
        return GlobalStats(
            total_shipments=total_shipments,
            total_buyers=total_buyers,
            total_suppliers=total_suppliers,
            total_countries=total_countries,
            total_hs_codes=total_hs_codes,
            ledger_date_range=date_range,
            last_pipeline_runs=pipeline_runs
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
