# Panama Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Panama.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Panama Export F.xlsx | EXPORT | FULL | 2 | 6 | EXPORTER_NAME | HS_CODE | CIF_VALUE |
| Panama Export S.xlsx | EXPORT | SHORT | 4 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Panama Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | TOTAL_TAX_TO_PAY |
| Panama Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALUSD |

## Detailed Format Analysis

### Panama Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME, EXP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, USD_FOB
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME, RUC_EXPORTER_ID

**Config File:** `config/panama_export_full.yml`

<details>
<summary>All Columns (27 total)</summary>

```
BUYER_NAME
CIF_VALUE
COUNTRY
COUNTRY_ISO_CODE_2
CUSTOMS_NAME
CUSTOMS_ZONE
DECLARATION_NUMBER
DEPARTURE_PORT_OR_PREMISES
DIGITO_CONTROL
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
NET_WEIGHT
PACKAGES
PRODUCT_DESCRIPTION
QUANTITY
RECINTO_ENCLOSURE
RECORDS_TAG
RECORD_ID
RUC_EXPORTER_ID
TRANSPORT_TYPE
UNIT
USD_FOB
HS_CODE_DESCRIPTION
```
</details>

---

### Panama Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 4

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/panama_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
BUYER_NAME
EXPORTER_NAME
HS_CODE
COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

### Panama Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMPORT_TAX, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_TAX_TO_PAY, USD_CIF, USD_FOB, USD_FREIGHT, USD_INSURANCE
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME, RUC_IMPORTER_ID, IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/panama_import_full.yml`

<details>
<summary>All Columns (36 total)</summary>

```
CALCULATED_TAX
CONTROL_DIGITAL
COUNTRY_ISO_CODE_2
CUSTOMS_NAME
CUSTOMS_ZONE
DECLARATION_NUMBER
DEPARTURE_PORT_OR_PREMISES
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
ICDDP
IMPORTER_NAME
IMPORT_TAX
IMP_DATE
ISC
ITBMS
NET_WEIGHT
ORIGIN_COUNTRY
PACKAGES
PRODUCT_DESCRIPTION
QUANTITY
RECINTO_ENCLOSURE
RECORDS_TAG
RECORD_ID
RUC_IMPORTER_ID
SUPPLIER_NAME
TOTAL_TAX_TO_PAY
TRANSPORT_TYPE
UNIT
USD_CIF
USD_FOB
USD_FREIGHT
USD_INSURANCE
HS_CODE_DESCRIPTION
IMPORTER_NAME_EN
```
</details>

---

### Panama Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/panama_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
SUPPLIER_NAME
IMPORTER_NAME
ORIGIN_COUNTRY
TOTALUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

