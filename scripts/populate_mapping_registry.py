#!/usr/bin/env python3
"""
Populate Mapping Registry (EPIC 10)
===================================
Creates the mapping_registry table and populates it from:
1. Existing hand-written configs (India/Kenya/Indonesia) → LIVE
2. Auto-generated configs in config/*.yml → DRAFT

Usage:
    python scripts/populate_mapping_registry.py
"""

import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import yaml

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
# CONSTANTS
# ============================================================================

# Hand-crafted configs that are already in production (LIVE status)
LIVE_CONFIGS = {
    'kenya_import_full',
    'kenya_import_short',
    'kenya_export_full',
    'kenya_export_short',
    'india_import_full',
    'india_import_short', 
    'india_export_full',
    'india_export_short',
    'indonesia_import_full',
    'indonesia_import_short',
    'indonesia_export_full',
    'indonesia_export_short',
}

# Mapping from config key patterns to sample file patterns
SAMPLE_FILE_PATTERNS = {
    # Format: config_key_pattern -> (filename_pattern, format_suffix)
    'import_full': ('Import F', 'Import Full'),
    'import_short': ('Import S', 'Import Short'),
    'export_full': ('Export F', 'Export Full'),
    'export_short': ('Export S', 'Export Short'),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_config_key(config_key: str) -> Optional[Dict[str, str]]:
    """
    Parse a config key like 'kenya_import_full' into components.
    Returns dict with: country, direction, source_format
    """
    # Pattern: {country}_{direction}_{format}
    # Country can have underscores (e.g., 'ivory_coast', 'south_sudan')
    pattern = r'^(.+?)_(import|export)_(full|short)$'
    match = re.match(pattern, config_key.lower())
    
    if match:
        country = match.group(1).upper().replace('_', ' ')
        direction = match.group(2).upper()
        source_format = match.group(3).upper()
        return {
            'country': country,
            'direction': direction,
            'source_format': source_format,
        }
    return None


def find_sample_file(country: str, direction: str, source_format: str, data_dir: Path) -> Optional[str]:
    """
    Find a sample file in data/reference/port_real/ matching the mapping.
    """
    # Normalize country name for file matching
    country_variants = [
        country.title(),
        country.replace(' ', '_').title(),
        country.replace('_', ' ').title(),
    ]
    
    # Format suffix variants
    format_key = f"{direction.lower()}_{source_format.lower()}"
    suffixes = SAMPLE_FILE_PATTERNS.get(format_key, (None, None))
    
    for variant in country_variants:
        for suffix in suffixes:
            if suffix:
                # Try exact pattern: "{Country} {Direction} {F/S/Full/Short}.xlsx"
                pattern = f"{variant} {suffix}*.xlsx"
                matches = list(data_dir.glob(pattern))
                if matches:
                    return str(matches[0])
    
    return None


def load_config_metadata(yaml_path: Path) -> Dict:
    """Load metadata from a YAML config file."""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load {yaml_path}: {e}")
        return {}


def run_migration(db: DatabaseManager) -> bool:
    """Run the 009 migration to create mapping_registry table."""
    migration_path = Path("db/migrations/009_mapping_registry.sql")
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False
    
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(migration_sql)
                conn.commit()
        
        logger.info("Migration 009 applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


def populate_registry(db: DatabaseManager) -> Dict:
    """
    Populate mapping_registry from config files.
    
    Returns summary dict.
    """
    config_dir = Path("config")
    data_dir = Path("data/reference/port_real")
    
    results = {
        'total_configs': 0,
        'live': 0,
        'draft': 0,
        'skipped': 0,
        'errors': [],
    }
    
    # Find all YAML config files
    yaml_files = list(config_dir.glob("*.yml")) + list(config_dir.glob("*.yaml"))
    
    # Filter to only country mapping configs (not db_config, etc.)
    mapping_files = []
    for f in yaml_files:
        # Skip non-mapping configs
        if f.stem in ['db_config', 'config']:
            continue
        # Check if it looks like a mapping config
        parsed = parse_config_key(f.stem)
        if parsed:
            mapping_files.append(f)
    
    logger.info(f"Found {len(mapping_files)} mapping config files")
    results['total_configs'] = len(mapping_files)
    
    # Process each config
    for yaml_path in mapping_files:
        config_key = yaml_path.stem
        parsed = parse_config_key(config_key)
        
        if not parsed:
            logger.warning(f"Could not parse config key: {config_key}")
            results['skipped'] += 1
            continue
        
        # Determine status
        if config_key.lower() in {k.lower() for k in LIVE_CONFIGS}:
            status = 'LIVE'
            results['live'] += 1
        else:
            status = 'DRAFT'
            results['draft'] += 1
        
        # Find sample file
        sample_file = find_sample_file(
            parsed['country'],
            parsed['direction'],
            parsed['source_format'],
            data_dir
        )
        
        # Load config for notes
        config_data = load_config_metadata(yaml_path)
        notes = None
        if config_data.get('_metadata', {}).get('auto_generated'):
            notes = f"Auto-generated from {config_data.get('_metadata', {}).get('source_file', 'unknown')}"
        
        # Insert or update
        try:
            upsert_sql = """
                INSERT INTO mapping_registry (
                    reporting_country, direction, source_format,
                    config_key, yaml_path, status,
                    sample_file_path, notes, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (reporting_country, direction, source_format)
                DO UPDATE SET
                    config_key = EXCLUDED.config_key,
                    yaml_path = EXCLUDED.yaml_path,
                    status = CASE 
                        WHEN mapping_registry.status = 'LIVE' THEN 'LIVE'
                        ELSE EXCLUDED.status 
                    END,
                    sample_file_path = COALESCE(EXCLUDED.sample_file_path, mapping_registry.sample_file_path),
                    notes = COALESCE(EXCLUDED.notes, mapping_registry.notes),
                    updated_at = NOW()
            """
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(upsert_sql, (
                        parsed['country'],
                        parsed['direction'],
                        parsed['source_format'],
                        config_key,
                        str(yaml_path),
                        status,
                        sample_file,
                        notes,
                    ))
                    conn.commit()
            
            logger.debug(f"Registered: {config_key} → {status}")
            
        except Exception as e:
            logger.error(f"Failed to register {config_key}: {e}")
            results['errors'].append({'config': config_key, 'error': str(e)})
    
    return results


def print_summary(db: DatabaseManager):
    """Print summary of mapping registry."""
    
    # Get counts by status
    count_sql = """
        SELECT status, COUNT(*) as count
        FROM mapping_registry
        GROUP BY status
        ORDER BY 
            CASE status 
                WHEN 'LIVE' THEN 1 
                WHEN 'VERIFIED' THEN 2 
                ELSE 3 
            END
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(count_sql)
            counts = cursor.fetchall()
    
    print("\n" + "=" * 60)
    print("  MAPPING REGISTRY SUMMARY")
    print("=" * 60)
    
    for status, count in counts:
        emoji = {'LIVE': '🟢', 'VERIFIED': '🟡', 'DRAFT': '🔴'}.get(status, '⚪')
        print(f"  {emoji} {status}: {count} mappings")
    
    # Show LIVE countries
    live_sql = """
        SELECT DISTINCT reporting_country
        FROM mapping_registry
        WHERE status = 'LIVE'
        ORDER BY reporting_country
    """
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(live_sql)
            live_countries = [row[0] for row in cursor.fetchall()]
    
    if live_countries:
        print(f"\n  LIVE Countries: {', '.join(live_countries)}")
    
    print("=" * 60 + "\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    
    print("=" * 60)
    print("  EPIC 10: Populate Mapping Registry")
    print("=" * 60)
    print()
    
    # Initialize database
    db = DatabaseManager('config/db_config.yml')
    
    # Step 1: Run migration
    print("Step 1: Running migration 009...")
    if not run_migration(db):
        print("ERROR: Migration failed!")
        return 1
    
    # Step 2: Populate registry
    print("\nStep 2: Populating mapping registry from config files...")
    results = populate_registry(db)
    
    print(f"\n  Processed: {results['total_configs']} configs")
    print(f"  - LIVE: {results['live']}")
    print(f"  - DRAFT: {results['draft']}")
    print(f"  - Skipped: {results['skipped']}")
    print(f"  - Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\n  Errors:")
        for err in results['errors'][:5]:
            print(f"    - {err['config']}: {err['error']}")
    
    # Step 3: Print summary
    print_summary(db)
    
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
