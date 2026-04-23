# F20 Spec: Move logic into modules

## 1. Goal (one sentence)

Copy every parsing, scoring, identity, and envelope-assembly helper out of `gazette_docling_pipeline_spatial.ipynb` into named submodules under `kenya_gazette_parser/` so the notebook becomes a thin demo that `from kenya_gazette_parser import ...`, while the 6 canonical PDFs still validate via `Envelope.model_validate` and `check_regression()` still reports PASS at the F19 baseline tolerance of 0.05.

---

## 2. Input/Output Contract

F20 is a **refactor**, not a behaviour change. The "I/O contract" is the set of migrated symbols the notebook re-imports, plus the rules that govern how they move. The two active-debt fixes (D1, D2) happen during the move because they collapse into "remove now-redundant line at the new call site".

### 2a. Target module layout (F20 scope only — F21 adds `parse_file` wiring)

```
kenya_gazette_parser/
  __init__.py             # unchanged from F17 — parse_file/parse_bytes still stubs
  __version__.py          # NOW also exports SCHEMA_VERSION (= "1.0"); see 2c
  py.typed                # unchanged
  models/                 # unchanged from F18 (Envelope, Notice, Warning, ...)
    __init__.py
    base.py
    envelope.py
    notice.py
  identity.py             # NEW — F11/F13/F14 identity + version helpers
  masthead.py             # NEW — F11 masthead parser
  spatial.py              # NEW — F2 spatial reorder + layout confidence
  splitting.py            # NEW — F3 notice splitter + helpers
  trailing.py             # NEW — F12 trailing-content detector
  corrigenda.py           # NEW — F4 corrigenda extractor (regex-based)
  scoring.py              # NEW — F5/F6 per-notice + per-document confidence
  envelope_builder.py     # NEW — F19 build_envelope_dict + corrigendum sub-adapter
  pipeline.py             # NEW — F20 orchestration; `build_envelope` pure function
```

### 2b. Per-module contents (exact symbols lifted from the notebook)

| Module | Public symbols (re-exported) | Private symbols (underscore-prefixed) | Source lines in notebook |
|--------|------------------------------|---------------------------------------|--------------------------|
| `identity.py` | `LIBRARY_VERSION`, `SCHEMA_VERSION` (both re-exported from `__version__.py`), `make_extracted_at`, `compute_pdf_sha256`, `make_gazette_issue_id`, `make_notice_id` | — | 1826-1916 |
| `masthead.py` | `parse_masthead` | — | 85-177 |
| `spatial.py` | `reorder_by_spatial_position`, `reorder_by_spatial_position_with_confidence`, `compute_page_layout_confidence` | `_BBoxElement`, `_table_to_text`, `_extract_elements`, `_get_page_dimensions`, `_reorder_page`, `_cluster_y_bands`, `_classify_band` | 1421-1800 |
| `splitting.py` | `split_gazette_notices` | `_strip_running_headers`, `_split_on_multiple_spaces`, `_extract_title_stack`, `_segment_body_lines`, `_repair_merged_rows`, `_try_parse_s_no_table`, `_ends_with_terminal_punct`, `_find_recovered_boundaries`, `_stitch_multipage_notices` | 297-760 |
| `trailing.py` | `detect_trailing_content_cutoff` | — | 569-616 |
| `corrigenda.py` | `extract_corrigenda` | (any regex constants inlined in the function today stay with it) | 762-840 |
| `scoring.py` | `score_notice_number`, `score_structure`, `score_spatial`, `score_boundary`, `score_table`, `composite_confidence`, `score_notice`, `score_notices`, `compute_document_confidence`, `aggregate_confidence`, `filter_notices`, `partition_by_band`, `explain` | `_clip`, `_estimate_ocr_quality` (per Q4 resolution — returns a document-level OCR confidence score, belongs with the other confidence helpers; consumed by `pipeline.build_envelope` before boundary capping) | 943-1412 |
| `envelope_builder.py` | `build_envelope_dict` | — | 1917-2088 |
| `pipeline.py` | `build_envelope(pdf_path: Path, *, include_full_docling_dict: bool = False) -> Envelope` (NEW pure function; see 2d) | — | derived from `GazettePipeline.process_pdf` (2094-2255) |

**Notebook helpers that do NOT move in F20** (they are notebook-only infrastructure, not library logic):

- `extract_title_from_docling`, `docling_export_summary`, `highlight_gazette_notices_in_markdown` — diagnostic / side-file helpers the notebook's demo cells still call; moving them is out of scope (they touch Docling export and markdown rendering, not envelope assembly). Revisit when F21 introduces `write_envelope`.
- `run_pdfs`, `run_folder`, `resolve_pdf_selection` — notebook UX helpers.
- `confidence_report`, `_iter_output_gazette_jsons`, `_llm_cache_path`, `_llm_call_openai`, `llm_validate_notice`, `enhance_with_llm` — notebook-only (LLM stages land in F22/M6; `confidence_report` is a CSV writer that belongs with `write_envelope` in F21).
- `sample_for_calibration`, `_parse_calibration_yaml`, `_coerce`, `score_calibration`, `update_regression_fixture`, `check_regression` — calibration/regression tooling that roadmap M2 sends to `kenya_gazette_parser/quality/` later. Keeping them in the notebook at F20 means `check_regression()` still runs the exact same code that produced today's 6-PDF baseline — which is the only way Gate 1 can credibly clear.
- `_BBoxElement` stays private to `spatial.py`; do NOT re-export.

### 2c. `LIBRARY_VERSION` / `SCHEMA_VERSION` single-source-of-truth (resolves D1)

Both constants live in `kenya_gazette_parser/__version__.py`. Extend the existing file:

```python
__version__ = "0.1.0"
LIBRARY_VERSION = __version__     # alias for legacy notebook callers
SCHEMA_VERSION = "1.0"            # envelope JSON shape version; see contract section 7
```

`kenya_gazette_parser/identity.py` re-exports both so notebook code can write either:

```python
from kenya_gazette_parser import __version__ as LIBRARY_VERSION
from kenya_gazette_parser.identity import LIBRARY_VERSION, SCHEMA_VERSION
```

The notebook cell that today declares `LIBRARY_VERSION = "0.1.0"` and `SCHEMA_VERSION = "1.0"` (lines 1826-1827) is **deleted**. After F20, running `grep -n '"0.1.0"' gazette_docling_pipeline_spatial.ipynb` must return zero matches in `"source"` strings (cell output streams may still legitimately contain the literal from previous runs — the regression is on declarations, not on captured stdout). Same rule for `SCHEMA_VERSION = "1.0"` — it is declared exactly once, in `__version__.py`.

**Why `__version__.py` and not a new `versions.py`:** F17 already designated `__version__.py` as the single source of truth for the library version string; piggy-backing `SCHEMA_VERSION` there avoids a second stand-alone module and keeps both version constants one import away. Alternative placements (`identity.py`, `pipeline.py`, a new `versions.py`) create a second file anyone bumping a version has to remember. `__version__.py` is already the file anyone bumping the version edits.

### 2d. `pipeline.build_envelope` — the `process_pdf` rehousing (resolves the F20 `process_pdf` fate question)

**Recommendation: move the pure-computation body of `GazettePipeline.process_pdf` into `kenya_gazette_parser.pipeline.build_envelope`; keep the file-I/O writes (`json.dump(..., _gazette_spatial.json)`, `write_text(_spatial.txt)`, `_docling_markdown.md`, `_spatial_markdown.md`, `_docling.json`) in the notebook demo cell.** The file-I/O split is F21's job (`write_envelope` + `Bundles`); F20 must not pre-empt it.

New signature (exact):

```python
# kenya_gazette_parser/pipeline.py
from pathlib import Path
from docling.document_converter import DocumentConverter
from kenya_gazette_parser.models import Envelope

def build_envelope(
    pdf_path: Path,
    *,
    converter: DocumentConverter | None = None,
    include_full_docling_dict: bool = False,
) -> Envelope:
    """Pure-compute path from PDF on disk to a validated Envelope.

    Orchestrates (in this order): Docling convert -> spatial reorder ->
    masthead parse -> OCR-quality estimate -> notice split -> notice scoring
    -> OCR-boundary capping -> identity stamping (pdf_sha256, gazette_issue_id,
    notice_id, content_sha256) -> corrigenda extract -> document confidence ->
    flat record build -> build_envelope_dict adapter -> Envelope.model_validate.

    Returns the validated Envelope. Never writes to disk, never prints.
    ValidationError propagates uncaught (same rule as F19).
    """
```

The notebook's pipeline cell becomes a thin shim:

```python
# demo cell in gazette_docling_pipeline_spatial.ipynb (post-F20)
from dataclasses import dataclass, field
from pathlib import Path
import json
from docling.document_converter import DocumentConverter
from kenya_gazette_parser.pipeline import build_envelope
from kenya_gazette_parser.spatial import reorder_by_spatial_position_with_confidence
from kenya_gazette_parser.models import Envelope  # only for optional type hints

@dataclass
class GazettePipeline:
    converter: DocumentConverter = field(default_factory=DocumentConverter)
    include_full_docling_dict: bool = False

    def process_pdf(self, pdf_path: Path) -> dict:
        env = build_envelope(
            pdf_path,
            converter=self.converter,
            include_full_docling_dict=self.include_full_docling_dict,
        )
        record = env.model_dump(mode="json")

        pdf_output_dir = OUTPUT_DIR / Path(pdf_path).stem
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        with open(pdf_output_dir / f"{Path(pdf_path).stem}_gazette_spatial.json", "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        # ... other side files (spatial.txt, markdown, docling.json) written
        #     from build_envelope's returned diagnostic payload OR recomputed
        #     inside the demo cell; see Open Question Q3 ...
        return record
```

**Justification:** `build_envelope` is the unit every downstream F21/F22 caller wants — "PDF path in, validated Envelope out, no side effects". Lifting it now means F21 only has to add (a) `parse_file`/`parse_bytes` that call `build_envelope` and (b) a `write_envelope` that materializes Bundles from an Envelope. Leaving `process_pdf` in the notebook as a monolith would force F21 to re-copy the same orchestration, defeating the "one source of truth" point of F20.

**Non-negotiable carry-overs from F19 that must survive the move:**

- The `Envelope.model_validate(build_envelope_dict(record))` tail call is preserved verbatim — it is now the last line of `build_envelope`. `ValidationError` is NOT caught.
- `content_sha256` stamping loop runs immediately after `notice_id` stamping, before the adapter (same ordering as F19).
- The OCR-quality boundary-cap pass (lines 2139-2156 in the current notebook) runs exactly where it runs today — after `score_notices`, before identity stamping.
- The F19 adapter's sentinel `scope="notice_references_other"` + placeholder `provenance` + one `Warning(kind="corrigendum_scope_defaulted", ...)` per corrigendum stay in place (real extraction is F31).
- The F19 adapter's `"table"`-body-segment coercion + paired `Warning(kind="table_coerced_to_text", ...)` stay in place (richer segment types are M5).

### 2e. `layout_info.n_pages` source fix (resolves D2)

In `kenya_gazette_parser/spatial.py`, the lifted `reorder_by_spatial_position_with_confidence` returns the info dict **without** the `"n_pages"` key. Exact change:

| Before (notebook line 1779) | After (in `spatial.py`) |
|-----------------------------|-------------------------|
| `{"layout_confidence": round(doc_layout_conf, 3), "n_pages": len(page_infos), "pages": page_infos}` | `{"layout_confidence": round(doc_layout_conf, 3), "pages": page_infos}` |

Consequence for `envelope_builder.build_envelope_dict`: the prune step (current notebook lines 2076-2081, `layout_info = {"layout_confidence": ..., "pages": ...}`) is **deleted**. Replace with a direct pass-through:

```python
# envelope_builder.py (replaces current prune)
"layout_info": record_flat["layout_info"],
```

Rationale: once the source stops emitting `n_pages`, `record_flat["layout_info"]` already has exactly the two keys `LayoutInfo` accepts (`layout_confidence`, `pages`), so the adapter has no work to do. Any caller that wants the page count computes `len(env.layout_info.pages)`.

**Validation:** After the fix, `Envelope.model_validate(...)` on all 6 canonical PDFs must still pass. Because `LayoutInfo` inherits `StrictBase` (`extra="forbid"`), the F19 adapter was the only thing preventing a `ValidationError` on `n_pages`; once the source drops the key, both paths align.

### 2f. Public API surface (`parse_file` / `parse_bytes`)

**No change in F20.** Both stubs stay exactly as they are after F17 — raising `NotImplementedError` with a message pointing at F20/F21. F20's deliverable is the set of **internal** modules F21 will call; wiring `parse_file` to call `pipeline.build_envelope` is F21's job. `kenya_gazette_parser/__init__.py` adds no new re-exports in F20; callers reach internals via their full dotted paths (e.g. `from kenya_gazette_parser.pipeline import build_envelope`).

### 2g. Notebook end state (what a thin demo looks like after F20)

Allowed in the notebook after F20:

- **Imports block at the top** (new cell or folded into existing first cell):

  ```python
  from kenya_gazette_parser import __version__ as LIBRARY_VERSION
  from kenya_gazette_parser.identity import (
      SCHEMA_VERSION, make_extracted_at, compute_pdf_sha256,
      make_gazette_issue_id, make_notice_id,
  )
  from kenya_gazette_parser.masthead import parse_masthead
  from kenya_gazette_parser.spatial import (
      reorder_by_spatial_position,
      reorder_by_spatial_position_with_confidence,
      compute_page_layout_confidence,
  )
  from kenya_gazette_parser.splitting import split_gazette_notices
  from kenya_gazette_parser.trailing import detect_trailing_content_cutoff
  from kenya_gazette_parser.corrigenda import extract_corrigenda
  from kenya_gazette_parser.scoring import (
      score_notice_number, score_structure, score_spatial, score_boundary,
      score_table, composite_confidence, score_notice, score_notices,
      compute_document_confidence, aggregate_confidence, filter_notices,
      partition_by_band, explain,
  )
  from kenya_gazette_parser.envelope_builder import build_envelope_dict
  from kenya_gazette_parser.pipeline import build_envelope
  from kenya_gazette_parser.models import Envelope
  ```

- **`GazettePipeline` wrapper** (see 2d above) — a ~20-line dataclass that calls `build_envelope` and does file writes.

- **Run / selection cells** (`run_pdfs`, `run_folder`, `resolve_pdf_selection`, the `PDF_SELECTION_MODE` / `SELECTED_PDF_NAMES` configuration cell, the visual-inspection cells that render markdown, the `confidence_report` CSV cell, the `enhance_with_llm` cell, the calibration + regression cells).

Deleted in the notebook after F20:

- Every `def parse_masthead`, `def _segment_body_lines`, `def split_gazette_notices`, `def extract_corrigenda`, `def detect_trailing_content_cutoff`, `def reorder_by_spatial_position*`, `def score_*`, `def composite_confidence`, `def compute_document_confidence`, `def _estimate_ocr_quality`, `def compute_pdf_sha256`, `def make_*`, `def build_envelope_dict`, `def _clip`, `def _BBoxElement`, `def _extract_elements`, `def _get_page_dimensions`, `def _reorder_page`, `def _cluster_y_bands`, `def _classify_band`, `def compute_page_layout_confidence`, `def _strip_running_headers`, `def _split_on_multiple_spaces`, `def _extract_title_stack`, `def _repair_merged_rows`, `def _try_parse_s_no_table`, `def _ends_with_terminal_punct`, `def _find_recovered_boundaries`, `def _stitch_multipage_notices`, `def _table_to_text` — every symbol listed in the 2b table.

- The `LIBRARY_VERSION = "0.1.0"` and `SCHEMA_VERSION = "1.0"` declarations (resolves D1).

- The `test_parse_masthead()` cell (notebook line 178) — F11's inline smoke test. It is duplicated by the canonical-PDF regression and cannot be kept in the notebook once `parse_masthead` lives in a module (would require `from kenya_gazette_parser.masthead import parse_masthead` at the top of the test cell, which is fine to keep if it still runs). Implementer choice: keep as documentation of the F11 fixtures OR delete.

Kept in the notebook after F20:

- All markdown narration cells (introduction, section headers, methodology notes).
- Visual-inspection cells (dataframe displays, per-notice previews, `explain(notice)` invocations).
- The sample run output streams (regenerated on every notebook run anyway).
- The `PROJECT_ROOT`, `PDF_DIR`, `OUTPUT_DIR`, `TESTS_DIR`, `CALIBRATION_FILE`, `REGRESSION_FILE`, `CANONICAL_PDFS` path constants (they anchor demo-only paths; not library logic).

---

## 3. Links to Canonical Docs

| Doc | Section | Why it matters |
|-----|---------|----------------|
| `docs/library-contract-v1.md` | Section 3 (Envelope, Notice, LayoutInfo, Warning models) | `LayoutInfo` accepts only `{layout_confidence, pages}` — every other key raises `ValidationError` under `extra="forbid"`. `Warning.kind` is a free dotted string. |
| `docs/library-contract-v1.md` | Section 2 (Identity model) | `gazette_issue_id`, `notice_id`, `pdf_sha256`, `content_sha256` formation rules constrain the lifted `identity.py` helpers. |
| `docs/library-contract-v1.md` | Section 5 (Public API sketch) | `parse_file`/`parse_bytes` signatures — F20 does NOT touch them; it only sets up the internal modules F21 will call from inside `parse_file`. |
| `docs/library-contract-v1.md` | Section 7 (Versioning rules) | `schema_version` is `"1.0"`; `output_format_version` is `1`. These belong in one module (`__version__.py`) to prevent drift. |
| `docs/library-roadmap-v1.md` | Blueprint 2 module sketch (section 2) | Names the target layout (`pipeline.py`, `spatial/`, `notices/`, `corrigenda/`, `confidence/`). F20 adopts single-file-per-concern instead of packages-per-concern because the current code volume (one to three hundred lines per concern) does not justify subpackages. |
| `docs/library-roadmap-v1.md` | M2 ("package + Pydantic models"), M3 ("I/O split + GazetteConfig + Bundles") | F20 is the second half of M2 (logic move); F21 is M3 (I/O split). The boundary between them is "file-writes stay in notebook in F20, move to `write_envelope` in F21". |
| `PROGRESS.md` | F20 row | Original definition: "Copy helpers into submodules". Done-when: "notebook imports from package and canonical PDFs still validate / regression still PASS". |
| `PROGRESS.md` | D1, D2 | Both active-debt rows target F20 and must resolve in this feature. |
| `PROGRESS.md` | G1-G5 | G1 (regression tolerance 0.05), G3 (`Warning` shadows built-in), G4 (`extra="forbid"` everywhere except `DerivedTable`), G5 (orphan `notice_id` uses line_span, not list index) all constrain what F20 is allowed to change. |

---

## 4. Test Case Matrix

Source PDFs are the 6 canonical fixtures listed in `tests/expected_confidence.json`. Baseline `mean_composite` values (from F16/F18/F19): CXINo 100 = 0.990, CXINo 103 = 0.989, CXIINo 76 = 0.963, CXXVIINo 63 = 0.977, CXXIVNo 282 = 0.968, CIINo 83 pre-2010 = 0.253. Tolerance stays at 0.05 (G1 — never tighten).

| ID | Scenario | Source | Input | Expected | Why |
|----|----------|--------|-------|----------|-----|
| TC1 | Happy path end-to-end (modern 2-column) | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` + `tests/expected_confidence.json` | Re-run notebook demo cell after F20 merge | `env = build_envelope(...)` returns a valid `Envelope`; `env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"` (corrected 2026-04-22: original spec wrote `2022-12-30`, which was a typo — the masthead date on this PDF is 23 Dec 2022, confirmed by the F19 on-disk baseline); `len(env.notices) == 201`; `env.document_confidence.mean_composite` within 0.05 of 0.968; no `ValidationError` | Proves the lifted modules reproduce F19 behaviour on the densest modern fixture; same assertions F19 TC1 ran |
| TC2 | OCR-heavy regression (Gate 1 band) | `pdfs/Kenya Gazette Vol CXXVIINo 63.pdf` | Re-run via notebook | `env.document_confidence.mean_composite` within 0.05 of 0.977; count of `Warning(kind="table_coerced_to_text")` in `env.warnings` equals the F19 baseline of 186 | G1 calls out this PDF specifically — Docling OCR non-determinism ~0.005; anything tighter would false-positive. Also guards the F19 `"table"` coercion warning pipeline that moves through `envelope_builder.py` |
| TC3 | Pre-2010 scanned edge case | `pdfs/Kenya Gazette Vol CIINo 83 - pre 2010.pdf` | Re-run via notebook | `env.document_confidence.mean_composite` within 0.05 of 0.253 (the OCR-boundary-cap path fires on this PDF, evidenced by the document mean collapsing to 0.253 far below the per-notice high range); `env.document_confidence.ocr_quality` within 0.05 of 0.926 (corrected 2026-04-22: original spec wrote `< 0.5` based on a misread — the cap does fire, but it fires off composite/structure signals, not off raw `ocr_quality`, which stays high; F19 baseline confirms `ocr_quality = 0.926`); exactly one `Notice` in `env.notices` | Proves the OCR-quality boundary-cap pass survived the move from the notebook's `process_pdf` body into `pipeline.build_envelope` — this is the most fragile piece of the orchestration and the easiest to reorder incorrectly |
| TC4 | D2 `n_pages` source fix | `pdfs/Kenya Gazette Vol CXINo 100.pdf` | Call `spatial.reorder_by_spatial_position_with_confidence(doc_dict)` directly (before the adapter) | Returned info dict keys are exactly `{"layout_confidence", "pages"}`; assert `"n_pages" not in info`. Separately: call `envelope_builder.build_envelope_dict(record)` with a handcrafted `record["layout_info"] = {"layout_confidence": 0.5, "pages": []}`; assert the returned envelope dict's `layout_info` is an identity pass-through (no new keys synthesized, no keys dropped) | Confirms the adapter's prune step is deleted and the source emits contract-compliant shape directly — both halves of D2 |
| TC5 | D1 `LIBRARY_VERSION` single-source | `gazette_docling_pipeline_spatial.ipynb` (static file scan) + Python import | `(1)` `grep -n '"0.1.0"' gazette_docling_pipeline_spatial.ipynb` on `"source"` strings returns zero matches. `(2)` `grep -n 'SCHEMA_VERSION *= *"1.0"' gazette_docling_pipeline_spatial.ipynb` returns zero matches. `(3)` In Python: `from kenya_gazette_parser import __version__ as LIBRARY_VERSION; from kenya_gazette_parser.identity import LIBRARY_VERSION as ID_LV, SCHEMA_VERSION; assert LIBRARY_VERSION == ID_LV == "0.1.0"; assert SCHEMA_VERSION == "1.0"` | No `"0.1.0"` left in the notebook | Proves D1 resolved: one declaration in the package, every other reference is an import |
| TC6 | Regression / Gate 2 | All 6 canonical PDFs | Re-run pipeline end-to-end via notebook demo cell; then `check_regression(tolerance=0.05)` | Returns `True` (PASS) for all 6 PDFs. Additionally: `notice_id` values for every notice must be identical to the F19 baseline saved on disk (read `output/{stem}/{stem}_gazette_spatial.json`, compare `[n["notice_id"] for n in old["notices"]] == [n["notice_id"] for n in new["notices"]]` element-wise, excluding `extracted_at` per G2) | Gate 1 + Gate 2 combined — the two non-negotiable quality gates from PROGRESS.md |
| TC7 | Import-smoke for every new module | — | `python -c "import kenya_gazette_parser.identity, kenya_gazette_parser.masthead, kenya_gazette_parser.spatial, kenya_gazette_parser.splitting, kenya_gazette_parser.trailing, kenya_gazette_parser.corrigenda, kenya_gazette_parser.scoring, kenya_gazette_parser.envelope_builder, kenya_gazette_parser.pipeline"` | Exits 0; no `ImportError`, no `AttributeError` | Cheap circular-import and typo guard; catches Open Question Q3 (circular risks) if it materializes |

Minimum required: TC1-TC5. TC6 and TC7 are added because F20 is a cross-cutting refactor and the two quality gates (regression, notice_id stability) are the whole reason "Copy helpers into submodules" is allowed to ship as a standalone feature.

---

## 5. Integration Point

### Called by (consumers of F20-produced modules)

- **Notebook demo cell(s)** — imports every public symbol listed in 2b. No other caller changes.
- **F21 (next feature)** — `parse_file` and `parse_bytes` inside `kenya_gazette_parser/__init__.py` will import `pipeline.build_envelope` and wrap it. F20 must leave `build_envelope` callable with a bare `Path` argument, no config object required (F22 adds `GazetteConfig`).

### Calls (dependencies each migrated module has)

| Module | Calls into |
|--------|------------|
| `identity.py` | stdlib only (`hashlib`, `datetime`) — no package-internal imports |
| `masthead.py` | stdlib only (`re`) — no package-internal imports |
| `spatial.py` | stdlib only (`dataclasses`, `statistics`, `math`) — no package-internal imports |
| `splitting.py` | stdlib (`re`) + **one package-internal edge: imports `detect_trailing_content_cutoff` from `kenya_gazette_parser.trailing`** (corrected 2026-04-22: original spec said "stdlib only" but implementation reuses the trailing-content detector rather than duplicating it; dependency graph stays a DAG — `trailing.py` is stdlib-only and has no upward edges) |
| `trailing.py` | stdlib only (`re`) — no package-internal imports |
| `corrigenda.py` | stdlib only (`re`) — no package-internal imports |
| `scoring.py` | stdlib only (`statistics`) — no package-internal imports; model imports are NOT added (scoring works on plain dicts today and stays that way in F20 to avoid churn); deliberately duplicates the four-line `_ends_with_terminal_punct` helper from `splitting.py` to keep `scoring.py` strictly stdlib-only (added 2026-04-22 post-build clarification) |
| `envelope_builder.py` | no package-internal imports in F20; `build_envelope_dict` remains a dict-in / dict-out function (it does NOT call `Envelope.model_validate` — that is `pipeline.py`'s job) |
| `pipeline.py` | `docling.document_converter.DocumentConverter`; `kenya_gazette_parser.models.Envelope`; `kenya_gazette_parser.spatial.reorder_by_spatial_position_with_confidence`; `kenya_gazette_parser.masthead.parse_masthead`; `kenya_gazette_parser.splitting.split_gazette_notices`; `kenya_gazette_parser.corrigenda.extract_corrigenda`; `kenya_gazette_parser.scoring.{score_notices, composite_confidence, compute_document_confidence, _estimate_ocr_quality}`; `kenya_gazette_parser.identity.{LIBRARY_VERSION, SCHEMA_VERSION, make_extracted_at, compute_pdf_sha256, make_gazette_issue_id, make_notice_id}`; `kenya_gazette_parser.envelope_builder.build_envelope_dict` |

Dependency graph is a DAG (`pipeline` sits at the top and imports everything; no module lower in the tree imports any peer). See Open Question Q3 for the one risk.

### Side effects

- **None added by F20.** `build_envelope` is pure; it does not write, log, or warn (apart from appending to `env.warnings`, which is envelope data, not a side effect).
- The notebook's demo `GazettePipeline.process_pdf` still writes the same five `output/{stem}/` files it wrote before F20 — unchanged behaviour from the outside.

### Model wiring

- `Envelope`, `LayoutInfo`, `Warning`, `Notice`, `Corrigendum` are populated exactly as they were at F19. The only change is that the code that populates them now lives in `kenya_gazette_parser/` instead of in notebook cells.
- `LayoutInfo.pages: list[dict[str, Any]]` accepts whatever per-page dict `spatial.compute_page_layout_confidence` returns — same permissive typing as F18.
- `Warning.kind` values emitted by F20: `"masthead.parse_failed"`, `"corrigendum_scope_defaulted"`, `"table_coerced_to_text"` — identical to F19.
- `output_format_version` remains hard-coded `1` inside `envelope_builder.build_envelope_dict` (contract section 7).

---

## 6. Pass/Fail Criteria

| Check | How to verify |
|-------|---------------|
| All 9 new modules import cleanly | TC7 runs without error |
| Every helper listed in 2b has moved | `grep -n 'def parse_masthead\|def split_gazette_notices\|def build_envelope_dict\|def compute_pdf_sha256\|def score_notice_number\|def reorder_by_spatial_position\|def detect_trailing_content_cutoff\|def extract_corrigenda' gazette_docling_pipeline_spatial.ipynb` returns zero matches in `"source"` blocks (matches in `"outputs"` do not count) |
| D1 resolved | TC5 grep checks + runtime identity assertion |
| D2 resolved | TC4 `"n_pages" not in info` + adapter pass-through check |
| Envelope still validates on 6 PDFs | TC1 + TC2 + TC3 `Envelope.model_validate` succeeds for each canonical PDF |
| Regression clears | TC6: `check_regression(tolerance=0.05) == True` |
| `notice_id` stability (Gate 2) | TC6 element-wise diff of notice_id lists against F19 output on disk |
| `Warning` count parity with F19 | TC2 asserts 186 `table_coerced_to_text` warnings on CXXVIINo 63; F19 baseline for `corrigendum_scope_defaulted` totals 16 across 6 PDFs — total must match |
| Public API stubs unchanged | `import kenya_gazette_parser; kenya_gazette_parser.parse_file("x")` still raises `NotImplementedError` with the F17 message string |
| No accidental `Warning` shadowing (G3) | Every new module that imports from `kenya_gazette_parser.models` uses either the explicit alias `from kenya_gazette_parser.models import Warning as GazetteWarning` OR does not import `Warning` at all. Python's built-in `Warning` is never shadowed inside any F20 module |
| No new `extra` keys leak (G4) | Any dict built inside F20 modules and handed to a `StrictBase` model has only keys documented in the contract. Specifically, no module re-introduces `n_pages` under `layout_info`, `pdf_title` under `Envelope`, or any rename-in-progress key |
| `output_format_version` still stamped | TC1-TC3 assert `env.output_format_version == 1` |
| Idempotency | Two consecutive invocations of `build_envelope(pdf_path)` on the same PDF produce envelopes equal on every field except `extracted_at` (G2) |

---

## 7. Definition of Done

- [ ] All 9 new modules created at the exact paths in 2a, with the exact symbol sets in 2b.
- [ ] `__version__.py` extended with `LIBRARY_VERSION` alias and `SCHEMA_VERSION = "1.0"`.
- [ ] Notebook imports from the package; every helper listed in 2b deleted from `"source"` cells.
- [ ] `GazettePipeline.process_pdf` in the notebook is a thin wrapper that calls `kenya_gazette_parser.pipeline.build_envelope` and writes the same five `output/{stem}/` files it wrote before.
- [ ] `spatial.py`'s `reorder_by_spatial_position_with_confidence` no longer emits `n_pages`.
- [ ] `envelope_builder.build_envelope_dict`'s `layout_info` handling is a pass-through (D2 prune step deleted).
- [ ] Notebook has zero `"0.1.0"` literals in source cells; zero `SCHEMA_VERSION = "1.0"` declarations.
- [ ] TC1-TC7 all pass.
- [ ] `check_regression(tolerance=0.05)` returns `True` on all 6 canonical PDFs.
- [ ] Gate 2 still clears: `notice_id` arrays element-wise-equal to the F19 on-disk baseline.
- [ ] `parse_file` / `parse_bytes` stubs in `kenya_gazette_parser/__init__.py` unchanged (still raise `NotImplementedError`).
- [ ] PROGRESS.md row F20 updated to "✅ Complete"; D1 and D2 rows marked obsolete (strike-through or explicit note — do not delete).

---

## 8. Open Questions / Risks

**Q1. Does `process_pdf` move in F20 or wait for F21?** — **RESOLVED (human, 2026-04-21): move the pure-compute body into `pipeline.build_envelope` now (F20).** Ship 9 modules. File-I/O writes stay in the notebook's thin `GazettePipeline` wrapper until F21.

**Q2. Does the corrigendum sub-adapter get its own `corrigenda.py` or stay in `envelope_builder.py`?** — **RESOLVED (human, 2026-04-21): stay in `envelope_builder.py`.** The sub-adapter is 100% about transforming the notebook's corrigendum dict shape into `Corrigendum` and has no life independent of envelope assembly. F31 will eventually rewrite the extractor (real `scope` + `provenance`), at which point the sub-adapter becomes a no-op and can be deleted.

**Q3. Are there circular-import risks given `models/` already exists?**
Audited in section 5 above. None of `identity`, `masthead`, `spatial`, `splitting`, `trailing`, `corrigenda`, `scoring`, `envelope_builder` import from `models`. Only `pipeline.py` imports `models.Envelope`, and no model imports any F20 module. Graph is a DAG with `pipeline` at the root — zero cycles. Risk becomes real if a later edit adds `from kenya_gazette_parser.models import Notice` inside `scoring.py` for type hints; guard with the `from __future__ import annotations` idiom (PEP 563) already used in `models/envelope.py` if that happens.

**Q4. Does `_estimate_ocr_quality` belong in `scoring.py` or `envelope_builder.py`?** — **RESOLVED (human, 2026-04-21): `scoring.py`.** The function returns a document-level OCR confidence score; it belongs with the other confidence helpers. No circular-import risk: `scoring.py` remains stdlib-only (see section 5 "Calls" table), `pipeline.py` imports `_estimate_ocr_quality` from `scoring` alongside the other scoring calls. Section 2b and section 5 have been updated to reflect this placement.

**Q5. G3 reminder — do NOT shadow `Warning`.**
`kenya_gazette_parser.models.Warning` is deliberately named `Warning`. Any F20 module that needs it must import with the `as GazetteWarning` alias (or skip the import entirely). No F20 module should contain the bare line `from kenya_gazette_parser.models import Warning`. This is called out here because F20 creates 9 new modules and the odds of one slipping up are non-zero.

**Q6. G4 reminder — `StrictBase` means no stray keys.**
The F19 adapter's `_DROP / _PASS / _ISSUE / _OTHER` key-partition logic stays inside `envelope_builder.build_envelope_dict`. Do NOT move the `raise KeyError` on unknown top-level keys — it is the guardrail that catches contract drift.

**Q7. Baseline JSONs on disk reference `layout_info.n_pages` — will Gate 2 notice?** — **RESOLVED (human, 2026-04-21): no refresh needed.** Spot-check of on-disk baseline JSON confirms `layout_info` has exactly `{layout_confidence, pages[]}` with no `n_pages` top-level key (F19 adapter pruned it before write). Pages are listed individually with `{layout_confidence, bands[], mode, n_bands, page_no}`. TC6 can run against existing baselines without regeneration.

**Q8. What about `extract_title_from_docling`, `docling_export_summary`, markdown rendering, confidence CSV, LLM stages?**
Explicitly out of scope for F20 per 2b "Notebook helpers that do NOT move". Revisit in F21 (I/O split) or F22 (GazetteConfig + Bundles). Noted here so the builder does not get talked into migrating them by "while I'm at it" reasoning.
