"""
EPIC 7B - API Dependencies
===========================
Database dependency injection for FastAPI endpoints.

Uses the existing DatabaseManager from etl.db_utils for connection pooling.
"""

import os
import logging
from typing import Generator
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager

logger = logging.getLogger(__name__)

# Global database manager instance (singleton)
_db_manager: DatabaseManager = None


def get_db_manager() -> DatabaseManager:
    """
    Get or create the global DatabaseManager instance.
    Uses singleton pattern to reuse connection pool across requests.
    """
    global _db_manager
    
    if _db_manager is None:
        config_path = os.environ.get('DB_CONFIG_PATH', 'config/db_config.yml')
        _db_manager = DatabaseManager(config_path)
        logger.info(f"DatabaseManager initialized with config: {config_path}")
    
    return _db_manager


def get_db() -> Generator[DatabaseManager, None, None]:
    """
    FastAPI dependency that yields a DatabaseManager instance.
    
    Usage in endpoints:
        @router.get("/endpoint")
        def endpoint(db: DatabaseManager = Depends(get_db)):
            results = db.execute_query("SELECT ...")
    """
    db = get_db_manager()
    try:
        yield db
    finally:
        # Don't close the pool here - it's reused across requests
        pass


def check_db_health(db: DatabaseManager) -> bool:
    """
    Check database connectivity with a simple query.
    Returns True if healthy, False otherwise.
    """
    try:
        result = db.execute_query("SELECT 1")
        return result is not None and len(result) > 0
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def shutdown_db():
    """
    Cleanup function to close database connections on app shutdown.
    """
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None
        logger.info("DatabaseManager closed")
