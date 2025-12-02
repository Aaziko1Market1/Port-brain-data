# Armenia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Armenia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Armenia Export F.xlsx | EXPORT | FULL | 1 | 6 | EXPORTER NAME | HS CODE | INVOICE AMOUNT |
| Armenia Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME_EN | HS_CODE | TOTALVALUE |
| Armenia Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME_EN | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Armenia Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER NAME, EXPORTER NAME EN, ASSESSMENT DATE, INVOICE AMOUNT, INVOICE CURRENCY, INVOICE RATE, INVOICE AMOUNT USD
- 📦 HS Code: HS CODE, HS CODE 2, HS CODE 4
- 💰 Value: INVOICE AMOUNT, CUSTOMS VALUE LC, TOTAL VALUE, TOTAL VALUE 1, TOTAL VALUE 2, TOTAL VALUE 3, TOTAL VALUE 4, USD EXCHANGE RATE, INVOICE AMOUNT USD, CUSTOMS VALUE USD
- 📊 Quantity: GROSS WEIGHT, NET WEIGHT, QUANTITY, QUANTITY 2
- 🏢 Buyer/Importer: BUYER NAME, BUYER NAME EN
- 🏭 Supplier/Exporter: EXPORTER NAME, EXPORTER NAME EN

**Config File:** `config/armenia_export_full.yml`

<details>
<summary>All Columns (52 total)</summary>

```
RECORDS TAG
BUYER NAME
BUYER NAME EN
TAX ID NUMBER
EXPORTER NAME
EXPORTER NAME EN
PROCEDURE CODE
CUSTOMS POINT CODE
ASSESSMENT DATE
DECLARATION NUMBER
HS CODE
PRODUCT DESCRIPTION
PRODUCT DESCRIPTION EN
ORIGIN COUNTRY
DESTINATION COUNTRY
TRADE COUNTRY
GROSS WEIGHT
NET WEIGHT
QUANTITY
UNIT
QUANTITY 2
UNIT 2
INVOICE AMOUNT
CUSTOMS VALUE LC
VAT
CUSTOMS DUTY TAX
EXCISE TAX
ECOLOGY TAX
ANTI DUMPING TAX
TOTAL VALUE
TOTAL VALUE 1
TOTAL VALUE 2
TOTAL VALUE 3
TOTAL VALUE 4
METHOD
USD EXCHANGE RATE
EURO EXCHANGE RATE
INVOICE CURRENCY
INVOICE RATE
INCOTERM
CUSTOMS TARIFF
CUSTOMS TARIFF 1
CUSTOMS BROKER
CUSTOMS BROKER EN
ITEM NUMBER
PROCEDURE CODE MEANING
HS DESCRIPTION
INVOICE AMOUNT USD
CUSTOMS VALUE USD
HS CODE 2
HS CODE 4
COUNTRY ISO CODE 2
```
</details>

---

### Armenia Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: BUYER_NAME_EN
- 🏭 Supplier/Exporter: EXPORTER_NAME_EN

**Config File:** `config/armenia_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
BUYER_NAME_EN
EXPORTER_NAME_EN
HS_CODE
HS_DESCRIPTION
ORIGIN_COUNTRY
DESTINATION_COUNTRY
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

### Armenia Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: SUPPLIER_NAME_EN

**Config File:** `config/armenia_import_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
IMPORTER_NAME_EN
SUPPLIER_NAME_EN
ORIGIN_COUNTRY
HS_CODE
HS_DESCRIPTION
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

