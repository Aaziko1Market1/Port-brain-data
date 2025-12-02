# Uruguay Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Uruguay.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Uruguay Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ID | HS_CODE | TOTAL_GROSS_WEIGHT |
| Uruguay Export S.xlsx | EXPORT | SHORT | 9 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Uruguay Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | TOTAL_GROSS_WEIGHT |
| Uruguay Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Uruguay Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ID, EXPORTER_NAME, EXPORT_ID, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_GROSS_WEIGHT, USD_FOB_ITEM, USD_FOB_UNIT
- 📊 Quantity: COMERCIAL_QUANTITY, NET_WEIGHT, STAT_QUANTITY, TOTAL_GROSS_WEIGHT, UNIT_QUANTITY
- 🏭 Supplier/Exporter: EXPORTER_ID, EXPORTER_NAME, VERIF_EXPORTER_ID

**Config File:** `config/uruguay_export_full.yml`

<details>
<summary>All Columns (28 total)</summary>

```
COMERCIAL_QUANTITY
COMERCIAL_UNIT
CUSTOM
DESTINATION_COUNTRY
EXPORTER_ID
EXPORTER_NAME
EXPORT_ID
EXP_DATE
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
INCOTERMS
ITEM
NET_WEIGHT
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
STAT_QUANTITY
STAT_UNIT
TOTAL_GROSS_WEIGHT
TRANSPORT_COMPANY
TRANSPORT_TYPE
TYPE_OF_EXPORT
UNIT_QUANTITY
USD_FOB_ITEM
USD_FOB_UNIT
VERIF_EXPORTER_ID
```
</details>

---

### Uruguay Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 9

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/uruguay_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
EXPORTER_NAME
HS_CODE_DESCRIPTION
DESTINATION_COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Uruguay Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, IMPORT_ID, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_2, HS_CODE_4
- 💰 Value: TOTAL_GROSS_WEIGHT, USD_CIF_ITEM, USD_FOB_ITEM, USD_FOB_UNIT, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: COMERCIAL_QUANTITY, NET_WEIGHT, STAT_QUANTITY, TOTAL_GROSS_WEIGHT, UNIT_QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, VERIF_IMPORTER_ID, IMPORTER_NAME_EN

**Config File:** `config/uruguay_import_full.yml`

<details>
<summary>All Columns (34 total)</summary>

```
ADQUISITION_COUNTRY
COMERCIAL_QUANTITY
COMERCIAL_UNIT
CUSTOM
HS_CODE
HS_CODE_DESCRIPTION
IMPORTER_ID
IMPORTER_NAME
IMPORT_ID
IMP_DATE
INCOTERMS
ITEM
NET_WEIGHT
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
PROVENANCE_COUNTRY
RECORDS_TAG
RECORD_ID
STAT_QUANTITY
STAT_UNIT
TOTAL_GROSS_WEIGHT
TRANSPORT_COMPANY
TRANSPORT_TYPE
TYPE_OF_IMPORT
UNIT_QUANTITY
USD_CIF_ITEM
USD_FOB_ITEM
USD_FOB_UNIT
USD_FREIGHT
USD_INSURANCE
VERIF_IMPORTER_ID
HS_CODE_2
HS_CODE_4
IMPORTER_NAME_EN
```
</details>

---

### Uruguay Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME

**Config File:** `config/uruguay_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
IMPORTER_NAME
ORIGIN_COUNTRY
HS_CODE_DESCRIPTION
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

