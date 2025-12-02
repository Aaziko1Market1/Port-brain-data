# Moldova Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Moldova.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| moldova export short.xlsx | EXPORT | SHORT | 90 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Moldova Import Full.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | PRICE_LEI |
| Moldova import short.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALQUANTITY |

## Detailed Format Analysis

### moldova export short.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 90

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/moldova_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
EXPORTER_NAME
HS_CODE
DESTINATION_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Moldova Import Full.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: PRICE_LEI, TOTAL_QUANTITY_OF_SKU, UNIT_AVERAGE_PRICE_LEI, UNIT_VALUE_IN_USD, VALUE_IN_USD
- 📊 Quantity: QUANTITY, TOTAL_QUANTITY_OF_SKU
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/moldova_import_full.yml`

<details>
<summary>All Columns (25 total)</summary>

```
CONTRACTORS_NAME_AND_LOCATION
COUNTRY_ISO_CODE_2
COUNTRY_OF_ORIGIN_CODE
COUNTRY_OF_SHIPMENT_OR_DESTINATION
COUNTRY_OF_SHIPMENT_OR_DESTINATION_CODE
DECLARATION_TYPE
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_NAME
IMP_DATE
NUMBER_OF_SKU_IN_DECLARATION_FORM
ORIGIN_COUNTRY
PRICE_LEI
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
TOTAL_QUANTITY_OF_SKU
UNIT
UNIT_AVERAGE_PRICE_LEI
UNIT_VALUE_IN_USD
VALUE_IN_USD
```
</details>

---

### Moldova import short.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALQUANTITY, TOTALVALUE, %GTTOTALVALUE
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/moldova_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
HS_CODE
SUPPLIER_NAME
ORIGIN_COUNTRY
TOTALQUANTITY
%GTTOTALQUANTITY
TOTALVALUE
%GTTOTALVALUE
MONTHYEAR
```
</details>

---

