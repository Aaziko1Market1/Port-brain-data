#!/usr/bin/env python3
"""
Bulk Ingest LIVE Countries (EPIC 10)
====================================
Processes only countries with mapping_registry.status = 'LIVE'.

Usage:
    python scripts/bulk_ingest_live_countries.py
    python scripts/bulk_ingest_live_countries.py --country KENYA --direction IMPORT
    python scripts/bulk_ingest_live_countries.py --dry-run

This script:
1. Reads mapping_registry WHERE status = 'LIVE'
2. For each LIVE mapping, finds all matching files in:
   - data/raw/{country}/{direction}/
   - file_registry WHERE is_production = true
3. Runs the full pipeline: ingestion → standardization → identity → ledger
4. Uses pipeline_runs tracking

IMPORTANT CONSTRAINTS:
- NEVER processes DRAFT or VERIFIED mappings
- Idempotent using file_registry checksums and std_id
- India/Kenya/Indonesia behavior unchanged
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.db_utils import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_live_mappings(db: DatabaseManager, country: str = None, direction: str = None) -> List[Dict]:
    """Get all LIVE mappings from registry, optionally filtered."""
    
    query = """
        SELECT 
            mapping_id, reporting_country, direction, source_format,
            config_key, yaml_path, sample_file_path
        FROM mapping_registry
        WHERE status = 'LIVE'
    """
    params = []
    
    if country:
        query += " AND UPPER(reporting_country) = UPPER(%s)"
        params.append(country)
    
    if direction:
        query += " AND UPPER(direction) = UPPER(%s)"
        params.append(direction)
    
    query += " ORDER BY reporting_country, direction, source_format"
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
    
    return [
        {
            'mapping_id': r[0],
            'reporting_country': r[1],
            'direction': r[2],
            'source_format': r[3],
            'config_key': r[4],
            'yaml_path': r[5],
            'sample_file_path': r[6],
        }
        for r in rows
    ]


def find_files_for_mapping(
    db: DatabaseManager, 
    country: str, 
    direction: str, 
    source_format: str
) -> List[Dict]:
    """
    Find all files matching a mapping that need processing.
    
    Sources:
    1. data/raw/{country}/{direction}/ folder
    2. file_registry where is_production = true and not fully processed
    """
    files = []
    
    # Source 1: Raw data folder
    raw_dir = Path(f"data/raw/{country.lower()}/{direction.lower()}")
    if raw_dir.exists():
        for file_path in raw_dir.glob("*.xlsx"):
            files.append({
                'source': 'raw_folder',
                'path': str(file_path),
                'name': file_path.name,
            })
        for file_path in raw_dir.glob("*.csv"):
            files.append({
                'source': 'raw_folder', 
                'path': str(file_path),
                'name': file_path.name,
            })
    
    # Source 2: file_registry (uploaded via Admin UI)
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT file_id, file_name, file_path, status, ledger_completed_at
                FROM file_registry
                WHERE UPPER(reporting_country) = UPPER(%s)
                AND UPPER(direction) = UPPER(%s)
                AND UPPER(COALESCE(source_format, 'FULL')) = UPPER(%s)
                AND is_production = true
                AND status != 'FAILED'
            """, (country, direction, source_format))
            
            for row in cursor.fetchall():
                files.append({
                    'source': 'file_registry',
                    'file_id': row[0],
                    'name': row[1],
                    'path': row[2],
                    'status': row[3],
                    'ledger_completed': row[4] is not None,
                })
    
    return files


def check_file_already_processed(db: DatabaseManager, file_path: str) -> bool:
    """Check if a file has already been fully processed."""
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ledger_completed_at 
                FROM file_registry 
                WHERE file_path = %s AND ledger_completed_at IS NOT NULL
            """, (file_path,))
            return cursor.fetchone() is not None


def run_pipeline_for_country(
    db: DatabaseManager,
    mapping: Dict,
    dry_run: bool = False
) -> Dict:
    """
    Run the full pipeline for a single country mapping.
    
    Returns summary dict with counts.
    """
    result = {
        'mapping_id': mapping['mapping_id'],
        'country': mapping['reporting_country'],
        'direction': mapping['direction'],
        'source_format': mapping['source_format'],
        'files_found': 0,
        'files_processed': 0,
        'files_skipped': 0,
        'rows_ingested': 0,
        'rows_standardized': 0,
        'errors': [],
    }
    
    # Find files for this mapping
    files = find_files_for_mapping(
        db,
        mapping['reporting_country'],
        mapping['direction'],
        mapping['source_format']
    )
    result['files_found'] = len(files)
    
    if not files:
        logger.info(f"No files found for {mapping['config_key']}")
        return result
    
    for file_info in files:
        file_path = file_info['path']
        
        # Skip already processed files
        if file_info.get('ledger_completed'):
            result['files_skipped'] += 1
            logger.debug(f"Skipping already processed: {file_info['name']}")
            continue
        
        if check_file_already_processed(db, file_path):
            result['files_skipped'] += 1
            logger.debug(f"Skipping already processed: {file_info['name']}")
            continue
        
        if dry_run:
            logger.info(f"[DRY RUN] Would process: {file_info['name']}")
            result['files_processed'] += 1
            continue
        
        # Run pipeline stages
        try:
            # Import pipeline modules
            from etl.ingestion.ingest_files import FileIngestionEngine
            from etl.standardization.standardize_shipments import ShipmentStandardizer
            from etl.identity.resolve_organizations import IdentityEngine
            from etl.ledger.load_global_trades import LedgerLoader
            
            # Stage 1: Ingestion
            logger.info(f"Ingesting: {file_info['name']}")
            engine = FileIngestionEngine('config/db_config.yml')
            ingest_result = engine.ingest_file(
                Path(file_path),
                mapping['reporting_country'],
                mapping['direction']
            )
            result['rows_ingested'] += ingest_result.get('rows_inserted', 0)
            
            # Stage 2: Standardization
            logger.info(f"Standardizing: {file_info['name']}")
            standardizer = ShipmentStandardizer('config/db_config.yml')
            std_result = standardizer.standardize_country(
                mapping['reporting_country'],
                mapping['direction']
            )
            result['rows_standardized'] += std_result.get('rows_standardized', 0)
            
            # Stage 3: Identity Resolution
            logger.info(f"Resolving identities: {file_info['name']}")
            identity = IdentityEngine('config/db_config.yml')
            identity.resolve_all()
            
            # Stage 4: Ledger Load
            logger.info(f"Loading to ledger: {file_info['name']}")
            ledger = LedgerLoader('config/db_config.yml')
            ledger.load_incremental()
            
            result['files_processed'] += 1
            logger.info(f"✅ Completed: {file_info['name']}")
            
        except Exception as e:
            logger.error(f"Failed to process {file_info['name']}: {e}")
            result['errors'].append({
                'file': file_info['name'],
                'error': str(e),
            })
    
    return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bulk ingest LIVE countries only"
    )
    parser.add_argument('--country', help='Process specific country only')
    parser.add_argument('--direction', choices=['IMPORT', 'EXPORT'], help='Process specific direction only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without doing it')
    parser.add_argument('--list-only', action='store_true', help='Only list LIVE mappings')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  EPIC 10: Bulk Ingest LIVE Countries")
    print("=" * 70)
    print()
    
    db = DatabaseManager('config/db_config.yml')
    
    # Get LIVE mappings
    mappings = get_live_mappings(db, args.country, args.direction)
    
    if not mappings:
        print("  No LIVE mappings found.")
        print()
        print("  To promote a mapping to LIVE, run:")
        print("    UPDATE mapping_registry SET status = 'LIVE' WHERE config_key = 'your_config_key';")
        return 0
    
    print(f"  Found {len(mappings)} LIVE mappings:")
    print()
    
    for m in mappings:
        print(f"    🟢 {m['reporting_country']} {m['direction']} {m['source_format']}")
    
    print()
    
    if args.list_only:
        return 0
    
    if args.dry_run:
        print("  [DRY RUN MODE - No changes will be made]")
        print()
    
    # Process each mapping
    total_results = {
        'mappings_processed': 0,
        'files_found': 0,
        'files_processed': 0,
        'files_skipped': 0,
        'rows_ingested': 0,
        'rows_standardized': 0,
        'errors': [],
    }
    
    for mapping in mappings:
        print(f"  Processing: {mapping['config_key']}")
        print("-" * 50)
        
        result = run_pipeline_for_country(db, mapping, args.dry_run)
        
        total_results['mappings_processed'] += 1
        total_results['files_found'] += result['files_found']
        total_results['files_processed'] += result['files_processed']
        total_results['files_skipped'] += result['files_skipped']
        total_results['rows_ingested'] += result['rows_ingested']
        total_results['rows_standardized'] += result['rows_standardized']
        total_results['errors'].extend(result['errors'])
        
        print(f"    Files found:     {result['files_found']}")
        print(f"    Files processed: {result['files_processed']}")
        print(f"    Files skipped:   {result['files_skipped']}")
        print(f"    Rows ingested:   {result['rows_ingested']}")
        print(f"    Rows std:        {result['rows_standardized']}")
        print()
    
    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    print(f"  Mappings processed:  {total_results['mappings_processed']}")
    print(f"  Total files found:   {total_results['files_found']}")
    print(f"  Files processed:     {total_results['files_processed']}")
    print(f"  Files skipped:       {total_results['files_skipped']}")
    print(f"  Rows ingested:       {total_results['rows_ingested']}")
    print(f"  Rows standardized:   {total_results['rows_standardized']}")
    
    if total_results['errors']:
        print()
        print(f"  Errors: {len(total_results['errors'])}")
        for err in total_results['errors'][:5]:
            print(f"    ❌ {err['file']}: {err['error']}")
    
    print()
    print("=" * 70)
    
    return 0 if not total_results['errors'] else 1


if __name__ == "__main__":
    sys.exit(main())
