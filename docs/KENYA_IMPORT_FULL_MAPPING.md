# Kenya Import Full Format - Mapping Documentation

## Overview
This document describes the implementation of Kenya Import Full format standardization in the GTI-OS Data Platform.

**Data Source**: Kenya Revenue Authority (KRA) Import Data - Full Format  
**File Pattern**: `Kenya Import F.xlsx`  
**Config File**: `config/kenya_import_full.yml`

## File Structure

### Excel Layout
- **Header Row**: Row 6 (1-indexed)
- **Data Starts**: Row 7
- **Rows 1-5**: Empty or contain metadata
- **Total Columns**: 32

### Column Mapping

#### Entity Information
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| IMPORTER_NAME | buyer_name_raw | Company importing goods into Kenya |
| IMPORTER_ADDRESS | buyer_address_raw | Importer's address |
| IMPORTER_PI | buyer_tax_id_raw | Importer's PIN (tax ID) |
| SUPPLIER_NAME | supplier_name_raw | Foreign supplier/exporter |
| SUPPLIER_ADDRESS | supplier_address_raw | Supplier's address |
| AGENT_NAME | agent_name | Clearing agent name |
| AGENT_PIN | agent_tax_id | Agent's PIN |

#### Product Classification
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| HS_CODE | hs_code_raw | 10-digit HS code (Kenya format) |
| HS_CODE_2 | hs_code_2 | 2-digit HS chapter |
| HS_CODE_4 | hs_code_4 | 4-digit HS heading |
| PRODUCT_DESCRIPTION | goods_description | Product description |
| HS_CODE_DESCRIPTION | hs_code_description | Official HS code description |

**HS Code Normalization**: Kenya uses 10-digit HS codes. These are normalized to 6-digit international HS codes by taking the first 6 digits.

Example:
- Raw: `6907210000` → Normalized: `690721`

#### Geography
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| ORIGIN_COUNTRY | origin_country_raw | Country where goods originated |
| DESTINATION_PORT | destination_port_raw | Port in Kenya (EMK = Mombasa, etc.) |
| PORT_OF_DISCHARGE | port_of_discharge_raw | Discharge port |
| *Default* | destination_country | Always "KENYA" for imports |

**Country Normalization**: Common patterns:
- `UNITED ARAB EMIRATES` → `UAE`
- `CHINA` → `CHINA`
- `UNITED STATES` → `USA`

#### Dates
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| IMP_DATE | import_date | Import declaration date (YYYY-MM-DD) |
| YEAR | year | Year field |

#### Quantities and Values
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| QUANTITY | quantity_raw | Quantity value |
| UNIT | unit_raw | Unit of measurement |
| UNIT_VALUE | unit_value_raw | Value per unit |
| TOTAL_VALUE | total_value_local_raw | Total value in KES |
| TOTAL_VALUE_USD | total_value_usd_raw | Total value in USD |

**Currency**: Kenya provides values in both KES (Kenyan Shillings) and USD. We use the USD field directly.

#### Unit Conversions

Kenya uses UN/LOCODE standard units:

| Kenya Unit | Type | Conversion to kg | Notes |
|------------|------|------------------|-------|
| KGM | Weight | 1.0 | Kilograms |
| TNE | Weight | 1000.0 | Tonnes |
| GRM | Weight | 0.001 | Grams |
| MTK | Area | null | Square meters (tiles, fabric) - not weight |
| PCS | Count | null | Pieces - not weight |
| LTR | Volume | 1.0 (estimate) | Liters - estimated for liquids |
| NMB | Count | null | Number - not weight |

**Important**: Non-weight units (MTK, PCS, NMB) result in `qty_kg = NULL` since we cannot reliably convert them to weight.

#### Shipment Details
| Kenya Column Name | Standardized Field | Description |
|-------------------|-------------------|-------------|
| BILL_OF_LADING | bill_of_lading | B/L number |
| ENTRY_NO | entry_number | Customs entry number |
| MANIFESTO_NO | manifesto_number | Manifest number |
| MODE_OF_TRANSPORT | mode_of_transport | SEA, ROAD, AIR, etc. |
| TYPE_OF_PACK | type_of_pack | Packaging type |
| EXCHANGE_RATE | exchange_rate | KES/USD exchange rate |

## Data Processing Pipeline

### 1. Ingestion (Epic 0)
```
data/raw/kenya/import/2023/01/Kenya Import F.xlsx
↓
Detected metadata:
  - reporting_country: KENYA
  - direction: IMPORT
  - source_format: FULL (detected from " F" in filename)
  - year: 2023
  - month: 01
↓
Header row 6 detected from config
↓
Stored in stg_shipments_raw with raw_data JSONB
```

### 2. Standardization (Epic 2)
```
stg_shipments_raw (Kenya IMPORT FULL)
↓
Load config/kenya_import_full.yml
↓
Extract columns from raw_data:
  - IMPORTER_NAME → buyer_name_raw
  - HS_CODE → hs_code_raw → normalize to hs_code_6
  - ORIGIN_COUNTRY → origin_country_raw → normalize to origin_country
  - QUANTITY + UNIT → qty_kg (if weight unit)
  - TOTAL_VALUE_USD → customs_value_usd
  - IMP_DATE → import_date
↓
Calculate derived fields:
  - price_usd_per_kg = customs_value_usd / qty_kg
  - teu = qty_kg / 20000
↓
Stored in stg_shipments_standardized
```

## Example Data

### Raw Record (from Kenya Import F.xlsx)
```
IMPORTER_NAME: PYRAMID BUILDERS LIMITED
SUPPLIER_NAME: R A K CERAMICS PJSC
HS_CODE: 6907210000
PRODUCT_DESCRIPTION: GLAZED PORCELAIN TILES; 600 X 100MM; 200; 0
ORIGIN_COUNTRY: UNITED ARAB EMIRATES
IMP_DATE: 2025-10-31
QUANTITY: 200
UNIT: MTK
TOTAL_VALUE: 174100.1 (KES)
TOTAL_VALUE_USD: 1347.09
```

### Standardized Record
```
buyer_name_raw: PYRAMID BUILDERS LIMITED
supplier_name_raw: R A K CERAMICS PJSC
hs_code_raw: 6907210000
hs_code_6: 690721
goods_description: GLAZED PORCELAIN TILES; 600 X 100MM; 200; 0
origin_country_raw: UNITED ARAB EMIRATES
origin_country: UAE
destination_country: KENYA
import_date: 2025-10-31
quantity_raw: 200
unit_raw: MTK
qty_kg: NULL (MTK is area, not weight)
customs_value_usd: 1347.09
price_usd_per_kg: NULL (no weight)
```

## Data Quality Considerations

### Expected Completeness
- **HS Code**: ~100% (required for customs)
- **Importer Name**: ~100% (required)
- **Origin Country**: ~100% (required)
- **Value USD**: ~100% (required)
- **Quantity**: ~100% (required)
- **Qty_kg**: 40-60% (only for weight-based units)

### Known Issues
1. **Non-weight units**: Items measured in area (MTK), count (PCS, NMB) have no weight conversion
2. **NULL values**: Kenya data contains literal "NULL" strings which must be handled
3. **Agent vs Importer**: Some records have agents as importers; the actual buyer is in IMPORTER_NAME

## Testing

See test commands in main documentation.

## Files Modified/Created

### Created
- `config/kenya_import_full.yml` - Mapping configuration
- `docs/KENYA_IMPORT_FULL_MAPPING.md` - This document

### Modified
- `etl/ingestion/ingest_files.py` - Added Kenya format detection and header row support
- `etl/standardization/standardize_shipments.py` - Enhanced config loading and unit conversions
- `db/epic2_verification_queries.sql` - Added Kenya-specific validation queries

## References
- GTI-OS Data Platform Architecture v1.0
- EPIC 2 Design Document
- UN/LOCODE Unit Codes: https://unece.org/trade/uncefact/cl-recommendations
