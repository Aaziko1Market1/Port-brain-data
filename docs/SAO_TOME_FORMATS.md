# Sao Tome Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Sao Tome.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Sao tome Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME_EN | HS_CODE | TOTALVALUE |
| Sao tome Import S.xlsx | IMPORT | SHORT | 8 | 1 | IMPORTER_NAME_EN | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Sao tome Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME_EN, EXPORTER_CODE
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY, AVERAGEOFUNIT_VALUE_USD
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME_EN
- 🏭 Supplier/Exporter: EXPORTER_NAME_EN, EXPORTER_CODE

**Config File:** `config/sao_tome_export_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
BUYER_NAME_EN
EXPORTER_NAME_EN
EXPORTER_CODE
HS_CODE
ORIGIN_COUNTRY
DESTINATION_COUNTRY
TOTALVALUE
TOTALQUANTITY
AVERAGEOFUNIT_VALUE_USD
MONTHYEAR
```
</details>

---

### Sao tome Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 8

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME_EN

**Config File:** `config/sao_tome_import_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
HS_CODE
ORIGIN_COUNTRY
IMPORTER_NAME_EN
SUPPLIER_NAME_EN
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

