# Uganda Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Uganda.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Uganda Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ID | HS_CODE | CIF_IN_UGX |
| Uganda Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | CIF_IN_USD |
| Uganda Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | CIF_IN_UGX |
| Uganda Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | SUMOFCIF_IN_USD |

## Detailed Format Analysis

### Uganda Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ID, EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_IN_UGX, CIF_IN_USD, TAX_IN_USD, TOTAL_TAX_AMT
- 📊 Quantity: GROSS_WEIGHT_IN_KG, NET_WEIGHT_IN_KG, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME, BUYER_UUID, STD_BUYER_NAME, STD_BUYER_ADDRESS
- 🏭 Supplier/Exporter: EXPORTER_ID, EXPORTER_NAME, STD_EXPORTER_NAME

**Config File:** `config/uganda_export_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
BUYER_NAME
CIF_IN_UGX
CIF_IN_USD
COUNTRY
DESTINATION_COUNTRY
EXPORTER_ID
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT_IN_KG
HS_CODE
HS_CODE_DESCRIPTION
NET_WEIGHT_IN_KG
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
STD_EXPORTER_NAME
TAX_IN_UGX
TAX_IN_USD
TAX_PAYER_TIN
TOTAL_TAX_AMT
UNIT
HS_CODE_2
HS_CODE_4
BUYER_UUID
STD_BUYER_NAME
STD_BUYER_ADDRESS
```
</details>

---

### Uganda Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: CIF_IN_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/uganda_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
HS_CODE_DESCRIPTION
CIF_IN_USD
QUANTITY
MONTHYEAR
```
</details>

---

### Uganda Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_IN_UGX, CIF_IN_USD, TAX_IN_USD, TOTAL_TAX_AMT
- 📊 Quantity: GROSS_WEIGHT_IN_KG, NET_WEIGHT_IN_KG, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, STD_IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME, STD_SUPPLIER_NAME, STD_SUPPLIER_ADDRESS, SUPPLIER_UUID

**Config File:** `config/uganda_import_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
CIF_IN_UGX
CIF_IN_USD
COUNTRY
DESTINATION_COUNTRY
GROSS_WEIGHT_IN_KG
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_ID
IMPORTER_NAME
IMP_DATE
NET_WEIGHT_IN_KG
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
STD_IMPORTER_NAME
SUPPLIER_NAME
TAXPAYER_TIN
TAX_IN_UGX
TAX_IN_USD
TOTAL_TAX_AMT
UNIT
STD_SUPPLIER_NAME
STD_SUPPLIER_ADDRESS
SUPPLIER_UUID
```
</details>

---

### Uganda Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: SUMOFCIF_IN_USD
- 📊 Quantity: SUMOFQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/uganda_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
HS_CODE
HS_CODE_DESCRIPTION
ORIGIN_COUNTRY
SUMOFQUANTITY
SUMOFCIF_IN_USD
MONTHYEAR
```
</details>

---

