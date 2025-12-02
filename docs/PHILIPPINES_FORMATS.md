# Philippines Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Philippines.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Philippines export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ADDRESS | HS_CODE | FOB_VALUE |
| Philippines export S.xlsx | EXPORT | SHORT | 10 | 1 | EXPORTER_NAME | HS_CODE | FOB_VALUE |
| Philippines Import F.xlsx | IMPORT | FULL | 2 | 6 | EXPORT_COUNTRY | HS_CODE | CIF_VALUE_USD |
| Philippines import s.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | SUMOFFOB_VALUE_USD |

## Detailed Format Analysis

### Philippines export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ADDRESS, EXPORTER_NAME, EXPORT_COUNTRY, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: FOB_VALUE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY_OF_PACKAGE
- 🏢 Buyer/Importer: BUYER_ADDRESS, BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ADDRESS, EXPORTER_NAME

**Config File:** `config/philippines_export_full.yml`

<details>
<summary>All Columns (22 total)</summary>

```
DESTINATION_COUNTRY
BUYER_ADDRESS
BUYER_NAME
COUNTRY_ISO_CODE_2
CURRENCY
EXPORTER_ADDRESS
EXPORTER_NAME
EXPORT_COUNTRY
EXP_DATE
FOB_VALUE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
INCOTERMS
NET_WEIGHT
PACKAGE_UNIT
PRODUCT_DESCRIPTION
QUANTITY_OF_PACKAGE
RECORDS_TAG
RECORD_ID
HS_CODE_DESCRIPTION
```
</details>

---

### Philippines export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 10

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: FOB_VALUE
- 📊 Quantity: QUANTITY_OF_PACKAGE
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/philippines_export_short.yml`

<details>
<summary>All Columns (6 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
FOB_VALUE
QUANTITY_OF_PACKAGE
MONTHYEAR
```
</details>

---

### Philippines Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORT_COUNTRY, IMPORTER_ADDRESS, IMPORTER_EMAIL, IMPORTER_NAME, IMPORTER_TELEPHONE, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE_USD, FOB_VALUE_USD, FREIGHT_USD, INSURANCE_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY, QUANTITY_OF_PACKAGE, QUANTITY_UNIT
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_EMAIL, IMPORTER_NAME, IMPORTER_TELEPHONE
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/philippines_import_full.yml`

<details>
<summary>All Columns (31 total)</summary>

```
BL_NO
CIF_VALUE_USD
COUNTRY_ISO_CODE_2
DESTINATION_COUNTRY
EXPORT_COUNTRY
FOB_VALUE_USD
FREIGHT_USD
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_ADDRESS
IMPORTER_EMAIL
IMPORTER_NAME
IMPORTER_TELEPHONE
IMP_DATE
INCOTERMS
INSURANCE_USD
NET_WEIGHT
ORIGIN_COUNTRY
PACKAGE_UNIT
PORT
PRODUCT_DESCRIPTION
QUANTITY
QUANTITY_OF_PACKAGE
QUANTITY_UNIT
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
VESSEL_NAME
HS_CODE_DESCRIPTION
```
</details>

---

### Philippines import s.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFFOB_VALUE_USD, SUMOFCIF_VALUE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/philippines_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
HS_CODE
SUPPLIER_NAME
ORIGIN_COUNTRY
QUANTITY
PORT
SUMOFFOB_VALUE_USD
SUMOFCIF_VALUE_USD
MONTHYEAR
```
</details>

---

