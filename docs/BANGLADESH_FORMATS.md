# Bangladesh Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Bangladesh.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Bangladesh Export F.xlsx | EXPORT | FULL | 2 | 6 | BE_REGISTRATION_DATE | HS_CODE | ASSESSED_VALUE_IN_TK |
| Bangladesh Export S.xlsx | EXPORT | SHORT | 3 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Bangladesh Import F.xlsx | IMPORT | FULL | 2 | 6 | BILL_OF_ENTRY_DATE | HS_CODE | ASSESSED_UNIT_PRICE_FC |
| Bangladesh Import S.xlsx | IMPORT | SHORT | 35 | 1 | IMPORTERNAME | HSCODE | TOTALWEIGHT |

## Detailed Format Analysis

### Bangladesh Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: BE_REGISTRATION_DATE, EXPORTER_ADDRESS, EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: ASSESSED_VALUE_IN_TK, ASSESSED_VALUE_IN_USD
- 📊 Quantity: GROSS_WT_IN_KG, NET_WT_IN_KG, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ADDRESS, EXPORTER_NAME

**Config File:** `config/bangladesh_export_full.yml`

<details>
<summary>All Columns (24 total)</summary>

```
ASSESSED_VALUE_IN_TK
ASSESSED_VALUE_IN_USD
BE_NUMBER
BE_REGISTRATION_DATE
BIN
BUYER_NAME
COUNTRY_CODE
COUNTRY_ISO_CODE_2
DESTINATION_COUNTRY
EXD_TK
EXPORTER_ADDRESS
EXPORTER_NAME
EXP_DATE
GROSS_WT_IN_KG
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
NET_WT_IN_KG
OFFICE_CODE
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
```
</details>

---

### Bangladesh Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 3

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/bangladesh_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
EXPORTER_NAME
BUYER_NAME
HS_CODE
HS_CODE_DESCRIPTION
TOTALVALUE
%GTTOTALVALUE
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Bangladesh Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: BILL_OF_ENTRY_DATE, EXPORTER_NAME_AND_ADDRESS, IMPORTER_ADDRESS, IMPORTER_NAME, IMP_DATE, INVOICE_NUMBER, INVOICE_VALUE_FC
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: ASSESSED_UNIT_PRICE_FC, ASSESSED_VALUE_TK, ASSESSED_VALUE_USD, CUSTOM_VALUE, DECLARED_UNIT_PRICE_FC, INVOICE_VALUE_FC
- 📊 Quantity: GROSS_WEIGHT_IN_KG, NET_WEIGHT_IN_KG, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME_AND_ADDRESS

**Config File:** `config/bangladesh_import_full.yml`

<details>
<summary>All Columns (39 total)</summary>

```
AGENT_IDENTIFICATION_NUMBER
ASSESSED_UNIT_PRICE_FC
ASSESSED_VALUE_TK
ASSESSED_VALUE_USD
BANK_NAME
BILL_OF_ENTRY
BILL_OF_ENTRY_DATE
BILL_OF_ENTRY_NO
BL_NUMBER
BRANCH_NAME
BUSINESS_IDENTIFICATION_NUMBER
COUNTRY_ISO_CODE_2
COUNTRY_OF_ORIGIN
CPC_CODE_AND_DESCRIPTION
CURRENCY_CODE
CUSTOM_VALUE
DECLARED_UNIT_PRICE_FC
EXCHANGE_RATE
EXPORTER_NAME_AND_ADDRESS
GROSS_WEIGHT_IN_KG
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_ADDRESS
IMPORTER_NAME
IMP_DATE
INVOICE_NUMBER
INVOICE_VALUE_FC
LC_NUMBER
MENIFEST_NO
NAME_OF_CF_AGENT
NET_WEIGHT_IN_KG
OFFICE_CODE_AND_NAME
PRODUCT_DESCRIPTION
PRODUCT_TYPE
QUANTITY
RECORDS_TAG
RECORD_ID
```
</details>

---

### Bangladesh Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 35

**Detected Column Types:**

- 📅 Date: IMPORTERNAME
- 📦 HS Code: HSCODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALWEIGHT, TOTALVALUE, %GTTOTALVALUE
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTERNAME

**Config File:** `config/bangladesh_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTERNAME
HSCODE
HS_CODE_DESCRIPTION
TOTALWEIGHT
%GTTOTALWEIGHT
TOTALVALUE
%GTTOTALVALUE
MONTHYEAR
```
</details>

---

