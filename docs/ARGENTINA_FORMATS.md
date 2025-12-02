# Argentina Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Argentina.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Argentina Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | TOTAL_USD_CIF |
| Argentina Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | SUMOFTOTAL_USD_FOB |
| Argentina Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | CIF_ITEM |
| Argentina Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALQUANTITY |

## Detailed Format Analysis

### Argentina Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXPORT_ID, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_USD_CIF, TOTAL_USD_FOB, USD_CIF_ITEM, USD_FOB_ITEM, USD_FOB_SUB_ITEM
- 📊 Quantity: COMMERCIAL_QUANTITY, GROSS_WEIGHT, QUANTITY_SUB_ITEM
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/argentina_export_full.yml`

<details>
<summary>All Columns (31 total)</summary>

```
ATTRIBUTES
BRAND
COMMERCIAL_QUANTITY
COMMERCIAL_UNIT
COUNTRY_DESTINATION
COUNTRY_ISO_CODE_2
CUSTOM
EXPORTER_NAME
EXPORT_ID
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
INCOTERM
ITEM_NUMBER
NUMBER_OF_PACKAGES
OPERATION_TYPE
PRODUCT_DESCRIPTION
QUANTITY_SUB_ITEM
RECORDS_TAG
RECORD_ID
SUB_ITEM_NUMBER
TOTAL_USD_CIF
TOTAL_USD_FOB
TYPE_OF_TRANSPORT
USD_CIF_ITEM
USD_FOB_ITEM
USD_FOB_SUB_ITEM
VARIETY
HS_CODE_DESCRIPTION
```
</details>

---

### Argentina Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: SUMOFTOTAL_USD_FOB, TOTAL_USD_FOBPERCENTAGE
- 📊 Quantity: SUMOFCOMMERCIAL_QUANTITY, COMMERCIAL_QUANTITYPERCENTAGE
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/argentina_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
SUMOFCOMMERCIAL_QUANTITY
COMMERCIAL_QUANTITYPERCENTAGE
SUMOFTOTAL_USD_FOB
TOTAL_USD_FOBPERCENTAGE
MONTHYEAR
```
</details>

---

### Argentina Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, IMPORT_ID, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_ITEM, FOB_ITEM, FREIGHT_USD, INSURANCE_USD, TOTAL_CIF, TOTAL_FOB, USD_FOB_SUB_ITEM
- 📊 Quantity: COMMERCIAL_QUANTITY, GROSS_WEIGHT, QUANTITY_SUB_ITEM
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN

**Config File:** `config/argentina_import_full.yml`

<details>
<summary>All Columns (39 total)</summary>

```
ADQ_COUNTRY
ATTRIBUTES
BRAND
CIF_ITEM
COMMERCIAL_QUANTITY
COMMERCIAL_UNIT
COUNTRY_ISO_CODE_2
CUSTOM
EMBARQ_PORT
FOB_ITEM
FREIGHT_ITEM
FREIGHT_USD
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_ID
IMPORTER_NAME
IMPORT_ID
IMP_DATE
INCOTERMS
INSURANCE_ITEM
INSURANCE_USD
ITEM_NUMBER
NUMBER_OF_PACKAGES
OPERATION_TYPE
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY_SUB_ITEM
RECORDS_TAG
RECORD_ID
SUB_ITEM_NUMBER
TOTAL_CIF
TOTAL_FOB
TYPE_OF_TRANSPORT
USD_FOB_SUB_ITEM
VARIETY
HS_CODE_DESCRIPTION
IMPORTER_NAME_EN
```
</details>

---

### Argentina Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALQUANTITY, TOTALVALUE, TOTALFOBPERCENTAGE
- 📊 Quantity: TOTALQUANTITY, COMMERCIAL_QUANTITYPERCENTAGE
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/argentina_import_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
HS_CODE
IMPORTER_NAME
TOTALQUANTITY
TOTALVALUE
TOTALFOBPERCENTAGE
COMMERCIAL_QUANTITYPERCENTAGE
MONTHYEAR
```
</details>

---

