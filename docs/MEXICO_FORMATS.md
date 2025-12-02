# Mexico Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Mexico.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Mexico  Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Mexico  Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |
| Mexico Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ADDRESS | HS_CODE | FOB_UNIT_USD |
| Mexico Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ADDRESS | HS_CODE | CIF_UNIT_USD |

## Detailed Format Analysis

### Mexico  Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/mexico_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
HS_CODE
HS_DESCRIPTION
DESTINATION_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Mexico  Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/mexico_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
SUPPLIER_NAME
IMPORTER_NAME
HS_CODE
HS_DESCRIPTION
ORIGIN_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

### Mexico Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ADDRESS, EXPORTER_CITY, EXPORTER_NAME, EXPORTER_PROVINCE_STATE, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: FOB_UNIT_USD, FOB_USD, TOTAL_WEIGHT
- 📊 Quantity: COMERCIAL_QUANTITY, QUANTITY, TOTAL_WEIGHT
- 🏢 Buyer/Importer: BUYER_ADDRESS, BUYER_CITY, BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ADDRESS, EXPORTER_CITY, EXPORTER_NAME, EXPORTER_PROVINCE_STATE

**Config File:** `config/mexico_export_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
BUYER_ADDRESS
BUYER_CITY
BUYER_NAME
COMERCIAL_QUANTITY
COMERCIAL_UNIT
COUNTRY_ISO_CODE_2
CUSTOM_STATE_PORT
DESTINATION_COUNTRY
DOCUMENT_NO
EXPORTER_ADDRESS
EXPORTER_CITY
EXPORTER_NAME
EXPORTER_PROVINCE_STATE
EXP_DATE
FOB_UNIT_USD
FOB_USD
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
LOCAL_PORT_POL
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
TOTAL_WEIGHT
TRANSPORT
UNIT
```
</details>

---

### Mexico Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ADDRESS, IMPORTER_CITY, IMPORTER_NAME, IMPORTER_STATE, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_UNIT_USD, CIF_USD, TOTAL_WEIGHT
- 📊 Quantity: COMERCIAL_QUANTITY, QUANTITY, TOTAL_WEIGHT
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_CITY, IMPORTER_NAME, IMPORTER_STATE
- 🏭 Supplier/Exporter: SUPPLIER_ADDRESS, SUPPLIER_CITY, SUPPLIER_NAME

**Config File:** `config/mexico_import_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
CIF_UNIT_USD
CIF_USD
COMERCIAL_QUANTITY
COMERCIAL_UNIT
COUNTRY_ISO_CODE_2
CUSTOM_STATE_PORT
DOCUMENT_NO
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMPORTER_ADDRESS
IMPORTER_CITY
IMPORTER_NAME
IMPORTER_STATE
IMP_DATE
LOCAL_PORT_POD
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_ADDRESS
SUPPLIER_CITY
SUPPLIER_NAME
TOTAL_WEIGHT
TRANSPORT
UNIT
```
</details>

---

