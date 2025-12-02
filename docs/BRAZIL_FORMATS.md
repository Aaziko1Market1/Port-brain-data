# Brazil Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Brazil.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Brazil Import F.xlsx | IMPORT | FULL | 2 | 6 | IMP_DATE | HS_CODE | FOB_USD |
| Brazil Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME_EN | HS_CODE | TOTALVALUE |

## Detailed Format Analysis

### Brazil Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMP_DATE, IMPORTER_TAX_ID, IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN, IMPORTER_CITY, IMPORTER_STATE, EXPORTER_NAME, EXPORTER_NAME_EN, EXPORTER_COUNTRY_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION, HS_CODE_DESCRIPTION_EN, HS_CODE_2, HS_CODE_4
- 💰 Value: FOB_USD, FREIGHT_USD, INSURANCE_USD, CIF_USD, CIF_UNIT_USD
- 📊 Quantity: QUANTITY, WEIGHT_KG
- 🏢 Buyer/Importer: IMPORTER_TAX_ID, IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN, IMPORTER_CITY, IMPORTER_STATE
- 🏭 Supplier/Exporter: EXPORTER_NAME, EXPORTER_NAME_EN, EXPORTER_COUNTRY_NAME

**Config File:** `config/brazil_import_full.yml`

<details>
<summary>All Columns (33 total)</summary>

```
RECORD_ID
RECORDS_TAG
IMP_DATE
IMPORTER_TAX_ID
IMPORTER_ID
IMPORTER_NAME
IMPORTER_NAME_EN
IMPORTER_CITY
IMPORTER_STATE
EXPORTER_NAME
EXPORTER_NAME_EN
EXPORTER_COUNTRY_NAME
ORIGIN_COUNTRY_NAME
TRANS_TYPE
INCOTERMS
ENTRY_CUSTOMS_OFFICE_CODE_AND_NAME
CLEARANCE_CUSTOMS_OFFICE_CODE_AND_NAME_EN
HS_CODE
HS_CODE_DESCRIPTION
HS_CODE_DESCRIPTION_EN
PRODUCT_DESCRIPTION
PRODUCT_DESCRIPTION_EN
QUANTITY
UNIT
WEIGHT_KG
FOB_USD
FREIGHT_USD
INSURANCE_USD
CIF_USD
CIF_UNIT_USD
HS_CODE_2
HS_CODE_4
COUNTRY_ISO_CODE_2
```
</details>

---

### Brazil Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME_EN, EXPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION_EN
- 💰 Value: TOTALVALUE, TOTALQUANTITY
- 📊 Quantity: TOTALQUANTITY
- 🏢 Buyer/Importer: IMPORTER_NAME_EN
- 🏭 Supplier/Exporter: EXPORTER_NAME_EN

**Config File:** `config/brazil_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
IMPORTER_NAME_EN
EXPORTER_NAME_EN
ORIGIN_COUNTRY_NAME
CLEARANCE_CUSTOMS_OFFICE_CODE_AND_NAME_EN
HS_CODE
HS_CODE_DESCRIPTION_EN
TOTALVALUE
TOTALQUANTITY
MONTHYEAR
```
</details>

---

