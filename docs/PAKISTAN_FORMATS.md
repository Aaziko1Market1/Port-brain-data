# Pakistan Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Pakistan.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Pakistan export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | TOTAL_VALUE_FC |
| Pakistan export S.xlsx | EXPORT | SHORT | 14 | 1 | EXPORTER_NAME | HS_CODE | SUMOFTOTAL_VALUE_FC |
| Pakistan Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ADDRESS | HS_CODE | RATE_ASSIGNED_USD |
| Pakistan Import s.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | SUMOFTOTAL_ASSESS_VALUE_USD |

## Detailed Format Analysis

### Pakistan export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXPORTER_NTN, EXP_DATE, EXPORTER_ADDRESS
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_VALUE_FC, TOTAL_VALUE_PAK_RS, UNIT_PRICE_FC, UNIT_VALUE
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME, BUYER_ADDRESS
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_NTN, EXPORTER_ADDRESS

**Config File:** `config/pakistan_export_full.yml`

<details>
<summary>All Columns (27 total)</summary>

```
AGENT_NAME
BUYER_NAME
COUNTRY
COUNTRY_CODE
COUNTRY_ISO_CODE_2
CURRENCY
CURRENCY_CODE
EXPORTER_NAME
EXPORTER_NTN
EXP_DATE
HS_CODE
HS_CODE_2
HS_CODE_4
PORT_OF_SHIPMENT
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SB_NO
TOTAL_VALUE_FC
TOTAL_VALUE_PAK_RS
UNIT
UNIT_PRICE_FC
UNIT_VALUE
HS_CODE_DESCRIPTION
EXPORTER_ADDRESS
BUYER_ADDRESS
```
</details>

---

### Pakistan export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 14

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFTOTAL_VALUE_FC
- 📊 Quantity: SUMOFQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/pakistan_export_short.yml`

<details>
<summary>All Columns (6 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
SUMOFTOTAL_VALUE_FC
SUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Pakistan Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ADDRESS, IMPORTER_NAME, IMPORTER_NTN, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: RATE_ASSIGNED_USD, RATE_DECLARED_USD, TOTAL_ASSESS_VALUE_PAK_RS, TOTAL_ASSESS_VALUE_USD, TOTAL_DCL_VALUE_PAK_RS, TOTAL_DCL_VALUE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_NAME, IMPORTER_NTN
- 🏭 Supplier/Exporter: SUPPLIER_NAME, SUPPLIER_ADDRESS

**Config File:** `config/pakistan_import_full.yml`

<details>
<summary>All Columns (35 total)</summary>

```
AGENT_NAME
BE_TYPE
CASH_NO
COUNTRY_ISO_CODE_2
CURRENCY_CODE
CUSTOMS_DUTY
HS_CODE
HS_CODE_2
HS_CODE_4
IGMNO
IMPORTER_ADDRESS
IMPORTER_NAME
IMPORTER_NTN
IMP_DATE
INCOME_TAX
ORIGIN_COUNTRY
OTHER_TAX
PORTSTR
PRODUCT_DESCRIPTION
QUANTITY
RATE_ASSIGNED_USD
RATE_DECLARED_USD
RECORDS_TAG
RECORD_ID
SALES_TAX
SALES_TAX_ADDITIONAL
SRO
SUPPLIER_NAME
TOTAL_ASSESS_VALUE_PAK_RS
TOTAL_ASSESS_VALUE_USD
TOTAL_DCL_VALUE_PAK_RS
TOTAL_DCL_VALUE_USD
UNIT
HS_CODE_DESCRIPTION
SUPPLIER_ADDRESS
```
</details>

---

### Pakistan Import s.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFTOTAL_ASSESS_VALUE_USD
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/pakistan_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTER_NAME
HS_CODE
SUPPLIER_NAME
ORIGIN_COUNTRY
QUANTITY
PORTSTR
SUMOFTOTAL_ASSESS_VALUE_USD
MONTHYEAR
```
</details>

---

