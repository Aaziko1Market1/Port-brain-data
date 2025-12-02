"""
GTI-OS Data Platform - File Ingestion Engine (Phase 1)
Bulk ingestion of raw Excel/CSV files into stg_shipments_raw

Features:
- Checksum-based deduplication via file_registry
- Chunked reading for large files (50k+ rows)
- Bulk insert via PostgreSQL COPY
- Metadata extraction from file paths
- Comprehensive error handling
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from io import StringIO
import logging

import polars as pl
import pandas as pd

from ..db_utils import DatabaseManager

logger = logging.getLogger(__name__)


def compute_file_checksum(file_path: Path) -> str:
    """
    Compute SHA256 checksum of a file for deduplication
    
    Args:
        file_path: Path to file
    
    Returns:
        Hexadecimal checksum string
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    
    checksum = sha256_hash.hexdigest()
    logger.debug(f"Computed checksum for {file_path.name}: {checksum[:16]}...")
    return checksum


def detect_file_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from file path structure
    Expected structure: data/raw/{country}/{direction}/{year}/{month}/{file}.xlsx
    
    Args:
        file_path: Path object for the file
    
    Returns:
        Dictionary with metadata fields
    """
    parts = file_path.parts
    
    metadata = {
        'reporting_country': None,
        'direction': None,
        'year': None,
        'month': None,
        'source_format': 'FULL',  # Default, can be refined later
        'record_grain': 'LINE_ITEM'  # Default
    }
    
    try:
        # Parse path structure: data/raw/{country}/{direction}/{year}/{month}/
        # Find 'raw' in path and extract from there
        if 'raw' in parts:
            raw_idx = parts.index('raw')
            
            # Country (next after raw)
            if len(parts) > raw_idx + 1:
                metadata['reporting_country'] = parts[raw_idx + 1].upper()
            
            # Direction (export/import)
            if len(parts) > raw_idx + 2:
                direction_raw = parts[raw_idx + 2].upper()
                if 'EXPORT' in direction_raw:
                    metadata['direction'] = 'EXPORT'
                elif 'IMPORT' in direction_raw:
                    metadata['direction'] = 'IMPORT'
            
            # Year
            if len(parts) > raw_idx + 3:
                year_str = parts[raw_idx + 3]
                if year_str.isdigit() and len(year_str) == 4:
                    metadata['year'] = int(year_str)
            
            # Month
            if len(parts) > raw_idx + 4:
                month_str = parts[raw_idx + 4]
                if month_str.isdigit() and 1 <= int(month_str) <= 12:
                    metadata['month'] = int(month_str)
        
        # Detect format from filename heuristics
        filename_lower = file_path.stem.lower()
        filename_upper = file_path.stem.upper()
        
        # Country-specific format detection
        # Production files: "* Import F.xlsx" = FULL, "* Import S.xlsx" = SHORT
        # Test/synthetic files: "*_import_202301.xlsx" = TEST (to be skipped)
        import re
        
        # Kenya format detection
        if 'kenya' in filename_lower:
            if re.match(r'kenya_(import|export)_\d+', filename_lower):
                metadata['source_format'] = 'TEST'
                metadata['is_synthetic'] = True
            elif filename_upper.endswith(' F'):
                metadata['source_format'] = 'FULL'
            elif filename_upper.endswith(' S'):
                metadata['source_format'] = 'SHORT'
            else:
                metadata['source_format'] = 'TEST'
                metadata['is_synthetic'] = True
        
        # Indonesia format detection
        elif 'indonesia' in filename_lower:
            if re.match(r'indonesia_(import|export)_\d+', filename_lower):
                metadata['source_format'] = 'TEST'
                metadata['is_synthetic'] = True
            elif filename_upper.endswith(' F'):
                metadata['source_format'] = 'FULL'
            elif filename_upper.endswith(' S'):
                metadata['source_format'] = 'SHORT'
            else:
                metadata['source_format'] = 'TEST'
                metadata['is_synthetic'] = True
        
        # Generic format detection
        elif 'summary' in filename_lower or 'agg' in filename_lower or 'short' in filename_lower:
            metadata['source_format'] = 'SHORT'
        elif 'full' in filename_lower or 'detail' in filename_lower:
            metadata['source_format'] = 'FULL'
        
        logger.debug(f"Detected metadata for {file_path.name}: {metadata}")
    
    except Exception as e:
        logger.warning(f"Error parsing metadata from path {file_path}: {e}")
    
    return metadata


def scan_raw_files(root_path: str, extensions: Optional[List[str]] = None) -> List[Path]:
    """
    Recursively scan directory for data files
    
    Args:
        root_path: Root directory to scan
        extensions: List of file extensions to include (default: ['.xlsx', '.xls', '.csv'])
    
    Returns:
        List of Path objects for discovered files
    """
    if extensions is None:
        extensions = ['.xlsx', '.xls', '.csv']
    
    root = Path(root_path)
    
    if not root.exists():
        logger.warning(f"Root path does not exist: {root_path}")
        return []
    
    files = []
    for ext in extensions:
        # Use rglob for recursive search
        files.extend(root.rglob(f'*{ext}'))
    
    logger.info(f"Scanned {root_path}: found {len(files)} files")
    return sorted(files)


class FileIngestionEngine:
    """
    Orchestrates bulk ingestion of raw files into stg_shipments_raw
    """
    
    def __init__(self, db_manager: DatabaseManager, chunk_size: int = 50000):
        """
        Initialize ingestion engine
        
        Args:
            db_manager: Database manager instance
            chunk_size: Number of rows per processing chunk
        """
        self.db_manager = db_manager
        self.chunk_size = chunk_size
    
    def check_file_already_ingested(self, checksum: str) -> Tuple[bool, Optional[int]]:
        """
        Check if file with given checksum exists in file_registry
        
        Args:
            checksum: File checksum
        
        Returns:
            Tuple of (exists, file_id)
        """
        query = """
            SELECT file_id, status 
            FROM file_registry 
            WHERE file_checksum = %s;
        """
        result = self.db_manager.execute_query(query, (checksum,))
        
        if result:
            file_id, status = result[0]
            if status == 'INGESTED':
                logger.info(f"File already ingested: checksum={checksum[:16]}... (file_id={file_id})")
                return True, file_id
        
        return False, None
    
    def register_file(
        self, 
        file_path: Path, 
        checksum: str, 
        metadata: Dict[str, Any],
        status: str = 'PENDING'
    ) -> int:
        """
        Register file in file_registry
        
        Args:
            file_path: Path to file
            checksum: File checksum
            metadata: Detected metadata
            status: Initial status (default: PENDING)
        
        Returns:
            file_id of registered entry
        """
        query = """
            INSERT INTO file_registry (
                file_name, file_path, file_checksum, 
                reporting_country, direction, year, month,
                file_size_bytes, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (file_checksum) 
            DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING file_id;
        """
        
        file_size = file_path.stat().st_size
        
        params = (
            file_path.name,
            str(file_path),
            checksum,
            metadata.get('reporting_country'),
            metadata.get('direction'),
            metadata.get('year'),
            metadata.get('month'),
            file_size,
            status
        )
        
        result = self.db_manager.execute_query(query, params)
        file_id = result[0][0] if result else None
        
        logger.info(f"Registered file: {file_path.name} (file_id={file_id})")
        return file_id
    
    def update_file_status(
        self, 
        file_id: int, 
        status: str, 
        total_rows: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """
        Update file_registry status
        
        Args:
            file_id: File registry ID
            status: New status (INGESTED, FAILED, etc.)
            total_rows: Total rows ingested
            error_message: Error message if failed
        """
        query = """
            UPDATE file_registry
            SET status = %s,
                total_rows = COALESCE(%s, total_rows),
                error_message = %s,
                ingested_at = CASE WHEN %s = 'INGESTED' THEN CURRENT_TIMESTAMP ELSE ingested_at END,
                updated_at = CURRENT_TIMESTAMP
            WHERE file_id = %s;
        """
        
        self.db_manager.execute_insert(
            query, 
            (status, total_rows, error_message, status, file_id)
        )
        
        logger.info(f"Updated file_id={file_id} to status={status}")
    
    def read_file_in_chunks(
        self, 
        file_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[pl.DataFrame]:
        """
        Read Excel/CSV file in chunks using Polars
        
        Args:
            file_path: Path to file
            metadata: Optional metadata to determine header row
        
        Returns:
            List of Polars DataFrames (chunks)
        """
        chunks = []
        extension = file_path.suffix.lower()
        
        # Determine header row (0-indexed for pandas)
        header_row = 0  # Default
        if metadata:
            # Check if we need to load config for header row info
            try:
                reporting_country = metadata.get('reporting_country', '').lower()
                direction = metadata.get('direction', '').lower()
                source_format = metadata.get('source_format', 'full').lower()
                
                config_file = f"config/{reporting_country}_{direction}_{source_format}.yml"
                config_path = Path(config_file)
                
                if config_path.exists():
                    import yaml
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    # YAML header_row is 1-indexed, pandas expects 0-indexed
                    header_row = config.get('header_row', 1) - 1
                    logger.info(f"Using header row {header_row} (0-indexed) from config")
            except Exception as e:
                logger.debug(f"Could not load config for header detection: {e}")
        
        try:
            if extension == '.csv':
                # Read CSV in chunks using Polars
                df = pl.read_csv(file_path, infer_schema_length=10000)
                
                # Split into chunks
                total_rows = len(df)
                for i in range(0, total_rows, self.chunk_size):
                    chunk = df[i:i + self.chunk_size]
                    chunks.append(chunk)
                
                logger.info(f"Read CSV file: {total_rows} rows in {len(chunks)} chunks")
            
            elif extension in ['.xlsx', '.xls']:
                # For Excel, use pandas with openpyxl (Polars doesn't support Excel streaming well)
                # Read in chunks manually
                try:
                    # Read full file first (pandas) with proper header row
                    df_pandas = pd.read_excel(file_path, engine='openpyxl', header=header_row)
                    
                    # Convert to Polars and chunk
                    df = pl.from_pandas(df_pandas)
                    total_rows = len(df)
                    
                    for i in range(0, total_rows, self.chunk_size):
                        chunk = df[i:i + self.chunk_size]
                        chunks.append(chunk)
                    
                    logger.info(f"Read Excel file: {total_rows} rows in {len(chunks)} chunks")
                
                except Exception as e:
                    logger.error(f"Error reading Excel file with openpyxl: {e}")
                    # Fallback to xlrd for older .xls files
                    if extension == '.xls':
                        df_pandas = pd.read_excel(file_path, engine='xlrd', header=header_row)
                        df = pl.from_pandas(df_pandas)
                        total_rows = len(df)
                        
                        for i in range(0, total_rows, self.chunk_size):
                            chunk = df[i:i + self.chunk_size]
                            chunks.append(chunk)
                        
                        logger.info(f"Read Excel file (xlrd): {total_rows} rows in {len(chunks)} chunks")
            
            else:
                raise ValueError(f"Unsupported file extension: {extension}")
        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
        
        return chunks
    
    def prepare_staging_data(
        self,
        chunk: pl.DataFrame,
        file_path: Path,
        metadata: Dict[str, Any],
        chunk_start_row: int
    ) -> StringIO:
        """
        Prepare chunk data for COPY into stg_shipments_raw
        
        Args:
            chunk: Polars DataFrame chunk
            file_path: Source file path
            metadata: File metadata
            chunk_start_row: Starting row number for this chunk
        
        Returns:
            StringIO buffer with CSV data
        """
        rows = []
        
        for idx, row in enumerate(chunk.iter_rows(named=True)):
            row_number = chunk_start_row + idx + 1
            
            # Convert row to JSON (handle None/NaN)
            raw_data = {}
            for key, value in row.items():
                # Skip None and NaN values
                if value is None:
                    continue
                if isinstance(value, float):
                    # Check for NaN using != comparison trick
                    if value != value:  # NaN != NaN is True
                        continue
                
                # Add valid values
                if isinstance(value, (int, float, str, bool)):
                    raw_data[key] = value
                else:
                    raw_data[key] = str(value)
            
            raw_data_json = json.dumps(raw_data, ensure_ascii=False)
            
            # Extract optional fields
            hs_code_raw = raw_data.get('hs_code') or raw_data.get('HS_CODE') or raw_data.get('hscode') or ''
            buyer_name_raw = raw_data.get('buyer') or raw_data.get('BUYER') or raw_data.get('importer') or ''
            supplier_name_raw = raw_data.get('supplier') or raw_data.get('SUPPLIER') or raw_data.get('exporter') or ''
            shipment_date_raw = raw_data.get('date') or raw_data.get('shipment_date') or ''
            
            # Build CSV row
            csv_row = [
                file_path.name,
                metadata.get('reporting_country', ''),
                metadata.get('direction', ''),
                metadata.get('source_format', 'FULL'),
                metadata.get('record_grain', 'LINE_ITEM'),
                str(row_number),
                raw_data_json.replace('"', '""'),  # Escape quotes for CSV
                hs_code_raw,
                buyer_name_raw,
                supplier_name_raw,
                shipment_date_raw
            ]
            
            rows.append(','.join([f'"{field}"' if field else '' for field in csv_row]))
        
        # Create CSV buffer
        csv_data = '\n'.join(rows)
        buffer = StringIO(csv_data)
        
        return buffer
    
    def bulk_insert_chunk(
        self,
        chunk: pl.DataFrame,
        file_path: Path,
        metadata: Dict[str, Any],
        chunk_start_row: int
    ) -> int:
        """
        Bulk insert chunk into stg_shipments_raw using COPY
        
        Args:
            chunk: Polars DataFrame chunk
            file_path: Source file path
            metadata: File metadata
            chunk_start_row: Starting row number
        
        Returns:
            Number of rows inserted
        """
        # Prepare data buffer
        data_buffer = self.prepare_staging_data(chunk, file_path, metadata, chunk_start_row)
        
        # Define columns
        columns = [
            'raw_file_name',
            'reporting_country',
            'direction',
            'source_format',
            'record_grain',
            'raw_row_number',
            'raw_data',
            'hs_code_raw',
            'buyer_name_raw',
            'supplier_name_raw',
            'shipment_date_raw'
        ]
        
        # Bulk insert via COPY
        rows_inserted = self.db_manager.bulk_insert_copy(
            'stg_shipments_raw',
            columns,
            data_buffer
        )
        
        return rows_inserted
    
    def ingest_file(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ingest single file into stg_shipments_raw
        
        Args:
            file_path: Path to file
            metadata: Optional pre-computed metadata
        
        Returns:
            Ingestion result summary
        """
        result = {
            'file_path': str(file_path),
            'status': 'PENDING',
            'rows_ingested': 0,
            'error': None
        }
        
        try:
            # Compute checksum
            checksum = compute_file_checksum(file_path)
            
            # Check if already ingested
            already_ingested, file_id = self.check_file_already_ingested(checksum)
            if already_ingested:
                result['status'] = 'DUPLICATE'
                result['file_id'] = file_id
                return result
            
            # Detect metadata
            if metadata is None:
                metadata = detect_file_metadata(file_path)
            
            # Skip synthetic/test files
            if metadata.get('source_format') == 'TEST' or metadata.get('is_synthetic'):
                logger.warning(f"Skipping synthetic/test file: {file_path.name}")
                result['status'] = 'SKIPPED'
                result['skip_reason'] = 'SYNTHETIC_TEST_FILE'
                return result
            
            # Register file
            file_id = self.register_file(file_path, checksum, metadata, status='PROCESSING')
            result['file_id'] = file_id
            
            # Read file in chunks (pass metadata for header detection)
            chunks = self.read_file_in_chunks(file_path, metadata)
            
            # Ingest each chunk
            total_rows = 0
            chunk_start_row = 0
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_rows = len(chunk)
                logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} ({chunk_rows} rows)")
                
                rows_inserted = self.bulk_insert_chunk(
                    chunk,
                    file_path,
                    metadata,
                    chunk_start_row
                )
                
                total_rows += rows_inserted
                chunk_start_row += chunk_rows
            
            # Update status
            self.update_file_status(file_id, 'INGESTED', total_rows)
            
            result['status'] = 'INGESTED'
            result['rows_ingested'] = total_rows
            
            logger.info(f"Successfully ingested {file_path.name}: {total_rows} rows")
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to ingest {file_path.name}: {error_msg}")
            
            if 'file_id' in result:
                self.update_file_status(result['file_id'], 'FAILED', error_message=error_msg)
            
            result['status'] = 'FAILED'
            result['error'] = error_msg
        
        return result


def ingest_file_to_staging(
    file_path: Path,
    db_manager: DatabaseManager,
    chunk_size: int = 50000
) -> Dict[str, Any]:
    """
    Convenience function to ingest a single file
    
    Args:
        file_path: Path to file
        db_manager: Database manager instance
        chunk_size: Chunk size for processing
    
    Returns:
        Ingestion result dictionary
    """
    engine = FileIngestionEngine(db_manager, chunk_size)
    return engine.ingest_file(file_path)
