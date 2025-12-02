# India Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for India.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| India Import F.xlsx | IMPORT | FULL | 2 | 6 | DATE | HS CODE | UNIT PRICE_INR |
| India Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTAL_VALUE_USD |

## Detailed Format Analysis

### India Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DATE, IMPORTER, INVOICE CURRENCY, INVOICE UNITPRICE_FC, INVOICE NO
- 📦 HS Code: HS CODE, HS CODE_2, HS CODE_4, HS CODE_DESCRIPTION
- 💰 Value: UNIT PRICE_INR, TOTAL VALUE_INR, UNIT PRICE_USD, TOTAL VALUE_USD, INVOICE UNITPRICE_FC, STD UNIT_VALUE_INR, STD UNIT_PRICE_USD
- 📊 Quantity: QUANTITY, STD QUANTITY
- 🏢 Buyer/Importer: IMPORTER
- 🏭 Supplier/Exporter: SUPPLIER, SUPPLIER ADDRESS, STD SUPPLIER, STD SUPPLIER ADDRESS

**Config File:** `config/india_import_full.yml`

<details>
<summary>All Columns (39 total)</summary>

```
PORT CODE
INDIAN PORT
DATE
IEC
IMPORTER
ADDRESS
CITY
CHA NO
CHA NAME
COUNTRY OF_ORIGIN
HS CODE
GOODS DESCRIPTION
QUANTITY
UNIT
UNIT PRICE_INR
TOTAL VALUE_INR
UNIT PRICE_USD
TOTAL VALUE_USD
DUTY PAID_INR
APPRAISING GROUP
LOADING PORT
INVOICE CURRENCY
SUPPLIER
SUPPLIER ADDRESS
STD SUPPLIER
STD SUPPLIER ADDRESS
INVOICE UNITPRICE_FC
BE TYPE
INVOICE NO
STD QUANTITY
STD UNIT
STD UNIT_VALUE_INR
STD UNIT_PRICE_USD
DECLARATION NO
HS CODE_2
HS CODE_4
country iso_code_2
HS CODE_DESCRIPTION
PIN
```
</details>

---

### India Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_VALUE_USD, TOTAL_QUANTITY, AVG_UNITPRICE
- 📊 Quantity: TOTAL_QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/india_import_short.yml`

<details>
<summary>All Columns (13 total)</summary>

```
IMPORTER_NAME
SUPPLIER_NAME
HS_CODE
HS_CODE_DESCRIPTION
IEC
INDIAN_PORT
PORT_OF_SHIPMENT
ORIGIN_COUNTRY
IMP_DATE
TOTAL_VALUE_USD
TOTAL_QUANTITY
AVG_UNITPRICE
MONTHYEAR
```
</details>

---

