# Srilanka Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Srilanka.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Srilanka Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | TOTAL_AMOUNT |
| Srilanka export s.xlsx | EXPORT | SHORT | 56 | 1 | EXPORTER_NAME | HS_CODE | VALUE_IN_USD |
| Srilanka import F (1).xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | TOTAL_AMOUNT |
| Srilanka import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | TOTAL_AMOUNT |
| Srilanka Import s.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALUSD |

## Detailed Format Analysis

### Srilanka Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_AMOUNT, UNIT_PRICE, UNIT_VALUE_USD, VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME, STD_BUYER_NAME, STD_BUYER_ADDRESS, BUYER_UUID
- 🏭 Supplier/Exporter: EXPORTER_NAME, STD_EXPORTER_NAME

**Config File:** `config/srilanka_export_full.yml`

<details>
<summary>All Columns (26 total)</summary>

```
BUYER_NAME
COUNTRY_ISO_CODE_2
CURRENCY
DESTINATION_COUNTRY
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
NET_WEIGHT
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
STD_BUYER_NAME
STD_EXPORTER_NAME
TOTAL_AMOUNT
TRANSPORT
UNIT
UNIT_PRICE
UNIT_VALUE_USD
VALUE_IN_USD
HS_CODE_DESCRIPTION
STD_BUYER_ADDRESS
BUYER_UUID
```
</details>

---

### Srilanka export s.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 56

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: VALUE_IN_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/srilanka_export_short.yml`

<details>
<summary>All Columns (6 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
QUANTITY
VALUE_IN_USD
MONTHYEAR
```
</details>

---

### Srilanka import F (1).xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_AMOUNT, UNIT_PRICE, UNIT_VALUE_USD, VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME, STD_IMPORTER_NAME
- 🏭 Supplier/Exporter: STD_SUPPLIER_NAME, SUPPLIER_NAME, STD_SUPPLIER_ADDRESS, SUPPLIER_UUID

**Config File:** `config/srilanka_import_full.yml`

<details>
<summary>All Columns (26 total)</summary>

```
COUNTRY_ISO_CODE_2
CURRENCY
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_NAME
IMP_DATE
NET_WEIGHT
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
STD_IMPORTER_NAME
STD_SUPPLIER_NAME
SUPPLIER_NAME
TOTAL_AMOUNT
TRANSPORT
UNIT
UNIT_PRICE
UNIT_VALUE_USD
VALUE_IN_USD
HS_CODE_DESCRIPTION
STD_SUPPLIER_ADDRESS
SUPPLIER_UUID
```
</details>

---

### Srilanka import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_AMOUNT, UNIT_PRICE, UNIT_VALUE_USD, VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME, STD_IMPORTER_NAME
- 🏭 Supplier/Exporter: STD_SUPPLIER_NAME, SUPPLIER_NAME, STD_SUPPLIER_ADDRESS, SUPPLIER_UUID

**Config File:** `config/srilanka_import_full.yml`

<details>
<summary>All Columns (26 total)</summary>

```
COUNTRY_ISO_CODE_2
CURRENCY
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_NAME
IMP_DATE
NET_WEIGHT
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
STD_IMPORTER_NAME
STD_SUPPLIER_NAME
SUPPLIER_NAME
TOTAL_AMOUNT
TRANSPORT
UNIT
UNIT_PRICE
UNIT_VALUE_USD
VALUE_IN_USD
HS_CODE_DESCRIPTION
STD_SUPPLIER_ADDRESS
SUPPLIER_UUID
```
</details>

---

### Srilanka Import s.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALUSD, SUMOFUNIT_VALUE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/srilanka_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
SUPPLIER_NAME
HS_CODE
ORIGIN_COUNTRY
QUANTITY
TOTALUSD
SUMOFUNIT_VALUE_USD
IMPORTER_NAME
MONTHYEAR
```
</details>

---

