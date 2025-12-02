# Burundi Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Burundi.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Burundi Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | CIF |
| Burundi Import S.xlsx | IMPORT | SHORT | 47 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Burundi Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMPORTS_DUTY, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, TARIFF_RATE
- 💰 Value: CIF, CIF_USD, FOB, FOB_USD, TOTAL_DUTY_AND_TAXES
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/burundi_import_full.yml`

<details>
<summary>All Columns (32 total)</summary>

```
BUSINESS_TIN
CIF
CIF_USD
COUNTRY_ISO_CODE_2
DESTINATION_COUNTRY
EXCISE_DUTY
FOB
FOB_USD
FREIGHT
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMPORTER_NAME
IMPORTS_DUTY
IMP_DATE
INSURANCE
NET_WEIGHT
NUMBER_OF_PACKAGE
ORIGIN_COUNTRY
OTHER_COSTS
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
TARIFF_RATE
TOTAL_DUTY_AND_TAXES
UNIT
VAT
WHT
```
</details>

---

### Burundi Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 47

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: SUMOFQUANTITY, TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/burundi_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
ORIGIN_COUNTRY
HS_CODE
SUMOFQUANTITY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

