# Ethiopia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Ethiopia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Ethiopia Export F.xlsx | EXPORT | FULL | 1 | 6 | EXPORTER_NAME | HS_CODE | TOTAL_VALUE_ETB |
| Ethiopia Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME | HS_CODE | SUMOFTOTAL_VALUE_USD |
| Ethiopia Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | TOTAL_TAX_ETB |
| Ethiopia import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Ethiopia Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXP_DATE, REG_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: TOTAL_VALUE_ETB, TOTAL_VALUE_USD, USD_PER_KG
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT_KG, QUANTITY, USD_PER_KG
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/ethiopia_export_full.yml`

<details>
<summary>All Columns (22 total)</summary>

```
BUYER_NAME
CATEGORY
COUNTRY
COUNTRY_ISO_CODE_2
CUSTOMS_OFFICE
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
NET_WEIGHT_KG
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REG_DATE
TOTAL_VALUE_ETB
TOTAL_VALUE_USD
UNIT
USD_PER_KG
```
</details>

---

### Ethiopia Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFTOTAL_VALUE_USD
- 📊 Quantity: SUMOFQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/ethiopia_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
HS_DESCRIPTION
SUMOFTOTAL_VALUE_USD
SUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Ethiopia Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: TOTAL_TAX_ETB, TOTAL_TAX_USD, TOTAL_VALUE_ETB, TOTAL_VALUE_USD
- 📊 Quantity: GROSS_WEIGHT_KG, NET_WEIGHT_KG, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/ethiopia_import_full.yml`

<details>
<summary>All Columns (20 total)</summary>

```
CONSIGNMENT_COUNTRY
COUNTRY_ISO_CODE_2
CUSTOMS_PROCEDURE_CODE
GROSS_WEIGHT_KG
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMPORTER_NAME
IMP_DATE
NET_WEIGHT_KG
ORIGIN_COUNTRY
QUANTITY
RECORDS_TAG
RECORD_ID
TOTAL_TAX_ETB
TOTAL_TAX_USD
TOTAL_VALUE_ETB
TOTAL_VALUE_USD
UNIT
```
</details>

---

### Ethiopia import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/ethiopia_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
HS_CODE
HS_DESCRIPTION
ORIGIN_COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

