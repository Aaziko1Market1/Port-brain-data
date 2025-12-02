# Mongolia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Mongolia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Mongolia Export F.xlsx | EXPORT | FULL | 2 | 6 | EXP_DATE | HS_CODE | AMOUNT_USD |
| Mongolia Export S.xlsx | EXPORT | SHORT | 4 | 1 | EXPORTER_NAME_EN | HS_CODE | TOTALVALUE |
| Mongolia Import F.xlsx | IMPORT | FULL | 2 | 6 | IMP_DATE | HS_CODE | TOTAL_VALUE_IN_USD |
| Mongolia Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME_EN | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Mongolia Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXP_DATE, EXPORTER_NAME, EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN, HS_CODE_2, HS_CODE_4
- 💰 Value: AMOUNT_USD, UNIT_PRICE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME, BUYER_NAME_EN
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_NAME_EN

**Config File:** `config/mongolia_export_full.yml`

<details>
<summary>All Columns (29 total)</summary>

```
RECORD_ID
RECORDS_TAG
EXP_DATE
DECLARATION_NO
EXPORTER_NAME
EXPORTER_NAME_EN
BUYER_NAME
BUYER_NAME_EN
HS_CODE
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
BRAND_MODEL
BRAND_MODEL_EN
MANUFACTURER
MANUFACTURER_EN
QUANTITY
UNIT
UNIT_EN
AMOUNT_USD
UNIT_PRICE_USD
DESTINATION_COUNTRY
DESTINATION_COUNTRY_EN
PORT
INCOTERM
HS_CODE_2
HS_CODE_4
COUNTRY_ISO_CODE_2
```
</details>

---

### Mongolia Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 4

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME_EN
- 🏭 Supplier/Exporter: EXPORTER_NAME_EN

**Config File:** `config/mongolia_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
BUYER_NAME_EN
EXPORTER_NAME_EN
HS_CODE
HS_CODE_DESCRIPTION_EN
PORT
DESTINATION_COUNTRY_EN
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Mongolia Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMP_DATE, IMPORTER_NAME, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN, HS_CODE_2, HS_CODE_4
- 💰 Value: TOTAL_VALUE_IN_USD, UNIT_VALUE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME, SUPPLIER_NAME_EN

**Config File:** `config/mongolia_import_full.yml`

<details>
<summary>All Columns (29 total)</summary>

```
RECORD_ID
RECORDS_TAG
IMP_DATE
DECLARATION_NO
IMPORTER_NAME
IMPORTER_NAME_EN
SUPPLIER_NAME
SUPPLIER_NAME_EN
HS_CODE
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
MODEL_NUMBER
MODEL_NUMBER_EN
MANUFACTUER
MANUFACTUER_EN
QUANTITY
UNIT
UNIT_EN
TOTAL_VALUE_IN_USD
UNIT_VALUE_USD
ORIGIN_COUNTRY
ORIGIN_COUNTRY_EN
PORT
INCOTERM
HS_CODE_2
HS_CODE_4
COUNTRY_ISO_CODE_2
```
</details>

---

### Mongolia Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME_EN

**Config File:** `config/mongolia_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTER_NAME_EN
SUPPLIER_NAME_EN
ORIGIN_COUNTRY_EN
HS_CODE
HS_CODE_DESCRIPTION_EN
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

