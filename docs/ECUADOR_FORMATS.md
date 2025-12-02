# Ecuador Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Ecuador.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Equador Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ID | HS_CODE | USD_FOB |
| Equador Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Equador Import F.xlsx | IMPORT | FULL | 2 | 6 | ARRIVAL_DATE | HS_CODE | USD_CIF |

## Detailed Format Analysis

### Equador Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ID, EXPORTER_NAME, EXPORT_TYPE, EXP_DATE, SHIP, SHIPPING_AGENCY
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_FOB
- 📊 Quantity: NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ID, EXPORTER_NAME

**Config File:** `config/ecuador_export_full.yml`

<details>
<summary>All Columns (32 total)</summary>

```
BL_NUMBER
BUYER_NAME
CONDITION
CONOCIMIENTO_EMB
CONTAINER
CUSTOMS
CUSTOMS_AGENCY
CUSTOMS_AGENT
DESTINATION_COUNTRY
EXPORTER_ID
EXPORTER_NAME
EXPORT_TYPE
EXP_DATE
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
ITEM_NUMBER
LOADING_PORT
NET_WEIGHT
PACKAGES
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REFRENDO
SHIP
SHIPPING_AGENCY
TRANSPORT_TYPE
UNIT
USD_FOB
DECLARATION_NUMBER_DAU
```
</details>

---

### Equador Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUEUSD, %GTSUMOFUSD_FOB
- 📊 Quantity: SUMOFQUANTITY, %GTSUMOFQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/ecuador_export_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
BUYER_NAME
EXPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
DESTINATION_COUNTRY
TOTALVALUEUSD
%GTSUMOFUSD_FOB
SUMOFQUANTITY
%GTSUMOFQUANTITY
MONTHYEAR
```
</details>

---

### Equador Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: ARRIVAL_DATE, IMPORTER_ID, IMPORTER_NAME, IMPORT_TYPE, IMP_DATE, SHIP, SHIPPING_AGENCY, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_CIF, USD_FOB, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/ecuador_import_full.yml`

<details>
<summary>All Columns (42 total)</summary>

```
AD_VALOREM_RATE
ARRIVAL_DATE
BL_NUMBER
BRAND
COMMERCIAL_DEPOSIT
CONDITION
CONOCIMIENTO_EMB
CONTAINER
CUSTOMS
CUSTOMS_AGENCY
CUSTOMS_AGENT
DECLARATION_NUMBER_DAU
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_ID
IMPORTER_NAME
IMPORT_TYPE
IMP_DATE
ITEM_NUMBER
LOADING_COUNTRY
LOADING_PORT
NET_WEIGHT
ORIGIN_COUNTRY
PACKAGES
PROCEDENCE_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
REFRENDO
SHIP
SHIPPING_AGENCY
SUPPLIER_NAME
TRANSPORT_TYPE
UNIT
USD_CIF
USD_FOB
USD_FREIGHT
USD_INSURANCE
IMPORTER_NAME_EN
```
</details>

---

