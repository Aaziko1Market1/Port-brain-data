# Database Column Reference

Quick reference for commonly confused column names in the GTI-OS Data Platform.

## Common Column Name Corrections

### ❌ Wrong → ✅ Correct

| Wrong Column Name | Correct Column Name | Table | Notes |
|-------------------|---------------------|-------|-------|
| `unit_raw` | `qty_unit_raw` | `stg_shipments_standardized` | Unit of measurement for quantity |
| `quantity_raw` | `qty_raw` | `stg_shipments_standardized` | Raw quantity value |
| `raw_file_name` | `source_file` | `stg_shipments_standardized` | Source file name |
| `raw_file_name` | `raw_file_name` | `stg_shipments_raw` | ✅ Correct in raw table |
| `total_value_usd_raw` | `value_raw` | `stg_shipments_standardized` | Raw value field |

## Table: stg_shipments_raw

**Key Columns:**
- `raw_id` - Primary key
- `raw_file_name` - Source file name
- `reporting_country` - Country (KENYA, INDIA, etc.)
- `direction` - IMPORT or EXPORT
- `source_format` - FULL or SHORT
- `raw_data` - JSONB with all raw columns

## Table: stg_shipments_standardized

**Entity Fields:**
- `buyer_name_raw` - Importer/buyer name (raw)
- `buyer_name_clean` - Cleaned buyer name
- `supplier_name_raw` - Supplier/exporter name (raw)
- `supplier_name_clean` - Cleaned supplier name

**Product Fields:**
- `hs_code_raw` - Raw HS code (can be 6, 8, or 10 digits)
- `hs_code_6` - Normalized 6-digit HS code
- `goods_description` - Product description

**Geography Fields:**
- `origin_country_raw` - Raw origin country name
- `origin_country` - Normalized origin country
- `destination_country_raw` - Raw destination country name
- `destination_country` - Normalized destination country
- `reporting_country` - Reporting country (KENYA, INDIA, etc.)

**Date Fields:**
- `export_date` - Export date
- `import_date` - Import date
- `shipment_date` - Shipment date (best available)
- `year` - Year (extracted from dates)
- `month` - Month (extracted from dates)

**Quantity Fields:**
- `qty_raw` - Raw quantity value ⚠️ NOT `quantity_raw`
- `qty_unit_raw` - Raw unit (KGM, TNE, MTK, PCS, etc.) ⚠️ NOT `unit_raw`
- `qty_kg` - Quantity converted to kilograms (NULL for non-weight units)

**Value Fields:**
- `value_raw` - Raw value (main value field)
- `value_currency` - Currency of raw value
- `fob_usd` - FOB value in USD
- `cif_usd` - CIF value in USD
- `customs_value_usd` - Customs value in USD (main standardized value)
- `price_usd_per_kg` - Price per kilogram in USD

**Logistics Fields:**
- `teu` - Twenty-foot Equivalent Units
- `vessel_name` - Vessel name
- `container_id` - Container ID
- `port_loading` - Port of loading
- `port_unloading` - Port of unloading

**Metadata Fields:**
- `source_file` - Source file name ⚠️ NOT `raw_file_name`
- `record_grain` - LINE_ITEM or AGGREGATE
- `source_format` - FULL or SHORT
- `direction` - IMPORT or EXPORT
- `standardized_at` - Timestamp of standardization

## Example Queries

### ✅ Correct Query - Kenya Import Full
```sql
SELECT 
    buyer_name_raw AS importer,
    hs_code_raw, 
    hs_code_6,
    origin_country,
    qty_unit_raw,  -- ✅ Correct
    qty_raw,       -- ✅ Correct
    qty_kg,
    customs_value_usd, 
    price_usd_per_kg
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA'
  AND direction = 'IMPORT'
  AND source_format = 'FULL'
LIMIT 10;
```

### ❌ Common Mistakes
```sql
-- ❌ WRONG - will fail
SELECT unit_raw FROM stg_shipments_standardized;
-- ✅ CORRECT
SELECT qty_unit_raw FROM stg_shipments_standardized;

-- ❌ WRONG - will fail
SELECT quantity_raw FROM stg_shipments_standardized;
-- ✅ CORRECT
SELECT qty_raw FROM stg_shipments_standardized;

-- ❌ WRONG - will fail (in standardized table)
SELECT raw_file_name FROM stg_shipments_standardized;
-- ✅ CORRECT
SELECT source_file FROM stg_shipments_standardized;
```

## Quick Tips

1. **Quantity fields use `qty_` prefix**, not `quantity_`
2. **Unit field is `qty_unit_raw`**, not `unit_raw`
3. **File name in standardized table is `source_file`**, not `raw_file_name`
4. **File name in raw table IS `raw_file_name`** (different from standardized!)

## Need Help?

Run this to see all columns in standardized table:
```sql
\d stg_shipments_standardized
```

Or:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'stg_shipments_standardized' 
ORDER BY ordinal_position;
```
