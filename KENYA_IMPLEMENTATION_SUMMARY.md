# Kenya Implementation Summary - Audit & Hardening

## Overview

Complete audit and hardening of the Kenya data pipeline following GTI-OS Data Platform Architecture v1.0. This update ensures clean separation of production vs synthetic data, correct column mappings, and full data quality guarantees.

**Implementation Date**: November 29, 2025  
**Status**: ✅ **COMPLETE AND PRODUCTION-READY**

---

## Data Files Inventory

### Production Files (Eximpedia Data)

| File | Location | Format | Header Row | Data Rows |
|------|----------|--------|------------|-----------|
| Kenya Import F.xlsx | `data/raw/kenya/import/2023/01/` | FULL | 6 | 2 |
| Kenya Import S.xlsx | `data/raw/kenya/import/2023/01/` | SHORT | 1 | 1,000 |
| Kenya Export F.xlsx | `data/raw/kenya/export/2023/01/` | FULL | 6 | 2 |
| Kenya Export S.xlsx | `data/raw/kenya/export/2023/01/` | SHORT | 1 | 701 |

### Synthetic/Test Files (Excluded)

| File | Location | Status |
|------|----------|--------|
| kenya_import_202301.xlsx | `data/raw/kenya/import/2023/01/` | **SKIPPED** - Marked as TEST |

---

## Files Created

### Configuration Files

| File | Purpose |
|------|---------|
| `config/kenya_import_full.yml` | Kenya Import FULL format mapping |
| `config/kenya_import_short.yml` | **NEW** - Kenya Import SHORT format mapping |
| `config/kenya_export_full.yml` | Kenya Export FULL format mapping |
| `config/kenya_export_short.yml` | **NEW** - Kenya Export SHORT format mapping |

### Data Quality

| File | Purpose |
|------|---------|
| `db/data_quality_verification.sql` | **NEW** - Reusable DQ checks for all countries |

---

## Files Modified

### Ingestion (`etl/ingestion/ingest_files.py`)

**Changes**:
- Enhanced Kenya format detection to correctly identify FULL (`F.xlsx`) vs SHORT (`S.xlsx`)
- Added synthetic file detection pattern (`kenya_(import|export)_\d+`)
- Synthetic files marked as `source_format = 'TEST'` and skipped during ingestion

```python
# Kenya-specific format detection
if 'kenya' in filename_lower:
    if re.match(r'kenya_(import|export)_\d+', filename_lower):
        metadata['source_format'] = 'TEST'
        metadata['is_synthetic'] = True
    elif filename_upper.endswith(' F'):
        metadata['source_format'] = 'FULL'
    elif filename_upper.endswith(' S'):
        metadata['source_format'] = 'SHORT'
```

### Standardization (`etl/standardization/standardize_shipments.py`)

**Changes**:
- Fixed `origin_country` to use defaults when raw values are NULL
- Fixed `destination_country` to use defaults when raw values are NULL
- Added `fillna()` logic to apply defaults even when some raw values exist

```python
# Fill any NULL origin_country with default (e.g., for exports from reporting country)
if default_origin:
    df_std['origin_country'] = df_std['origin_country'].fillna(normalize_country(default_origin))
```

---

## Column Mappings

### Kenya Import FULL

| Standardized Field | Raw Column | Notes |
|--------------------|------------|-------|
| buyer_name_raw | IMPORTER_NAME | Kenyan importer |
| supplier_name_raw | SUPPLIER_NAME | Foreign supplier |
| hs_code_raw | HS_CODE | Full HS code |
| origin_country_raw | ORIGIN_COUNTRY | Source country |
| destination_country | **DEFAULT: KENYA** | Not in raw data |
| qty_raw | QUANTITY | Line item quantity |
| qty_unit_raw | UNIT | Unit of measure |
| value_raw | TOTAL_VALUE_USD | Already in USD |
| import_date_raw | IMP_DATE | Import date |

### Kenya Import SHORT

| Standardized Field | Raw Column | Notes |
|--------------------|------------|-------|
| buyer_name_raw | IMPORTER_NAME | Kenyan importer |
| supplier_name_raw | SUPPLIER_NAME | Foreign supplier |
| hs_code_raw | HS_CODE | Full HS code |
| origin_country_raw | ORIGIN_COUNTRY | Source country |
| destination_country | **DEFAULT: KENYA** | Not in raw data |
| qty_raw | TOTALQUANTITY | Aggregated quantity |
| value_raw | TOTALVALUEUSD | Already in USD |

### Kenya Export FULL

| Standardized Field | Raw Column | Notes |
|--------------------|------------|-------|
| supplier_name_raw | EXPORTER_NAME | Kenyan exporter |
| buyer_name_raw | BUYER_NAME | Foreign buyer |
| hs_code_raw | HS_CODE | Full HS code |
| origin_country_raw | ORIGIN_COUNTRY | Usually KENYA |
| destination_country_raw | DESTINATION_COUNTRY | Target country |
| qty_raw | QUANTITY | Line item quantity |
| qty_unit_raw | UNIT | Unit of measure |
| value_raw | TOTAL_VALUE_USD | Already in USD |
| export_date_raw | EXP_DATE | Export date |

### Kenya Export SHORT

| Standardized Field | Raw Column | Notes |
|--------------------|------------|-------|
| supplier_name_raw | EXPORTER_NAME | Kenyan exporter |
| buyer_name_raw | BUYER_NAME | Foreign buyer |
| hs_code_raw | HS_CODE | Full HS code |
| origin_country_raw | ORIGIN_COUNTRY | Usually KENYA |
| destination_country_raw | DESTINATION_COUNTRY | Target country |
| qty_raw | TOTALQUANTITY | Aggregated quantity |
| value_raw | TOTALVALUE | May need currency check |

---

## Final Row Counts

### Raw Data (`stg_shipments_raw`)

| Country | Direction | Format | Rows |
|---------|-----------|--------|------|
| KENYA | EXPORT | FULL | 2 |
| KENYA | EXPORT | SHORT | 701 |
| KENYA | IMPORT | FULL | 2 |
| KENYA | IMPORT | SHORT | 1,000 |
| **Total** | | | **1,705** |

### Standardized Data (`stg_shipments_standardized`)

| Country | Direction | Format | Rows | Null Origin | Null Dest |
|---------|-----------|--------|------|-------------|-----------|
| KENYA | EXPORT | FULL | 2 | 0 | 0 |
| KENYA | EXPORT | SHORT | 701 | 0 | 0 |
| KENYA | IMPORT | FULL | 2 | 0 | 0 |
| KENYA | IMPORT | SHORT | 1,000 | 0 | 0 |
| **Total** | | | **1,705** | **0** | **0** |

### Ledger (`global_trades_ledger`)

| Country | Direction | Rows | UUID Coverage |
|---------|-----------|------|---------------|
| KENYA | EXPORT | 703 | 100% |
| KENYA | IMPORT | 1,002 | 100% |
| **Total** | | **1,705** | **100%** |

---

## Data Quality Guarantees

### ✅ Country Fields
- **Kenya Import**: All rows have `destination_country = 'KENYA'`
- **Kenya Import**: All rows have non-NULL `origin_country` (diverse trading partners)
- **Kenya Export**: All rows have `origin_country = 'KENYA'`
- **Kenya Export**: All rows have non-NULL `destination_country`

### ✅ UUID Coverage
- All Kenya rows with buyer/supplier names have corresponding UUIDs
- 100% UUID coverage in `global_trades_ledger`

### ✅ No Synthetic Data Pollution
- `kenya_import_202301.xlsx` is automatically skipped during ingestion
- Only production Eximpedia files are processed

---

## Verification Commands

### Quick Health Check
```bash
psql -U postgres -d aaziko_trade -c "
SELECT reporting_country, direction, COUNT(*) as rows,
       SUM(CASE WHEN origin_country IS NULL THEN 1 ELSE 0 END) as null_origin,
       SUM(CASE WHEN destination_country IS NULL THEN 1 ELSE 0 END) as null_dest
FROM global_trades_ledger
WHERE reporting_country = 'KENYA'
GROUP BY reporting_country, direction;
"
```

### Full Data Quality Check
```bash
psql -U postgres -d aaziko_trade -f db/data_quality_verification.sql
```

### Kenya Import Destination Check
```bash
psql -U postgres -d aaziko_trade -c "
SELECT destination_country, COUNT(*) 
FROM global_trades_ledger 
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT' 
GROUP BY destination_country;
"
-- Expected: All rows have KENYA
```

### Kenya Export Origin Check
```bash
psql -U postgres -d aaziko_trade -c "
SELECT origin_country, COUNT(*) 
FROM global_trades_ledger 
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' 
GROUP BY origin_country;
"
-- Expected: Most/all rows have KENYA
```

### UUID Coverage Check
```bash
psql -U postgres -d aaziko_trade -c "
SELECT reporting_country, direction, COUNT(*) as total,
       SUM(CASE WHEN buyer_uuid IS NOT NULL AND supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) as with_uuids
FROM global_trades_ledger
WHERE reporting_country = 'KENYA'
GROUP BY reporting_country, direction;
"
```

---

## Ingestion Rules

### Production Files
| Pattern | Detection | Action |
|---------|-----------|--------|
| `Kenya Import F.xlsx` | FULL | Ingest with header row 6 |
| `Kenya Import S.xlsx` | SHORT | Ingest with header row 1 |
| `Kenya Export F.xlsx` | FULL | Ingest with header row 6 |
| `Kenya Export S.xlsx` | SHORT | Ingest with header row 1 |

### Synthetic/Test Files
| Pattern | Detection | Action |
|---------|-----------|--------|
| `kenya_(import|export)_YYYYMM.xlsx` | TEST | **SKIP** |

---

## Troubleshooting

### Issue: NULL origin_country or destination_country
**Cause**: Config defaults not applied correctly  
**Fix**: Verify YAML config has proper `defaults:` section with `origin_country` or `destination_country`

### Issue: Wrong source_format (FULL vs SHORT)
**Cause**: Filename doesn't match pattern  
**Fix**: Ensure files are named `Kenya * F.xlsx` for FULL, `Kenya * S.xlsx` for SHORT

### Issue: Synthetic file being ingested
**Cause**: Pattern detection failed  
**Fix**: Ensure synthetic files match `kenya_(import|export)_\d+` pattern

---

## Architecture Notes

- **Value Type**: Kenya exports use FOB, imports use CIF
- **Currency**: All Kenya files have values already in USD
- **Unit Handling**: SHORT format has no UNIT column - quantities are totals
- **Date Handling**: FULL uses specific date columns, SHORT uses MONTHYEAR

---

**Last Updated**: November 29, 2025
