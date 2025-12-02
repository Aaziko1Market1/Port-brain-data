# Paraguay Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Paraguay.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Paraguay Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ID | HS_CODE | USD_CIF |
| Paraguay Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Paraguay Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | USD_CIF |
| Paraguay Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Paraguay Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ID, EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_CIF, USD_FOB, USD_FOB_UNIT, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: GROSS_KILO, NET_KILO, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ID, EXPORTER_NAME

**Config File:** `config/paraguay_export_full.yml`

<details>
<summary>All Columns (27 total)</summary>

```
BRAND
BUYER_NAME
CUSTOM
DESTINATION_COUNTRY
EXPORTER_ID
EXPORTER_NAME
EXP_DATE
GROSS_KILO
HS_CODE
HS_CODE_2
HS_CODE_4
MANIFEST
MEASURE_UNIT
NET_KILO
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
TRANSPORT_COMPANY
TRANSPORT_COUNTRY
TRANSPORT_TYPE
USD_CIF
USD_FOB
USD_FOB_UNIT
USD_FREIGHT
USD_INSURANCE
HS_CODE_DESCRIPTION
```
</details>

---

### Paraguay Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/paraguay_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
EXPORTER_NAME
HS_CODE
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Paraguay Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_CIF, USD_FOB, USD_FOB_UNIT, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: GROSS_KILO, NET_KILO, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/paraguay_import_full.yml`

<details>
<summary>All Columns (30 total)</summary>

```
ACQUISITION_COUNTRY
BL_NUMBER
BRAND
CUSTOM
GROSS_KILO
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_ID
IMPORTER_NAME
IMP_DATE
MANIFEST
MEASURE_UNIT
NET_KILO
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
TRANSPORT_COMPANY
TRANSPORT_COUNTRY
TRANSPORT_TYPE
USD_CIF
USD_FOB
USD_FOB_UNIT
USD_FREIGHT
USD_INSURANCE
IMPORTER_NAME_EN
HS_CODE_DESCRIPTION
```
</details>

---

### Paraguay Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/paraguay_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
IMPORTER_NAME
SUPPLIER_NAME
ORIGIN_COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

