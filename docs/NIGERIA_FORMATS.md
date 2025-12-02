# Nigeria Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Nigeria.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Nigeria Export F.xlsx | EXPORT | FULL | 1 | 6 | EXPORTER_NAME | HS_CODE | CIF_IN_NIGERIA |
| Nigeria Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Nigeria Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | CIF_IN_NIGERIA |
| Nigeria Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Nigeria Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, REGISTRY_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_IN_NIGERIA, CIF_USD, FOB_IN_FC, FOB_IN_NIGERIA, FOB_USD
- 📊 Quantity: NET_WEIGHT_IN_KG, QUANTITY
- 🏢 Buyer/Importer: BUYER_ADDRESS, BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/nigeria_export_full.yml`

<details>
<summary>All Columns (26 total)</summary>

```
AGENT_NAME
BUYER_ADDRESS
BUYER_NAME
CIF_IN_NIGERIA
CIF_USD
CPC
CURRENCY
CURRENCY_RATE
CUSTOMS
DESTINATION_COUNTRY
EXPORTER_NAME
FOB_IN_FC
FOB_IN_NIGERIA
FOB_USD
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
ITEMS
NET_WEIGHT_IN_KG
QUANTITY
RECORDS_TAG
RECORD_ID
REGISTRY_DATE
SERVICE
VESSEL
```
</details>

---

### Nigeria Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY, %GTTOTALVALUE
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/nigeria_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
TOTALVALUE
TOTALQUANTITY
%GTTOTALVALUE
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

### Nigeria Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, RECEIPT_DATE, REGISTRY_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_IN_NIGERIA, CIF_USD, FOB_IN_NIGERIA, FOB_USD
- 📊 Quantity: VOLUME_KG
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/nigeria_import_full.yml`

<details>
<summary>All Columns (25 total)</summary>

```
CIF_IN_NIGERIA
CIF_USD
CONTAINER_NUMBER
CUSTOM
FOB_IN_NIGERIA
FOB_USD
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMPORTER_ID
IMPORTER_NAME
ITEMS
ITEMS_CNT
ORIGIN_COUNTRY
RECEIPT
RECEIPT_DATE
RECORDS_TAG
RECORD_ID
REGISTRY
REGISTRY_DATE
SUPPLIER_NAME
SUPPLY_COUNTRY
TAX_NIGERIA
VOLUME_KG
```
</details>

---

### Nigeria Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, %GTTOTALVALUE
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/nigeria_import_short.yml`

<details>
<summary>All Columns (6 total)</summary>

```
HS_CODE
IMPORTER_NAME
SUPPLIER_NAME
TOTALVALUE
%GTTOTALVALUE
MONTHYEAR
```
</details>

---

