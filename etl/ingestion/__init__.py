"""
GTI-OS Data Platform - Ingestion Module (Phase 1)
Handles bulk ingestion of raw trade data files into staging
"""

from .ingest_files import (
    scan_raw_files,
    compute_file_checksum,
    detect_file_metadata,
    ingest_file_to_staging,
    FileIngestionEngine
)

__all__ = [
    'scan_raw_files',
    'compute_file_checksum',
    'detect_file_metadata',
    'ingest_file_to_staging',
    'FileIngestionEngine'
]
