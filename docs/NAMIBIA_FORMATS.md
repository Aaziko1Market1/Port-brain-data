# Namibia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Namibia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Namibia Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ADDRESS | HS_CODE | CIF_VALUE |
| Namibia Export S.xlsx | EXPORT | SHORT | 2 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Namibia Import F.xlsx | IMPORT | FULL | 2 | 6 | EXPORTING_COUNTRY | HS_CODE | CIF_VALUE |
| Namibia IMport S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Namibia Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ADDRESS, EXPORTER_NAME, EXPORTING_COUNTRY, EXP_DATE, INVOICE_VALUE_FOB, REGISTRATION_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, CIF_VALUE_IN_USD, FOB_VALUE_IN_USD, INVOICE_VALUE_FOB
- 📊 Quantity: NET_WEIGHT
- 🏢 Buyer/Importer: BUYER_ADDRESS, BUYER_NAME, STD_BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ADDRESS, EXPORTER_NAME, STD_EXPORTER_NAME

**Config File:** `config/namibia_export_full.yml`

<details>
<summary>All Columns (30 total)</summary>

```
ASSESSMENT_NUMBER
BUYER_ADDRESS
BUYER_NAME
CIF_VALUE
CIF_VALUE_IN_USD
DESTINATION_COUNTRY
EXPORTER_ADDRESS
EXPORTER_NAME
EXPORTING_COUNTRY
EXP_DATE
EXTENDED_PROCEDURE
FOB_VALUE_IN_USD
HS_CODE
HS_CODE_2
HS_CODE_4
INVOICE_VALUE_FOB
ITEM_NUMBER
NATIONAL_PROCEDURE
NET_WEIGHT
OFFICE_OF_EXIT_ENTRY
ORIGIN_COUNTRY
PACKAGE
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
REGISTRATION_DATE
REGISTRATION_NUMBER
STD_BUYER_NAME
STD_EXPORTER_NAME
HS_CODE_DESCRIPTION
```
</details>

---

### Namibia Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/namibia_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
TOTALVALUE
%GTTOTALVALUE
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Namibia Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTING_COUNTRY, IMPORTER_ADDRESS, IMPORTER_NAME, IMP_DATE, REGISTRATION_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, CIF_VALUE_IN_USD, FOB_VALUE, FOB_VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_NAME, STD_IMPORTER_NAME
- 🏭 Supplier/Exporter: STD_SUPPLIER_NAME, SUPPLIER_ADDRESS, SUPPLIER_NAME

**Config File:** `config/namibia_import_full.yml`

<details>
<summary>All Columns (32 total)</summary>

```
ASSESSMENT_NUMBER
CIF_VALUE
CIF_VALUE_IN_USD
DESTINATION_COUNTRY
EXPORTING_COUNTRY
EXTENDED_PROCEDURE
FOB_VALUE
FOB_VALUE_IN_USD
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_ADDRESS
IMPORTER_NAME
IMP_DATE
ITEM
MODEL
NATIONAL_PROCEDURE
NET_WEIGHT
OFFICE
ORIGIN_COUNTRY
PACKAGE
PRODUCT_DESCRIPTION
RECORD_ID
REGISTRATION_DATE
REGISTRATION_NUMBER
STD_IMPORTER_NAME
STD_SUPPLIER_NAME
SUPPLIER_ADDRESS
SUPPLIER_NAME
RECORDS_TAG
```
</details>

---

### Namibia IMport S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/namibia_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
HS_CODE
TOTALVALUE
%GTTOTALVALUE
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

