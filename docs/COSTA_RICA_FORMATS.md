# Costa Rica Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Costa Rica.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Costarica Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | FOB_UNIT_USD |
| Costarica Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | %GTSUMOFFOB_USD |
| Costarica Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | CIF_UNIT_USD |
| Costarica IMport S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Costarica Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXP_DATE, EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: FOB_UNIT_USD, FOB_USD
- 📊 Quantity: GROSS_KG, NET_KG, QUANTITY
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_NAME_EN

**Config File:** `config/costa_rica_export_full.yml`

<details>
<summary>All Columns (32 total)</summary>

```
AGENT_NAME
COD_LOC
COUNTRY_ISO_CODE_2
CUSTOMS
DECLARANT
DECLARATION_NUMBER
DESTINATION_COUNTRY
DUA_NUMBER
EXPORTER_NAME
EXP_DATE
FOB_UNIT_USD
FOB_USD
GROSS_KG
HS_CODE
HS_CODE_2
HS_CODE_4
ITEM
LOCATION
MODALITY
NET_KG
NUMBER_AGENT
PACKAGES
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REGIME
RUC
TRANSPORTATION_MODE
UNIT
HS_CODE_DESCRIPTION
EXPORTER_NAME_EN
```
</details>

---

### Costarica Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: %GTSUMOFFOB_USD, SUMOFFOB_USD
- 📊 Quantity: QUANTITY, %GTSUMOFQUANTITY
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/costa_rica_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
HS_CODE
QUANTITY
AGENT_NAME
%GTSUMOFFOB_USD
SUMOFFOB_USD
%GTSUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Costarica Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_UNIT_USD, CIF_USD, FOB_UNIT_USD, FOB_USD, FREIGHT_USD, INSURANCE_USD, VADUANA_USD
- 📊 Quantity: GROSS_KG, NET_KG, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME, IMPORTER_NAME_EN

**Config File:** `config/costa_rica_import_full.yml`

<details>
<summary>All Columns (41 total)</summary>

```
ACQUISITION_COUNTRY
AGENT_NAME
CIF_UNIT_USD
CIF_USD
COD_LOC
COUNTRY_ISO_CODE_2
CUSTOMS
DECLARANT
DECLARATION_NUMBER
DUA_NUMBER
FOB_UNIT_USD
FOB_USD
FOREIGN_COUNTRY
FREIGHT_USD
GROSS_KG
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_NAME
IMP_DATE
INSURANCE_USD
ITEM
LOCATION
MODALITY
NET_KG
NUMBER_AGENT
ORIGIN_COUNTRY
PACKAGES
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REGIME
RUC
TRANSPORTATION_MODE
UNIT
UVF
VADUANA_USD
VOLPHYSICAL
HS_CODE_DESCRIPTION
IMPORTER_NAME_EN
```
</details>

---

### Costarica IMport S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/costa_rica_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
ORIGIN_COUNTRY
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

