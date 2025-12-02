#!/usr/bin/env python3
"""
Port Format Discovery Script
============================
Scans all Excel files in data/reference/port_real/ and:
1. Automatically discovers file formats
2. Generates YAML mapping config skeletons in config/
3. Generates country-wise format documentation in docs/

IMPORTANT: This script is READ-ONLY for ETL tables.
It only reads Excel files and writes YAML/Markdown files.
It does NOT write to: stg_shipments_raw, stg_shipments_standardized, global_trades_ledger

Usage:
    python scripts/discover_port_formats.py
"""

import re
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict

import pandas as pd
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

# Common date column name patterns
DATE_COLUMN_PATTERNS = [
    r'.*DATE.*', r'.*_DT$', r'.*_DATE$',
    r'EXPORT.*', r'IMPORT.*', r'SHIP.*', r'INVOICE.*',
    r'IMP_DATE', r'EXP_DATE', r'BILL.*DATE', r'DECL.*DATE',
]

# Common HS code column name patterns  
HS_CODE_PATTERNS = [
    r'HS.*CODE.*', r'HS_CODE.*', r'HSCODE.*', r'TARIFF.*', 
    r'.*HARMONIZED.*', r'PRODUCT.*CODE', r'COMMODITY.*CODE',
]

# Common value/amount column patterns
VALUE_PATTERNS = [
    r'.*VALUE.*', r'.*USD.*', r'FOB.*', r'CIF.*', r'.*AMOUNT.*',
    r'TOTAL.*', r'CUSTOMS.*VALUE', r'.*PRICE.*',
]

# Common quantity column patterns
QUANTITY_PATTERNS = [
    r'.*QTY.*', r'.*QUANTITY.*', r'.*WEIGHT.*', r'.*KG.*',
    r'.*VOLUME.*', r'NET.*', r'GROSS.*',
]

# Common unit column patterns
UNIT_PATTERNS = [
    r'.*UNIT.*', r'UOM', r'.*MEASURE.*',
]

# Common buyer/importer column patterns
BUYER_PATTERNS = [
    r'.*IMPORTER.*', r'.*BUYER.*', r'.*CONSIGNEE.*', 
    r'.*RECEIVER.*', r'NOTIFY.*PARTY',
]

# Common supplier/exporter column patterns
SUPPLIER_PATTERNS = [
    r'.*EXPORTER.*', r'.*SUPPLIER.*', r'.*SHIPPER.*',
    r'.*SELLER.*', r'.*SENDER.*',
]

# Common origin country patterns
ORIGIN_PATTERNS = [
    r'.*ORIGIN.*', r'.*SOURCE.*COUNTRY', r'COUNTRY.*ORIGIN',
    r'FROM.*COUNTRY', r'EXPORT.*COUNTRY',
]

# Common destination country patterns  
DESTINATION_PATTERNS = [
    r'.*DESTINATION.*', r'.*DEST.*COUNTRY', r'TO.*COUNTRY',
    r'IMPORT.*COUNTRY', r'.*PORT.*DISCHARGE',
]

# Filename parsing patterns
FILENAME_PATTERNS = [
    # "{Country} Import F.xlsx" or "{Country} Export S.xlsx"
    r'^(?P<country>[\w\s]+?)\s+(?P<direction>Import|Export)\s+(?P<format>F|S|Full|Short)(?:\s+\([\d]+\))?\.xlsx$',
    # "{Country} Import Full.xlsx"
    r'^(?P<country>[\w\s]+?)\s+(?P<direction>Import|Export)\s+(?P<format>Full|Short)(?:\s+\([\d]+\))?\.xlsx$',
    # "{Country} BL Import F.xlsx" (Bill of Lading format)
    r'^(?P<country>[\w\s]+?)\s+BL\s+(?P<direction>Import|Export)\s+(?P<format>F|S)(?:\s+\([\d]+\))?\.xlsx$',
    # "output_excel.xlsx" or other misc files
    r'^(?P<misc>.+)\.xlsx$',
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """
    Parse metadata from filename.
    
    Returns dict with: country, direction, source_format
    Or None if parsing fails.
    """
    for pattern in FILENAME_PATTERNS:
        match = re.match(pattern, filename, re.IGNORECASE)
        if match:
            groups = match.groupdict()
            
            # Handle misc files
            if 'misc' in groups:
                logger.warning(f"Cannot parse metadata from: {filename}")
                return None
            
            country = groups.get('country', '').strip().upper()
            direction = groups.get('direction', '').upper()
            fmt = groups.get('format', 'FULL').upper()
            
            # Normalize format
            if fmt in ['F', 'FULL']:
                source_format = 'FULL'
            elif fmt in ['S', 'SHORT']:
                source_format = 'SHORT'
            else:
                source_format = fmt
            
            # Normalize country names with spaces
            country = country.replace(' ', '_').replace('-', '_')
            # Handle special cases
            country_mapping = {
                'IVORY_COAST': 'IVORY_COAST',
                'SOUTH_SUDAN': 'SOUTH_SUDAN',
                'DOMINICAN_REPUBLIC': 'DOMINICAN_REPUBLIC',
                'SRI_LANKA': 'SRILANKA',
                'SRILANKA': 'SRILANKA',
                'COSTARICA': 'COSTA_RICA',
                'SAO_TOME': 'SAO_TOME',
                'EQUADOR': 'ECUADOR',
            }
            country = country_mapping.get(country, country)
            
            return {
                'country': country,
                'direction': direction,
                'source_format': source_format,
            }
    
    logger.warning(f"No pattern matched for: {filename}")
    return None


def detect_header_row(df_raw: pd.DataFrame, max_rows: int = 10) -> int:
    """
    Detect which row contains the header.
    Returns 0-indexed row number.
    
    Heuristics:
    - Look for rows with mostly string values
    - Look for common header keywords
    """
    header_keywords = ['date', 'code', 'value', 'name', 'country', 'quantity', 'unit', 'port', 'hs', 'description']
    
    best_row = 0
    best_score = 0
    
    for i in range(min(max_rows, len(df_raw))):
        row = df_raw.iloc[i]
        score = 0
        
        # Count string values
        for val in row:
            if isinstance(val, str):
                val_lower = val.lower()
                # Check for header keywords
                for keyword in header_keywords:
                    if keyword in val_lower:
                        score += 2
                # Bonus for all-caps or title-case strings
                if val.isupper() or val.istitle():
                    score += 1
        
        if score > best_score:
            best_score = score
            best_row = i
    
    return best_row


def match_column_pattern(column_name: str, patterns: List[str]) -> bool:
    """Check if column name matches any of the patterns."""
    col_upper = column_name.upper()
    for pattern in patterns:
        if re.match(pattern, col_upper, re.IGNORECASE):
            return True
    return False


def detect_column_types(columns: List[str]) -> Dict[str, List[str]]:
    """
    Detect column types based on naming patterns.
    
    Returns dict mapping column type to list of matching column names.
    """
    detected = {
        'date_columns': [],
        'hs_code_columns': [],
        'value_columns': [],
        'quantity_columns': [],
        'unit_columns': [],
        'buyer_columns': [],
        'supplier_columns': [],
        'origin_columns': [],
        'destination_columns': [],
        'other_columns': [],
    }
    
    for col in columns:
        matched = False
        
        if match_column_pattern(col, DATE_COLUMN_PATTERNS):
            detected['date_columns'].append(col)
            matched = True
        if match_column_pattern(col, HS_CODE_PATTERNS):
            detected['hs_code_columns'].append(col)
            matched = True
        if match_column_pattern(col, VALUE_PATTERNS):
            detected['value_columns'].append(col)
            matched = True
        if match_column_pattern(col, QUANTITY_PATTERNS):
            detected['quantity_columns'].append(col)
            matched = True
        if match_column_pattern(col, UNIT_PATTERNS):
            detected['unit_columns'].append(col)
            matched = True
        if match_column_pattern(col, BUYER_PATTERNS):
            detected['buyer_columns'].append(col)
            matched = True
        if match_column_pattern(col, SUPPLIER_PATTERNS):
            detected['supplier_columns'].append(col)
            matched = True
        if match_column_pattern(col, ORIGIN_PATTERNS):
            detected['origin_columns'].append(col)
            matched = True
        if match_column_pattern(col, DESTINATION_PATTERNS):
            detected['destination_columns'].append(col)
            matched = True
        
        if not matched:
            detected['other_columns'].append(col)
    
    return detected


def analyze_excel_file(file_path: Path) -> Dict[str, Any]:
    """
    Analyze an Excel file and extract metadata.
    
    Returns dict with:
    - columns: list of column names
    - detected_types: column type detection results
    - row_count: number of data rows
    - header_row: detected header row (1-indexed)
    - sample_data: first few rows of data
    """
    result = {
        'file_path': str(file_path),
        'file_name': file_path.name,
        'columns': [],
        'detected_types': {},
        'row_count': 0,
        'header_row': 1,
        'sample_data': [],
        'error': None,
    }
    
    try:
        # Read raw to detect header
        df_raw = pd.read_excel(file_path, header=None, nrows=15)
        header_row_idx = detect_header_row(df_raw)
        
        # Re-read with detected header
        df = pd.read_excel(file_path, header=header_row_idx, nrows=100)
        
        # Clean column names
        columns = [str(col).strip() for col in df.columns.tolist()]
        
        result['columns'] = columns
        result['header_row'] = header_row_idx + 1  # Convert to 1-indexed
        result['detected_types'] = detect_column_types(columns)
        result['row_count'] = len(df)
        
        # Get sample data (first 3 rows)
        if len(df) > 0:
            result['sample_data'] = df.head(3).to_dict(orient='records')
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error analyzing {file_path.name}: {e}")
    
    return result


def generate_yaml_config(
    country: str,
    direction: str,
    source_format: str,
    analysis: Dict[str, Any]
) -> str:
    """Generate YAML config skeleton for a file format."""
    
    detected = analysis.get('detected_types', {})
    columns = analysis.get('columns', [])
    header_row = analysis.get('header_row', 1)
    
    # Pick primary columns (first match for each type)
    date_col = detected.get('date_columns', ['TODO_DATE_COLUMN'])[0] if detected.get('date_columns') else 'TODO_DATE_COLUMN'
    hs_col = detected.get('hs_code_columns', ['TODO_HS_CODE'])[0] if detected.get('hs_code_columns') else 'TODO_HS_CODE'
    value_col = detected.get('value_columns', ['TODO_VALUE'])[0] if detected.get('value_columns') else 'TODO_VALUE'
    qty_col = detected.get('quantity_columns', ['TODO_QUANTITY'])[0] if detected.get('quantity_columns') else 'TODO_QUANTITY'
    unit_col = detected.get('unit_columns', ['TODO_UNIT'])[0] if detected.get('unit_columns') else 'TODO_UNIT'
    buyer_col = detected.get('buyer_columns', ['TODO_BUYER'])[0] if detected.get('buyer_columns') else 'TODO_BUYER'
    supplier_col = detected.get('supplier_columns', ['TODO_SUPPLIER'])[0] if detected.get('supplier_columns') else 'TODO_SUPPLIER'
    origin_col = detected.get('origin_columns', ['TODO_ORIGIN'])[0] if detected.get('origin_columns') else 'TODO_ORIGIN'
    dest_col = detected.get('destination_columns', ['TODO_DESTINATION'])[0] if detected.get('destination_columns') else 'TODO_DESTINATION'
    
    # Determine date field name based on direction
    date_field = 'import_date_raw' if direction == 'IMPORT' else 'export_date_raw'
    
    config = {
        'reporting_country': country.replace('_', ' ').upper(),
        'direction': direction,
        'source_format': source_format,
        'record_grain': 'LINE_ITEM',
        'header_row': header_row,
        'data_start_row': header_row + 1,
        'column_mapping': {
            'buyer_name_raw': buyer_col,
            'supplier_name_raw': supplier_col,
            'hs_code_raw': hs_col,
            date_field: date_col,
            'qty_raw': qty_col,
            'qty_unit_raw': unit_col,
            'value_raw': value_col,
            'origin_country_raw': origin_col,
            'destination_country_raw': dest_col,
        },
        'defaults': {
            'reporting_country': country.replace('_', ' ').upper(),
            'direction': direction,
        },
        'date_formats': [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
        ],
        'quality_rules': {
            'require_hs_code': True,
            'require_importer': True,
            'require_value_usd': False,
            'require_origin_country': False,
            'require_quantity': False,
        },
        '_metadata': {
            'auto_generated': True,
            'generated_at': datetime.now().isoformat(),
            'source_file': analysis.get('file_name', 'unknown'),
            'detected_columns': columns,
            'needs_review': True,
        }
    }
    
    # Add defaults based on direction
    if direction == 'IMPORT':
        config['defaults']['destination_country_raw'] = country.replace('_', ' ').upper()
    else:
        config['defaults']['origin_country_raw'] = country.replace('_', ' ').upper()
    
    return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)


def generate_country_doc(
    country: str,
    files_data: List[Dict[str, Any]]
) -> str:
    """Generate Markdown documentation for a country's formats."""
    
    doc = f"""# {country.replace('_', ' ').title()} Port Data Formats

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This document describes the port data file formats available for {country.replace('_', ' ').title()}.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
"""
    
    for fd in files_data:
        analysis = fd.get('analysis', {})
        meta = fd.get('metadata', {})
        detected = analysis.get('detected_types', {})
        
        direction = meta.get('direction', 'N/A')
        fmt = meta.get('source_format', 'N/A')
        rows = analysis.get('row_count', 'N/A')
        header = analysis.get('header_row', 'N/A')
        
        date_col = detected.get('date_columns', ['N/A'])[0] if detected.get('date_columns') else 'N/A'
        hs_col = detected.get('hs_code_columns', ['N/A'])[0] if detected.get('hs_code_columns') else 'N/A'
        val_col = detected.get('value_columns', ['N/A'])[0] if detected.get('value_columns') else 'N/A'
        
        doc += f"| {fd.get('file_name', 'N/A')} | {direction} | {fmt} | {rows} | {header} | {date_col} | {hs_col} | {val_col} |\n"
    
    doc += "\n## Detailed Format Analysis\n\n"
    
    for fd in files_data:
        analysis = fd.get('analysis', {})
        meta = fd.get('metadata', {})
        detected = analysis.get('detected_types', {})
        
        doc += f"### {fd.get('file_name', 'Unknown File')}\n\n"
        doc += f"- **Direction:** {meta.get('direction', 'N/A')}\n"
        doc += f"- **Format:** {meta.get('source_format', 'N/A')}\n"
        doc += f"- **Header Row:** {analysis.get('header_row', 'N/A')}\n"
        doc += f"- **Sample Rows:** {analysis.get('row_count', 'N/A')}\n"
        
        if analysis.get('error'):
            doc += f"- **Error:** {analysis.get('error')}\n\n"
            continue
        
        doc += f"\n**Detected Column Types:**\n\n"
        
        if detected.get('date_columns'):
            doc += f"- 📅 Date: {', '.join(detected['date_columns'])}\n"
        else:
            doc += f"- 📅 Date: ⚠️ Not detected\n"
            
        if detected.get('hs_code_columns'):
            doc += f"- 📦 HS Code: {', '.join(detected['hs_code_columns'])}\n"
        else:
            doc += f"- 📦 HS Code: ⚠️ Not detected\n"
            
        if detected.get('value_columns'):
            doc += f"- 💰 Value: {', '.join(detected['value_columns'])}\n"
        else:
            doc += f"- 💰 Value: ⚠️ Not detected\n"
            
        if detected.get('quantity_columns'):
            doc += f"- 📊 Quantity: {', '.join(detected['quantity_columns'])}\n"
            
        if detected.get('buyer_columns'):
            doc += f"- 🏢 Buyer/Importer: {', '.join(detected['buyer_columns'])}\n"
            
        if detected.get('supplier_columns'):
            doc += f"- 🏭 Supplier/Exporter: {', '.join(detected['supplier_columns'])}\n"
        
        config_name = f"{meta.get('country', 'unknown').lower()}_{meta.get('direction', 'unknown').lower()}_{meta.get('source_format', 'full').lower()}.yml"
        doc += f"\n**Config File:** `config/{config_name}`\n\n"
        
        if detected.get('other_columns'):
            doc += f"<details>\n<summary>All Columns ({len(analysis.get('columns', []))} total)</summary>\n\n"
            doc += "```\n"
            for col in analysis.get('columns', []):
                doc += f"{col}\n"
            doc += "```\n</details>\n\n"
        
        doc += "---\n\n"
    
    return doc


# ============================================================================
# MAIN DISCOVERY FUNCTION
# ============================================================================

def discover_port_formats(
    data_dir: Path = Path("data/reference/port_real"),
    config_dir: Path = Path("config"),
    docs_dir: Path = Path("docs"),
    logs_dir: Path = Path("logs"),
) -> Dict[str, Any]:
    """
    Main discovery function.
    
    Scans all Excel files, analyzes them, and generates:
    - YAML config skeletons in config/
    - Country format docs in docs/
    - Error log in logs/
    
    Returns summary dict.
    """
    
    # Ensure directories exist
    config_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)
    
    # Find all Excel files
    excel_files = list(data_dir.glob("*.xlsx"))
    logger.info(f"Found {len(excel_files)} Excel files in {data_dir}")
    
    # Track results
    results = {
        'total_files': len(excel_files),
        'processed': 0,
        'errors': [],
        'configs_generated': [],
        'docs_generated': [],
        'by_country': defaultdict(list),
    }
    
    error_log = []
    
    # Process each file
    for file_path in excel_files:
        logger.info(f"Processing: {file_path.name}")
        
        # Parse filename metadata
        metadata = parse_filename(file_path.name)
        if not metadata:
            error_log.append({
                'file': file_path.name,
                'error': 'Could not parse filename',
                'context': 'filename_parsing',
            })
            continue
        
        # Analyze file structure
        analysis = analyze_excel_file(file_path)
        
        if analysis.get('error'):
            error_log.append({
                'file': file_path.name,
                'error': analysis['error'],
                'context': 'excel_analysis',
            })
        
        # Store results
        file_data = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'metadata': metadata,
            'analysis': analysis,
        }
        
        country = metadata['country']
        results['by_country'][country].append(file_data)
        results['processed'] += 1
    
    # Generate YAML configs for each unique format
    seen_configs = set()
    existing_configs = set(f.stem for f in config_dir.glob("*.yml"))
    
    for country, files_data in results['by_country'].items():
        for fd in files_data:
            meta = fd['metadata']
            analysis = fd['analysis']
            
            if analysis.get('error'):
                continue
            
            config_key = f"{meta['country'].lower()}_{meta['direction'].lower()}_{meta['source_format'].lower()}"
            
            # Skip if already generated this session or exists
            if config_key in seen_configs:
                continue
            if config_key in existing_configs:
                logger.info(f"Config already exists: {config_key}.yml - skipping")
                continue
            
            seen_configs.add(config_key)
            
            # Generate config
            yaml_content = generate_yaml_config(
                meta['country'],
                meta['direction'],
                meta['source_format'],
                analysis
            )
            
            config_path = config_dir / f"{config_key}.yml"
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(f"# Auto-generated config for {meta['country']} {meta['direction']} {meta['source_format']}\n")
                f.write(f"# Source: {fd['file_name']}\n")
                f.write(f"# REVIEW REQUIRED: Verify column mappings before use\n\n")
                f.write(yaml_content)
            
            results['configs_generated'].append(str(config_path))
            logger.info(f"Generated config: {config_path}")
    
    # Generate country docs
    for country, files_data in results['by_country'].items():
        doc_content = generate_country_doc(country, files_data)
        doc_path = docs_dir / f"{country}_FORMATS.md"
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        results['docs_generated'].append(str(doc_path))
        logger.info(f"Generated doc: {doc_path}")
    
    # Write error log
    results['errors'] = error_log
    if error_log:
        error_log_path = logs_dir / "discover_port_formats_errors.log"
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"Port Format Discovery Error Log\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"=" * 60 + "\n\n")
            for err in error_log:
                f.write(f"File: {err['file']}\n")
                f.write(f"Context: {err['context']}\n")
                f.write(f"Error: {err['error']}\n")
                f.write("-" * 40 + "\n")
        
        logger.info(f"Error log written to: {error_log_path}")
    
    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the discovery script."""
    
    print("=" * 70)
    print("  PORT FORMAT DISCOVERY SCRIPT")
    print("  Scanning Excel files in data/reference/port_real/")
    print("=" * 70)
    print()
    
    # Run discovery
    results = discover_port_formats()
    
    # Print summary
    print()
    print("=" * 70)
    print("  DISCOVERY COMPLETE")
    print("=" * 70)
    print()
    print(f"Total files found: {results['total_files']}")
    print(f"Files processed: {results['processed']}")
    print(f"Files with errors: {len(results['errors'])}")
    print()
    print(f"Countries discovered: {len(results['by_country'])}")
    for country, files in sorted(results['by_country'].items()):
        print(f"  - {country}: {len(files)} files")
    print()
    print(f"Config files generated: {len(results['configs_generated'])}")
    for cfg in results['configs_generated'][:5]:
        print(f"  - {cfg}")
    if len(results['configs_generated']) > 5:
        print(f"  ... and {len(results['configs_generated']) - 5} more")
    print()
    print(f"Documentation files generated: {len(results['docs_generated'])}")
    for doc in results['docs_generated'][:5]:
        print(f"  - {doc}")
    if len(results['docs_generated']) > 5:
        print(f"  ... and {len(results['docs_generated']) - 5} more")
    
    if results['errors']:
        print()
        print(f"Errors encountered: {len(results['errors'])}")
        print("See logs/discover_port_formats_errors.log for details")
    
    print()
    print("=" * 70)
    
    return results


if __name__ == "__main__":
    results = main()
    sys.exit(0 if len(results.get('errors', [])) < results.get('total_files', 0) else 1)
