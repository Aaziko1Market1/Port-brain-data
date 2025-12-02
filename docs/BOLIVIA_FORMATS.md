# Bolivia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Bolivia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Bolivia Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALQUANTITY |

## Detailed Format Analysis

### Bolivia Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALQUANTITY, TOTALVALUE, %GTTOTALVALUE
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/bolivia_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
HS_CODE
ORIGIN_COUNTRY
TOTALQUANTITY
%GTTOTALQUANTITY
TOTALVALUE
%GTTOTALVALUE
HS_CODE_DESCRIPTION
MONTHYEAR
```
</details>

---

