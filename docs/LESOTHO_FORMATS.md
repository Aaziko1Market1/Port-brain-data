# Lesotho Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Lesotho.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Lesotho Export F.xlsx | EXPORT | FULL | 2 | 6 | DATE | HS_CODE | CUSTOMS_VALUE_LSL |
| Lesotho Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME | HS_CODE | TOTALWEIGHT |
| Lesotho IMport F.xlsx | IMPORT | FULL | 2 | 6 | DATE | HS_CODE | TAX_AMOUNT_LSL |
| Lesotho Import S.xlsx | IMPORT | SHORT | 77 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Lesotho Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DATE, EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CUSTOMS_VALUE_LSL, CUSTOMS_VALUE_USD, TAX_AMOUNT_LSL
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME, STD_EXPORTER_NAME

**Config File:** `config/lesotho_export_full.yml`

<details>
<summary>All Columns (20 total)</summary>

```
BUYER_NAME
COMMERCIAL_DESCRIPTION
COUNTRY_ISO_CODE_2
CUSTOMS_VALUE_LSL
CUSTOMS_VALUE_USD
DATE
DESTINATION_COUNTRY
EXPORTER_NAME
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
NET_WEIGHT
NUMBER_OF_PACKAGES
PACKAGE_TYPE
RECORDS_TAG
RECORD_ID
STD_EXPORTER_NAME
TAX_AMOUNT_LSL
```
</details>

---

### Lesotho Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALWEIGHT, TOTALUSD
- 📊 Quantity: TOTALWEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/lesotho_export_short.yml`

<details>
<summary>All Columns (8 total)</summary>

```
BUYER_NAME
EXPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
DESTINATION_COUNTRY
TOTALWEIGHT
TOTALUSD
MONTHYEAR
```
</details>

---

### Lesotho IMport F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: DATE, IMPORTER_ID, IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TAX_AMOUNT_LSL, TOTAL_VALUE_LSL, TOTAL_VALUE_USD
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, STD_IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/lesotho_import_full.yml`

<details>
<summary>All Columns (29 total)</summary>

```
AGENT_ID
AGENT_NAME
COMMERCIAL_DESCRIPTION
COUNTRY_ISO_CODE_2
COUNTRY_OF_ORIGIN
DATE
ENTRY_NUMBER
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_ID
IMPORTER_NAME
MODE_OF_TRANSPORT
NET_WEIGHT
NUMBER_OF_PACKAGES
NUMBER_OF_PACKAGES_1
PACKAGE_TYPE
PACKAGE_TYPE_1
PORT_OF_ENTRY
RECORDS_TAG
RECORD_ID
STD_IMPORTER_NAME
SUPPLIER_NAME
TAX_AMOUNT_LSL
TOTAL_VALUE_LSL
TOTAL_VALUE_USD
UNIT_OF_MEASURE
```
</details>

---

### Lesotho Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 77

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHTS
- 📊 Quantity: TOTALWEIGHTS, %GTTOTALWEIGHTS
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/lesotho_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
SUPPLIER_NAME
IMPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
COUNTRY_OF_ORIGIN
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHTS
%GTTOTALWEIGHTS
MONTHYEAR
```
</details>

---

