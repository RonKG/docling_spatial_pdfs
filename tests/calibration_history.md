# Calibration History

This file tracks successive calibration runs. Each time you run calibration, add a new entry at the top.

---

## Run 1 — 2026-04-20 (Initial Baseline)

**Sample size:** 26 notices (20 high, 6 medium, 0 low)

**Results:**
| Band | Labeled | Correct | Wrong | Precision | Target | Status |
|------|---------|---------|-------|-----------|--------|--------|
| High | 20 | 20 | 0 | 100.0% | ≥85% | ✅ PASS |
| Medium | 6 | 2 | 4 | 33.3% | Mixed | ✅ PASS |
| Low | 0 | - | - | - | ≤30% | N/A |

**Verdict:** Scoring well-calibrated, no weight tuning needed.

**Data source:**
- Kenya Gazette Vol CXINo 103 (most notices)
- Kenya Gazette Vol CXXIVNo 282 (3 notices)

**Notes:**
- First calibration after implementing confidence scoring system
- High-band precision exceeds target by significant margin (100% vs 85%)
- Medium-band shows expected mixed quality
- No low-confidence notices in current dataset
- Labeled sample preserved in `calibration_sample.yaml`

**Action taken:** None needed. Proceed to F16 (capture regression baseline).

---

## Template for Next Run

Copy this template when you run calibration again:

```markdown
## Run N — YYYY-MM-DD

**Sample size:** X notices (N high, N medium, N low)

**Results:**
| Band | Labeled | Correct | Wrong | Precision | Target | Status |
|------|---------|---------|-------|-----------|--------|--------|
| High | X | X | X | X% | ≥85% | PASS/FAIL |
| Medium | X | X | X | X% | Mixed | PASS |
| Low | X | X | X | X% | ≤30% | PASS/FAIL |

**Verdict:** [Well-calibrated / Needs tuning]

**Data source:**
- [List PDFs used]

**Changes since last run:**
- [What changed: new PDFs, scoring tweaks, etc.]

**Notes:**
- [Any observations]

**Action taken:** [What you did: tuned weights, accepted baseline, etc.]
```

---

## When to Re-Calibrate

Run a new calibration when:
- ✅ **New PDF types added** (e.g., pre-2000 gazettes, special supplements)
- ✅ **Scoring weights changed** (modified `composite_confidence()` or sub-scores)
- ✅ **Notice quality shifts** (OCR improves, different data sources)
- ✅ **Time-based** (~6-12 months to validate scoring still holds)
- ✅ **After major refactors** (notice splitting, layout changes)

## Process Reminder

1. **Generate sample:** Uncomment `sample_for_calibration()` in notebook, run once
   - ⚠️ This overwrites `calibration_sample.yaml` — any existing labels are lost
   - ✅ Solution: Git tracks your previous labeled version if needed
2. **Label notices:** Open the new YAML, set `is_correct: true/false` for each
3. **Score it:** Run `score_calibration()` in notebook
4. **Document:** Copy results here using the template above
5. **Commit:** Stage both this file and the labeled YAML

---

## Calibration Data Preservation

Each calibration run's labeled sample is preserved via:
- **Git history** — `tests/calibration_sample.yaml` commits show labels over time
- **This file** — Human-readable summary with verdict and actions
- **PROGRESS.md** — Session log entries document when calibration ran
