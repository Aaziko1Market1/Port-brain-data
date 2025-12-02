# Ivory Coast Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Ivory Coast.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Ivory coast Export F (1).xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_CODE | HS_CODE | CIF_VALUE |
| Ivory coast Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_CODE | HS_CODE | CIF_VALUE |
| Ivory coast Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | SUMOFFOB_VALUE |
| Ivory coast Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_CODE | HS_CODE | CIF_VALUE |
| Ivory coast IMport S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | SUMOFFOB_VALUE |

## Detailed Format Analysis

### Ivory coast Export F (1).xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_CODE, EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, FOB_VALUE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_CODE, EXPORTER_NAME

**Config File:** `config/ivory_coast_export_full.yml`

<details>
<summary>All Columns (33 total)</summary>

```
BUYER_NAME
CIF_VALUE
CODE_MODE_TRANSP_FRONTIERE
CODE_PORT
DESTINATION_COUNTRY
EXPORTER_CODE
EXPORTER_NAME
EXP_DATE
FOB_VALUE
FREIGHT
GEN_CTY_DES_COD
GEN_CTY_FLT
GEN_CTY_ORG
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
INSURANCE
NATURE_COLIS
NET_WEIGHT
NUMBER_OF_PRODUCTS
ORIGIN_COUNTRY
PORT_OR_OFFICE
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
PROVENANCE
QUANTITY
RECORDS_TAG
RECORD_ID
SENS
TRANSPORT_MODE
UNIT
HS_CODE_DESCRIPTION
```
</details>

---

### Ivory coast Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_CODE, EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, FOB_VALUE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_CODE, EXPORTER_NAME

**Config File:** `config/ivory_coast_export_full.yml`

<details>
<summary>All Columns (33 total)</summary>

```
BUYER_NAME
CIF_VALUE
CODE_MODE_TRANSP_FRONTIERE
CODE_PORT
DESTINATION_COUNTRY
EXPORTER_CODE
EXPORTER_NAME
EXP_DATE
FOB_VALUE
FREIGHT
GEN_CTY_DES_COD
GEN_CTY_FLT
GEN_CTY_ORG
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
INSURANCE
NATURE_COLIS
NET_WEIGHT
NUMBER_OF_PRODUCTS
ORIGIN_COUNTRY
PORT_OR_OFFICE
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
PROVENANCE
QUANTITY
RECORDS_TAG
RECORD_ID
SENS
TRANSPORT_MODE
UNIT
HS_CODE_DESCRIPTION
```
</details>

---

### Ivory coast Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFFOB_VALUE
- 📊 Quantity: SUMOFQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/ivory_coast_export_short.yml`

<details>
<summary>All Columns (6 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
SUMOFFOB_VALUE
SUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Ivory coast Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_CODE, IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, FOB_VALUE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_CODE, IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/ivory_coast_import_full.yml`

<details>
<summary>All Columns (33 total)</summary>

```
CIF_VALUE
CODE_MODE_TRANSP_FRONTIERE
CODE_PORT
DESTINATION_COUNTRY
FOB_VALUE
FREIGHT
GEN_CTY_DES_COD
GEN_CTY_FLT
GEN_CTY_ORG
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_CODE
IMPORTER_NAME
IMP_DATE
INSURANCE
NATURE_COLIS
NET_WEIGHT
NUMBER_OF_PRODUCTS
ORIGIN_COUNTRY
PORT_OR_OFFICE
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
PROVENANCE
QUANTITY
RECORDS_TAG
RECORD_ID
SENS
SUPPLIER_NAME
TRANSPORT_MODE
UNIT
HS_CODE_DESCRIPTION
```
</details>

---

### Ivory coast IMport S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFFOB_VALUE
- 📊 Quantity: QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/ivory_coast_import_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
IMPORTER_NAME
HS_CODE
SUPPLIER_NAME
ORIGIN_COUNTRY
QUANTITY
SUMOFFOB_VALUE
MONTHYEAR
```
</details>

---

