# F13 Spec: Identity Fields Wired into Record

## 1. What to Build

Wire the three canonical identity fields from `library-contract-v1.md` section 2 into every record produced by `process_pdf`: `pdf_sha256` (SHA-256 of the source PDF bytes), `gazette_issue_id` (the `KE-GAZ-...` canonical issue key derived from the F11 masthead), and `notice_id` (the per-notice composite key `f"{gazette_issue_id}:{notice_no}"`). `pdf_sha256` is already computed in `process_pdf`; this feature adds `gazette_issue_id` to the record and back-fills `notice_id` and `gazette_issue_id` onto every entry in `gazette_notices` (and `corrigenda` where applicable). The defining requirement is **determinism**: re-running the same PDF must produce byte-identical `pdf_sha256`, `gazette_issue_id`, and `notice_id` values across runs (Quality Gate 2). Identity construction must never raise — when masthead fields are missing or unparseable, the issue id falls back to `KE-GAZ-UNKNOWN-{pdf_sha256[:12]}` and a `masthead.parse_failed` warning is appended to the record's `warnings` list.

---

## 2. Interface Contract

### Helper functions (new)

| Aspect | Specification |
|--------|---------------|
| **Function** | `compute_pdf_sha256(pdf_path: Path) -> str` |
| **Input** | `pdf_path`: existing PDF file path |
| **Output** | Lowercase hex string, length 64 (SHA-256 of file bytes) |
| **Error Rule** | Never raise. On read failure return `"unknown_" + pdf_path.name` (length-stable enough for fallback id; logged via warning by caller). |

| Aspect | Specification |
|--------|---------------|
| **Function** | `make_gazette_issue_id(masthead: dict, pdf_sha256: str) -> tuple[str, bool]` |
| **Input** | `masthead`: dict from `parse_masthead()` with keys `volume`, `issue_no`, `publication_date`, `supplement_no`; `pdf_sha256`: hex digest used only for fallback |
| **Output** | `(issue_id, is_fallback)` where `issue_id` is either canonical `KE-GAZ-{volume}-{issue_no}-{publication_date}[-S{n}]` or fallback `KE-GAZ-UNKNOWN-{pdf_sha256[:12]}`; `is_fallback` is `True` when any required masthead field was missing |
| **Error Rule** | Never raise. Required fields are `volume`, `issue_no`, `publication_date`. If any is `None`, return fallback. `supplement_no` is optional — appended as `-S{n}` only when present and non-zero. |

| Aspect | Specification |
|--------|---------------|
| **Function** | `make_notice_id(gazette_issue_id: str, gazette_notice_no: Any, line_span_start: int) -> str` |
| **Input** | `gazette_issue_id` from above; `gazette_notice_no` (int, str like `"31A"`, or `None` for orphan blocks); `line_span_start`: integer line index from `provenance.line_span[0]`, used only for orphan stability |
| **Output** | `f"{gazette_issue_id}:{gazette_notice_no}"` when `gazette_notice_no` is not `None`; `f"{gazette_issue_id}:_orphan_{line_span_start}"` otherwise |
| **Error Rule** | Never raise. `None` line span defaults to `0`. Output is always a non-empty string. |

### Modifications to `process_pdf`

After the existing `pdf_sha256` computation and after `notices = score_notices(notices)` runs, add a single identity-stamping pass:

1. Call `make_gazette_issue_id(masthead_data, pdf_sha256)` to get `(gazette_issue_id, is_fallback)`.
2. If `is_fallback`, append a `Warning`-shaped dict to a new `warnings` list on the record:
   ```python
   {"kind": "masthead.parse_failed", "message": "...", "where": {"pdf_file_name": pdf_path.name}}
   ```
3. For each notice in `notices`:
   - Set `notice["gazette_issue_id"] = gazette_issue_id`
   - Set `notice["notice_id"] = make_notice_id(gazette_issue_id, notice["gazette_notice_no"], (notice.get("provenance") or {}).get("line_span", [0, 0])[0])`
4. For each corrigendum in `corrigenda` (if list of dicts), set `corrigendum["gazette_issue_id"] = gazette_issue_id` (no `notice_id` — corrigenda are not notices).

### Record additions

Add to the top-level `record` dict returned by `process_pdf`:

| Key | Value |
|-----|-------|
| `gazette_issue_id` | string from `make_gazette_issue_id` |
| `warnings` | list of warning dicts; empty list when no fallback |

`pdf_sha256` is already present and unchanged.

### Determinism guarantees (Quality Gate 2)

- `pdf_sha256` derives from file bytes only — always reproducible.
- `gazette_issue_id` derives from masthead fields (or `pdf_sha256[:12]` in fallback) — both deterministic for a given PDF.
- `notice_id` for keyed notices uses `gazette_notice_no` (extracted by deterministic regex). For orphan blocks (`gazette_notice_no is None`), the id uses `provenance.line_span[0]`, which is a position in the spatial plain text — also deterministic for a given PDF. **Never use list index, processing time, random values, or `id()`**.

---

## 3. Test Cases

| ID | Scenario | Source File | Expected Result |
|----|----------|-------------|-----------------|
| **T1** | Happy path — modern clean | `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json` (re-run) | `pdf_sha256` = `fd6adb427496096cd9e00ad652e7915556a021518c4713a7d929c918f9daf12e`. `gazette_issue_id` = `KE-GAZ-CXXIV-282-2022-12-23`. First notice (`gazette_notice_no` 15793) has `notice_id` = `KE-GAZ-CXXIV-282-2022-12-23:15793`. `record["warnings"]` is `[]`. |
| **T2** | Determinism (Gate 2) | Same PDF as T1, two runs | Run `process_pdf` twice on `Kenya Gazette Vol CXXIVNo 282.pdf`. All 201 `notice_id`s identical between runs (pairwise `==`). `gazette_issue_id` identical. `pdf_sha256` identical. |
| **T3** | Degraded — missing masthead fields | Synthetic call: `make_gazette_issue_id({"volume": None, "issue_no": None, "publication_date": None, "supplement_no": None}, "abc123def456...")` | Returns `("KE-GAZ-UNKNOWN-abc123def456", True)`. Notices still get a `notice_id` shaped `KE-GAZ-UNKNOWN-abc123def456:{notice_no}`. When called via `process_pdf`, `record["warnings"]` contains a `masthead.parse_failed` entry. No exception raised. |
| **T4** | Cross-gazette uniqueness | Re-run `Kenya Gazette Vol CXINo 100.pdf` and `Kenya Gazette Vol CXXIVNo 282.pdf` | CXINo 100 → `gazette_issue_id` = `KE-GAZ-CXI-100-2009-11-20-S76` (supplement 76). CXXIVNo 282 → `KE-GAZ-CXXIV-282-2022-12-23`. The two ids differ. No `notice_id` from one issue collides with any from the other. |
| **T5** | Orphan block stability | `output/Kenya Gazette Vol CXIXNo 194/Kenya Gazette Vol CXIXNo 194_gazette_spatial.json` (has 1 notice with `gazette_notice_no = None`) | The orphan notice gets `notice_id` = `KE-GAZ-{...}:_orphan_{N}` where `N` is `provenance.line_span[0]` for that notice. Re-running the same PDF produces the same `_orphan_{N}` id. |
| **T6** | Supplement formatting | Re-run `Kenya Gazette Vol CXINo 100.pdf` | `gazette_issue_id` ends with `-S76` (since `supplement_no=76`). For CXXIVNo 282 (`supplement_no=None`), id has no `-S` suffix. |

**Validation steps:**

1. Re-run pipeline on `Kenya Gazette Vol CXXIVNo 282.pdf`; load resulting JSON; assert top-level keys include `pdf_sha256`, `gazette_issue_id`, `warnings`.
2. Assert every notice in `gazette_notices` has both `notice_id` and `gazette_issue_id` keys.
3. Run pipeline twice on same PDF; load both JSONs; assert `[n["notice_id"] for n in r1["gazette_notices"]] == [n["notice_id"] for n in r2["gazette_notices"]]`.
4. Assert `len(set(notice_ids)) == len(notice_ids)` (no duplicate ids within an issue).
5. Run `check_regression()` — must pass (no change to confidence numbers).

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F13: Identity Fields Wired into Record**

Read this spec: `specs/F13-identity-fields.md`

Implement in location: `gazette_docling_pipeline_spatial.ipynb` — add a new helper cell defining `compute_pdf_sha256`, `make_gazette_issue_id`, `make_notice_id` near the top of the orchestration section (before the `GazettePipeline` class around line 1863). Then modify `GazettePipeline.process_pdf` to call them and stamp ids onto notices.

Requirements:

1. Add three helpers per the Interface Contract (Section 2):
   - `compute_pdf_sha256(pdf_path: Path) -> str` — read file bytes, SHA-256, lowercase hex.
   - `make_gazette_issue_id(masthead: dict, pdf_sha256: str) -> tuple[str, bool]` — build canonical `KE-GAZ-{volume}-{issue_no}-{publication_date}[-S{n}]` or fallback `KE-GAZ-UNKNOWN-{pdf_sha256[:12]}`.
   - `make_notice_id(gazette_issue_id: str, gazette_notice_no: Any, line_span_start: int) -> str` — composite for keyed notices, `_orphan_{line_span_start}` for `None`.
2. Refactor `process_pdf` to use `compute_pdf_sha256` (replace inline `hashlib.sha256(pdf_bytes).hexdigest()` block) and to call `make_gazette_issue_id` after `parse_masthead`.
3. After `notices = score_notices(notices)` (and after the OCR-cap loop), iterate over `notices` and stamp `notice["gazette_issue_id"]` and `notice["notice_id"]` onto each. Use `provenance.line_span[0]` for orphan stability — never list index.
4. Iterate over `corrigenda` (list returned by `extract_corrigenda`); if items are dicts, stamp `gazette_issue_id` onto each. Skip if shape is something else.
5. Add `gazette_issue_id` and `warnings` to the top-level `record` dict. Initialize `warnings = []`. When `is_fallback` is `True`, append `{"kind": "masthead.parse_failed", "message": "Required masthead field missing; using fallback issue id", "where": {"pdf_file_name": pdf_path.name}}`.
6. Move the `import hashlib` to a top-of-cell or top-of-notebook import (no per-call imports).
7. Never raise from any of the three helpers or from the stamping loop. Missing keys → defaults.
8. Run all 6 test cases (Section 3) by re-processing `Kenya Gazette Vol CXXIVNo 282.pdf`, `Kenya Gazette Vol CXINo 100.pdf`, and `Kenya Gazette Vol CXIXNo 194.pdf`.
9. After implementation, run `check_regression()` — must pass with no degradation.
10. Update PROGRESS.md: F13 status `⬜ Not started` → `⬜ In Progress` → `✅ Complete`. Update Gate 2 status to `✅ Cleared` once T2 passes. Move "Today" to F14 and add a Session Log row.
11. Return final status: PASS (all tests pass + regression OK) or FAIL (what broke).

**Build Report Format:**

```markdown
# Build Report: F13

## Implementation
- Location: helper cell added at line ~XXXX, `process_pdf` modified at line ~1888 and ~1926-1936
- Helpers: `compute_pdf_sha256`, `make_gazette_issue_id`, `make_notice_id` (~30 lines total)
- Stamping pass: ~10 lines after `score_notices`
- Record additions: `gazette_issue_id`, `warnings`

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 | PASS/FAIL | issue_id = KE-GAZ-CXXIV-282-2022-12-23, sha256 match |
| T2 | PASS/FAIL | All 201 notice_ids identical across two runs |
| T3 | PASS/FAIL | Fallback id KE-GAZ-UNKNOWN-..., warning emitted |
| T4 | PASS/FAIL | CXINo 100 vs CXXIVNo 282 ids differ |
| T5 | PASS/FAIL | Orphan id stable across runs |
| T6 | PASS/FAIL | Supplement -S76 suffix present for CXINo 100 |

## Regression
Status: PASS/FAIL

## Quality Gate 2
Status: CLEARED / NOT CLEARED

## Final Status: PASS/FAIL
```

---
