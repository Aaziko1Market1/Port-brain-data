# HS 690721 – Kenya DAVITA SOLUTIONS Validation Report

**Date:** December 1, 2025  
**Buyer:** DAVITA SOLUTIONS LIMITED  
**HS Code:** 690721 (Ceramic Tiles)  
**Country:** KENYA  
**Status:** ✅ RESOLVED

---

## Executive Summary

DAVITA SOLUTIONS LIMITED was not visible in the Buyer Hunter UI despite having valid trade data (~$56,108 USD). This was **NOT a data bug** but a **UI/UX limitation** - the buyer was ranked #69 out of 316 buyers and the UI only shows the top 20 by default.

**Fix Applied:** Added a "Search by Name" feature to allow finding any buyer regardless of their ranking position.

---

## 1. Data Verification - DAVITA Appears in Each Layer

### Source File: Kenya Import S.xlsx
| Column | Value |
|--------|-------|
| IMPORTER_NAME | DAVITA SOLUTIONS LIMITED |
| HS_CODE | 6907210000 |
| TOTALVALUEUSD | $7,216.52 + $48,891.96 = **$56,108.48** |
| ORIGIN_COUNTRY | INDIA |
| MONTHYEAR | Sep 2025, Oct 2025 |

### stg_shipments_standardized
| std_id | buyer_name_raw | hs_code_6 | customs_value_usd |
|--------|----------------|-----------|-------------------|
| 21414 | DAVITA SOLUTIONS LIMITED | 690721 | $7,216.52 |
| 21415 | DAVITA SOLUTIONS LIMITED | 690721 | $48,891.96 |
| **Total** | | | **$56,108.48** ✓ |

### organizations_master
| Column | Value |
|--------|-------|
| org_uuid | `d55e818c-2582-4bb9-a32c-dc4c9c9ac365` |
| name_normalized | DAVITA SOLUTIONS |
| country_iso | KENYA |

### global_trades_ledger
- **2 rows** for DAVITA with HS 690721, KENYA destination
- **Total value:** $56,108.48 ✓
- **buyer_uuid correctly linked**

### buyer_profile
- **buyer_uuid:** `d55e818c-2582-4bb9-a32c-dc4c9c9ac365`
- **destination_country:** KENYA
- **total_customs_value_usd:** $56,108.48 ✓

---

## 2. Root Cause Analysis

### Problem Statement
DAVITA was not visible in the Buyer Hunter UI even though the data was correctly ingested.

### Root Cause
DAVITA is ranked **#69 out of 316 buyers** for HS 690721 in Kenya. The default "Top Buyers" view shows only the **top 20 results**, so DAVITA was never displayed.

| Metric | DAVITA Value | Top Buyer (TILE AND CARPET CENTRE) |
|--------|-------------|-------------------------------------|
| Value | $56,108 | $4,263,227 |
| Rank | #69 | #1 |
| Shipments | 2 | 74 |

### This is NOT a data bug
- All pipeline stages processed correctly
- DAVITA exists in every database table
- Opportunity score (68.0) is valid

---

## 3. Fix Implemented

### New API Endpoint: `/api/v1/buyer-hunter/search-by-name`

```python
# In api/routers/buyer_hunter.py
@router.get("/search-by-name")
def search_buyers_by_name(
    buyer_name: str,  # Partial match using ILIKE
    hs_code_6: str,
    destination_countries: Optional[str],
    min_total_value_usd: float = 10000,  # Lower threshold
    max_risk_level: str = "ALL",  # All risk levels
    ...
)
```

### Backend Changes
| File | Change |
|------|--------|
| `api/routers/buyer_hunter.py` | Added `/search-by-name` endpoint |
| `etl/analytics/buyer_hunter.py` | Added `buyer_name_filter` parameter to `search_target_buyers()` and `build_buyer_hunter_query()` |

### Frontend Changes
| File | Change |
|------|--------|
| `control-tower-ui/src/api/client.ts` | Added `searchBuyerHunterByName()` function |
| `control-tower-ui/src/pages/BuyerHunter.tsx` | Added search mode toggle ("Top Buyers" / "Search by Name") and buyer name input field |

---

## 4. Test Added

```python
# In tests/test_buyer_hunter.py
def test_davita_kenya_tiles_is_discoverable():
    """
    Ensure DAVITA SOLUTIONS LIMITED is discoverable
    for HS 690721 (tiles) in Kenya via search-by-name.
    """
    response = client.get(
        "/api/v1/buyer-hunter/search-by-name",
        params={
            "buyer_name": "DAVITA",
            "hs_code_6": "690721",
            "destination_countries": "KENYA"
        }
    )
    assert response.status_code == 200
    
    # Find DAVITA in results
    davita = next((item for item in data["items"] 
                   if "DAVITA" in item["buyer_name"].upper()), None)
    
    assert davita is not None
    assert 50000 <= davita["total_value_usd_12m"] <= 60000
    assert davita["total_shipments_12m"] >= 2
```

### Test Results
```
✓ DAVITA SOLUTIONS found and validated:
  - UUID: d55e818c-2582-4bb9-a32c-dc4c9c9ac365
  - Value: $56,108.48
  - Shipments: 2
  - Opportunity Score: 68.0

RESULTS: 14 passed, 0 failed
```

---

## 5. API Verification

### Before Fix
```
GET /api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries=KENYA
→ Returns top 20 buyers, DAVITA NOT included (ranked #69)
```

### After Fix
```
GET /api/v1/buyer-hunter/search-by-name?buyer_name=DAVITA&hs_code_6=690721&destination_countries=KENYA
→ Returns DAVITA with:
  - buyer_name: "DAVITA SOLUTIONS"
  - total_value_usd_12m: 56108.48
  - opportunity_score: 68.0
  - hs_share_pct: 100.0
```

---

## 6. UI Changes

### New Search Mode Toggle
The Buyer Hunter page now has a toggle between:
1. **Top Buyers** (default): Shows top 20 buyers by opportunity score
2. **Search by Name**: Find any buyer matching a name pattern

### How to Find DAVITA
1. Go to Buyer Hunter
2. Click "Search by Name" toggle
3. Enter HS Code: `690721`
4. Enter Country: `KENYA`
5. Enter Buyer Name: `DAVITA`
6. Click Search
7. DAVITA SOLUTIONS appears with full details

---

## 7. Conclusion

| Aspect | Status |
|--------|--------|
| Data Ingestion | ✅ Correct |
| Data Standardization | ✅ Correct |
| Identity Resolution | ✅ Correct |
| Ledger Loading | ✅ Correct |
| Buyer Profile | ✅ Correct |
| Buyer Hunter Query | ✅ Correct (DAVITA ranked #69) |
| UI Discoverability | ✅ **FIXED** (search by name added) |
| Test Coverage | ✅ Added `test_davita_kenya_tiles_is_discoverable()` |

**No data pipeline fixes were required.** The issue was purely a UX limitation that has been resolved by adding a buyer name search feature.
