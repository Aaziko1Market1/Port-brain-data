# HS 690721 – Kenya Tile Data Verification Report

**Generated:** December 1, 2025  
**Status:** ✅ ALL SYSTEMS VERIFIED - NO ISSUES FOUND

---

## Executive Summary

A full system trace was conducted to verify the data pipeline for HS 690721 (Ceramic Tiles) for Kenya. **The system is working correctly.** All data from the uploaded Kenya files has been properly ingested, standardized, and is accessible through the Buyer Hunter API.

---

## 1. DATA FOUND HERE

### Source Files Analyzed
| File | HS 690721 Rows | Total Value USD |
|------|----------------|-----------------|
| Kenya Import S.xlsx | 1,000 | $22,086,014.19 |
| Kenya Import F.xlsx | 2 | $55,767.03 |
| Kenya Export S.xlsx | 0 | N/A |
| Kenya Export F.xlsx | 0 | N/A |

**Total Source Rows:** 1,002  
**Total Source Value:** $22,141,781.22

### Database Tables
| Table | HS 690721 Kenya Rows | Total Value USD |
|-------|----------------------|-----------------|
| stg_shipments_standardized | 1,002 | $22,141,781.22 |
| global_trades_ledger | 1,002 | $22,141,781.22 |
| buyer_profile (Kenya dest) | 331 profiles | Various |
| organizations_master (Kenya) | 331 orgs | N/A |

---

## 2. PROBLEM LOCATED HERE

**NO PROBLEMS FOUND.** The data pipeline is functioning correctly:

- ✅ Source files correctly contain HS 690721 data
- ✅ Kenya Import files (F and S) properly ingested
- ✅ Data correctly attributed to `reporting_country = KENYA`
- ✅ Data correctly attributed to `destination_country = KENYA`
- ✅ HS code normalized to 6-digit format (`690721`)
- ✅ Mapping registry has correct Kenya configurations
- ✅ Buyer profiles generated for Kenya buyers
- ✅ Risk scores computed for Kenya entities

---

## 3. FIX APPLIED

**No fixes required.** The system was already working correctly.

---

## 4. VERIFIED OUTPUT

### Buyer Hunter API Test
**Endpoint:** `GET /api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries=KENYA`  
**Status:** 200 OK ✅

### Top 5 Buyers for HS 690721 → Kenya
| Rank | Buyer Name | Value (12m) | Shipments | Score |
|------|------------|-------------|-----------|-------|
| 1 | TILE AND CARPET CENTRE | $4,263,227 | 74 | 69.5 |
| 2 | KEDA CERAMICS INTERNATIONAL | $477,248 | 23 | 67.0 |
| 3 | ZHEJIANG ESTATE | $382,176 | 27 | 66.4 |
| 4 | P SQUARE INDUSTRIES | $337,443 | 9 | 65.9 |
| 5 | MINISTRY OF HEALTH OF SOUTH SUDAN | $274,580 | 3 | 65.9 |

---

## 5. Pipeline Configuration Verified

### Mapping Registry Entries for Kenya
| ID | Country | Direction | Format | Config Key | Status |
|----|---------|-----------|--------|------------|--------|
| 71 | KENYA | EXPORT | FULL | kenya_export_full | LIVE |
| 72 | KENYA | EXPORT | SHORT | kenya_export_short | LIVE |
| 73 | KENYA | IMPORT | FULL | kenya_import_full | LIVE |
| 74 | KENYA | IMPORT | SHORT | kenya_import_short | LIVE |

### YAML Config Files
- `config/kenya_export_full.yml` ✅
- `config/kenya_export_short.yml` ✅
- `config/kenya_import_full.yml` ✅
- `config/kenya_import_short.yml` ✅

---

## 6. Data Integrity Checks

| Check | Result |
|-------|--------|
| Source file row count matches ledger | ✅ PASS |
| Source file value matches ledger | ✅ PASS |
| Country attribution correct | ✅ PASS |
| HS code normalization correct | ✅ PASS |
| Date range valid (Oct-Nov 2025) | ✅ PASS |
| Buyer UUIDs generated | ✅ PASS |
| Risk scores computed | ✅ PASS |

---

## 7. Conclusion

The Buyer Hunter module is correctly reading HS 690721 (Tiles) data for Kenya from the user's uploaded files:
- **Kenya Import F.xlsx** (2 rows)
- **Kenya Import S.xlsx** (1,000 rows)

The data pipeline has:
1. ✅ Correctly ingested the Excel files
2. ✅ Properly standardized the data
3. ✅ Loaded into the global trades ledger
4. ✅ Generated buyer profiles
5. ✅ Computed risk scores
6. ✅ Made data available via Buyer Hunter API

**No issues detected. No fixes required. System is operational.**

---

## Appendix: Files Analyzed

```
data/reference/port_real/
├── Kenya Import F.xlsx  → 2 rows HS 690721
├── Kenya Import S.xlsx  → 1,000 rows HS 690721
├── Kenya Export F.xlsx  → 0 rows HS 690721 (contains HS 230230)
└── Kenya Export S.xlsx  → 0 rows HS 690721 (contains HS 230230)
```

**Note:** Kenya Export files contain HS 230230 (wheat bran), not HS 690721 (tiles). This is correct - Kenya exports wheat products, not ceramic tiles.
