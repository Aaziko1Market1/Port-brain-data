#  Venezuela Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for  Venezuela.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| _Venezuela Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | USD_CIF |

## Detailed Format Analysis

### _Venezuela Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_CIF, USD_CIF_BOLIVARES, USD_FOB, USD_FOB_BOLIVARES
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/_venezuela_import_full.yml`

<details>
<summary>All Columns (24 total)</summary>

```
ADQ_COUNTRY
BL
CHAPTER
CHAPTER_DESCRIPTION
COUNTRY_ISO_CODE_2
CUSTOM
EMBARQ_PORT
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_NAME
IMP_DATE
NET_WEIGHT
ORIGIN_COUNTRY
RECORD
RECORDS_TAG
RECORD_ID
TRANSPORT_TYPE
USD_CIF
USD_CIF_BOLIVARES
USD_FOB
USD_FOB_BOLIVARES
```
</details>

---

