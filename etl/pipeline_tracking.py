"""
Pipeline Tracking Module
========================
Provides utilities for tracking pipeline runs in the Control Tower.

Part of GTI-OS Data Platform Architecture Hardening for Scale.

Features:
- Context manager for automatic run tracking
- Metrics update helpers
- Status management (RUNNING, SUCCESS, FAILED, PARTIAL)

Usage:
    from etl.pipeline_tracking import track_pipeline_run, update_run_metrics
    
    with track_pipeline_run(db_manager, "standardization", countries=["INDIA"]) as run_id:
        result = do_work()
        update_run_metrics(db_manager, run_id, rows_processed=result.count)
"""

import logging
import uuid
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Generator
from datetime import datetime

logger = logging.getLogger(__name__)


@contextmanager
def track_pipeline_run(
    db_manager,
    pipeline_name: str,
    countries: Optional[List[str]] = None,
    directions: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Generator[str, None, None]:
    """
    Context manager for tracking a pipeline run.
    
    Automatically creates a run record on entry and updates status on exit.
    On success: status = 'SUCCESS'
    On exception: status = 'FAILED' with error_message
    
    Args:
        db_manager: DatabaseManager instance
        pipeline_name: One of 'ingestion', 'standardization', 'identity', 'ledger'
        countries: List of countries being processed (optional filter)
        directions: List of directions being processed (optional filter)
        metadata: Additional JSON metadata to store
        
    Yields:
        run_id: UUID string of the created run record
        
    Example:
        with track_pipeline_run(db, "standardization", countries=["INDIA"]) as run_id:
            process_data()
            update_run_metrics(db, run_id, rows_processed=1000)
    """
    run_id = str(uuid.uuid4())
    countries_arr = countries or []
    countries_str = ",".join(countries_arr) if countries_arr else None
    directions_arr = directions or []
    
    # Convert metadata to JSON-safe format
    import json
    metadata_json = json.dumps(metadata) if metadata else None
    
    # Insert initial run record
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pipeline_runs (
                        run_id, pipeline_name, countries_filter, 
                        countries_filter_str, directions_filter, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (run_id, pipeline_name, countries_arr, countries_str, 
                     directions_arr, metadata_json)
                )
        logger.info(f"Pipeline run started: {pipeline_name} (run_id={run_id[:8]}...)")
    except Exception as e:
        logger.error(f"Failed to create pipeline run record: {e}")
        raise
    
    try:
        yield run_id
        
        # Success - update status
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE pipeline_runs
                    SET completed_at = NOW(), status = 'SUCCESS'
                    WHERE run_id = %s
                    """,
                    (run_id,)
                )
        logger.info(f"Pipeline run completed: {pipeline_name} (run_id={run_id[:8]}...) - SUCCESS")
        
    except Exception as e:
        # Failure - update status with error
        error_msg = str(e)[:1000]  # Truncate long errors
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE pipeline_runs
                        SET completed_at = NOW(),
                            status = 'FAILED',
                            error_message = %s
                        WHERE run_id = %s
                        """,
                        (error_msg, run_id)
                    )
            logger.error(f"Pipeline run failed: {pipeline_name} (run_id={run_id[:8]}...) - {error_msg}")
        except Exception as db_error:
            logger.error(f"Failed to update pipeline run status: {db_error}")
        raise


def update_run_metrics(
    db_manager,
    run_id: str,
    rows_processed: Optional[int] = None,
    rows_created: Optional[int] = None,
    rows_updated: Optional[int] = None,
    rows_skipped: Optional[int] = None,
    files_processed: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None
) -> None:
    """
    Update metrics for a pipeline run.
    
    Only non-None values are updated. This allows incremental updates
    during batch processing.
    
    Args:
        db_manager: DatabaseManager instance
        run_id: UUID string of the run to update
        rows_processed: Total rows processed
        rows_created: New rows created
        rows_updated: Existing rows updated
        rows_skipped: Rows skipped (duplicates, etc.)
        files_processed: Number of files processed
        metadata: Additional JSON metadata (merged with existing)
        status: Override status ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL')
    """
    updates = []
    values = []
    
    if rows_processed is not None:
        updates.append("rows_processed = %s")
        values.append(rows_processed)
    
    if rows_created is not None:
        updates.append("rows_created = %s")
        values.append(rows_created)
    
    if rows_updated is not None:
        updates.append("rows_updated = %s")
        values.append(rows_updated)
    
    if rows_skipped is not None:
        updates.append("rows_skipped = %s")
        values.append(rows_skipped)
    
    if files_processed is not None:
        updates.append("files_processed = %s")
        values.append(files_processed)
    
    if status is not None:
        updates.append("status = %s")
        values.append(status)
    
    if metadata is not None:
        import json
        # Merge with existing metadata using JSONB concatenation
        updates.append("metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb")
        values.append(json.dumps(metadata))
    
    if not updates:
        return  # Nothing to update
    
    values.append(run_id)
    set_clause = ", ".join(updates)
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE pipeline_runs SET {set_clause} WHERE run_id = %s",
                    tuple(values)
                )
    except Exception as e:
        logger.warning(f"Failed to update run metrics: {e}")


def mark_run_partial(
    db_manager,
    run_id: str,
    error_message: Optional[str] = None
) -> None:
    """
    Mark a pipeline run as PARTIAL (some success, some failures).
    
    Use this when a batch run has partial success that shouldn't
    be marked as complete failure.
    
    Args:
        db_manager: DatabaseManager instance
        run_id: UUID string of the run
        error_message: Optional description of partial failures
    """
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE pipeline_runs
                    SET status = 'PARTIAL',
                        error_message = COALESCE(error_message, '') || %s
                    WHERE run_id = %s
                    """,
                    (error_message or '', run_id)
                )
        logger.warning(f"Pipeline run marked as PARTIAL: {run_id[:8]}...")
    except Exception as e:
        logger.error(f"Failed to mark run as partial: {e}")


def get_latest_run(
    db_manager,
    pipeline_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get the most recent run for a given pipeline.
    
    Useful for checking when a pipeline was last run successfully.
    
    Args:
        db_manager: DatabaseManager instance
        pipeline_name: Name of the pipeline
        
    Returns:
        Dictionary with run details or None if no runs found
    """
    try:
        result = db_manager.execute_query(
            """
            SELECT run_id, started_at, completed_at, status, 
                   rows_processed, rows_created, rows_updated, rows_skipped,
                   files_processed, error_message
            FROM pipeline_runs
            WHERE pipeline_name = %s
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (pipeline_name,)
        )
        
        if result:
            row = result[0]
            return {
                'run_id': str(row[0]),
                'started_at': row[1],
                'completed_at': row[2],
                'status': row[3],
                'rows_processed': row[4],
                'rows_created': row[5],
                'rows_updated': row[6],
                'rows_skipped': row[7],
                'files_processed': row[8],
                'error_message': row[9]
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get latest run: {e}")
        return None


def get_running_pipelines(db_manager) -> List[Dict[str, Any]]:
    """
    Get all currently running pipelines.
    
    Useful for detecting stuck runs or concurrent execution.
    
    Args:
        db_manager: DatabaseManager instance
        
    Returns:
        List of running pipeline dictionaries
    """
    try:
        results = db_manager.execute_query(
            """
            SELECT run_id, pipeline_name, started_at, countries_filter_str
            FROM pipeline_runs
            WHERE status = 'RUNNING'
            ORDER BY started_at
            """
        )
        
        return [
            {
                'run_id': str(row[0]),
                'pipeline_name': row[1],
                'started_at': row[2],
                'countries': row[3]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Failed to get running pipelines: {e}")
        return []
