#!/usr/bin/env python3
"""
Country Mapping Validator (EPIC 10)
===================================
Validates a country mapping in a sandbox environment without touching production tables.

Usage:
    python scripts/validate_country_mapping.py --country BRAZIL --direction IMPORT --format FULL
    python scripts/validate_country_mapping.py --country BRAZIL --direction IMPORT --format FULL --dry-run

This script:
1. Copies 1-2 reference files into tmp_stg_shipments_raw (sandbox)
2. Runs standardization using the mapping config → tmp_stg_shipments_standardized
3. Runs data quality checks
4. Generates a validation report
5. Updates mapping_registry.status = 'VERIFIED' if all checks pass

IMPORTANT: This script NEVER writes to production tables:
- stg_shipments_raw
- stg_shipments_standardized
- global_trades_ledger
"""

import argparse
import json
import re
import sys
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field

import pandas as pd
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
# DATA CLASSES
# ============================================================================

@dataclass
class ValidationResult:
    """Result of a validation run."""
    success: bool
    country: str
    direction: str
    source_format: str
    config_key: str
    session_id: str
    
    # Row counts
    total_raw_rows: int = 0
    total_std_rows: int = 0
    
    # DQ metrics
    pct_valid_date: float = 0.0
    pct_valid_hs_code: float = 0.0
    pct_valid_quantity: float = 0.0
    pct_valid_value: float = 0.0
    pct_valid_buyer: float = 0.0
    pct_valid_supplier: float = 0.0
    
    # Date coverage
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    
    # Sample rows
    sample_rows: List[Dict] = field(default_factory=list)
    
    # Errors/warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def passed_checks(self) -> bool:
        """Check if all DQ thresholds are met."""
        return (
            self.pct_valid_date >= 90.0 and
            self.pct_valid_hs_code >= 90.0 and
            len(self.errors) == 0
        )


# ============================================================================
# SANDBOX OPERATIONS
# ============================================================================

def clear_sandbox_session(db: DatabaseManager, session_id: str):
    """Clear sandbox tables for a specific session."""
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tmp_stg_shipments_standardized WHERE validation_session_id = %s",
                (session_id,)
            )
            cursor.execute(
                "DELETE FROM tmp_stg_shipments_raw WHERE validation_session_id = %s", 
                (session_id,)
            )
            conn.commit()
    logger.info(f"Cleared sandbox for session {session_id}")


def ingest_to_sandbox(
    db: DatabaseManager,
    file_path: Path,
    country: str,
    direction: str,
    source_format: str,
    session_id: str,
    header_row: int = 1,
    max_rows: int = 1000
) -> int:
    """
    Ingest a file into the sandbox raw table.
    Returns number of rows ingested.
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path, header=header_row - 1, nrows=max_rows)
        
        if df.empty:
            logger.warning(f"Empty file: {file_path}")
            return 0
        
        # Clean column names
        df.columns = [str(c).strip().upper().replace(' ', '_') for c in df.columns]
        
        rows_inserted = 0
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for idx, row in df.iterrows():
                    # Convert row to JSON, handling NaN/NaT
                    row_dict = {}
                    for col, val in row.items():
                        if pd.isna(val):
                            row_dict[col] = None
                        elif hasattr(val, 'isoformat'):
                            row_dict[col] = val.isoformat()
                        else:
                            row_dict[col] = val
                    
                    cursor.execute("""
                        INSERT INTO tmp_stg_shipments_raw (
                            raw_file_name, reporting_country, direction,
                            source_format, raw_row_number, raw_data,
                            validation_session_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        file_path.name,
                        country,
                        direction,
                        source_format,
                        idx + 1,
                        json.dumps(row_dict),
                        session_id,
                    ))
                    rows_inserted += 1
                
                conn.commit()
        
        logger.info(f"Ingested {rows_inserted} rows from {file_path.name}")
        return rows_inserted
        
    except Exception as e:
        logger.error(f"Failed to ingest {file_path}: {e}")
        return 0


def standardize_sandbox(
    db: DatabaseManager,
    config: Dict,
    session_id: str
) -> int:
    """
    Standardize sandbox raw data using the mapping config.
    Returns number of rows standardized.
    """
    column_mapping = config.get('column_mapping', {})
    defaults = config.get('defaults', {})
    date_formats = config.get('date_formats', ['%Y-%m-%d', '%d/%m/%Y'])
    
    # Get raw rows for this session
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT raw_id, raw_data, reporting_country, direction, raw_file_name
                FROM tmp_stg_shipments_raw
                WHERE validation_session_id = %s
            """, (session_id,))
            raw_rows = cursor.fetchall()
    
    if not raw_rows:
        logger.warning("No raw rows to standardize")
        return 0
    
    rows_standardized = 0
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            for raw_id, raw_data, country, direction, source_file in raw_rows:
                data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)
                
                # Apply column mapping
                std_row = {
                    'raw_id': raw_id,
                    'reporting_country': country,
                    'direction': direction,
                    'source_file': source_file,
                    'validation_session_id': session_id,
                }
                
                # Map columns
                for std_field, raw_field in column_mapping.items():
                    if raw_field in data:
                        std_row[std_field] = data[raw_field]
                
                # Apply defaults
                for key, val in defaults.items():
                    if key not in std_row or std_row.get(key) is None:
                        std_row[key] = val
                
                # Parse dates and derive year/month
                shipment_date = None
                for date_field in ['import_date_raw', 'export_date_raw', 'shipment_date']:
                    if std_row.get(date_field):
                        shipment_date = parse_date(std_row[date_field], date_formats)
                        if shipment_date:
                            break
                
                if shipment_date:
                    std_row['shipment_date'] = shipment_date.strftime('%Y-%m-%d')
                    std_row['year'] = shipment_date.year
                    std_row['month'] = shipment_date.month
                    if direction == 'IMPORT':
                        std_row['import_date'] = shipment_date.strftime('%Y-%m-%d')
                    else:
                        std_row['export_date'] = shipment_date.strftime('%Y-%m-%d')
                
                # Normalize HS code
                hs_raw = std_row.get('hs_code_raw', '')
                if hs_raw:
                    hs_clean = re.sub(r'[^0-9]', '', str(hs_raw))
                    std_row['hs_code_6'] = hs_clean[:6] if len(hs_clean) >= 6 else hs_clean
                
                # Parse numeric values
                for num_field in ['qty_raw', 'value_raw', 'fob_usd', 'cif_usd']:
                    if std_row.get(num_field):
                        std_row[num_field] = parse_numeric(std_row[num_field])
                
                # Insert into sandbox standardized table
                cursor.execute("""
                    INSERT INTO tmp_stg_shipments_standardized (
                        raw_id, buyer_name_raw, supplier_name_raw,
                        hs_code_raw, hs_code_6, goods_description,
                        origin_country, origin_country_raw,
                        destination_country, destination_country_raw,
                        reporting_country, export_date, import_date,
                        shipment_date, year, month,
                        qty_raw, qty_unit_raw, value_raw, fob_usd, cif_usd,
                        source_file, direction, validation_session_id
                    ) VALUES (
                        %(raw_id)s, %(buyer_name_raw)s, %(supplier_name_raw)s,
                        %(hs_code_raw)s, %(hs_code_6)s, %(goods_description)s,
                        %(origin_country)s, %(origin_country_raw)s,
                        %(destination_country)s, %(destination_country_raw)s,
                        %(reporting_country)s, %(export_date)s, %(import_date)s,
                        %(shipment_date)s, %(year)s, %(month)s,
                        %(qty_raw)s, %(qty_unit_raw)s, %(value_raw)s, %(fob_usd)s, %(cif_usd)s,
                        %(source_file)s, %(direction)s, %(validation_session_id)s
                    )
                """, {
                    'raw_id': std_row.get('raw_id'),
                    'buyer_name_raw': std_row.get('buyer_name_raw'),
                    'supplier_name_raw': std_row.get('supplier_name_raw'),
                    'hs_code_raw': std_row.get('hs_code_raw'),
                    'hs_code_6': std_row.get('hs_code_6'),
                    'goods_description': std_row.get('goods_description'),
                    'origin_country': std_row.get('origin_country'),
                    'origin_country_raw': std_row.get('origin_country_raw'),
                    'destination_country': std_row.get('destination_country'),
                    'destination_country_raw': std_row.get('destination_country_raw'),
                    'reporting_country': std_row.get('reporting_country'),
                    'export_date': std_row.get('export_date'),
                    'import_date': std_row.get('import_date'),
                    'shipment_date': std_row.get('shipment_date'),
                    'year': std_row.get('year'),
                    'month': std_row.get('month'),
                    'qty_raw': std_row.get('qty_raw'),
                    'qty_unit_raw': std_row.get('qty_unit_raw'),
                    'value_raw': std_row.get('value_raw'),
                    'fob_usd': std_row.get('fob_usd'),
                    'cif_usd': std_row.get('cif_usd'),
                    'source_file': std_row.get('source_file'),
                    'direction': std_row.get('direction'),
                    'validation_session_id': session_id,
                })
                rows_standardized += 1
            
            conn.commit()
    
    logger.info(f"Standardized {rows_standardized} rows")
    return rows_standardized


def parse_date(value: Any, formats: List[str]) -> Optional[datetime]:
    """Try to parse a date value using multiple formats."""
    if value is None:
        return None
    
    # Already a datetime
    if isinstance(value, datetime):
        return value
    
    # Handle pandas Timestamp
    if hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime()
    
    # Try string parsing
    str_val = str(value).strip()
    for fmt in formats:
        try:
            return datetime.strptime(str_val, fmt)
        except (ValueError, TypeError):
            continue
    
    # Try ISO format
    try:
        return datetime.fromisoformat(str_val.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        pass
    
    return None


def parse_numeric(value: Any) -> Optional[float]:
    """Parse a numeric value."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # Remove currency symbols and commas
        clean = re.sub(r'[,$€£¥]', '', str(value))
        return float(clean)
    except (ValueError, TypeError):
        return None


# ============================================================================
# DATA QUALITY CHECKS
# ============================================================================

def run_dq_checks(db: DatabaseManager, session_id: str) -> Dict:
    """Run data quality checks on sandbox standardized data."""
    
    checks = {}
    
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            # Total rows
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
            """, (session_id,))
            total = cursor.fetchone()[0]
            checks['total_rows'] = total
            
            if total == 0:
                return checks
            
            # Valid date percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND shipment_date IS NOT NULL
            """, (session_id,))
            valid_date = cursor.fetchone()[0]
            checks['pct_valid_date'] = (valid_date / total) * 100
            
            # Valid HS code percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND hs_code_6 IS NOT NULL AND LENGTH(hs_code_6) >= 4
            """, (session_id,))
            valid_hs = cursor.fetchone()[0]
            checks['pct_valid_hs_code'] = (valid_hs / total) * 100
            
            # Valid quantity percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND qty_raw IS NOT NULL
            """, (session_id,))
            valid_qty = cursor.fetchone()[0]
            checks['pct_valid_quantity'] = (valid_qty / total) * 100
            
            # Valid value percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND (value_raw IS NOT NULL OR fob_usd IS NOT NULL OR cif_usd IS NOT NULL)
            """, (session_id,))
            valid_val = cursor.fetchone()[0]
            checks['pct_valid_value'] = (valid_val / total) * 100
            
            # Valid buyer percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND buyer_name_raw IS NOT NULL AND LENGTH(TRIM(buyer_name_raw)) > 0
            """, (session_id,))
            valid_buyer = cursor.fetchone()[0]
            checks['pct_valid_buyer'] = (valid_buyer / total) * 100
            
            # Valid supplier percentage
            cursor.execute("""
                SELECT COUNT(*) FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                AND supplier_name_raw IS NOT NULL AND LENGTH(TRIM(supplier_name_raw)) > 0
            """, (session_id,))
            valid_supplier = cursor.fetchone()[0]
            checks['pct_valid_supplier'] = (valid_supplier / total) * 100
            
            # Date range
            cursor.execute("""
                SELECT MIN(shipment_date), MAX(shipment_date)
                FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s AND shipment_date IS NOT NULL
            """, (session_id,))
            date_range = cursor.fetchone()
            checks['min_date'] = str(date_range[0]) if date_range[0] else None
            checks['max_date'] = str(date_range[1]) if date_range[1] else None
            
            # Sample rows
            cursor.execute("""
                SELECT shipment_date, hs_code_6, qty_raw, value_raw, buyer_name_raw, supplier_name_raw
                FROM tmp_stg_shipments_standardized
                WHERE validation_session_id = %s
                LIMIT 5
            """, (session_id,))
            samples = cursor.fetchall()
            checks['sample_rows'] = [
                {
                    'date': str(r[0]) if r[0] else None,
                    'hs_code': r[1],
                    'qty': str(r[2]) if r[2] else None,
                    'value': str(r[3]) if r[3] else None,
                    'buyer': r[4][:50] if r[4] else None,
                    'supplier': r[5][:50] if r[5] else None,
                }
                for r in samples
            ]
    
    return checks


# ============================================================================
# REGISTRY OPERATIONS
# ============================================================================

def get_mapping_info(db: DatabaseManager, country: str, direction: str, source_format: str) -> Optional[Dict]:
    """Get mapping info from registry."""
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT mapping_id, config_key, yaml_path, status, sample_file_path
                FROM mapping_registry
                WHERE UPPER(reporting_country) = UPPER(%s)
                AND UPPER(direction) = UPPER(%s)
                AND UPPER(source_format) = UPPER(%s)
            """, (country, direction, source_format))
            row = cursor.fetchone()
            
            if row:
                return {
                    'mapping_id': row[0],
                    'config_key': row[1],
                    'yaml_path': row[2],
                    'status': row[3],
                    'sample_file_path': row[4],
                }
    return None


def update_mapping_verified(db: DatabaseManager, mapping_id: int, row_count: int, date_coverage: str):
    """Update mapping status to VERIFIED."""
    with db.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE mapping_registry
                SET status = 'VERIFIED',
                    last_verified_at = NOW(),
                    verified_row_count = %s,
                    verified_date_coverage = %s,
                    updated_at = NOW()
                WHERE mapping_id = %s
            """, (row_count, date_coverage, mapping_id))
            conn.commit()
    logger.info(f"Updated mapping {mapping_id} to VERIFIED")


# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_validation_report(result: ValidationResult) -> str:
    """Generate a markdown validation report."""
    
    status_emoji = "✅" if result.success else "❌"
    
    report = f"""# {result.country} {result.direction} {result.source_format} Validation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Config Key:** `{result.config_key}`  
**Session ID:** `{result.session_id}`  
**Status:** {status_emoji} {'PASSED' if result.success else 'FAILED'}

## Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total Raw Rows | {result.total_raw_rows} | > 0 | {'✅' if result.total_raw_rows > 0 else '❌'} |
| Total Standardized Rows | {result.total_std_rows} | > 0 | {'✅' if result.total_std_rows > 0 else '❌'} |
| Valid Date % | {result.pct_valid_date:.1f}% | ≥ 90% | {'✅' if result.pct_valid_date >= 90 else '❌'} |
| Valid HS Code % | {result.pct_valid_hs_code:.1f}% | ≥ 90% | {'✅' if result.pct_valid_hs_code >= 90 else '❌'} |
| Valid Quantity % | {result.pct_valid_quantity:.1f}% | ≥ 50% | {'✅' if result.pct_valid_quantity >= 50 else '⚠️'} |
| Valid Value % | {result.pct_valid_value:.1f}% | ≥ 50% | {'✅' if result.pct_valid_value >= 50 else '⚠️'} |
| Valid Buyer % | {result.pct_valid_buyer:.1f}% | ≥ 50% | {'✅' if result.pct_valid_buyer >= 50 else '⚠️'} |
| Valid Supplier % | {result.pct_valid_supplier:.1f}% | ≥ 50% | {'✅' if result.pct_valid_supplier >= 50 else '⚠️'} |

## Date Coverage

- **Min Date:** {result.min_date or 'N/A'}
- **Max Date:** {result.max_date or 'N/A'}

## Sample Rows

| Date | HS Code | Quantity | Value | Buyer | Supplier |
|------|---------|----------|-------|-------|----------|
"""
    
    for row in result.sample_rows[:5]:
        report += f"| {row.get('date', 'N/A')} | {row.get('hs_code', 'N/A')} | {row.get('qty', 'N/A')} | {row.get('value', 'N/A')} | {row.get('buyer', 'N/A')[:30] if row.get('buyer') else 'N/A'} | {row.get('supplier', 'N/A')[:30] if row.get('supplier') else 'N/A'} |\n"
    
    if result.errors:
        report += "\n## Errors\n\n"
        for err in result.errors:
            report += f"- ❌ {err}\n"
    
    if result.warnings:
        report += "\n## Warnings\n\n"
        for warn in result.warnings:
            report += f"- ⚠️ {warn}\n"
    
    report += f"""
## Next Steps

"""
    if result.success:
        report += """1. Review the sample rows above
2. If satisfactory, run: `UPDATE mapping_registry SET status = 'LIVE' WHERE config_key = '""" + result.config_key + """'`
3. Or use the Admin UI to promote to LIVE
"""
    else:
        report += """1. Review the errors above
2. Fix the YAML mapping config at `config/""" + result.config_key + """.yml`
3. Re-run validation: `python scripts/validate_country_mapping.py --country """ + result.country + """ --direction """ + result.direction + """ --format """ + result.source_format + """`
"""
    
    return report


def save_validation_report(result: ValidationResult, docs_dir: Path = Path("docs/validation")):
    """Save validation report to markdown file."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{result.country}_{result.direction}_{result.source_format}_VALIDATION.md"
    report_path = docs_dir / filename
    
    report = generate_validation_report(result)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Saved validation report: {report_path}")
    return report_path


# ============================================================================
# MAIN VALIDATION FUNCTION
# ============================================================================

def validate_country_mapping(
    country: str,
    direction: str,
    source_format: str,
    dry_run: bool = False,
    max_rows: int = 500
) -> ValidationResult:
    """
    Main validation function.
    
    Args:
        country: Country code (e.g., 'BRAZIL')
        direction: 'IMPORT' or 'EXPORT'
        source_format: 'FULL' or 'SHORT'
        dry_run: If True, don't update mapping_registry
        max_rows: Maximum rows to validate
    
    Returns:
        ValidationResult object
    """
    session_id = str(uuid.uuid4())
    config_key = f"{country.lower().replace(' ', '_')}_{direction.lower()}_{source_format.lower()}"
    
    result = ValidationResult(
        success=False,
        country=country.upper(),
        direction=direction.upper(),
        source_format=source_format.upper(),
        config_key=config_key,
        session_id=session_id,
    )
    
    db = DatabaseManager('config/db_config.yml')
    
    try:
        # Step 1: Get mapping info from registry
        logger.info(f"Looking up mapping: {country} {direction} {source_format}")
        mapping = get_mapping_info(db, country, direction, source_format)
        
        if not mapping:
            result.errors.append(f"Mapping not found in registry: {config_key}")
            return result
        
        result.config_key = mapping['config_key']
        
        # Step 2: Load YAML config
        yaml_path = Path(mapping['yaml_path'])
        if not yaml_path.exists():
            result.errors.append(f"Config file not found: {yaml_path}")
            return result
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        header_row = config.get('header_row', 1)
        
        # Step 3: Find sample file
        sample_file = None
        if mapping['sample_file_path']:
            sample_file = Path(mapping['sample_file_path'])
        
        if not sample_file or not sample_file.exists():
            # Try to find in reference folder
            ref_dir = Path("data/reference/port_real")
            for pattern in [f"*{country}*{direction}*{source_format[0]}*.xlsx", f"*{country}*{direction}*.xlsx"]:
                matches = list(ref_dir.glob(pattern))
                if matches:
                    sample_file = matches[0]
                    break
        
        if not sample_file or not sample_file.exists():
            result.errors.append(f"No sample file found for {country} {direction} {source_format}")
            return result
        
        logger.info(f"Using sample file: {sample_file}")
        
        # Step 4: Clear sandbox
        clear_sandbox_session(db, session_id)
        
        # Step 5: Ingest to sandbox
        result.total_raw_rows = ingest_to_sandbox(
            db, sample_file, country.upper(), direction.upper(),
            source_format.upper(), session_id, header_row, max_rows
        )
        
        if result.total_raw_rows == 0:
            result.errors.append("No rows ingested from sample file")
            return result
        
        # Step 6: Standardize in sandbox
        result.total_std_rows = standardize_sandbox(db, config, session_id)
        
        if result.total_std_rows == 0:
            result.errors.append("No rows standardized - check column mappings")
            return result
        
        # Step 7: Run DQ checks
        dq_results = run_dq_checks(db, session_id)
        
        result.pct_valid_date = dq_results.get('pct_valid_date', 0)
        result.pct_valid_hs_code = dq_results.get('pct_valid_hs_code', 0)
        result.pct_valid_quantity = dq_results.get('pct_valid_quantity', 0)
        result.pct_valid_value = dq_results.get('pct_valid_value', 0)
        result.pct_valid_buyer = dq_results.get('pct_valid_buyer', 0)
        result.pct_valid_supplier = dq_results.get('pct_valid_supplier', 0)
        result.min_date = dq_results.get('min_date')
        result.max_date = dq_results.get('max_date')
        result.sample_rows = dq_results.get('sample_rows', [])
        
        # Step 8: Check thresholds
        if result.pct_valid_date < 90:
            result.errors.append(f"Date validity {result.pct_valid_date:.1f}% < 90% threshold")
        
        if result.pct_valid_hs_code < 90:
            result.errors.append(f"HS code validity {result.pct_valid_hs_code:.1f}% < 90% threshold")
        
        if result.pct_valid_quantity < 50:
            result.warnings.append(f"Quantity validity {result.pct_valid_quantity:.1f}% < 50%")
        
        if result.pct_valid_value < 50:
            result.warnings.append(f"Value validity {result.pct_valid_value:.1f}% < 50%")
        
        # Step 9: Determine success
        result.success = result.passed_checks()
        
        # Step 10: Update registry if successful and not dry run
        if result.success and not dry_run:
            date_coverage = f"{result.min_date} to {result.max_date}" if result.min_date else None
            update_mapping_verified(db, mapping['mapping_id'], result.total_std_rows, date_coverage)
        
        # Step 11: Clean up sandbox
        clear_sandbox_session(db, session_id)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        result.errors.append(str(e))
        # Clean up on error
        try:
            clear_sandbox_session(db, session_id)
        except:
            pass
    
    return result


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Validate a country mapping in sandbox mode"
    )
    parser.add_argument('--country', required=True, help='Country name (e.g., BRAZIL)')
    parser.add_argument('--direction', required=True, choices=['IMPORT', 'EXPORT', 'import', 'export'])
    parser.add_argument('--format', required=True, choices=['FULL', 'SHORT', 'full', 'short'], dest='source_format')
    parser.add_argument('--dry-run', action='store_true', help='Do not update registry')
    parser.add_argument('--max-rows', type=int, default=500, help='Max rows to validate')
    parser.add_argument('--no-report', action='store_true', help='Do not save markdown report')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  EPIC 10: Country Mapping Validator")
    print("=" * 60)
    print()
    print(f"  Country:  {args.country.upper()}")
    print(f"  Direction: {args.direction.upper()}")
    print(f"  Format:   {args.source_format.upper()}")
    print(f"  Dry Run:  {args.dry_run}")
    print()
    
    # Run validation
    result = validate_country_mapping(
        args.country,
        args.direction.upper(),
        args.source_format.upper(),
        args.dry_run,
        args.max_rows
    )
    
    # Print results
    print("=" * 60)
    if result.success:
        print("  ✅ VALIDATION PASSED")
    else:
        print("  ❌ VALIDATION FAILED")
    print("=" * 60)
    print()
    print(f"  Raw Rows:       {result.total_raw_rows}")
    print(f"  Std Rows:       {result.total_std_rows}")
    print(f"  Valid Date %:   {result.pct_valid_date:.1f}%")
    print(f"  Valid HS %:     {result.pct_valid_hs_code:.1f}%")
    print(f"  Valid Qty %:    {result.pct_valid_quantity:.1f}%")
    print(f"  Valid Value %:  {result.pct_valid_value:.1f}%")
    print(f"  Date Range:     {result.min_date} to {result.max_date}")
    print()
    
    if result.errors:
        print("  Errors:")
        for err in result.errors:
            print(f"    ❌ {err}")
        print()
    
    if result.warnings:
        print("  Warnings:")
        for warn in result.warnings:
            print(f"    ⚠️ {warn}")
        print()
    
    # Save report
    if not args.no_report:
        report_path = save_validation_report(result)
        print(f"  Report saved: {report_path}")
    
    print()
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
