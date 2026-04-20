# F14 Spec: Envelope Versioning Fields

## 1. What to Build

Add three envelope-level versioning fields to every record produced by `process_pdf` so downstream consumers can tell **which library version produced this JSON**, **which envelope schema shape it follows**, and **when it was extracted**: `library_version` (semver string for the `kenya_gazette` package, currently the notebook), `schema_version` (semver `MAJOR.MINOR` of the `Envelope` JSON shape per `library-contract-v1.md` section 7), and `extracted_at` (ISO 8601 UTC timestamp). These fields enable schema evolution and the **v1-vs-v2 diff comparability** flow from `library-contract-v1.md` (the "ideation prompt section H" alignment): consumers diffing the same PDF across two pipeline versions need `library_version` + `schema_version` to know which fields they can compare, and an `extracted_at` to order runs. All three are written **once per `process_pdf` call** at the top of the function and live on the top-level record (not per notice). **Determinism caveat (Quality Gate 2):** `library_version` and `schema_version` are byte-stable across runs of the same code; `extracted_at` is the **one field that legitimately changes per run** by design — Gate 2 checks identity fields (`pdf_sha256`, `gazette_issue_id`, `notice_id`) only, and any future content-diff tooling MUST exclude `extracted_at` from comparisons. Identity fields from F13 remain deterministic.

---

## 2. Interface Contract

### Module-level constants (new)

| Constant | Value | Format | Source of truth |
|----------|-------|--------|-----------------|
| `LIBRARY_VERSION` | `"0.1.0"` | semver `MAJOR.MINOR.PATCH` | Hardcoded in helper cell. Migrates to `kenya_gazette.__version__` at F17. Single source of truth — referenced once in `process_pdf`. |
| `SCHEMA_VERSION` | `"1.0"` | semver `MAJOR.MINOR` | Hardcoded in helper cell. Tracks `Envelope` JSON shape per `library-contract-v1.md` section 7. **Bump rules:** MAJOR on breaking change (field removed, type changed, semantic shift); MINOR on additive change (new optional field, new enum value). Confidence-number tweaks do not bump it. |

Both constants live in the same helper cell as the F13 identity helpers (around notebook line ~1788), so the cell becomes the canonical "envelope identity + versioning" cell.

### Helper function (new, optional but preferred)

| Aspect | Specification |
|--------|---------------|
| **Function** | `make_extracted_at() -> str` |
| **Input** | None |
| **Output** | ISO 8601 UTC timestamp string with `Z` suffix, e.g. `"2026-04-19T16:45:00Z"`. Built from `datetime.now(timezone.utc)` then formatted as `.strftime("%Y-%m-%dT%H:%M:%SZ")` (whole-second precision is enough; microseconds add noise without value). |
| **Error Rule** | **Never raise.** `datetime.now(timezone.utc)` cannot fail in CPython under normal conditions; if it ever does, return `"1970-01-01T00:00:00Z"` so the field is always present and ISO-parseable. |

A single helper (rather than inlining the call) keeps the format in one place — important when F19 adds Pydantic validation that may want microseconds or `+00:00` style.

### Modifications to `process_pdf`

Capture the timestamp **once at the top of `process_pdf`** (before any heavy work), so the value reflects "when extraction started" and so retries within the function don't shift it:

```python
def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
    extracted_at = make_extracted_at()  # capture once, top of function
    # ... existing docling, masthead, splitting, scoring ...
    # ... existing F13 pdf_sha256 + gazette_issue_id block ...
```

Then add the three keys to the top-level `record` dict, **adjacent to the existing F13 identity block** (right after `gazette_issue_id`, before `warnings`) so the envelope's identity + versioning header reads as one logical group:

| Key | Value | Position in record dict |
|-----|-------|-------------------------|
| `library_version` | `LIBRARY_VERSION` | After `gazette_issue_id`, before `warnings` |
| `schema_version` | `SCHEMA_VERSION` | After `library_version` |
| `extracted_at` | `extracted_at` (captured at top) | After `schema_version` |

No per-notice change. Corrigenda unchanged. F13 fields unchanged.

### Imports

Add to the helper cell's imports (top of cell, not per-call):

```python
from datetime import datetime, timezone
```

### Error handling rule (consolidated)

- **Never raise.** All three fields must always be present on the record.
- `library_version` and `schema_version` are constants — they cannot fail.
- `extracted_at` defaults to the Unix epoch ISO string if `datetime.now` somehow raises.
- A missing or malformed timestamp **does not** add a warning to `record["warnings"]` — F14 is infallible by construction.

### Determinism guarantees (Quality Gate 2)

| Field | Deterministic across runs? | Notes |
|-------|----------------------------|-------|
| `library_version` | Yes | Module constant. Changes only when the developer bumps it. |
| `schema_version` | Yes | Module constant. Changes only on schema shape change. |
| `extracted_at` | **No, by design** | Changes every run. Document this loudly — it is **excluded** from any content-equality check. Gate 2 (`notice_id` stability) is unaffected. |

---

## 3. Test Cases

| ID | Scenario | Source File | Expected Result |
|----|----------|-------------|-----------------|
| **T1** | Happy path — modern clean | `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json` (re-run) | Top-level keys include `library_version`, `schema_version`, `extracted_at`. `library_version == "0.1.0"`. `schema_version == "1.0"`. `extracted_at` matches regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`. F13 fields (`pdf_sha256`, `gazette_issue_id`, `notice_id` on every notice) are still correct and unchanged. |
| **T2** | Format validation | T1 output | `re.fullmatch(r"\d+\.\d+\.\d+", record["library_version"])` matches. `re.fullmatch(r"\d+\.\d+", record["schema_version"])` matches. `datetime.fromisoformat(record["extracted_at"].replace("Z", "+00:00"))` parses without error and the parsed datetime has `tzinfo == timezone.utc`. |
| **T3** | Determinism partial (Gate 2 still holds) | Same PDF as T1, two runs | Run `process_pdf` twice on `Kenya Gazette Vol CXXIVNo 282.pdf`. Assert `r1["library_version"] == r2["library_version"]` and `r1["schema_version"] == r2["schema_version"]`. Assert `r1["extracted_at"] != r2["extracted_at"]` (timestamps differ between runs — confirms per-run capture, not a frozen constant). Assert F13 ids still match: `r1["pdf_sha256"] == r2["pdf_sha256"]`, `r1["gazette_issue_id"] == r2["gazette_issue_id"]`, `[n["notice_id"] for n in r1["gazette_notices"]] == [n["notice_id"] for n in r2["gazette_notices"]]`. **Gate 2 is unaffected** because it never inspects `extracted_at`. |
| **T4** | Cross-gazette consistency | Re-run `Kenya Gazette Vol CXINo 100.pdf`, `Kenya Gazette Vol CXIXNo 194.pdf`, `Kenya Gazette Vol CXXIVNo 282.pdf` | All three records have identical `library_version` (`"0.1.0"`) and identical `schema_version` (`"1.0"`). Each has its own `extracted_at` (may differ across the three calls). Versioning fields do not depend on PDF content. |

**Validation steps:**

1. Re-run pipeline on `Kenya Gazette Vol CXXIVNo 282.pdf`; load resulting JSON; assert top-level keys include `library_version`, `schema_version`, `extracted_at`.
2. Apply the format regexes from T2.
3. Run `process_pdf` twice on the same PDF in the same Python session; capture both records; apply T3 assertions.
4. Run pipeline on the other two PDFs; apply T4 cross-record assertions.
5. Run `check_regression()` — must pass (envelope additions do not affect confidence numbers).

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F14: Envelope Versioning Fields**

Read this spec: `specs/F14-envelope-versioning.md`

Implement in location: `gazette_docling_pipeline_spatial.ipynb` — extend the existing F13 identity helper cell (around line ~1788) with two module-level constants and one helper function, then modify `GazettePipeline.process_pdf` to capture `extracted_at` at the top of the function and to add the three new keys to the top-level `record` dict next to the F13 identity block.

Requirements:

1. In the F13 helper cell, add `from datetime import datetime, timezone` to the cell imports (alongside the existing `import hashlib`).
2. In the same cell, add two module-level constants directly under the imports:
   - `LIBRARY_VERSION = "0.1.0"` — semver string for the kenya_gazette package; lone source of truth, will migrate to `kenya_gazette.__version__` at F17.
   - `SCHEMA_VERSION = "1.0"` — `MAJOR.MINOR` for the Envelope JSON shape; bump rules per `docs/library-contract-v1.md` section 7.
3. Add helper function `make_extracted_at() -> str` returning a UTC ISO 8601 timestamp formatted as `"%Y-%m-%dT%H:%M:%SZ"` (whole-second precision, `Z` suffix). Wrap in try/except returning `"1970-01-01T00:00:00Z"` on the (impossible) failure path so the function never raises.
4. In `GazettePipeline.process_pdf`, capture the timestamp **once at the very top of the function** (before docling conversion) with `extracted_at = make_extracted_at()`. Do not re-capture it later. Do not capture it per-notice.
5. In the top-level `record` dict construction, insert the three keys directly after `gazette_issue_id` and before `warnings`, in this exact order:
   ```python
   "gazette_issue_id": gazette_issue_id,
   "library_version": LIBRARY_VERSION,
   "schema_version": SCHEMA_VERSION,
   "extracted_at": extracted_at,
   "warnings": warnings,
   ```
6. Do not add any per-notice or per-corrigendum versioning fields. The three fields are envelope-level only.
7. Never raise. The three fields must always be present on the record.
8. Run all 4 test cases (Section 3) by re-processing `Kenya Gazette Vol CXXIVNo 282.pdf`, `Kenya Gazette Vol CXINo 100.pdf`, and `Kenya Gazette Vol CXIXNo 194.pdf`. For T3, call `process_pdf` twice on the same PDF inside the same Python session and compare records.
9. After implementation, run `check_regression()` — must pass with no degradation (no confidence numbers should move).
10. Update PROGRESS.md: F14 status `⬜ Not started` → `⬜ In Progress` → `✅ Complete`. Move "Today" to F15. Add a Session Log row.
11. Return final status: PASS (all tests pass + regression OK) or FAIL (what broke).

**Build Report Format:**

```markdown
# Build Report: F14

## Implementation
- Location: helper cell at line ~1788 extended with `LIBRARY_VERSION`, `SCHEMA_VERSION`, `make_extracted_at`. `process_pdf` modified at line ~XXXX (top: extracted_at capture) and line ~2005 (record dict).
- Constants + helper: ~10 lines total
- process_pdf changes: 1 line at top, 3 keys inserted into record dict

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 | PASS/FAIL | All three fields present in CXXIVNo 282 record |
| T2 | PASS/FAIL | Format regexes pass; extracted_at parses as UTC datetime |
| T3 | PASS/FAIL | versions stable across two runs; extracted_at differs; F13 ids identical (Gate 2 holds) |
| T4 | PASS/FAIL | All 3 gazettes share library_version="0.1.0" and schema_version="1.0" |

## Regression
Status: PASS/FAIL

## Quality Gate 2
Status: STILL CLEARED (extracted_at excluded from identity check)

## Final Status: PASS/FAIL
```

---
