# KENYA IMPORT FULL Validation Report

**Generated:** 2025-12-01 10:28:56  
**Config Key:** `kenya_import_full`  
**Session ID:** `d83b4365-7a03-4dd4-a535-ccf94d3e2b5d`  
**Status:** ✅ PASSED

## Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total Raw Rows | 2 | > 0 | ✅ |
| Total Standardized Rows | 2 | > 0 | ✅ |
| Valid Date % | 100.0% | ≥ 90% | ✅ |
| Valid HS Code % | 100.0% | ≥ 90% | ✅ |
| Valid Quantity % | 100.0% | ≥ 50% | ✅ |
| Valid Value % | 100.0% | ≥ 50% | ✅ |
| Valid Buyer % | 100.0% | ≥ 50% | ✅ |
| Valid Supplier % | 100.0% | ≥ 50% | ✅ |

## Date Coverage

- **Min Date:** 2025-10-31
- **Max Date:** 2025-10-31

## Sample Rows

| Date | HS Code | Quantity | Value | Buyer | Supplier |
|------|---------|----------|-------|-------|----------|
| 2025-10-31 | 690721 | 200.0 | 1347.086087 | PYRAMID BUILDERS LIMITED | R A K CERAMICS PJSC |
| 2025-10-31 | 690721 | 1488.0 | 54419.94251 | MINISTRY OF HEALTH OF THE REPU | CHINA STATE CONSTRUCTION ENGIN |

## Next Steps

1. Review the sample rows above
2. If satisfactory, run: `UPDATE mapping_registry SET status = 'LIVE' WHERE config_key = 'kenya_import_full'`
3. Or use the Admin UI to promote to LIVE
