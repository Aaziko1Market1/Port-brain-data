# Venezuela Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Venezuela.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Venezuela Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | USD_FOB |
| Venezuela Export S.xlsx | EXPORT | SHORT | 9 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Venezuela Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | %GTTOTALUSD |

## Detailed Format Analysis

### Venezuela Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_FOB, USD_FOB_BOLIVARE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/venezuela_export_full.yml`

<details>
<summary>All Columns (22 total)</summary>

```
BL
CHAPTER
CHAPTER_DESCRIPTION
COUNTRY_ISO_CODE_2
CUSTOM
DESTINATION_COUNTRY
EMBARQ_PORT
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
NET_WEIGHT
PAYMENT
RECORD
RECORDS_TAG
RECORD_ID
TRANSPORT_TYPE
USD_FOB
USD_FOB_BOLIVARE
```
</details>

---

### Venezuela Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 9

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/venezuela_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
HS_CODE_DESCRIPTION
EXPORTER_NAME
DESTINATION_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Venezuela Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: %GTTOTALUSD, %GTTOTALVALUE, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/venezuela_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
HS_CODE
HS_CODE_DESCRIPTION
IMPORTER_NAME
ORIGIN_COUNTRY
ADQ_COUNTRY
%GTTOTALUSD
%GTTOTALVALUE
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

