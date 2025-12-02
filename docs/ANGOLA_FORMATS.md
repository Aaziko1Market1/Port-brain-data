# Angola Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Angola.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Angola Export S.xlsx | EXPORT | SHORT | 4 | 1 | EXPORTER_NAME_EN | HS_CODE | TOTALVALUE |
| Angola Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME_EN | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Angola Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 4

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME_EN

**Config File:** `config/angola_export_short.yml`

<details>
<summary>All Columns (11 total)</summary>

```
EXPORTER_NAME_EN
BUYER_NAME
HS_CODE
HS_CODE_DESCRIPTION_EN
ORIGIN_COUNTRY
LOADING_PORT
DESTINATION_COUNTRY
DESTINATION_PORT
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Angola Import S.xlsx

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
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/angola_import_short.yml`

<details>
<summary>All Columns (11 total)</summary>

```
IMPORTER_NAME_EN
SUPPLIER_NAME
HS_CODE
HS_CODE_DESCRIPTION_EN
ORIGIN_COUNTRY
DESTINATION_COUNTRY
DESTINATION_PORT
LOADING_PORT
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

