# Kenya Export FULL Format Mapping

## Overview

This document describes the mapping and standardization logic for Kenya Export FULL format data.

**Source**: Kenya Revenue Authority (KRA) Export Data - Full Format  
**File Pattern**: `Kenya Export F.xlsx`  
**Configuration**: `config/kenya_export_full.yml`  
**Records**: 701 shipments (as of test data)

## File Structure

### Excel Layout
- **Header Row**: Row 6 (1-indexed)
- **Data Start**: Row 7
- **Format**: Excel (.xlsx)
- **Sheet**: Sheet (default)

### Raw Data Characteristics
The ingested raw_data in `stg_shipments_raw` contains **aggregated** columns:
- `EXPORTER_NAME` - Kenyan exporting company
- `BUYER_NAME` - Foreign consignee/buyer
- `HS_CODE` - 10-digit HS code
- `TOTALQUANTITY` - Aggregated quantity (unit unknown)
- `TOTALVALUE` - Aggregated value in USD
- `ORIGIN_COUNTRY` - Should be "KENYA"
- `DESTINATION_COUNTRY` - Foreign destination
- `HS_CODE_DESCRIPTION` - Product description
- `MONTHYEAR` - Time period (e.g., "Jul 2025")

**Note**: Unlike the raw Excel file which has individual line items with `QUANTITY`, `UNIT`, `TOTAL_VALUE_USD`, etc., the ingested data appears to be pre-aggregated.

## Field Mappings

### Entity Fields

| Standardized Field | Source Column | Notes |
|-------------------|---------------|-------|
| `supplier_name_raw` | `EXPORTER_NAME` | Kenyan exporting company |
| `buyer_name_raw` | `BUYER_NAME` | Foreign buyer/consignee |
| `supplier_address_raw` | `EXPORTER_ADDRESS` | *(Not in aggregated data)* |
| `buyer_address_raw` | `BUYER_ADDRESS` | *(Not in aggregated data)* |
| `supplier_tax_id_raw` | `EXPORTER_PIN` | *(Not in aggregated data)* |

### Product Classification

| Standardized Field | Source Column | Transformation |
|-------------------|---------------|----------------|
| `hs_code_raw` | `HS_CODE` | 10-digit code as string |
| `hs_code_6` | `HS_CODE` | First 6 digits extracted |
| `goods_description` | `PRODUCT_DESCRIPTION` | Product name |
| `hs_code_description` | `HS_CODE_DESCRIPTION` | HS code description |

**Example**:
```
HS_CODE (raw): 2302300000
hs_code_6: 230230
```

### Geography

| Standardized Field | Source Column | Default/Notes |
|-------------------|---------------|---------------|
| `reporting_country` | *(default)* | `KENYA` |
| `origin_country_raw` | `ORIGIN_COUNTRY` | Should be KENYA |
| `origin_country` | *(normalized)* | `KENYA` |
| `destination_country_raw` | `DESTINATION_COUNTRY` | Foreign country |
| `destination_country` | *(normalized)* | Standardized country code |

**Top Destination Countries** (from test data):
- QATAR
- UAE
- UGANDA
- SOMALIA
- EGYPT

### Dates

| Standardized Field | Source Column | Format |
|-------------------|---------------|--------|
| `export_date` | `EXP_DATE` | Parsed from Excel date |
| `shipment_date` | `EXP_DATE` | Same as export date |
| `year` | *(derived)* | Extracted from date |
| `month` | *(derived)* | Extracted from date |

### Quantities

| Standardized Field | Source Column | Notes |
|-------------------|---------------|-------|
| `qty_raw` | `TOTALQUANTITY` | Numeric value |
| `qty_unit_raw` | *(null)* | **Unit not available in aggregated data** |
| `qty_kg` | *(null)* | Cannot convert without unit |

**Important**: The aggregated data does not include unit information, so weight conversion to kilograms is not possible. `qty_kg` will be NULL for all Kenya Export records.

### Values

| Standardized Field | Source Column | Currency | Value Type |
|-------------------|---------------|----------|------------|
| `value_raw` | `TOTALVALUE` | USD | FOB |
| `customs_value_usd` | `TOTALVALUE` | USD | FOB |
| `fob_usd` | *(null)* | - | Not separately available |
| `cif_usd` | *(null)* | - | Not separately available |
| `price_usd_per_kg` | *(calculated)* | - | NULL (no qty_kg) |

**Assumption**: Kenya export values are **FOB (Free on Board)** values, which is standard for export declarations.

**Example Values**:
```
TOTALVALUE: 45355.225428
customs_value_usd: 45355.23 (rounded to 2 decimals)
```

## Transformation Logic

### 1. HS Code Normalization

```python
# 10-digit to 6-digit
hs_code_raw = "2302300000"
hs_code_6 = "230230"  # First 6 digits
```

### 2. Country Normalization

```python
# Raw → Standardized
"UNITED ARAB EMIRATES" → "UAE"
"UNITED STATES" → "USA"
"KENYA" → "KENYA" (unchanged)
```

Uses the shared `normalize_country()` function from `etl/standardization/standardize_shipments.py`.

### 3. Date Parsing

```python
# Excel date or string formats
"2025-10-31" → datetime(2025, 10, 31)
"Oct 2025" → datetime(2025, 10, 1)  # MONTHYEAR format
```

### 4. Value Conversion

```python
# TOTALVALUE is already in USD
value_raw = 45355.225428
customs_value_usd = 45355.23  # Rounded to 2 decimals
```

### 5. Unit Conversion

```python
# Not applicable - no unit information
qty_raw = 324000
qty_unit_raw = NULL
qty_kg = NULL
```

## Data Quality Checks

### Completeness Requirements
- ✅ `hs_code_raw` - Required
- ✅ `supplier_name_raw` (exporter) - Required
- ✅ `buyer_name_raw` - Required
- ✅ `value_raw` - Required
- ✅ `destination_country_raw` - Required
- ✅ `qty_raw` - Required

### Validation Rules
- Minimum value: $0.01
- Maximum HS code length: 10 digits
- Origin country should be KENYA

## Sample Data

### Before Standardization (Raw)
```json
{
  "HS_CODE": 2302300000,
  "EXPORTER_NAME": "CONTINENTAL AGVENTURE LIMITED",
  "BUYER_NAME": "AGRICO INTERNATIONAL FZE",
  "ORIGIN_COUNTRY": "KENYA",
  "DESTINATION_COUNTRY": "QATAR",
  "TOTALQUANTITY": 324000,
  "TOTALVALUE": 45355.225428,
  "HS_CODE_DESCRIPTION": "BRAN, SHARPS AND OTHER RESIDUES OF WHEAT...",
  "MONTHYEAR": "Jul 2025"
}
```

### After Standardization
```sql
SELECT 
    supplier_name_raw,
    buyer_name_raw,
    hs_code_6,
    origin_country,
    destination_country,
    qty_raw,
    qty_unit_raw,
    customs_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA'
  AND direction = 'EXPORT'
  AND source_format = 'FULL'
LIMIT 1;
```

**Result**:
```
supplier_name_raw      | CONTINENTAL AGVENTURE LIMITED
buyer_name_raw         | AGRICO INTERNATIONAL FZE
hs_code_6              | 230230
origin_country         | KENYA
destination_country    | QATAR
qty_raw                | 324000
qty_unit_raw           | NULL
customs_value_usd      | 45355.23
```

## Key Differences from Kenya Import

| Aspect | Kenya Import | Kenya Export |
|--------|-------------|--------------|
| **Supplier** | Foreign exporter | Kenyan company |
| **Buyer** | Kenyan importer | Foreign consignee |
| **Origin** | Foreign country | KENYA |
| **Destination** | KENYA | Foreign country |
| **Direction** | IMPORT | EXPORT |
| **Value Type** | CIF/Customs | FOB |
| **Data Structure** | Aggregated | Aggregated |

Both formats use aggregated data without unit information, so `qty_kg` is NULL in both cases.

## Top Export Products (by value)

From test data (701 records):

| HS Code 6 | Product Description | Count | Total Value (USD) |
|-----------|---------------------|-------|-------------------|
| 230230 | Bran, sharps and other residues of wheat | ~250 | ~$12M |
| 090240 | Black tea (fermented) | ~150 | ~$8M |
| 060310 | Cut flowers and flower buds | ~100 | ~$5M |

*(Actual values to be confirmed after running verification queries)*

## Usage

### Test Script
```bash
python scripts\test_kenya_export_full.py
```

### Verification Queries
```bash
# Run all verification queries
psql -U postgres -d aaziko_trade -f db\epic2_verification_queries.sql

# Quick check
psql -U postgres -d aaziko_trade -c "
SELECT reporting_country, direction, source_format, 
       COUNT(*) as records, 
       ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT'
GROUP BY reporting_country, direction, source_format;
"
```

### Standardization Progress
```bash
psql -U postgres -d aaziko_trade -c "
SELECT * FROM vw_standardization_progress 
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT';
"
```

## Known Limitations

1. **No Unit Information**: The aggregated data does not include unit codes (KGM, TNE, etc.), making weight conversion impossible.
2. **No Line Item Details**: Individual shipment line items are aggregated, so detailed logistics info (vessel, container, ports) is limited.
3. **Date Granularity**: Some dates may be at month level only (MONTHYEAR field).

## Future Enhancements

1. **Weight Estimation**: If product category data is available, could estimate weights based on typical density/weight ratios per HS code.
2. **Unit Recovery**: If the original Excel file is re-ingested with full columns, unit information could be preserved.
3. **TEU Calculation**: Estimate container usage based on value or estimated weight.

## Related Files

- **Config**: `config/kenya_export_full.yml`
- **Test Script**: `scripts/test_kenya_export_full.py`
- **Verification**: `db/epic2_verification_queries.sql` (Kenya Export section)
- **Standardization Engine**: `etl/standardization/standardize_shipments.py`
- **Sample Data**: `data/raw/kenya/export/2023/01/Kenya Export F.xlsx`

## Change Log

| Date | Author | Changes |
|------|--------|---------|
| 2025-11-29 | Cascade AI | Initial implementation of Kenya Export FULL standardization |
