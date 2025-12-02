# Colombia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Colombia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Colombia Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_ADDRESS | HS_CODE | USD_FOB |
| Colombia Export S.xlsx | EXPORT | SHORT | 100 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUE |
| Colombia IMport F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ADDRESS | HS_CODE | USD_CIF |
| Colombia Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Colombia Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_ADDRESS, EXPORTER_ID, EXPORTER_NAME, EXP_DATE, SHIPMENT_AUTHORIZATION
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_FOB, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: QUANTITY, WEIGHT
- 🏢 Buyer/Importer: BUYER_ADDRESS, BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_ADDRESS, EXPORTER_ID, EXPORTER_NAME

**Config File:** `config/colombia_export_full.yml`

<details>
<summary>All Columns (27 total)</summary>

```
BUYER_ADDRESS
BUYER_NAME
CONTROL_ID
COUNTRY_ISO_CODE_2
CUSTOM
DEPARTMENT_DESTINATION
DESTINATION_COUNTRY
EXPORTER_ADDRESS
EXPORTER_ID
EXPORTER_NAME
EXP_DATE
HS_CODE
HS_CODE_2
HS_CODE_4
METHOD_OF_PAYMENT
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SHIPMENT_AUTHORIZATION
TYPE_OF_TRANSPORT
UNIT
USD_FOB
USD_FREIGHT
USD_INSURANCE
WEIGHT
HS_CODE_DESCRIPTION
```
</details>

---

### Colombia Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUE, %GTTOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/colombia_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
EXPORTER_NAME
HS_CODE
DESTINATION_COUNTRY
HS_CODE_DESCRIPTION
TOTALVALUE
%GTTOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Colombia IMport F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ADDRESS, IMPORTER_ID, IMPORTER_NAME, IMPORTER_PHONE, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: USD_CIF, USD_FOB, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: QUANTITY, WEIGHT
- 🏢 Buyer/Importer: IMPORTER_ADDRESS, IMPORTER_ID, IMPORTER_NAME, IMPORTER_PHONE, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_ADDRESS, SUPPLIER_CITY, SUPPLIER_COUNTRY, SUPPLIER_NAME, SUPPLIER_PHONE_E_MAIL

**Config File:** `config/colombia_import_full.yml`

<details>
<summary>All Columns (36 total)</summary>

```
CONTROL_ID
COUNTRY_ISO_CODE_2
COUNTRY_OF_ACQUISITION
CUSTOM
DEPARTMENT_DESTINATION
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_ADDRESS
IMPORTER_ID
IMPORTER_NAME
IMPORTER_PHONE
IMP_DATE
METHOD_OF_PAYMENT
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_ADDRESS
SUPPLIER_CITY
SUPPLIER_COUNTRY
SUPPLIER_NAME
SUPPLIER_PHONE_E_MAIL
TAX
TRANSPORTATION_COMPANY
TRANSPORT_DOCUMENT
TYPE_OF_TRANSPORT
UNIT
USD_CIF
USD_FOB
USD_FREIGHT
USD_INSURANCE
WEIGHT
HS_CODE_DESCRIPTION
IMPORTER_NAME_EN
```
</details>

---

### Colombia Import S.xlsx

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
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/colombia_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
SUPPLIER_NAME
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

