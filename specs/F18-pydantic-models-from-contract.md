# F18 Spec: Pydantic Models from Contract

## 1. What to Build

Translate every model defined in `docs/library-contract-v1.md` section 3 (the "Envelope and Notice Pydantic models" section) into concrete **Pydantic v2** classes that live under `kenya_gazette_parser/models/`. This covers the full output envelope surface: the top-level `Envelope`, the issue wrapper `GazetteIssue` (which holds the identity keys `gazette_issue_id`, `volume`, `issue_no`, `publication_date`, `supplement_no`, `masthead_text`, `parse_confidence`), `Notice` (with its nested `BodySegment`, optional `DerivedTable`, and identity fields `notice_id` / `gazette_issue_id` / `content_sha256`), `Corrigendum`, the confidence triad (`ConfidenceScores`, `DocumentConfidence`), `Provenance`, `LayoutInfo`, and the lightweight `Warning` and `Cost` types. All classes inherit a shared strict base (`model_config = ConfigDict(extra="forbid")`) so unknown fields are rejected loudly during F19 validation. No pipeline logic changes; `parse_file` / `parse_bytes` in `kenya_gazette_parser/__init__.py` keep their F17 stubs. In parallel, bump `pyproject.toml` `[project].dependencies` to add `pydantic>=2.0` (and re-run `pip install -e .` so the venv picks it up). Success is a green `from kenya_gazette_parser.models import Envelope, GazetteIssue, Notice, Corrigendum, ConfidenceScores, DocumentConfidence, Provenance, LayoutInfo, BodySegment, DerivedTable, Warning, Cost` plus the test cases in section 3 below. Gate 1 (regression on the 6 canonical PDFs) must stay cleared — the notebook is not edited.

---

## 2. Interface Contract

### Module layout (locked)

| File | Classes defined |
|------|-----------------|
| `kenya_gazette_parser/models/__init__.py` | Re-exports every public class; sets `__all__` with the 12 names listed in section 1. |
| `kenya_gazette_parser/models/base.py` | `StrictBase(BaseModel)` — shared parent with `model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=False)`. Every other model in this package subclasses `StrictBase` (not `BaseModel` directly). |
| `kenya_gazette_parser/models/envelope.py` | `Envelope`, `GazetteIssue`, `DocumentConfidence`, `LayoutInfo`, `Warning`, `Cost`. |
| `kenya_gazette_parser/models/notice.py` | `Notice`, `BodySegment`, `DerivedTable`, `Corrigendum`, `ConfidenceScores`, `Provenance`. |

Any Agent-2 split that preserves the **public import surface** (`from kenya_gazette_parser.models import <Name>`) is acceptable; above is the recommended shape. No new top-level `__init__.py` exports in F18 — the models are only reachable via `kenya_gazette_parser.models`. F19 wires them into `kenya_gazette_parser.__init__`.

### Model-by-model field contract

All field names, types, and optionality come verbatim from `docs/library-contract-v1.md` section 3. Each class accepts a **raw Python dict** (the kind produced by the notebook today or read back from a JSON file) and produces a **validated Pydantic instance**. Pydantic v2 `.model_dump(mode="json")` round-trips back to a dict that matches the source on valid inputs.

| Model | Required fields | Optional / nullable fields | Notes |
|-------|-----------------|----------------------------|-------|
| `Envelope` | `library_version: str`, `schema_version: str`, `output_format_version: int`, `extracted_at: datetime`, `pdf_sha256: str`, `issue: GazetteIssue`, `notices: list[Notice]`, `corrigenda: list[Corrigendum]`, `document_confidence: DocumentConfidence`, `layout_info: LayoutInfo`, `warnings: list[Warning]` | `cost: Cost \| None = None` | `extracted_at` accepts ISO 8601 strings (e.g. `"2026-04-20T03:35:08Z"`) — Pydantic v2 parses to aware `datetime`. |
| `GazetteIssue` | `gazette_issue_id: str`, `masthead_text: str`, `parse_confidence: float` | `volume: str \| None`, `issue_no: int \| None`, `publication_date: date \| None`, `supplement_no: int \| None = None` | `parse_confidence` is NOT constrained to `[0.0, 1.0]` at the Pydantic layer — the contract documents the meaning but invalid values surface as warnings, not validation errors (matches notebook behavior). |
| `Notice` | `notice_id: str`, `gazette_issue_id: str`, `title_lines: list[str]`, `gazette_notice_full_text: str`, `body_segments: list[BodySegment]`, `other_attributes: dict[str, Any]`, `provenance: Provenance`, `confidence_scores: ConfidenceScores`, `confidence_reasons: list[str]`, `content_sha256: str` | `gazette_notice_no: str \| None`, `gazette_notice_header: str \| None`, `derived_table: DerivedTable \| None = None` | `content_sha256` is contract-new (not in current `_gazette_spatial.json` output) and will be populated by F19/F20; tests build it manually. `other_attributes` is deliberately `dict[str, Any]` — carry-through for notebook-emitted fields like `char_span_start_line`. |
| `BodySegment` | `type: Literal["text", "blank"]`, `lines: list[str]` | — | The contract locks only `"text"` and `"blank"` for 1.0 (richer types arrive in 2.x as a MINOR bump). Use `Literal` so unknown types fail validation today. |
| `DerivedTable` | `rows: list[list[str]]` | `columns: list[str] \| None = None`, `notice_id: str \| None = None` | Contract does not lock the shape; this minimal skeleton is placeholder. Setting `model_config = ConfigDict(extra="allow")` on this one class (override `StrictBase`) so the 2.x richer schema can add fields without breaking 1.0 consumers. Flag this as the only `extra="allow"` exception in the package. |
| `Corrigendum` | `scope: Literal["issue_level", "notice_is_corrigendum", "notice_references_other"]`, `raw_text: str`, `provenance: Provenance` | `target_notice_no: str \| None`, `target_year: int \| None`, `amendment: str \| None` | Current `_gazette_spatial.json` emits a looser corrigendum shape (`referenced_notice_no`, `what_corrected`, etc.); F19/F20 will map between them. Tests use contract-shape dicts. |
| `ConfidenceScores` | `notice_number: float`, `structure: float`, `spatial: float`, `boundary: float`, `composite: float` | `table: float \| None = None` | No numeric range clamp at the Pydantic layer (see `parse_confidence` note above). |
| `Provenance` | `header_match: Literal["strict", "recovered", "inferred", "none"]`, `line_span: tuple[int, int]` | `raw_header_line: str \| None = None`, `stitched_from: list[str] = []`, `ocr_quality: float \| None = None` | `line_span` as `tuple[int, int]` — Pydantic v2 accepts JSON `[50, 70]` and coerces to tuple. Default for `stitched_from` uses `Field(default_factory=list)` to avoid mutable default pitfall. |
| `DocumentConfidence` | `layout: float`, `ocr_quality: float`, `notice_split: float`, `composite: float`, `counts: dict[Literal["high", "medium", "low"], int]`, `mean_composite: float`, `min_composite: float`, `n_notices: int` | `ocr_reasons: list[str] = []` | `counts` must have exactly the three literal keys — any other key raises `ValidationError`. |
| `LayoutInfo` | `layout_confidence: float`, `pages: list[dict[str, Any]]` | — | Per contract open question: `PageLayout` stays `dict[str, Any]` in 1.0. Do NOT introduce a `PageLayout` class in F18 — F18 follows the contract's explicit "lean toward `dict`" decision. |
| `Warning` | `kind: str`, `message: str` | `where: dict[str, Any] \| None = None` | Class name `Warning` matches the contract verbatim. It shadows the Python built-in when imported by name; callers who mix both should use `from kenya_gazette_parser.models import Warning as GazetteWarning`. Document this in a single-line module docstring; do not rename. |
| `Cost` | `llm_calls: int`, `prompt_tokens: int`, `completion_tokens: int` | `usd_estimate: float \| None = None` | — |

### Strictness and error rules

| Boundary | Rule |
|----------|------|
| Extra fields in input dict | `StrictBase.model_config = ConfigDict(extra="forbid")` → raises `pydantic.ValidationError`. Only `DerivedTable` overrides to `extra="allow"` (documented above). |
| Missing required field | Raises `ValidationError` with `type="missing"`. No silent defaults. |
| Wrong type (e.g. string where `int` expected) | Pydantic's default coercion is moderate (e.g. `"5"` → `5` for `int`); rely on v2 defaults. Anything that cannot be coerced raises `ValidationError`. |
| Unknown `Literal` value (e.g. `header_match="wiggle"`, `scope="garbage"`, `body_segment.type="table"`) | Raises `ValidationError` with `type="literal_error"`. |
| `.model_dump()` round-trip | For any dict `d` that validates cleanly, `M.model_validate(d).model_dump(mode="json")` must equal `d` once both are normalized (datetimes → ISO strings, dates → `YYYY-MM-DD`, tuples → lists). Tested in T4. |
| Unused model import at `kenya_gazette_parser.__init__` | None. F18 only populates `kenya_gazette_parser/models/`; `parse_file` / `parse_bytes` stubs stay as in F17. |

### Dependency bump

`pyproject.toml` edit (exact diff):

```toml
dependencies = [
    "docling>=2.86.0,<3",
    "docling-core>=2.0.0",
    "openai>=1.40.0",
    "pydantic>=2.0",
]
```

That is the only line added. Version bound is a lower-bound-only `>=2.0` — the contract explicitly calls Pydantic v2 syntax, and we do not cap the major because 2.x is pre-3.0 stable. Re-run `pip install -e .` after the edit so the venv picks up `pydantic` (and its `pydantic-core` transitive).

### Non-goals for F18

- No changes to `gazette_docling_pipeline_spatial.ipynb`. Gate 1 (regression) and Gate 2 (deterministic `notice_id`) must still be cleared after F18.
- No changes to `parse_file` / `parse_bytes` stubs in `kenya_gazette_parser/__init__.py`. Those still raise `NotImplementedError`. Wiring validation into the pipeline is F19.
- No JSON Schema export (`kenya_gazette_parser/schemas/`). That is F23.
- No `GazetteConfig`, `LLMPolicy`, `RuntimeOptions`, `Bundles` models. Those are contract section 5 types and land in F22.

---

## 3. Test Cases

Run all tests from the project venv (`.venv\Scripts\python.exe` on Windows) at repo root after `pip install -e .` picks up `pydantic`. The real-file tests anchor on `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json` (chosen because it has the F13/F14 identity + versioning fields stamped, per the PROGRESS.md session log).

| ID | Scenario | Input | Expected Result |
|----|----------|-------|-----------------|
| **T1** | **Happy path — all 12 classes importable and instantiate.** Models load cleanly and `__all__` is set. | `python -c "from kenya_gazette_parser.models import (Envelope, GazetteIssue, Notice, Corrigendum, ConfidenceScores, DocumentConfidence, Provenance, LayoutInfo, BodySegment, DerivedTable, Warning, Cost); import kenya_gazette_parser.models as m; assert set(m.__all__) >= {'Envelope','GazetteIssue','Notice','Corrigendum','ConfidenceScores','DocumentConfidence','Provenance','LayoutInfo','BodySegment','DerivedTable','Warning','Cost'}; print('T1 OK')"` | Prints `T1 OK`. Exit code `0`. No `ImportError`, no `ModuleNotFoundError`. |
| **T2** | **Happy path on real Notice dict.** Load the first notice from `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json`, stamp the contract-new field `content_sha256` (since it is not in the current on-disk output), and validate as `Notice`. Proves the current notebook-emitted notice shape is a strict subset of the Pydantic `Notice` contract. | Python script in `scripts/f18_validate_real_notice.py`: load JSON, pick `data["gazette_notices"][0]`, add `notice["content_sha256"] = hashlib.sha256(notice["gazette_notice_full_text"].encode("utf-8")).hexdigest()`, call `Notice.model_validate(notice)`. | `ValidationError` is NOT raised. `notice_obj.notice_id` starts with `"KE-GAZ-CXXIV-282-"`, `notice_obj.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"`, `notice_obj.provenance.header_match == "strict"`, `notice_obj.body_segments[0].type in {"text","blank"}`. Prints `T2 OK`. |
| **T3** | **Edge case — optional fields missing / None.** Build a minimal `Notice` dict that omits every optional field (`gazette_notice_no=None`, `gazette_notice_header=None`, no `derived_table`), plus a minimal `Envelope` whose `cost` is absent and whose `corrigenda`/`notices`/`warnings` are all empty lists. Validate both. | Inline Python (or in `scripts/f18_edge_cases.py`): construct dict literals with only the required keys per section 2, leaving all optionals out. Call `Notice.model_validate(...)` and `Envelope.model_validate(...)`. | Both validations succeed. `notice_obj.gazette_notice_no is None`, `notice_obj.derived_table is None`, `env.cost is None`, `env.notices == []`. Prints `T3 OK`. |
| **T4** | **Degraded — invalid inputs raise `ValidationError`.** Four sub-cases, each must raise `pydantic.ValidationError`: (a) `Notice.model_validate({**valid_notice, "notice_id": 123})` — wrong type on required field; (b) `Provenance.model_validate({"header_match": "bogus", "line_span": [0, 1]})` — unknown `Literal` value; (c) `Envelope.model_validate({**valid_env, "unknown_field": "x"})` — extra field under `extra="forbid"`; (d) `BodySegment.model_validate({"type": "table", "lines": []})` — `"table"` not in 1.0 `Literal`. | `scripts/f18_degraded.py`: four `try/except pydantic.ValidationError` blocks. | All four sub-cases raise `ValidationError`. Sub-case (c)'s error mentions `"unknown_field"` and `extra_forbidden`. Prints `T4 OK` only after all four pass. |
| **T5** | **Round-trip — `model_dump(mode="json")` preserves the source dict.** Take the real-notice dict from T2 (after adding `content_sha256`) and assert that validating then dumping produces the same JSON once normalized (tuples → lists, datetimes → ISO strings). | `scripts/f18_round_trip.py`: `after = Notice.model_validate(before).model_dump(mode="json")`; normalize `before` by `json.loads(json.dumps(before))` (to coerce tuples if any); assert `before == after`. Repeat with a synthetic `Envelope` dict. | Equality holds for both. Prints `T5 OK`. |
| **T6** | **Regression — notebook pipeline still green.** In Jupyter, run the cell defining `check_regression()` (after running its setup cells) and call it. Because F18 does not touch the notebook, all 6 canonical PDFs must still match `tests/expected_confidence.json`. | `check_regression()` in `gazette_docling_pipeline_spatial.ipynb`. | Returns / prints OK for all 6 canonical PDFs: `Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`. Gate 1 stays cleared. |

**Helper scripts recommended** (all under `scripts/`, one per test to keep the build report clean):

- `scripts/f18_validate_real_notice.py` (T2)
- `scripts/f18_edge_cases.py` (T3)
- `scripts/f18_degraded.py` (T4)
- `scripts/f18_round_trip.py` (T5)

Inline `-c` commands are fine for T1. T6 runs in Jupyter.

**Not tested in F18** (deferred): no `Envelope` validated against a real on-disk top-level JSON (current files use `gazette_notices` not `notices` and flat issue fields — that adapter is F19/F20); no JSON Schema export (F23); no `parse_file` end-to-end (F20-F21).

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F18: Pydantic models from contract**

Read this spec: `specs/F18-pydantic-models-from-contract.md`. Read `docs/library-contract-v1.md` section 3 — it is the source of truth for every field name and type. Do NOT touch `gazette_docling_pipeline_spatial.ipynb` or any file under `output/`, `pdfs/`, `.llm_cache/`, or `tests/`. The notebook must keep running so Gate 1 (regression on 6 canonical PDFs) stays cleared.

**Core files location:** `kenya_gazette_parser/models/` (new submodule, sibling of `kenya_gazette_parser/__init__.py`, `kenya_gazette_parser/__version__.py`, `kenya_gazette_parser/py.typed`).

**Requirements (do these in order):**

1. **Bump `pyproject.toml` dependencies.** Open `pyproject.toml` at repo root. In the `[project].dependencies` array, add one new entry after `"openai>=1.40.0"`:

   ```toml
   "pydantic>=2.0",
   ```

   Do not change any other dependency bound. Do not add `pydantic` to the `[project.optional-dependencies].dev` list — it is a runtime dependency.

2. **Re-install the package** so the venv picks up Pydantic: from the repo root, run `.\.venv\Scripts\python.exe -m pip install -e .`. Confirm the install output includes `Successfully installed ... pydantic-2.x.y ...` (and `pydantic-core`). Keep note of the exact Pydantic version installed for the Build Report.

3. **Create the package directory** `kenya_gazette_parser/models/` if it does not already exist.

4. **Create `kenya_gazette_parser/models/base.py`** containing `StrictBase(BaseModel)` with:

   ```python
   from pydantic import BaseModel, ConfigDict

   class StrictBase(BaseModel):
       model_config = ConfigDict(
           extra="forbid",
           validate_assignment=True,
           str_strip_whitespace=False,
       )
   ```

   Every other model in this submodule (except `DerivedTable` — see step 6) inherits from `StrictBase`, NOT from `BaseModel` directly.

5. **Create `kenya_gazette_parser/models/envelope.py`** with the six classes `Envelope`, `GazetteIssue`, `DocumentConfidence`, `LayoutInfo`, `Warning`, `Cost`. Follow the field tables in section 2 of the spec exactly. Notes:
   - `Envelope.extracted_at: datetime` — Pydantic v2 parses ISO 8601 strings automatically; do not add a custom validator.
   - `GazetteIssue.publication_date: date | None` — Pydantic v2 parses `"YYYY-MM-DD"` strings.
   - `DocumentConfidence.counts: dict[Literal["high","medium","low"], int]` — use `typing.Literal`; any other key must raise `ValidationError`.
   - `LayoutInfo.pages: list[dict[str, Any]]` — do NOT introduce a `PageLayout` class. The contract says lean toward `dict` in 1.0.
   - `Warning` — class name matches the contract verbatim. Add a one-line module docstring noting that this shadows the built-in `Warning` and that callers should use `as GazetteWarning` when mixing. Do not rename.
   - `Cost.usd_estimate: float | None = None` — optional.

6. **Create `kenya_gazette_parser/models/notice.py`** with the six classes `Notice`, `BodySegment`, `DerivedTable`, `Corrigendum`, `ConfidenceScores`, `Provenance`. Notes:
   - `BodySegment.type: Literal["text", "blank"]` — only these two values for 1.0. Unknown types must raise `ValidationError`.
   - `DerivedTable` is the ONE class that overrides `StrictBase` and sets `model_config = ConfigDict(extra="allow")` (so 2.x richer table schema can add fields without breaking consumers). Add an inline comment explaining this is the only `extra="allow"` exception in the package.
   - `Provenance.line_span: tuple[int, int]` — Pydantic v2 accepts JSON arrays and coerces to tuple.
   - `Provenance.stitched_from: list[str] = Field(default_factory=list)` — use `default_factory`, not `= []`.
   - `Notice.other_attributes: dict[str, Any]` — carry-through for notebook-emitted fields like `char_span_start_line`; do not introspect.
   - `Corrigendum.scope: Literal["issue_level", "notice_is_corrigendum", "notice_references_other"]` — exact three values from the contract.

7. **Create `kenya_gazette_parser/models/__init__.py`** that imports every public class and sets `__all__`. Example shape:

   ```python
   from kenya_gazette_parser.models.envelope import (
       Cost,
       DocumentConfidence,
       Envelope,
       GazetteIssue,
       LayoutInfo,
       Warning,
   )
   from kenya_gazette_parser.models.notice import (
       BodySegment,
       ConfidenceScores,
       Corrigendum,
       DerivedTable,
       Notice,
       Provenance,
   )

   __all__ = [
       "Envelope",
       "GazetteIssue",
       "Notice",
       "Corrigendum",
       "ConfidenceScores",
       "DocumentConfidence",
       "Provenance",
       "LayoutInfo",
       "BodySegment",
       "DerivedTable",
       "Warning",
       "Cost",
   ]
   ```

8. **Do not edit** `kenya_gazette_parser/__init__.py`. `parse_file` and `parse_bytes` stay as F17 stubs raising `NotImplementedError`. Wiring validation into the pipeline is F19.

9. **Run T1 (smoke import):**

   ```powershell
   .\.venv\Scripts\python.exe -c "from kenya_gazette_parser.models import (Envelope, GazetteIssue, Notice, Corrigendum, ConfidenceScores, DocumentConfidence, Provenance, LayoutInfo, BodySegment, DerivedTable, Warning, Cost); import kenya_gazette_parser.models as m; assert set(m.__all__) >= {'Envelope','GazetteIssue','Notice','Corrigendum','ConfidenceScores','DocumentConfidence','Provenance','LayoutInfo','BodySegment','DerivedTable','Warning','Cost'}; print('T1 OK')"
   ```

   Must print `T1 OK`.

10. **Write `scripts/f18_validate_real_notice.py` and run T2.** The script loads `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json`, picks `data["gazette_notices"][0]`, stamps `content_sha256 = hashlib.sha256(notice["gazette_notice_full_text"].encode("utf-8")).hexdigest()`, calls `Notice.model_validate(notice)`, and asserts: `.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"`, `.provenance.header_match == "strict"`, `.body_segments[0].type in {"text","blank"}`. On success, print `T2 OK`.

11. **Write `scripts/f18_edge_cases.py` and run T3.** Build a minimal `Notice` dict with every optional field omitted (`gazette_notice_no`, `gazette_notice_header`, `derived_table`) and a minimal `Envelope` with empty lists for `notices`/`corrigenda`/`warnings` and no `cost` field. Validate both. Assert `notice_obj.gazette_notice_no is None`, `notice_obj.derived_table is None`, `env.cost is None`. On success, print `T3 OK`.

12. **Write `scripts/f18_degraded.py` and run T4.** Run the four `try/except pydantic.ValidationError` sub-cases from section 3 T4 of this spec. All four must raise. Sub-case (c)'s error string must contain `"unknown_field"` and `"extra_forbidden"`. On success, print `T4 OK`.

13. **Write `scripts/f18_round_trip.py` and run T5.** Validate the T2 notice dict, call `.model_dump(mode="json")`, normalize the source dict by `json.loads(json.dumps(before))`, assert equality. Repeat with a synthetic `Envelope` dict (use `extracted_at="2026-04-20T03:35:08Z"` and a date-string `publication_date` to verify parse-then-serialize preserves ISO formats). On success, print `T5 OK`.

14. **Run T6 (regression):** in Jupyter, open `gazette_docling_pipeline_spatial.ipynb`, run the cell defining `check_regression()` and its setup cells, then call `check_regression()`. Must report OK for all 6 canonical PDFs in `tests/expected_confidence.json`: `Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`. If any PDF degrades, F18 is broken (since F18 does not touch the notebook, degradation means a bad install side effect — likely Pydantic clashing with a notebook import; investigate before continuing).

15. **Update `PROGRESS.md`** in this exact order of edits:
    - In the **Today** block, change `**Current:** F18 ...` to `**Current:** F19 — Validate at end of process_pdf` and update `**Previous:** F17 ...` to `**Previous:** F18 ✅ — Pydantic models from contract (kenya_gazette_parser/models/ populated, pydantic>=2.0 added)`.
    - In the **Work Items** table, change F18's row Status from `⬜ Not started` to `✅ Complete`.
    - Leave all **Quality Gates** rows as they are. F18 does not clear any new gate (Gate 4 needs F19+F23).
    - In **Session Log**, append a row dated `2026-04-20` (or today's date) with a one-paragraph summary: classes created (`Envelope`, `GazetteIssue`, `Notice`, `Corrigendum`, `ConfidenceScores`, `DocumentConfidence`, `Provenance`, `LayoutInfo`, `BodySegment`, `DerivedTable`, `Warning`, `Cost`), file layout (`models/base.py`, `models/envelope.py`, `models/notice.py`, `models/__init__.py`), `pyproject.toml` bump (`pydantic>=2.0`), and T1-T6 results including the exact Pydantic version installed.

16. **Return a Build Report** in the format below. If any test fails, report the exact failure output and stop — do not move on to F19 yourself.

**Build Report Format:**

```markdown
# Build Report: F18

## Implementation
- Files created:
  - `kenya_gazette_parser/models/__init__.py` (re-exports, __all__ with 12 names)
  - `kenya_gazette_parser/models/base.py` (StrictBase with extra="forbid")
  - `kenya_gazette_parser/models/envelope.py` (Envelope, GazetteIssue, DocumentConfidence, LayoutInfo, Warning, Cost)
  - `kenya_gazette_parser/models/notice.py` (Notice, BodySegment, DerivedTable, Corrigendum, ConfidenceScores, Provenance)
  - `scripts/f18_validate_real_notice.py`
  - `scripts/f18_edge_cases.py`
  - `scripts/f18_degraded.py`
  - `scripts/f18_round_trip.py`
- Files edited:
  - `pyproject.toml` (added `pydantic>=2.0` to [project].dependencies)
  - `PROGRESS.md` (F18 row → ✅; Today moved to F19; session log row appended)
- Files NOT touched: `gazette_docling_pipeline_spatial.ipynb`, `requirements.txt`, `kenya_gazette_parser/__init__.py`, `kenya_gazette_parser/__version__.py`, anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/`.

## Install
- Command: `.\.venv\Scripts\python.exe -m pip install -e .`
- Pydantic version installed: 2.X.Y  (paste exact)

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 — models import + __all__ | PASS/FAIL | |
| T2 — real notice validates | PASS/FAIL | issue_id = KE-GAZ-CXXIV-282-2022-12-23 |
| T3 — optional fields None | PASS/FAIL | |
| T4 — ValidationError on 4 degraded cases | PASS/FAIL | extra=forbid confirmed |
| T5 — round-trip dump equality | PASS/FAIL | |
| T6 — regression on 6 PDFs | PASS/FAIL | |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (T6 passes)
- Gate 2 (deterministic notice_id): STILL CLEARED (notebook untouched)
- Gate 3 (`from kenya_gazette_parser import parse_file` works): still PARTIAL — models land, but parse_file is still an F17 stub. Gate 3 fully clears at F21.
- Gate 4 (Envelope validates against JSON Schema): NOT REACHED (needs F19 + F23)

## PROGRESS.md
- F18 row: ⬜ Not started → ✅ Complete
- "Today" moved to F19 — Validate at end of process_pdf
- Session Log row appended

## Notes for F19
- Models are ready. F19 should call `Envelope.model_validate(record)` at the tail of `process_pdf` in the notebook, adapting the current flat output (`gazette_notices`, flat issue fields) into the nested `{issue: GazetteIssue, notices: [Notice]}` shape the contract requires. Expect to add `content_sha256` per notice during that adapter step.
- `DerivedTable` is the only `extra="allow"` model; every other model is strict. That matters for F19 because any stray key in a `Notice` dict will raise.

## Final Status: PASS / FAIL
```

---
