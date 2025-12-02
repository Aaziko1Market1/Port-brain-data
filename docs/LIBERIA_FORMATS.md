# Liberia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Liberia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Liberia Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | TOTAL_FEES |
| Liberia Import S.xlsx | IMPORT | SHORT | 88 | 1 | IMPORTER_NAME | HS_CODE | TOTALQUANTITY |

## Detailed Format Analysis

### Liberia Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE, SHIPMENT_NAME, SHIPMENT_PARTICULAR
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: TOTAL_FEES
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY, QUANTITY_TYPE
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/liberia_import_full.yml`

<details>
<summary>All Columns (33 total)</summary>

```
COST_INSURANCE_FREIGHT
COUNTRY_ISO_CODE_2
CURENCY
CUSTOM_OFFICE
DECLARATION_NUMBER
DESTINATION_COUNTRY
FREE_ON_BOARD
FREIGHT
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_NAME
IMP_DATE
INSURANCE
ITEM
NET_WEIGHT
ORIGIN_COUNTRY
PACKAGE_TYPE_NAME
PACKING_DESCRIPTION_NOMENCLATURE
PACKING_NUMBER
PRODUCT_DESCRIPTION
QUANTITY
QUANTITY_TYPE
RECIEPT_NUM
RECORDS_TAG
RECORD_ID
SHIPMENT_NAME
SHIPMENT_PARTICULAR
SUPPLIER_NAME
SUPPLY_COUNTRY
TAX_IDENTIFICATION_NUMBER
TOTAL_FEES
```
</details>

---

### Liberia Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 88

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALQUANTITY, TOTALVALUE, %GTTOTALVALUE
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/liberia_import_short.yml`

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

