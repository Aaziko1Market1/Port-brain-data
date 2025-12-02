# Brazil Bl Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Brazil Bl.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Brazil BL Export S (1).xlsx | EXPORT | SHORT | 2 | 6 | SHIPMENT_DATE | HS_CODE | VALUE_IN_USD |
| Brazil BL Export S.xlsx | EXPORT | SHORT | 100 | 1 | N/A | HS_CODE | SUMOFVALUE_IN_USD |
| Brazil BL Import F.xlsx | IMPORT | FULL | 2 | 6 | SHIPMENT_DATE | HS_CODE | VALUE_IN_USD |
| Brazil BL Import S.xlsx | IMPORT | SHORT | 100 | 1 | N/A | HS_CODE | TOTALVALUE_IN_USD |

## Detailed Format Analysis

### Brazil BL Export S (1).xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: SHIPMENT_DATE, SHIPPER_ADDRESS, SHIPPER_COUNTRY, SHIPPER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT
- 🏢 Buyer/Importer: CONSIGNEE_ADDRESS, CONSIGNEE_COUNTRY, CONSIGNEE_NAME
- 🏭 Supplier/Exporter: SHIPPER_ADDRESS, SHIPPER_COUNTRY, SHIPPER_NAME

**Config File:** `config/brazil_bl_export_short.yml`

<details>
<summary>All Columns (35 total)</summary>

```
CARGO_TYPE
CARRIER
CONSIGNEE_ADDRESS
CONSIGNEE_COUNTRY
CONSIGNEE_NAME
CONTAINER_LOAD_TYPE
CONTAINER_NUMBER_20
CONTAINER_NUMBER_40
CONTAINER_TYPE
DELIVERY_POINT
FORWARDER
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMP_OR_EXP
METRIC_TONS
NORTIFY_PARTY_NAME
ORIGIN_PLACE
ORIGIN_PORT
PORT_OF_MARITIME_DESTINATION
PORT_OF_MARITIME_ORIGIN
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
SHIPMENT_DATE
SHIPPER_ADDRESS
SHIPPER_COUNTRY
SHIPPER_NAME
TEU
TRANSPORT
UNLOADING_PORT
VALUE_IN_USD
VESSEL_NAME
```
</details>

---

### Brazil BL Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: ⚠️ Not detected
- 📦 HS Code: HS_CODE
- 💰 Value: SUMOFVALUE_IN_USD
- 📊 Quantity: SUMOFGROSS_WEIGHT
- 🏢 Buyer/Importer: CONSIGNEE_NAME

**Config File:** `config/brazil_bl_export_short.yml`

<details>
<summary>All Columns (7 total)</summary>

```
FORWARDER
CONSIGNEE_NAME
HS_CODE
HS_DESCRIPTION
SUMOFVALUE_IN_USD
SUMOFGROSS_WEIGHT
MONTHYEAR
```
</details>

---

### Brazil BL Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: SHIPMENT_DATE, SHIPPER_ADDRESS, SHIPPER_COUNTRY, SHIPPER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4
- 💰 Value: VALUE_IN_USD
- 📊 Quantity: GROSS_WEIGHT
- 🏢 Buyer/Importer: CONSIGNEE_ADDRESS, CONSIGNEE_COUNTRY, CONSIGNEE_NAME
- 🏭 Supplier/Exporter: SHIPPER_ADDRESS, SHIPPER_COUNTRY, SHIPPER_NAME

**Config File:** `config/brazil_bl_import_full.yml`

<details>
<summary>All Columns (35 total)</summary>

```
CARGO_TYPE
CARRIER
CONSIGNEE_ADDRESS
CONSIGNEE_COUNTRY
CONSIGNEE_NAME
CONTAINER_LOAD_TYPE
CONTAINER_NUMBER_20
CONTAINER_NUMBER_40
CONTAINER_TYPE
DELIVERY_POINT
FORWARDER
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_DESCRIPTION
IMP_OR_EXP
METRIC_TONS
NORTIFY_PARTY_NAME
ORIGIN_PLACE
ORIGIN_PORT
PORT_OF_MARITIME_DESTINATION
PORT_OF_MARITIME_ORIGIN
PRODUCT_DESCRIPTION
RECORDS_TAG
RECORD_ID
SHIPMENT_DATE
SHIPPER_ADDRESS
SHIPPER_COUNTRY
SHIPPER_NAME
TEU
TRANSPORT
UNLOADING_PORT
VALUE_IN_USD
VESSEL_NAME
```
</details>

---

### Brazil BL Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: ⚠️ Not detected
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUE_IN_USD, VALUE_IN_USDPERCENTAGE, TOTALGROSS_WEIGHT
- 📊 Quantity: TOTALGROSS_WEIGHT, GROSS_WEIGHTPERCENTAGE
- 🏢 Buyer/Importer: CONSIGNEE_NAME

**Config File:** `config/brazil_bl_import_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
FORWARDER
CONSIGNEE_NAME
HS_CODE
HS_DESCRIPTION
TOTALVALUE_IN_USD
VALUE_IN_USDPERCENTAGE
TOTALGROSS_WEIGHT
GROSS_WEIGHTPERCENTAGE
MONTHYEAR
```
</details>

---

