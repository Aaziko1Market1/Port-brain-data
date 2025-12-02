"""
EPIC 9 - Admin Upload API Router
=================================
Endpoints for uploading port data files and managing uploads.

POST /api/v1/admin/upload-port-file - Upload a new port data file
GET /api/v1/admin/files - List recent uploaded files
GET /api/v1/admin/files/{file_id} - Get file details
"""

import hashlib
import logging
import os
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from api.deps import get_db
from etl.db_utils import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

# ============================================================================
# ENUMS
# ============================================================================

class Direction(str, Enum):
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"


class SourceFormat(str, Enum):
    FULL = "FULL"
    SHORT = "SHORT"
    OTHER = "OTHER"


class DataGrain(str, Enum):
    SHIPMENT_LINE = "SHIPMENT_LINE"
    CONTAINER = "CONTAINER"
    INVOICE = "INVOICE"
    UNKNOWN = "UNKNOWN"


class DataQualityLevel(str, Enum):
    RAW = "RAW"
    CLEANED_BASIC = "CLEANED_BASIC"
    CLEANED_AAZIKO = "CLEANED_AAZIKO"
    UNKNOWN = "UNKNOWN"


class ProcessingMode(str, Enum):
    INGEST_ONLY = "INGEST_ONLY"
    INGEST_AND_STANDARDIZE = "INGEST_AND_STANDARDIZE"
    FULL_PIPELINE = "FULL_PIPELINE"


class MappingStatus(str, Enum):
    DRAFT = "DRAFT"
    VERIFIED = "VERIFIED"
    LIVE = "LIVE"
    NOT_FOUND = "NOT_FOUND"


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class MappingStatusResponse(BaseModel):
    """Response for mapping status lookup."""
    reporting_country: str
    direction: str
    source_format: str
    status: MappingStatus
    config_key: Optional[str] = None
    yaml_path: Optional[str] = None
    last_verified_at: Optional[str] = None
    allowed_modes: List[str] = []
    message: str


class ValidationResult(BaseModel):
    config_used: Optional[str] = None
    required_columns_found: List[str] = []
    required_columns_missing: List[str] = []
    status: str  # OK, ERROR


class PipelineResult(BaseModel):
    processing_mode: str
    run_now: bool
    pipeline_run_id: Optional[str] = None
    status: str  # QUEUED, COMPLETED, SKIPPED


class UploadResponse(BaseModel):
    file_id: int
    file_name: str
    file_path: str
    file_size_bytes: int
    reporting_country: str
    direction: str
    source_format: str
    min_shipment_date: Optional[str] = None  # Populated after standardization
    max_shipment_date: Optional[str] = None  # Populated after standardization
    validation: ValidationResult
    pipeline: PipelineResult
    created_at: str


class FileEntry(BaseModel):
    file_id: int
    file_name: str
    file_path: str
    file_size_bytes: Optional[int]
    reporting_country: Optional[str]
    direction: Optional[str]
    source_format: Optional[str]
    min_shipment_date: Optional[str] = None  # From actual data
    max_shipment_date: Optional[str] = None  # From actual data
    status: str
    created_at: str
    ingestion_completed_at: Optional[str]
    standardization_completed_at: Optional[str]
    identity_completed_at: Optional[str]
    ledger_completed_at: Optional[str]
    processing_mode: Optional[str]
    config_file_used: Optional[str]
    is_production: Optional[bool]
    tags: Optional[str]
    notes: Optional[str]


class FileListResponse(BaseModel):
    items: List[FileEntry]
    total: int
    limit: int
    offset: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_file_checksum(file_content: bytes) -> str:
    """Compute SHA256 checksum of file content."""
    return hashlib.sha256(file_content).hexdigest()


def get_mapping_status_from_registry(
    db: DatabaseManager,
    reporting_country: str,
    direction: str,
    source_format: str
) -> MappingStatusResponse:
    """
    Get mapping status from mapping_registry.
    
    Returns status with allowed processing modes:
    - DRAFT: Only INGEST_ONLY allowed
    - VERIFIED: INGEST_ONLY + INGEST_AND_STANDARDIZE allowed
    - LIVE: All modes allowed including FULL_PIPELINE
    - NOT_FOUND: No mapping exists, only INGEST_ONLY allowed
    """
    query = """
        SELECT mapping_id, config_key, yaml_path, status, last_verified_at
        FROM mapping_registry
        WHERE UPPER(reporting_country) = UPPER(%s)
        AND UPPER(direction) = UPPER(%s)
        AND UPPER(source_format) = UPPER(%s)
    """
    
    rows = db.execute_query(query, (reporting_country, direction, source_format))
    
    if not rows:
        return MappingStatusResponse(
            reporting_country=reporting_country.upper(),
            direction=direction.upper(),
            source_format=source_format.upper(),
            status=MappingStatus.NOT_FOUND,
            config_key=None,
            yaml_path=None,
            last_verified_at=None,
            allowed_modes=["INGEST_ONLY"],
            message="No mapping found in registry. Only INGEST_ONLY is allowed."
        )
    
    row = rows[0]
    mapping_id, config_key, yaml_path, status, last_verified_at = row
    
    # Determine allowed modes based on status
    if status == 'LIVE':
        allowed_modes = ["INGEST_ONLY", "INGEST_AND_STANDARDIZE", "FULL_PIPELINE"]
        message = "Ready – Full pipeline available"
    elif status == 'VERIFIED':
        allowed_modes = ["INGEST_ONLY", "INGEST_AND_STANDARDIZE"]
        message = "Verified in sandbox – ask dev to mark LIVE for full pipeline"
    else:  # DRAFT
        allowed_modes = ["INGEST_ONLY"]
        message = "Draft mapping – only INGEST_ONLY is allowed"
    
    return MappingStatusResponse(
        reporting_country=reporting_country.upper(),
        direction=direction.upper(),
        source_format=source_format.upper(),
        status=MappingStatus(status),
        config_key=config_key,
        yaml_path=yaml_path,
        last_verified_at=str(last_verified_at) if last_verified_at else None,
        allowed_modes=allowed_modes,
        message=message
    )


def find_mapping_config(
    reporting_country: str,
    direction: str,
    source_format: str
) -> Optional[Path]:
    """
    Find the appropriate YAML mapping config for the given trade context.
    
    Tries patterns like:
    - config/kenya_import_full.yml
    - config/kenya_import.yml
    - config/india_export.yml
    """
    config_dir = Path("config")
    country_lower = reporting_country.lower()
    direction_lower = direction.lower()
    format_lower = source_format.lower()
    
    # Try specific patterns first
    patterns = [
        f"{country_lower}_{direction_lower}_{format_lower}.yml",
        f"{country_lower}_{direction_lower}.yml",
        f"{country_lower}.yml",
    ]
    
    for pattern in patterns:
        config_path = config_dir / pattern
        if config_path.exists():
            return config_path
    
    return None


def get_required_columns_from_config(config_path: Path) -> List[str]:
    """
    Extract required column names from a mapping config YAML.
    Returns the mapped column names (Excel header names).
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        column_mapping = config.get('column_mapping', {})
        quality_rules = config.get('quality_rules', {})
        
        # These are the columns that are typically required
        required_keys = []
        if quality_rules.get('require_hs_code', False):
            required_keys.append('hs_code_raw')
        if quality_rules.get('require_importer', False):
            required_keys.append('buyer_name_raw')
        if quality_rules.get('require_value_usd', False):
            required_keys.append('value_raw')
        if quality_rules.get('require_origin_country', False):
            required_keys.append('origin_country_raw')
        if quality_rules.get('require_quantity', False):
            required_keys.append('qty_raw')
        
        # Get the actual Excel column names for required keys
        required_columns = []
        for key in required_keys:
            if key in column_mapping:
                required_columns.append(column_mapping[key])
        
        return required_columns
    except Exception as e:
        logger.error(f"Error reading config {config_path}: {e}")
        return []


def get_header_row_from_file(
    file_path: Path,
    header_row_index: int = 1,
    sheet_name: Optional[str] = None
) -> List[str]:
    """
    Read the header row from an Excel or CSV file.
    Returns list of column names.
    """
    import pandas as pd
    
    suffix = file_path.suffix.lower()
    
    try:
        if suffix == '.csv':
            # For CSV, header_row_index is 0-indexed
            df = pd.read_csv(file_path, header=header_row_index - 1, nrows=0)
        else:
            # For Excel, header_row_index is 0-indexed in pandas
            df = pd.read_excel(
                file_path,
                header=header_row_index - 1,
                sheet_name=sheet_name or 0,
                nrows=0
            )
        
        return [str(col).strip() for col in df.columns.tolist()]
    except Exception as e:
        logger.error(f"Error reading headers from {file_path}: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Could not read file headers: {str(e)}"
        )


def validate_file_columns(
    file_path: Path,
    config_path: Path,
    header_row_index: int = 1,
    sheet_name: Optional[str] = None
) -> ValidationResult:
    """
    Validate that the file contains all required columns from the config.
    """
    required_columns = get_required_columns_from_config(config_path)
    actual_columns = get_header_row_from_file(file_path, header_row_index, sheet_name)
    
    # Normalize column names for comparison
    actual_columns_normalized = {col.upper().strip() for col in actual_columns}
    
    found = []
    missing = []
    
    for req_col in required_columns:
        if req_col.upper().strip() in actual_columns_normalized:
            found.append(req_col)
        else:
            missing.append(req_col)
    
    return ValidationResult(
        config_used=str(config_path),
        required_columns_found=found,
        required_columns_missing=missing,
        status="OK" if len(missing) == 0 else "ERROR"
    )


def create_pipeline_run(
    db: DatabaseManager,
    pipeline_name: str,
    countries: List[str],
    directions: List[str]
) -> str:
    """Create a pipeline_runs entry and return the run_id."""
    run_id = str(uuid.uuid4())
    
    query = """
        INSERT INTO pipeline_runs (
            run_id, pipeline_name, started_at, status,
            countries_filter, countries_filter_str, directions_filter
        ) VALUES (
            %s, %s, NOW(), 'RUNNING',
            %s, %s, %s
        )
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, (
                run_id,
                pipeline_name,
                countries,
                ','.join(countries),
                directions
            ))
        finally:
            cursor.close()
    
    return run_id


def update_pipeline_run(
    db: DatabaseManager,
    run_id: str,
    status: str,
    rows_processed: int = 0,
    error_message: Optional[str] = None
):
    """Update a pipeline_runs entry."""
    query = """
        UPDATE pipeline_runs SET
            completed_at = NOW(),
            status = %s,
            rows_processed = %s,
            error_message = %s
        WHERE run_id = %s
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, (status, rows_processed, error_message, run_id))
        finally:
            cursor.close()


def spawn_pipeline_async(
    processing_mode: ProcessingMode,
    reporting_country: str,
    direction: str,
    run_id: str
):
    """
    Spawn pipeline scripts as background processes.
    Does not block the HTTP request.
    """
    scripts_dir = Path("scripts")
    
    # Determine which scripts to run based on processing_mode
    if processing_mode == ProcessingMode.INGEST_ONLY:
        # Ingestion is already done by saving the file
        return
    
    scripts = []
    if processing_mode in [ProcessingMode.INGEST_AND_STANDARDIZE, ProcessingMode.FULL_PIPELINE]:
        scripts.append("run_standardization.py")
    
    if processing_mode == ProcessingMode.FULL_PIPELINE:
        scripts.extend([
            "run_identity_engine.py",
            "run_ledger_loader.py",
            "run_build_profiles.py",
            "run_build_price_and_lanes.py",
            "run_build_risk_scores.py",
            "run_serving_refresh.py"
        ])
    
    # Build the command to run scripts sequentially
    if scripts:
        # Create a simple wrapper script content
        commands = []
        for script in scripts:
            script_path = scripts_dir / script
            if script_path.exists():
                cmd = f'python {script_path} --countries {reporting_country}'
                if direction:
                    cmd += f' --directions {direction}'
                commands.append(cmd)
        
        if commands:
            # Run in background using subprocess
            full_command = ' && '.join(commands)
            try:
                # Use start /B on Windows for background execution
                if os.name == 'nt':
                    subprocess.Popen(
                        f'cmd /c "{full_command}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(
                        full_command,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                logger.info(f"Spawned pipeline for run_id={run_id}")
            except Exception as e:
                logger.error(f"Failed to spawn pipeline: {e}")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/mapping-status", response_model=MappingStatusResponse)
def get_mapping_status(
    reporting_country: str,
    direction: Direction,
    source_format: SourceFormat,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get the mapping status for a country/direction/format combination.
    
    Returns:
    - status: LIVE, VERIFIED, DRAFT, or NOT_FOUND
    - allowed_modes: Which processing modes are allowed
    - message: Human-readable status message
    
    Use this to show status pills in the UI and enforce processing restrictions.
    """
    return get_mapping_status_from_registry(
        db,
        reporting_country,
        direction.value,
        source_format.value
    )


@router.post("/upload-port-file", response_model=UploadResponse)
async def upload_port_file(
    file: UploadFile = File(..., description="Excel or CSV file to upload"),
    reporting_country: str = Form(..., description="Country code (e.g., KENYA, INDIA)"),
    direction: Direction = Form(..., description="Trade direction"),
    source_format: SourceFormat = Form(..., description="Data format"),
    source_provider: Optional[str] = Form(None, description="Data source provider"),
    data_grain: Optional[DataGrain] = Form(None, description="Data granularity"),
    is_production: bool = Form(True, description="Is production data"),
    data_quality_level: Optional[DataQualityLevel] = Form(None, description="Data quality level"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    notes: Optional[str] = Form(None, description="Free text notes"),
    header_row_index: int = Form(1, ge=1, description="Header row index (1-indexed)"),
    sheet_name: Optional[str] = Form(None, description="Excel sheet name"),
    processing_mode: ProcessingMode = Form(..., description="Pipeline processing mode"),
    run_now: bool = Form(True, description="Run pipeline immediately"),
    db: DatabaseManager = Depends(get_db)
):
    """
    Upload a port data file with metadata and optional pipeline execution.
    
    This endpoint:
    1. Validates file extension (.xlsx, .xls, .csv)
    2. Saves file to disk with unique name
    3. Validates columns against mapping config
    4. Creates file_registry entry
    5. Optionally triggers pipeline execution
    """
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.xlsx', '.xls', '.csv']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {suffix}. Accepted: .xlsx, .xls, .csv"
        )
    
    # EPIC 10: Check mapping status and enforce processing mode restrictions
    mapping_status = get_mapping_status_from_registry(
        db,
        reporting_country,
        direction.value,
        source_format.value
    )
    
    if processing_mode.value not in mapping_status.allowed_modes:
        status_msg = {
            MappingStatus.DRAFT: "DRAFT mapping – only INGEST_ONLY is allowed. Run validate_country_mapping.py to verify.",
            MappingStatus.VERIFIED: "VERIFIED mapping – FULL_PIPELINE requires LIVE status. Ask admin to promote.",
            MappingStatus.NOT_FOUND: "No mapping found – only INGEST_ONLY is allowed. Create a mapping config first.",
        }.get(mapping_status.status, f"Processing mode {processing_mode.value} not allowed for {mapping_status.status} mapping")
        
        raise HTTPException(
            status_code=400,
            detail=f"{status_msg} Allowed modes: {mapping_status.allowed_modes}"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Compute checksum
    checksum = get_file_checksum(content)
    
    # Check for duplicate
    existing = db.execute_query(
        "SELECT file_id, file_name FROM file_registry WHERE file_checksum = %s",
        (checksum,)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate file. Already exists as file_id={existing[0][0]}: {existing[0][1]}"
        )
    
    # Normalize country
    reporting_country = reporting_country.upper().strip()
    
    # Create storage path - no year/month in path (will be derived from data)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    new_filename = f"{reporting_country}_{direction.value}_{timestamp}{suffix}"
    
    # Store in country/direction folders (year/month will be derived from data during standardization)
    storage_dir = Path("data/raw") / reporting_country / direction.value / "uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = storage_dir / new_filename
    
    # Save file to disk
    with open(file_path, 'wb') as f:
        f.write(content)
    
    logger.info(f"Saved file to {file_path}")
    
    # Find mapping config
    config_path = find_mapping_config(reporting_country, direction.value, source_format.value)
    
    # Validate columns if config exists
    if config_path:
        # Use config's header_row if not specified
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            config_header_row = config.get('header_row', header_row_index)
        except:
            config_header_row = header_row_index
        
        validation = validate_file_columns(
            file_path,
            config_path,
            config_header_row,
            sheet_name
        )
        
        if validation.status == "ERROR":
            # Don't delete the file, but return error
            raise HTTPException(
                status_code=422,
                detail=f"Missing required columns: {validation.required_columns_missing} for {config_path}"
            )
    else:
        # No config found - warn but proceed
        validation = ValidationResult(
            config_used=None,
            required_columns_found=[],
            required_columns_missing=[],
            status="OK"
        )
        logger.warning(f"No mapping config found for {reporting_country}/{direction.value}/{source_format.value}")
    
    # Insert into file_registry (year/month will be computed after standardization)
    insert_query = """
        INSERT INTO file_registry (
            file_name, file_path, file_checksum,
            reporting_country, direction, source_format,
            file_size_bytes, status,
            source_provider, data_grain, is_production, data_quality_level,
            tags, notes, header_row_index, sheet_name,
            processing_mode, config_file_used, upload_source,
            created_at, ingestion_completed_at
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, 'INGESTED',
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, 'admin_upload',
            NOW(), NOW()
        )
        RETURNING file_id, created_at
    """
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(insert_query, (
                new_filename,
                str(file_path),
                checksum,
                reporting_country,
                direction.value,
                source_format.value,
                file_size,
                source_provider,
                data_grain.value if data_grain else None,
                is_production,
                data_quality_level.value if data_quality_level else 'RAW',
                tags,
                notes,
                header_row_index,
                sheet_name,
                processing_mode.value,
                str(config_path) if config_path else None
            ))
            result = cursor.fetchone()
            file_id = result[0]
            created_at = result[1]
        finally:
            cursor.close()
    
    # Handle pipeline execution
    pipeline_run_id = None
    pipeline_status = "SKIPPED"
    
    if run_now and processing_mode != ProcessingMode.INGEST_ONLY:
        # Create pipeline run entry
        pipeline_run_id = create_pipeline_run(
            db,
            f"admin_upload_{processing_mode.value.lower()}",
            [reporting_country],
            [direction.value]
        )
        
        # Spawn pipeline in background
        spawn_pipeline_async(
            processing_mode,
            reporting_country,
            direction.value,
            pipeline_run_id
        )
        
        pipeline_status = "QUEUED"
    elif not run_now:
        pipeline_status = "SKIPPED"
    else:
        pipeline_status = "COMPLETED"  # INGEST_ONLY is already done
    
    return UploadResponse(
        file_id=file_id,
        file_name=new_filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        reporting_country=reporting_country,
        direction=direction.value,
        source_format=source_format.value,
        min_shipment_date=None,  # Will be populated after standardization
        max_shipment_date=None,  # Will be populated after standardization
        validation=validation,
        pipeline=PipelineResult(
            processing_mode=processing_mode.value,
            run_now=run_now,
            pipeline_run_id=pipeline_run_id,
            status=pipeline_status
        ),
        created_at=created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at)
    )


@router.get("/files", response_model=FileListResponse)
def list_files(
    limit: int = 50,
    offset: int = 0,
    reporting_country: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    List uploaded files from file_registry with pagination and filters.
    """
    
    # Build query with filters
    where_clauses = []
    params = []
    
    if reporting_country:
        where_clauses.append("reporting_country = %s")
        params.append(reporting_country.upper())
    
    if direction:
        where_clauses.append("direction = %s")
        params.append(direction.upper())
    
    if status:
        where_clauses.append("status = %s")
        params.append(status.upper())
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Count total
    count_query = f"SELECT COUNT(*) FROM file_registry WHERE {where_sql}"
    total = db.execute_query(count_query, tuple(params))[0][0]
    
    # Get items
    query = f"""
        SELECT 
            file_id, file_name, file_path, file_size_bytes,
            reporting_country, direction, source_format,
            min_shipment_date, max_shipment_date,
            status, created_at,
            ingestion_completed_at, standardization_completed_at,
            identity_completed_at, ledger_completed_at,
            processing_mode, config_file_used, is_production, tags, notes
        FROM file_registry
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    
    params.extend([limit, offset])
    rows = db.execute_query(query, tuple(params))
    
    items = []
    for row in rows:
        items.append(FileEntry(
            file_id=row[0],
            file_name=row[1],
            file_path=row[2],
            file_size_bytes=row[3],
            reporting_country=row[4],
            direction=row[5],
            source_format=row[6],
            min_shipment_date=row[7].isoformat() if row[7] else None,
            max_shipment_date=row[8].isoformat() if row[8] else None,
            status=row[9],
            created_at=row[10].isoformat() if row[10] else None,
            ingestion_completed_at=row[11].isoformat() if row[11] else None,
            standardization_completed_at=row[12].isoformat() if row[12] else None,
            identity_completed_at=row[13].isoformat() if row[13] else None,
            ledger_completed_at=row[14].isoformat() if row[14] else None,
            processing_mode=row[15],
            config_file_used=row[16],
            is_production=row[17],
            tags=row[18],
            notes=row[19]
        ))
    
    return FileListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/files/{file_id}", response_model=FileEntry)
def get_file(
    file_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get details for a specific file by ID.
    """
    query = """
        SELECT 
            file_id, file_name, file_path, file_size_bytes,
            reporting_country, direction, source_format,
            min_shipment_date, max_shipment_date,
            status, created_at,
            ingestion_completed_at, standardization_completed_at,
            identity_completed_at, ledger_completed_at,
            processing_mode, config_file_used, is_production, tags, notes
        FROM file_registry
        WHERE file_id = %s
    """
    
    rows = db.execute_query(query, (file_id,))
    
    if not rows:
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    row = rows[0]
    return FileEntry(
        file_id=row[0],
        file_name=row[1],
        file_path=row[2],
        file_size_bytes=row[3],
        reporting_country=row[4],
        direction=row[5],
        source_format=row[6],
        min_shipment_date=row[7].isoformat() if row[7] else None,
        max_shipment_date=row[8].isoformat() if row[8] else None,
        status=row[9],
        created_at=row[10].isoformat() if row[10] else None,
        ingestion_completed_at=row[11].isoformat() if row[11] else None,
        standardization_completed_at=row[12].isoformat() if row[12] else None,
        identity_completed_at=row[13].isoformat() if row[13] else None,
        ledger_completed_at=row[14].isoformat() if row[14] else None,
        processing_mode=row[15],
        config_file_used=row[16],
        is_production=row[17],
        tags=row[18],
        notes=row[19]
    )


@router.get("/configs", response_model=List[str])
def list_available_configs():
    """
    List available mapping configuration files.
    """
    config_dir = Path("config")
    configs = []
    
    for file in config_dir.glob("*.yml"):
        # Skip non-mapping configs
        if file.name in ['db_config.yml', 'db_config.yml.template', 'ingestion_config.yml']:
            continue
        configs.append(file.name)
    
    return sorted(configs)
