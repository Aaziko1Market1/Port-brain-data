#  Bolivia Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for  Bolivia.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| _Bolivia Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_ID | HS_CODE | TOTAL_CIF |

## Detailed Format Analysis

### _Bolivia Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_ID, IMPORTER_NAME, IMP_DATE, IMPORTER_NAME_EN
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: TOTAL_CIF, TOTAL_FOB
- 📊 Quantity: QUANTITY, WEIGHT
- 🏢 Buyer/Importer: IMPORTER_ID, IMPORTER_NAME, IMPORTER_NAME_EN

**Config File:** `config/_bolivia_import_full.yml`

<details>
<summary>All Columns (25 total)</summary>

```
COUNTRY_ISO_CODE_2
DECLARANT
DECLARANT_ID
DEPARTURE_COUNTRY
HS_CODE
HS_CODE_2
HS_CODE_4
IMPORTER_ID
IMPORTER_NAME
IMP_DATE
ITEM
ITEM_FOB
OPERATION_NUMBER
ORIGIN_COUNTRY
PACKAGES
PRODUCT_DESCRIPTION
PRODUCT_STATUS
QUANTITY
RECORDS_TAG
RECORD_ID
TOTAL_CIF
TOTAL_FOB
WEIGHT
HS_CODE_DESCRIPTION
IMPORTER_NAME_EN
```
</details>

---

