# Zimbabwe Port Data Formats

Generated: 2025-12-01 10:06:58

## Overview

This document describes the port data file formats available for Zimbabwe.

| File | Direction | Format | Rows | Header Row | Date Column | HS Code Column | Value Column |
|------|-----------|--------|------|------------|-------------|----------------|--------------|
| Zimbabwe Export F.xlsx | EXPORT | FULL | 1 | 6 | EXPORTER_BP | HS_CODE | CIF_VALUE |
| Zimbabwe Export S.xlsx | EXPORT | SHORT | 1 | 1 | EXPORTER_NAME | HS_CODE | TOTALVALUEUSD |
| Zimbabwe Import F.xlsx | IMPORT | FULL | 2 | 6 | IMPORTER_BP | HS_CODE | CIF_VALUE |
| Zimbabwe Import S.xlsx | IMPORT | SHORT | 100 | 1 | IMPORTER_NAME | HS_CODE | TOTALVALUEUSD |

## Detailed Format Analysis

### Zimbabwe Export F.xlsx

- **Direction:** EXPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_BP, EXPORTER_NAME, EXP_DATE, RECEIPT_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, CIF_VALUE_IN_USD, ITEM_PRICE, TOTAL_INVOICE_VALUE, UNIT_PRICE
- 📊 Quantity: GROSS_WEIGHT, NET_MASS
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_BP, EXPORTER_NAME

**Config File:** `config/zimbabwe_export_full.yml`

<details>
<summary>All Columns (41 total)</summary>

```
ACCOUNT_CODE
ASSEMENT_NUMBER
BUYER_NAME
CIF_VALUE
CIF_VALUE_IN_USD
COUNTRY_FST_CODE
COUNTRY_ISO_CODE_2
COUNTRY_OF_LAST_CONSIGNMENT
COUNTRY_OF_ORIGIN_CODE
CURRENCY
DECLARANT
DECLARANT_BP
DELIVERY_TERM_CODE
DELIVERY_TERM_PLACE
DESTINATION_COUNTRY
EXCHANGE_RATE
EXIT_OFFICE
EXPORTER_BP
EXPORTER_NAME
EXP_DATE
GROSS_WEIGHT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
INSTANCE_ID
ITEM
ITEM_PRICE
MODE_OF_PAYMENT
MODE_OF_TRANSPORT
NET_MASS
NUMBER_OF_PACKAGES
OFFICE_CODE
PRODUCT_DESCRIPTION
RECEIPT_DATE
RECEIPT_NO
RECORDS_TAG
RECORD_ID
SUPP_UNITS
TOTAL_INVOICE_VALUE
UNIT_PRICE
```
</details>

---

### Zimbabwe Export S.xlsx

- **Direction:** EXPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 1

**Detected Column Types:**

- 📅 Date: EXPORTER_NAME
- 📦 HS Code: HS_CODE
- 💰 Value: TOTALVALUEUSD, %GTSUMOFCIF_VALUE_IN_USD
- 📊 Quantity: SUMOFGROSS_WEIGHT, %GTSUMOFGROSS_WEIGHT
- 🏢 Buyer/Importer: BUYER_NAME
- 🏭 Supplier/Exporter: EXPORTER_NAME

**Config File:** `config/zimbabwe_export_short.yml`

<details>
<summary>All Columns (9 total)</summary>

```
HS_CODE
TOTALVALUEUSD
BUYER_NAME
EXPORTER_NAME
COUNTRY_OF_LAST_CONSIGNMENT
%GTSUMOFCIF_VALUE_IN_USD
SUMOFGROSS_WEIGHT
%GTSUMOFGROSS_WEIGHT
MONTHYEAR
```
</details>

---

### Zimbabwe Import F.xlsx

- **Direction:** IMPORT
- **Format:** FULL
- **Header Row:** 6
- **Sample Rows:** 2

**Detected Column Types:**

- 📅 Date: IMPORTER_BP, IMPORTER_NAME, IMP_DATE, INVOICE_VALUE, RECEIPT_DATE
- 📦 HS Code: HS_CODE, HS_CODE_2, HS_CODE_4, HS_CODE_DESCRIPTION
- 💰 Value: CIF_VALUE, CIF_VALUE_IN_USD, GUARANTEE_AMOUNT, INVOICE_VALUE, SUPP_VALUE, UNIT_PRICE, VAT_AMOUNT
- 📊 Quantity: GROSS_WEIGHT, NET_MASS
- 🏢 Buyer/Importer: IMPORTER_BP, IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/zimbabwe_import_full.yml`

<details>
<summary>All Columns (45 total)</summary>

```
ACCOUNT_CODE
ASSEMENT_NUMBER
CIF_VALUE
CIF_VALUE_IN_USD
COUNTRY_DESTINATION_CODE
COUNTRY_ISO_CODE_2
COUNTRY_OF_LAST_CONSIGNMENT
COUNTRY_OF_ORIGIN_CODE
CURRENCY
CUSTOMS_DUTY
DECLARANT
DECLARANT_BP
DELIVERY_TERM_CODE
DELIVERY_TERM_PLACE
EXCHANGE_RATE
EXCISE
GROSS_WEIGHT
GUARANTEE_AMOUNT
HS_CODE
HS_CODE_2
HS_CODE_4
HS_CODE_DESCRIPTION
IMPORTER_BP
IMPORTER_NAME
IMP_DATE
INSTANCE_ID
INVOICE_VALUE
ITEM
MODE_OF_PAYMENT
MODE_OF_TRANSPORT
NET_MASS
NUMBER_OF_PACKAGES
OFFICE_CODE
ORIGIN_COUNTRY
PRODUCT_DESCRIPTION
RECEIPT_DATE
RECEIPT_NO
RECORDS_TAG
RECORD_ID
SUPPLIER_NAME
SUPP_UNITS
SUPP_VALUE
SURTAX
UNIT_PRICE
VAT_AMOUNT
```
</details>

---

### Zimbabwe Import S.xlsx

- **Direction:** IMPORT
- **Format:** SHORT
- **Header Row:** 1
- **Sample Rows:** 100

**Detected Column Types:**

- 📅 Date: IMPORTER_NAME
- 📦 HS Code: HS_CODE, HS_CODE_DESCRIPTION
- 💰 Value: TOTALVALUEUSD, %GTTOTALUSD, TOTALWEIGHT
- 📊 Quantity: TOTALWEIGHT, %GTTOTALWEIGHT
- 🏢 Buyer/Importer: IMPORTER_NAME
- 🏭 Supplier/Exporter: SUPPLIER_NAME

**Config File:** `config/zimbabwe_import_short.yml`

<details>
<summary>All Columns (10 total)</summary>

```
SUPPLIER_NAME
IMPORTER_NAME
HS_CODE
HS_CODE_DESCRIPTION
ORIGIN_COUNTRY
TOTALVALUEUSD
%GTTOTALUSD
TOTALWEIGHT
%GTTOTALWEIGHT
MONTHYEAR
```
</details>

---

