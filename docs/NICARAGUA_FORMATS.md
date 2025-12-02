# Nicaragua Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Nicaragua.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Nicaragua Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER NAME EN | HS CODE | FOB VALUE |
| Nicaragua Export S.xlsx | EXPORT | SHORT | 5 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Nicaragua Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER NAME EN | HS CODE | FOB VALUE |
| Nicaragua Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Nicaragua Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER NAME EN, EXPORTER NAME, EXP DATE
- 📦 HS Code: HS CODE, HS CODE 2, HS CODE 4
- 💰 Value: FOB VALUE
- 📊 Quantity: GROSS WEIGHT, NET WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER NAME EN, BUYER NAME
- 🏭 Supplier/Exporter: EXPORTER NAME EN, EXPORTER NAME

**Config File:** `config/nicaragua_export_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
HS CODE
PRODUCT DESCRIPTION EN
TAX ID
EXPORTER NAME EN
BUYER NAME EN
GROSS WEIGHT
NET WEIGHT
FOB VALUE
QUANTITY
UNIT MEASURE 1
CUSTOM EN
DESTINATION COUNTRY EN
EXPORTER NAME
BUYER NAME
EXP DATE
PRODUCT DESCRIPTION
UNIT OF MEASUREMENT 1 EN
UNIT MEASURE 2
UNIT OF MEASUREMENT 2 EN
CORRELATIVE
INSURANCE POLICY NUMBER
CUSTOM SEAL
CUSTOM AGENCY ID
CUSTOM AGENCY NAME
CUSTOM AGENCY NAME EN
HS CODE 2
HS CODE 4
COUNTRY ISO CODE 2
```
</details>

---

### Nicaragua Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 5

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY, TOTALWEIGHT
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY, TOTALWEIGHT, %GTTOTALWEIGHT
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/nicaragua_export_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
HS_CODE
EXPORTER_NAME
DESTINATION_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
%GTTOTALQUANTITY
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Nicaragua Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER NAME EN, IMP DATE, IMPORTER NAME
- 📦 HS Code: HS CODE, HS CODE 2, HS CODE 4
- 💰 Value: FOB VALUE, CIF VALUE, FREIGHT VALUE, INSURANCE VALUE, OTHER EXPENDITURES VALUE, TAXABLE VALUE, NOT TAXABLE VALUE, TOTAL CUSTOM VALUE
- 📊 Quantity: NET WEIGHT, GROSS WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER NAME EN, IMPORTER NAME
- 🏭 Supplier/Exporter: SUPPLIER NAME EN, SUPPLIER NAME

**Config File:** `config/nicaragua_import_full.yml`

<details>
<summary>All Columns (40 total)</summary>

```
HS CODE
PRODUCT DESCRIPTION EN
TAX ID
IMPORTER NAME EN
SUPPLIER NAME EN
NET WEIGHT
GROSS WEIGHT
FOB VALUE
CIF VALUE
QUANTITY
UNIT MEASURE 1
UNIT OF MEASUREMENT 1 EN
CUSTOM EN
ORIGIN COUNTRY EN
ACQUISITION COUNTRY EN
IMP DATE
IMPORTER NAME
UNIT MEASURE 2
UNIT OF MEASUREMENT 2 EN
CORRELATIVE
INSURANCE POLICY NUMBER
CUSTOM SEAL
SUPPLIER NAME
FREIGHT VALUE
INSURANCE VALUE
OTHER EXPENDITURES VALUE
PRODUCT DESCRIPTION
CUSTOM AGENCY ID
CUSTOM AGENCY NAME
CUSTOM AGENCY NAME EN
MODEL
SAD LOC GOODS
COLOUR
COLOUR EN
TAXABLE VALUE
NOT TAXABLE VALUE
TOTAL CUSTOM VALUE
HS CODE 2
HS CODE 4
COUNTRY ISO CODE 2
```
</details>

---

### Nicaragua Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY, TOTALWEIGHT
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY, TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/nicaragua_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
IMPORTER_NAME
ORIGIN_COUNTRY_EN
HS_CODE
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
%GTTOTALQUANTITY
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

