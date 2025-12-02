# Cameroon Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Cameroon.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Cameroon Export F.xlsx | EXPORT | FULL | 2 | 6 | DECLARATION_DATE | HS_CODE | TOTAL_VALUE_USD |
| Cameroon Export S.xlsx | EXPORT | SHORT | 7 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Cameroon Import F.xlsx | IMPORT | FULL | 2 | 6 | DECLARATION_DATE | HS_CODE | TOTAL_VALUE_USD |
| Cameroon Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Cameroon Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DECLARATION_DATE, EXPORTER_CODE, EXPORTER_NAME, EXPORT_COUNTRY
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTAL_VALUE_USD, UNIT_VALUE_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_CODE, EXPORTER_NAME

**Config File:** `config/cameroon_export_full.yml`

<details>
<summary>All Columns (39 total)</summary>

```
BUYER_NAME
CODE_TYPE_DEC
COUNTRY_ISO_CODE_2
CURRENCY
CUSTOM_DETAILS
DECLARANT_CODE
DECLARANT_NAME
DECLARATION_DATE
DECLARATION_NUMBER
DESTINATION_COUNTRY
EXPORTER_CODE
EXPORTER_NAME
EXPORT_COUNTRY
FLUX
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
ITEM_NUMBER
NET_WEIGHT
NUMBER_OF_PACKAGES
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REGIME
REGIME_CODE
STATUS_DAU
TAX_ART
TOTAL_VALUE_USD
TYPE_DEC
UNIT
UNIT_VALUE_USD
VAL_FACT_ART
VAL_FACT_DEV
VAL_STAT_ART
```
</details>

---

### Cameroon Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 7

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUEUSD
- 📊 Quantity: SUMOFQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/cameroon_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
BUYER_NAME
EXPORTER_NAME
HS_CODE
ORIGIN_COUNTRY
HS_CODE_DESCRIPTION_EN
TOTALVALUEUSD
SUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Cameroon Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DECLARATION_DATE, EXPORT_COUNTRY, IMPORTER_CODE, IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTAL_VALUE_USD, UNIT_VALUE_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_CODE, IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/cameroon_import_full.yml`

<details>
<summary>All Columns (39 total)</summary>

```
CODE_TYPE_DEC
COUNTRY_ISO_CODE_2
CURRENCY
CUSTOM_DETAILS
DECLARANT_CODE
DECLARANT_NAME
DECLARATION_DATE
DECLARATION_NUMBER
DESTINATION_COUNTRY
EXPORT_COUNTRY
FLUX
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
IMPORTER_CODE
IMPORTER_NAME
ITEM_NUMBER
NET_WEIGHT
NUMBER_OF_PACKAGES
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REGIME
REGIME_CODE
STATUS_DAU
SUPPLIER_NAME
TAX_ART
TOTAL_VALUE_USD
TYPE_DEC
UNIT
UNIT_VALUE_USD
VAL_FACT_ART
VAL_FACT_DEV
VAL_STAT_ART
```
</details>

---

### Cameroon Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUEUSD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/cameroon_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
SUPPLIER_NAME
IMPORTER_NAME
HS_CODE
ORIGIN_COUNTRY
HS_CODE_DESCRIPTION_EN
TOTALVALUEUSD
QUANTITY
MONTHYEAR
```
</details>

---

