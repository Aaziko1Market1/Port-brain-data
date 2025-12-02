# Dominican Republic Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Dominican Republic.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Dominican republic Export F.xlsx | EXPORT | FULL | 2 | 6 | DECLARATION_DATE | HS_CODE | USD_FOB |
| Dominican republic Export S.xlsx | EXPORT | SHORT | 40 | 1 | EXPORTER_NAME | HS_CODE | TOTAL_VALUE_USD |
| Dominican republic Import F.xlsx | IMPORT | FULL | 2 | 6 | DECLARATION_DATE | HS_CODE | USD_FOB |
| Dominican republic Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTAL_VALUE_USD |

## Detailed Format Analysis

### Dominican republic Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DECLARATION_DATE, SETTLEMENT_DATE, EXPORTER_NAME, EXPORTER_NAME_EN, SHIPPING_LINE_CODE, SHIPPING_LINE_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_2, HS_CODE_4
- 💰 Value: USD_FOB, UNIT_FOB_USD, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: QUANTITY, NET_WEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: RUC_EXPORTER_ID, EXPORTER_NAME, EXPORTER_NAME_EN

**Config File:** `config/dominican_republic_export_full.yml`

<details>
<summary>All Columns (31 total)</summary>

```
RECORD_ID
RECORDS_TAG
DECLARATION_DATE
CUSTOMS_CLEARANCE
CUSTOMS_CLEARANCE_EN
SETTLEMENT_DATE
DESTINATION_COUNTRY
HS_CODE
HS_CODE_DESCRIPTION
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
QUANTITY
UNIT
NET_WEIGHT
USD_FOB
UNIT_FOB_USD
USD_FREIGHT
USD_INSURANCE
RUC_EXPORTER_ID
EXPORTER_NAME
EXPORTER_NAME_EN
REGIME_CODE
REGIME_NAME
BUYER_NAME
SHIPPING_LINE_CODE
SHIPPING_LINE_NAME
DESTINATION_CONTINENT_NAME
DESTINATION_REGION_NAME
HS_CODE_2
HS_CODE_4
COUNTRY_ISO_CODE_2
```
</details>

---

### Dominican republic Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 40

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTAL_VALUE_USD, TOTAL_QUANTITY
- 📊 Quantity: TOTAL_QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/dominican_republic_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
DESTINATION_COUNTRY
TOTAL_VALUE_USD
TOTAL_QUANTITY
MONTHYEAR
```
</details>

---

### Dominican republic Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DECLARATION_DATE, IMPORTER_NAME, IMPORTER_NAME_EN, SETTLEMENT_DATE
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN, HS_CODE_2, HS_CODE_4
- 💰 Value: USD_FOB, USD_FREIGHT, USD_INSURANCE, USD_OTHERS, USD_CIF, UNIT_CIF_USD, CIF_RD, TOTAL_PAGAR_RD
- 📊 Quantity: QUANTITY, NET_WEIGHT, GROSS_WEIGHT
- 🏢 Buyer/Importer: RUC_IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/dominican_republic_import_full.yml`

<details>
<summary>All Columns (41 total)</summary>

```
RECORD_ID
RECORDS_TAG
DECLARATION_DATE
CUSTOMS_CLEARANCE
CUSTOMS_CLEARANCE_EN
RUC_IMPORTER_ID
IMPORTER_NAME
IMPORTER_NAME_EN
SUPPLIER_NAME
HS_CODE
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
QUANTITY
UNIT
NET_WEIGHT
GROSS_WEIGHT
USD_FOB
USD_FREIGHT
USD_INSURANCE
USD_OTHERS
USD_CIF
UNIT_CIF_USD
ITEM_NUMBER
CIF_RD
TOTAL_PAGAR_RD
SETTLEMENT_DATE
PROCEDENCE
ORIGIN_COUNTRY
MODEL
REGIME
COLOR
CUSTOMS_AGENCY
CUSTOMS_AGENCY_EN
DESCRIPTION_OF_THE_SECTION
SECTION
SECTION_DESCRIPTION
HS_CODE_2
HS_CODE_4
COUNTRY_ISO_CODE_2
```
</details>

---

### Dominican republic Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTAL_VALUE_USD, TOTAL_QUANTITY, AVG_UNITPRICE
- 📊 Quantity: TOTAL_QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/dominican_republic_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
HS_CODE
HS_CODE_DESCRIPTION_EN
ORIGIN_COUNTRY
TOTAL_VALUE_USD
TOTAL_QUANTITY
AVG_UNITPRICE
MONTHYEAR
```
</details>

---

