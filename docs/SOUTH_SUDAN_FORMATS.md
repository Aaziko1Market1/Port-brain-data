# South Sudan Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for South Sudan.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| South sudan Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_NAME | HS_CODE | CIF |
| South sudan Import S.xlsx | IMPORT | SHORT | 83 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### South sudan Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME, IMPORT_DUTY, IMP_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: CIF, CIF_USD, FOB, FOB_USD, TOTAL_TAXES
- 📊 Quantity: GROSS_WEIGHT, NET_WEIGHT, QUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/south_sudan_import_full.yml`

<details>
<summary>All Columns (35 total)</summary>

```
AUO
CIF
CIF_USD
COUNTRY_ISO_CODE_2
DESTINATION_COUNTRY
EXCISE_DUTY
FOB
FOB_USD
FREIGHT
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IDL
IMPORTER_NAME
IMPORT_DUTY
IMP_DATE
INSURANCE
MVF
NET_WEIGHT
ORIGIN_COUNTRY
OTHER_COSTS
PRODUCT_DESCRIPTION
PV
QUALITY_INSPECTION_FEES
QUANTITY
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
TIN
TOTAL_TAXES
UNIT
VAT
WHT
```
</details>

---

### South sudan Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 83

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY, %GTTOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/south_sudan_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
IMPORTER_NAME
SUPPLIER_NAME
ORIGIN_COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALQUANTITY
%GTTOTALQUANTITY
MONTHYEAR
```
</details>

---

