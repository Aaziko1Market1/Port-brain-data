# Ghana Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Ghana.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Ghana Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | CIF_VALUE_FCY |
| Ghana export s.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Ghana Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | CIF_VALUE_FCY |
| Ghana Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Ghana Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXPORTER_TIN, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_VALUE_FCY, CIF_VALUE_NCY, FOB_FCY, FOB_IN_USD, FOB_NCY, TAX_AMOUNT_PAYABLE_GHS, UNIT_VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT_KGS, ITEM_QUANTITY, ITEM_QUANTITY_TYPE, NET_WEIGHT_KGS
- 🏢 Buyer/Importer: BUYER_NAME, BUYER_TIN, CONSIGNEE_NAME, CONSIGNEE_TIN
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_TIN

**Config File:** `config/ghana_export_full.yml`

<details>
<summary>All Columns (34 total)</summary>

```
BOE_NO
BUYER_NAME
BUYER_TIN
CIF_VALUE_FCY
CIF_VALUE_NCY
CONSIGNEE_NAME
CONSIGNEE_TIN
COUNTRY_ISO_CODE_2
COUNTRY_OF_ORIGIN
CURRENCY_CODE
DECLARANT_NAME
DECLARANT_TIN
DESTINATION_COUNTRY
EXCHANGE_RATE
EXPORTER_NAME
EXPORTER_TIN
EXP_DATE
FOB_FCY
FOB_IN_USD
FOB_NCY
GROSS_WEIGHT_KGS
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
ITEM_NO
ITEM_QUANTITY
ITEM_QUANTITY_TYPE
NET_WEIGHT_KGS
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
TAX_AMOUNT_PAYABLE_GHS
UNIT_VALUE_IN_USD
```
</details>

---

### Ghana export s.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTSUMOFFOB_IN_USD, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/ghana_export_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
BUYER_NAME
EXPORTER_NAME
HS_CODE
HS_DESCRIPTION
COUNTRY_OF_ORIGIN
TOTALVALUEUSD
%GTSUMOFFOB_IN_USD
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

### Ghana Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMPORTER_TIN, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF_VALUE_FCY, CIF_VALUE_IN_USD, CIF_VALUE_NCY, FOB_FCY, FOB_NCY, TAX_AMOUNT_PAYABLE_GHS, UNIT_VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT_KGS, ITEM_QUANTITY, ITEM_QUANTITY_TYPE, NET_WEIGHT_KGS
- 🏢 Buyer/Importer: CONSIGNEE_NAME, CONSIGNEE_TIN, IMPORTER_NAME, IMPORTER_TIN
- 🏭 Supplier/Exporter: SUPPLIER_NAME, SUPPLIER_TIN

**Config File:** `config/ghana_import_full.yml`

<details>
<summary>All Columns (34 total)</summary>

```
BOE_NO
CIF_VALUE_FCY
CIF_VALUE_IN_USD
CIF_VALUE_NCY
CONSIGNEE_NAME
CONSIGNEE_TIN
COUNTRY_ISO_CODE_2
COUNTRY_OF_CONSIGNMENT
CURRENCY_CODE
DECLARANT_NAME
DECLARANT_TIN
EXCHANGE_RATE
FOB_FCY
FOB_NCY
GROSS_WEIGHT_KGS
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMPORTER_NAME
IMPORTER_TIN
IMP_DATE
ITEM_NO
ITEM_QUANTITY
ITEM_QUANTITY_TYPE
NET_WEIGHT_KGS
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
SUPPLIER_TIN
TAX_AMOUNT_PAYABLE_GHS
UNIT_VALUE_IN_USD
```
</details>

---

### Ghana Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/ghana_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
SUPPLIER_NAME
IMPORTER_NAME
ORIGIN_COUNTRY
HS_CODE
HS_DESCRIPTION
TOTALVALUEUSD
%GTTOTALUSD
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

