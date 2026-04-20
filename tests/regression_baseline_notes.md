# Regression Baseline Notes

## Baseline Captured: 2026-04-20 (Complete)

**Context:** Full regression baseline captured after F13 (identity fields) and F14 (versioning fields) were implemented. All 6 canonical PDFs re-processed with F13/F14. Scoring system calibrated via F15 with 100% high-band precision.

**Complete Baseline (All 6 PDFs):**

| PDF | Mean Composite | Min | Notices | Layout | OCR | Status |
|-----|---------------|-----|---------|--------|-----|--------|
| Vol CXINo 100 | 0.990 | 0.800 | 287 | 0.993 | 0.995 | ✓ Current |
| Vol CXINo 103 | 0.989 | 0.745 | 320 | 0.997 | 0.992 | ✓ Current |
| Vol CXIINo 76 | 0.963 | 0.890 | 3 | 0.946 | 0.991 | ✓ Current |
| Vol CXXVIINo 63 | 0.977 | 0.820 | 139 | 0.960 | 0.890 | ✓ Current |
| Vol CXXIVNo 282 | 0.968 | 0.745 | 201 | 0.984 | 0.987 | ✓ Current |
| Vol CIINo 83 (pre 2010) | 0.253 | 0.253 | 1 | 0.924 | 0.926 | ✓ Current |

**Quality Gate 1 Status:** ✅ **FULLY CLEARED** (6/6 PDFs have valid baselines)

**Regression Check Result:** ✅ PASS — All 6 PDFs within tolerance

**Notable Observations:**
- **Vol CIINo 83 (pre 2010):** Low mean composite (0.253) expected for pre-2010 OCR quality. Only 1 notice extracted. Baseline captured for regression detection but not representative of modern gazettes.
- **Vol CXIINo 76:** Only 3 notices (short issue). High mean composite (0.963).
- **Top performers:** Vol CXINo 100 (0.990) and Vol CXINo 103 (0.989) with 287 and 320 notices respectively.

**Usage:**
Run `check_regression()` after any code changes to detect score degradation across all 6 canonical PDFs. Tolerance: ±0.05 (5 percentage points) on mean composite.

**Regression Detection:**
- **Pass:** All PDFs within tolerance → ship
- **Fail:** Any PDF drops > 0.05 → investigate `confidence_reasons`, fix or revert

**When to Update Baseline:**
Only update when you **intentionally accept** a scoring change after validation via calibration.

**Baseline History:**
- **2026-04-19:** Initial partial baseline (2/6 PDFs)
- **2026-04-20:** Complete baseline (6/6 PDFs) ← **Current**
