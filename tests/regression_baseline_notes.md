# Regression Baseline Notes

## Baseline Captured: 2026-04-19

**Context:** Initial regression baseline captured after F13 (identity fields) and F14 (versioning fields) were implemented. Scoring system calibrated via F15 with 100% high-band precision.

**Current Baseline (2 PDFs with F13/F14):**
| PDF | Mean Composite | Min | Notices | Status |
|-----|---------------|-----|---------|--------|
| Vol CXINo 100 | 0.990 | 0.800 | 287 | ✓ Current |
| Vol CXXIVNo 282 | 0.968 | 0.745 | 201 | ✓ Current |

**Pending Update (3 PDFs need re-processing):**
| PDF | Issue | Action |
|-----|-------|--------|
| Vol CXINo 103 | Missing F13/F14 fields | Re-process when ready |
| Vol CXIINo 76 | Missing F13/F14 fields | Re-process when ready |
| Vol CXXVIINo 63 | Missing F13/F14 fields | Re-process when ready |
| Vol CIINo 83 (pre 2010) | No output | Process when PDF available |

**Quality Gate 1 Status:** ⏳ Partially cleared (2/6 PDFs have valid baselines)

**Next Steps:**
- Batch re-process the 3 outdated PDFs when convenient
- Run `update_regression_fixture()` again to capture their updated scores
- Full baseline will enable comprehensive regression detection

**Usage:**
Run `check_regression()` after any code changes to detect score degradation on the 2 current PDFs.
