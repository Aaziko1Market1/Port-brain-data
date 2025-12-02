"""
GTI-OS Data Platform - Standardization Engine (Phase 2)
Transforms raw shipment data into normalized, standardized records

Features:
- Country+direction-specific YAML mapping configs
- Column renaming and extraction
- HS code normalization (6-digit)
- Date parsing with multiple format support
- Unit conversions (weight, currency)
- Bulk insert into stg_shipments_standardized
"""

import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache

import polars as pl
from dateutil import parser as date_parser

from ..db_utils import DatabaseManager

logger = logging.getLogger(__name__)


# =====================================================================
# CONFIGURATION MANAGEMENT
# =====================================================================

@lru_cache(maxsize=50)
def load_mapping_config(
    reporting_country: str, 
    direction: str, 
    source_format: str = "FULL"
) -> Dict[str, Any]:
    """
    Load country+direction-specific mapping configuration
    
    Args:
        reporting_country: Country code (e.g., INDIA, KENYA)
        direction: EXPORT or IMPORT
        source_format: FULL or SHORT
    
    Returns:
        Mapping configuration dictionary
    
    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    # Try format-specific config first (e.g., kenya_import_full.yml)
    config_filename_full = f"{reporting_country.lower()}_{direction.lower()}_{source_format.lower()}.yml"
    config_path_full = Path("config") / config_filename_full
    
    if config_path_full.exists():
        with open(config_path_full, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded mapping config: {config_filename_full}")
        return config
    
    # Fall back to generic config (e.g., kenya_import.yml)
    config_filename = f"{reporting_country.lower()}_{direction.lower()}.yml"
    config_path = Path("config") / config_filename
    
    if not config_path.exists():
        logger.error(f"Mapping config not found: {config_path} or {config_path_full}")
        raise FileNotFoundError(
            f"Missing mapping config for {reporting_country} {direction} {source_format}. "
            f"Expected: {config_path_full} or {config_path}"
        )
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Loaded mapping config: {config_filename}")
    return config


# =====================================================================
# NORMALIZATION UTILITIES
# =====================================================================

def normalize_hs_code(hs_code_raw: Optional[str]) -> Optional[str]:
    """
    Extract first 6 digits from HS code
    
    Args:
        hs_code_raw: Raw HS code string
    
    Returns:
        6-digit HS code or None
    """
    if not hs_code_raw:
        return None
    
    # Extract only digits
    digits = re.sub(r'\D', '', str(hs_code_raw))
    
    if len(digits) >= 6:
        return digits[:6]
    elif len(digits) >= 2:
        # If less than 6 digits, pad with zeros
        return digits.ljust(6, '0')
    
    return None


def normalize_country(country_raw: Optional[str]) -> Optional[str]:
    """
    Normalize country names to standard format
    
    Args:
        country_raw: Raw country string
    
    Returns:
        Normalized country name (uppercase)
    """
    if not country_raw:
        return None
    
    country = str(country_raw).strip().upper()
    
    # Common mappings
    country_mapping = {
        'U.S.A.': 'USA',
        'U.S.A': 'USA',
        'UNITED STATES': 'USA',
        'UNITED STATES OF AMERICA': 'USA',
        'U.K.': 'UK',
        'UNITED KINGDOM': 'UK',
        'U.A.E.': 'UAE',
        'UNITED ARAB EMIRATES': 'UAE',
        'PEOPLES REPUBLIC OF CHINA': 'CHINA',
        "PEOPLE'S REPUBLIC OF CHINA": 'CHINA',
        'P.R. CHINA': 'CHINA',
    }
    
    return country_mapping.get(country, country)


def parse_date(date_raw: Optional[str]) -> Optional[datetime]:
    """
    Parse date string with multiple format support
    
    Args:
        date_raw: Raw date string
    
    Returns:
        Parsed datetime object or None
    """
    if not date_raw:
        return None
    
    # Handle numeric dates (Excel serial numbers)
    if isinstance(date_raw, (int, float)):
        try:
            # Excel epoch: January 1, 1900
            excel_epoch = datetime(1899, 12, 30)
            return excel_epoch + timedelta(days=int(date_raw))
        except:
            return None
    
    date_str = str(date_raw).strip()
    if not date_str or date_str.upper() in ['NULL', 'NA', 'N/A', '']:
        return None
    
    try:
        # Use dateutil parser for flexible parsing
        return date_parser.parse(date_str, dayfirst=False)
    except:
        logger.debug(f"Failed to parse date: {date_str}")
        return None


# =====================================================================
# UNIT CONVERSIONS
# =====================================================================

def convert_weight_to_kg(
    qty_raw: Optional[float], 
    qty_unit_raw: Optional[str],
    config_unit_conversions: Optional[Dict] = None
) -> Optional[float]:
    """
    Convert weight to kilograms using config-based or default conversions
    
    Args:
        qty_raw: Raw quantity value
        qty_unit_raw: Raw unit string
        config_unit_conversions: Unit conversion config from YAML
    
    Returns:
        Weight in kilograms or None
    """
    if qty_raw is None or qty_raw == 0:
        return None
    
    qty = float(qty_raw)
    unit = str(qty_unit_raw or 'KG').upper().strip()
    
    # Try config-based conversions first
    if config_unit_conversions and unit in config_unit_conversions:
        unit_config = config_unit_conversions[unit]
        if unit_config.get('is_weight', False):
            multiplier = unit_config.get('to_kg_multiplier', 1.0)
            return qty * multiplier
        else:
            # Non-weight unit, check if there's an estimate
            estimate = unit_config.get('estimate_kg_per_unit')
            if estimate:
                return qty * estimate
            return None
    
    # Default conversion factors to KG
    conversions = {
        'KG': 1.0,
        'KGM': 1.0,  # Kenya standard for kilograms
        'KGS': 1.0,
        'KILOGRAMS': 1.0,
        'MT': 1000.0,
        'TNE': 1000.0,  # Kenya standard for tonnes
        'METRIC TONS': 1000.0,
        'METRIC TON': 1000.0,
        'TON': 1000.0,
        'TONS': 1000.0,
        'LB': 0.453592,
        'LBS': 0.453592,
        'POUNDS': 0.453592,
        'G': 0.001,
        'GRM': 0.001,  # Kenya standard for grams
        'GRAMS': 0.001,
        'GRAM': 0.001,
    }
    
    if unit in conversions:
        return qty * conversions[unit]
    
    # Non-weight units return None
    return None


def convert_currency_to_usd(
    value_raw: Optional[float],
    currency: str,
    fx_rates: Optional[Dict[str, float]] = None
) -> Optional[float]:
    """
    Convert currency to USD
    
    Args:
        value_raw: Raw value
        currency: Currency code (INR, KES, USD, etc.)
        fx_rates: Optional FX rate dictionary
    
    Returns:
        Value in USD or None
    """
    if value_raw is None or value_raw == 0:
        return None
    
    value = float(value_raw)
    currency = currency.upper().strip()
    
    if currency == 'USD':
        return value
    
    # Use provided FX rates or defaults
    if fx_rates is None:
        # Default approximate FX rates (placeholder - should be from DB later)
        fx_rates = {
            'INR': 0.012,   # 1 INR ≈ 0.012 USD
            'KES': 0.0077,  # 1 KES ≈ 0.0077 USD
            'EUR': 1.10,    # 1 EUR ≈ 1.10 USD
            'GBP': 1.27,    # 1 GBP ≈ 1.27 USD
            'CNY': 0.14,    # 1 CNY ≈ 0.14 USD
            'AED': 0.27,    # 1 AED ≈ 0.27 USD
            'BDT': 0.0091,  # 1 BDT ≈ 0.0091 USD
        }
    
    rate = fx_rates.get(currency, 1.0)
    return value * rate


def estimate_teu(qty_kg: Optional[float]) -> Optional[float]:
    """
    Estimate TEU (Twenty-foot Equivalent Unit) from weight
    Simple heuristic: 1 TEU ≈ 20,000 kg capacity
    
    Args:
        qty_kg: Weight in kilograms
    
    Returns:
        Estimated TEU or None
    """
    if qty_kg is None or qty_kg == 0:
        return None
    
    # Simple estimation: 1 TEU can hold ~20,000 kg
    # This is a rough approximation
    teu = qty_kg / 20000.0
    
    # Round to 2 decimals
    return round(teu, 2)


# =====================================================================
# BATCH STANDARDIZATION
# =====================================================================

def standardize_batch(
    df_raw: pl.DataFrame,
    config: Dict[str, Any],
    reporting_country: str,
    direction: str,
    source_format: str
) -> pl.DataFrame:
    """
    Standardize a batch of raw shipment records
    
    Args:
        df_raw: Polars DataFrame with raw data
        config: Mapping configuration
        reporting_country: Country code
        direction: EXPORT or IMPORT
        source_format: FULL or SHORT
    
    Returns:
        Standardized Polars DataFrame
    """
    logger.info(f"Standardizing {len(df_raw)} rows for {reporting_country} {direction}")
    
    column_mapping = config.get('column_mapping', {})
    unit_conversions = config.get('unit_conversions', {})
    value_currency = config.get('value_currency', {})
    defaults = config.get('defaults', {})
    
    # Extract raw fields from raw_data JSON
    raw_data_cols = []
    
    # Build expressions to extract from raw_data JSONB column
    # For Polars, we need to handle struct/JSON columns
    
    standardized_data = {
        'raw_id': df_raw['raw_id'].to_list(),
        'source_file': df_raw['raw_file_name'].to_list(),
        'reporting_country': [reporting_country] * len(df_raw),
        'direction': [direction] * len(df_raw),
        'source_format': [source_format] * len(df_raw),
        'record_grain': df_raw['record_grain'].to_list(),
    }
    
    # Extract raw fields
    for std_field, raw_field in column_mapping.items():
        if raw_field:
            # Extract from raw_data JSONB
            values = []
            for row in df_raw.iter_rows(named=True):
                raw_data = row.get('raw_data', {})
                if isinstance(raw_data, str):
                    import json
                    try:
                        raw_data = json.loads(raw_data)
                    except:
                        raw_data = {}
                values.append(raw_data.get(raw_field))
            standardized_data[std_field] = values
        else:
            standardized_data[std_field] = [None] * len(df_raw)
    
    # Convert to DataFrame for easier manipulation
    import pandas as pd
    df_std = pd.DataFrame(standardized_data)
    
    # Apply normalizations
    logger.debug("Applying HS code normalization...")
    df_std['hs_code_6'] = df_std.get('hs_code_raw', pd.Series([None]*len(df_std))).apply(normalize_hs_code)
    
    # Country normalization
    logger.debug("Applying country normalization...")
    if 'origin_country_raw' in df_std.columns and df_std['origin_country_raw'].notna().any():
        df_std['origin_country'] = df_std['origin_country_raw'].apply(normalize_country)
        # Fill any NULL origin_country with default (e.g., for exports from reporting country)
        default_origin = defaults.get('origin_country_raw') or defaults.get('origin_country')
        if default_origin:
            df_std['origin_country'] = df_std['origin_country'].fillna(normalize_country(default_origin))
    else:
        # Use default origin country if no raw field available
        default_origin = defaults.get('origin_country_raw') or defaults.get('origin_country')
        df_std['origin_country'] = normalize_country(default_origin) if default_origin else None
    
    if 'destination_country_raw' in df_std.columns and df_std['destination_country_raw'].notna().any():
        df_std['destination_country'] = df_std['destination_country_raw'].apply(normalize_country)
        # Fill any NULL destination_country with default (e.g., for imports to reporting country)
        default_dest = defaults.get('destination_country_raw') or defaults.get('destination_country')
        if default_dest:
            df_std['destination_country'] = df_std['destination_country'].fillna(normalize_country(default_dest))
    else:
        # Use default destination country if no raw field available
        default_dest = defaults.get('destination_country_raw') or defaults.get('destination_country')
        df_std['destination_country'] = normalize_country(default_dest) if default_dest else None
    
    # Date parsing
    logger.debug("Parsing dates...")
    for date_field in ['export_date_raw', 'import_date_raw', 'shipment_date_raw']:
        if date_field in df_std.columns:
            output_field = date_field.replace('_raw', '')
            df_std[output_field] = df_std[date_field].apply(parse_date)
    
    # Derive year and month from best available date
    df_std['shipment_date'] = df_std.get('shipment_date', df_std.get('import_date', df_std.get('export_date')))
    df_std['year'] = df_std['shipment_date'].apply(lambda d: d.year if d else None)
    df_std['month'] = df_std['shipment_date'].apply(lambda d: d.month if d else None)
    
    # Unit conversions
    logger.debug("Converting units...")
    df_std['qty_kg'] = df_std.apply(
        lambda row: convert_weight_to_kg(
            row.get('qty_raw'), 
            row.get('qty_unit_raw'),
            unit_conversions
        ),
        axis=1
    )
    
    # Currency conversions
    # Kenya data already has USD values in value_raw, but still handle conversion if needed
    if 'value_raw' in df_std.columns:
        config_currency = value_currency.get('usd', 'USD') if value_currency else 'USD'
        df_std['customs_value_usd'] = df_std['value_raw'].apply(
            lambda v: convert_currency_to_usd(v, config_currency) if v and v != 'NULL' else None
        )
    else:
        df_std['customs_value_usd'] = None
    
    df_std['fob_usd'] = None  # Not distinguished in Kenya data
    df_std['cif_usd'] = None   # Not distinguished in Kenya data
    
    # Calculate price per kg
    df_std['price_usd_per_kg'] = df_std.apply(
        lambda row: (
            round(row['customs_value_usd'] / row['qty_kg'], 2)
            if row.get('customs_value_usd') and row.get('qty_kg') and row['qty_kg'] > 0
            else None
        ),
        axis=1
    )
    
    # Estimate TEU
    df_std['teu'] = df_std['qty_kg'].apply(estimate_teu)
    
    # Add timestamp
    df_std['standardized_at'] = datetime.now()
    
    # Convert back to Polars
    df_result = pl.from_pandas(df_std)
    
    logger.info(f"Standardization complete: {len(df_result)} rows processed")
    
    return df_result


# =====================================================================
# ORCHESTRATION
# =====================================================================

def get_unstandardized_rows(
    db_manager: DatabaseManager,
    batch_size: int = 10000
) -> List[Tuple[str, str, str]]:
    """
    Get list of (reporting_country, direction, source_format) tuples 
    that have unstandardized rows
    
    Args:
        db_manager: Database manager instance
        batch_size: Rows to check at a time
    
    Returns:
        List of tuples to process
    """
    query = """
        SELECT DISTINCT 
            r.reporting_country,
            r.direction,
            r.source_format
        FROM stg_shipments_raw r
        LEFT JOIN stg_shipments_standardized s ON r.raw_id = s.raw_id
        WHERE s.std_id IS NULL
        AND r.reporting_country IS NOT NULL
        AND r.direction IS NOT NULL
        ORDER BY r.reporting_country, r.direction;
    """
    
    results = db_manager.execute_query(query)
    
    groups = [(row[0], row[1], row[2] or 'FULL') for row in results]
    logger.info(f"Found {len(groups)} country/direction groups to standardize")
    
    return groups


def standardize_group(
    db_manager: DatabaseManager,
    reporting_country: str,
    direction: str,
    source_format: str,
    batch_size: int = 10000
) -> int:
    """
    Standardize all rows for a specific country/direction/format
    
    Args:
        db_manager: Database manager instance
        reporting_country: Country code
        direction: EXPORT or IMPORT
        source_format: FULL or SHORT
        batch_size: Rows per batch
    
    Returns:
        Number of rows standardized
    """
    logger.info(f"Processing: {reporting_country} {direction} ({source_format})")
    
    try:
        # Load mapping config
        config = load_mapping_config(reporting_country, direction, source_format)
    except FileNotFoundError as e:
        logger.warning(f"Skipping {reporting_country} {direction}: {e}")
        return 0
    
    # Query unstandardized rows
    query = """
        SELECT 
            r.raw_id,
            r.raw_file_name,
            r.reporting_country,
            r.direction,
            r.source_format,
            r.record_grain,
            r.raw_data,
            r.hs_code_raw,
            r.buyer_name_raw,
            r.supplier_name_raw,
            r.shipment_date_raw
        FROM stg_shipments_raw r
        LEFT JOIN stg_shipments_standardized s ON r.raw_id = s.raw_id
        WHERE s.std_id IS NULL
        AND r.reporting_country = %s
        AND r.direction = %s
        AND COALESCE(r.source_format, 'FULL') = %s
        LIMIT %s;
    """
    
    total_processed = 0
    
    while True:
        # Fetch batch
        rows = db_manager.execute_query(
            query, 
            (reporting_country, direction, source_format, batch_size)
        )
        
        if not rows:
            break
        
        logger.info(f"Processing batch of {len(rows)} rows...")
        
        # Convert to DataFrame
        import pandas as pd
        import json
        
        df_data = []
        for row in rows:
            row_dict = {
                'raw_id': row[0],
                'raw_file_name': row[1],
                'reporting_country': row[2],
                'direction': row[3],
                'source_format': row[4],
                'record_grain': row[5],
                'raw_data': json.loads(row[6]) if isinstance(row[6], str) else row[6],
            }
            df_data.append(row_dict)
        
        df_raw = pl.from_dicts(df_data)
        
        # Standardize batch
        df_std = standardize_batch(
            df_raw,
            config,
            reporting_country,
            direction,
            source_format
        )
        
        # Insert into stg_shipments_standardized
        insert_standardized_batch(db_manager, df_std)
        
        total_processed += len(df_std)
        logger.info(f"Inserted {len(df_std)} standardized rows (total: {total_processed})")
    
    return total_processed


def insert_standardized_batch(
    db_manager: DatabaseManager,
    df_std: pl.DataFrame
) -> int:
    """
    Bulk insert standardized rows into stg_shipments_standardized
    
    Args:
        db_manager: Database manager instance
        df_std: Standardized DataFrame
    
    Returns:
        Number of rows inserted
    """
    # Convert to list of tuples for bulk insert
    import pandas as pd
    df_pandas = df_std.to_pandas()
    
    # Prepare insert query
    insert_query = """
        INSERT INTO stg_shipments_standardized (
            raw_id, source_file, reporting_country, direction, source_format, record_grain,
            buyer_name_raw, buyer_name_clean, supplier_name_raw, supplier_name_clean,
            hs_code_raw, hs_code_6, goods_description,
            origin_country_raw, origin_country, destination_country_raw, destination_country,
            export_date, import_date, shipment_date, year, month,
            qty_raw, qty_unit_raw, qty_kg,
            value_raw, fob_usd, cif_usd, customs_value_usd, price_usd_per_kg,
            teu, vessel_name, container_id, port_loading, port_unloading,
            standardized_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s
        );
    """
    
    # Build data tuples
    data_tuples = []
    for _, row in df_pandas.iterrows():
        data_tuples.append((
            row.get('raw_id'),
            row.get('source_file'),
            row.get('reporting_country'),
            row.get('direction'),
            row.get('source_format'),
            row.get('record_grain'),
            row.get('buyer_name_raw'),
            row.get('buyer_name_clean'),  # Will be populated in Phase 3
            row.get('supplier_name_raw'),
            row.get('supplier_name_clean'),  # Will be populated in Phase 3
            row.get('hs_code_raw'),
            row.get('hs_code_6'),
            row.get('goods_description'),
            row.get('origin_country_raw'),
            row.get('origin_country'),
            row.get('destination_country_raw'),
            row.get('destination_country'),
            row.get('export_date'),
            row.get('import_date'),
            row.get('shipment_date'),
            row.get('year'),
            row.get('month'),
            row.get('qty_raw'),
            row.get('qty_unit_raw'),
            row.get('qty_kg'),
            row.get('value_raw'),
            row.get('fob_usd'),
            row.get('cif_usd'),
            row.get('customs_value_usd'),
            row.get('price_usd_per_kg'),
            row.get('teu'),
            row.get('vessel_name'),
            row.get('container_id'),
            row.get('port_loading'),
            row.get('port_unloading'),
            row.get('standardized_at'),
        ))
    
    # Bulk insert
    rows_inserted = db_manager.bulk_insert_execute_batch(
        insert_query,
        data_tuples,
        page_size=1000
    )
    
    return rows_inserted


def standardize_staging_rows(
    db_config_path: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main orchestration function to standardize all unstandardized rows
    
    Args:
        db_config_path: Path to database config YAML
        limit: Optional limit on total rows to process
    
    Returns:
        Summary statistics dictionary
    """
    db_manager = DatabaseManager(db_config_path)
    
    summary = {
        'groups_processed': 0,
        'groups_skipped': 0,
        'total_rows_standardized': 0,
        'errors': []
    }
    
    try:
        # Get groups to process
        groups = get_unstandardized_rows(db_manager)
        
        if not groups:
            logger.info("No unstandardized rows found")
            return summary
        
        # Process each group
        for reporting_country, direction, source_format in groups:
            try:
                rows_processed = standardize_group(
                    db_manager,
                    reporting_country,
                    direction,
                    source_format,
                    batch_size=10000
                )
                
                if rows_processed > 0:
                    summary['groups_processed'] += 1
                    summary['total_rows_standardized'] += rows_processed
                else:
                    summary['groups_skipped'] += 1
                
                # Check limit
                if limit and summary['total_rows_standardized'] >= limit:
                    logger.info(f"Reached limit of {limit} rows, stopping")
                    break
            
            except Exception as e:
                error_msg = f"Error processing {reporting_country} {direction}: {e}"
                logger.error(error_msg)
                summary['errors'].append(error_msg)
                summary['groups_skipped'] += 1
    
    finally:
        db_manager.close()
    
    return summary
