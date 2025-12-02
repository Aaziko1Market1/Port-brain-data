# Malawi Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Malawi.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Malawi Export S.xlsx | EXPORT | SHORT | 1 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |
| Malawi Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Malawi Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, EXPORTER_NAME, EXPORTER_CODE
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY, AVERAGEOFUNIT_VALUE_USD
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_CODE

**Config File:** `config/malawi_export_short.yml`

<details>
<summary>All Columns (11 total)</summary>

```
IMPORTER_NAME
EXPORTER_NAME
EXPORTER_CODE
HS_CODE
ORIGIN_COUNTRY
OFFICE
DESTINATION_COUNTRY
TOTALVALUE
TOTALQUANTITY
AVERAGEOFUNIT_VALUE_USD
MONTHYEAR
```
</details>

---

### Malawi Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY, AVGUNITPRICEUSD
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/malawi_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
OFFICE
ORIGIN_COUNTRY
HS_CODE
TPIN
TOTALVALUE
TOTALQUANTITY
AVGUNITPRICEUSD
MONTHYEAR
```
</details>

---

