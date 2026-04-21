# Kenya Gazette Library — Build Progress

**Project:** Kenya Gazette PDF -> structured library  
**Builder:** Solo, part-time  
**Target 1.0:** `pip install`-able package returning a validated `Envelope` from a PDF  
**Last updated:** 2026-04-20

---

## How to use this file

- This is the only doc you read at the start of a session.
- Update **Today** + **Work Items** + **Session Log** at the end of every session.
- Do not start a new item until the current "⬜ Next" is marked "✅ Complete".

**Session-start prompt:**
> "Read `PROGRESS.md`. The ⬜ Next item is what I work on. Build it."

---

## Today (the only thing on your plate)

**Current:** F18 — Pydantic models from contract  
**What:** Translate `docs/library-contract-v1.md` section 3 into Pydantic v2 classes under `kenya_gazette_parser/models/`  
**Where:** New submodule; bump `pyproject.toml` deps to add `pydantic>=2.0`  
**Done when:** All contract types instantiate, `from kenya_gazette_parser.models import Envelope` works.

**Previous:** F17 ✅ — Package skeleton (`kenya_gazette_parser/` created, `pip install -e .` works, T1-T5 all PASS)

---

## Work Items (F1-F30)

| ID | Name | Simple Explanation | Status | Commit |
|----|------|-------------------|--------|--------|
| **F1** | Docling extraction wrapper | Convert PDF to JSON, markdown, plain text | ✅ Complete | — |
| **F2** | Spatial reading-order reorder | Two-column pages read left-then-right | ✅ Complete | — |
| **F3** | Notice splitting | Split text into individual notices | ✅ Complete | — |
| **F4** | Corrigenda extractor | Capture correction notices separately | ✅ Complete | — |
| **F5** | Per-notice rule-based confidence | Score notices on structure/quality | ✅ Complete | — |
| **F6** | Per-document confidence aggregation | Combine scores into document score | ✅ Complete | — |
| **F7** | Optional LLM semantic validation | Second-pass LLM check with cache | ✅ Complete | — |
| **F8** | Confidence report (CSV) | Sortable CSV for human triage | ✅ Complete | — |
| **F9** | Calibration tooling | Sample and hand-label notices | ✅ Complete (tooling) | — |
| **F10** | Regression tooling | Capture and check baselines | ✅ Complete (tooling) | — |
| **F11** | Masthead parser | Parse volume/issue/date/supplement | ✅ Complete | 88179ea |
| **F12** | Trailing content detector | Exclude ads/pricing from notices | ✅ Complete | 0af6b42 |
| **F13** | Identity fields wired into record | Add `pdf_sha256`, `gazette_issue_id`, `notice_id` | ✅ Complete | 29132ed |
| **F14** | Envelope versioning fields | Add `library_version`, `schema_version`, `extracted_at` | ✅ Complete | e0d9672 |
| **F15** | Hand-label calibration sample | Label ~30 notices, run scoring | ✅ Complete | e6b7bab |
| **F16** | Capture regression baseline | Create `expected_confidence.json` | ✅ Complete | cddacba |
| **F17** | Package skeleton | Create `kenya_gazette_parser/` with `pyproject.toml` | ✅ Complete | 19e9e2c |
| **F18** | Pydantic models from contract | Translate contract into classes | ⬜ Not started | — |
| **F19** | Validate at end of `process_pdf` | Call `Envelope.model_validate()` | ⬜ Not started | — |
| **F20** | Move logic into modules | Copy helpers into submodules | ⬜ Not started | — |
| **F21** | Public API + I/O split | Separate `parse_file`, `write_envelope` | ⬜ Not started | — |
| **F22** | GazetteConfig + Bundles | Config object with options | ⬜ Not started | — |
| **F23** | JSON Schema export | Generate schema file | ⬜ Not started | — |
| **F24** | Installable package smoke test | Test `pip install` works | ⬜ Not started | — |
| **F25** | README points at `parse_file` | Library quickstart | ⬜ Not started | — |
| *F26-F30* | *Post-1.0 items* | *Protocols, ML, CLI, PyPI, multi-stage LLM* | *Post-1.0* | *See roadmap* |

**1.0 ships when F11-F25 are all ✅.**

---

## Quality Gates (do not skip)

| Gate | Condition | Status |
|------|-----------|--------|
| **Gate 0** | Pipeline runs end-to-end, writes all 5 output files | ✅ Cleared |
| **Gate 1** | `check_regression()` returns OK on canonical PDFs | ✅ Cleared (6/6 PDFs) |
| **Gate 2** | Re-running same PDF produces identical `notice_id`s | ✅ Cleared |
| **Gate 3** | `from kenya_gazette_parser import parse_file` works | ⬜ Partially unblocked (import works after F17; `parse_file` fully clears at F21) |
| **Gate 4** | `Envelope` validates against JSON Schema | ⬜ Not reached (needs F19+F23) |
| **Gate 5** | `pip install git+...` works on different machine | ⬜ Not reached (needs F24) |

---

## Reference docs

- [`docs/library-contract-v1.md`](docs/library-contract-v1.md) — spec: output shape, public API
- [`docs/library-roadmap-v1.md`](docs/library-roadmap-v1.md) — long-form milestone view
- [`docs/data-quality-confidence-scoring.md`](docs/data-quality-confidence-scoring.md) — confidence scoring
- [`specs/SOP.md`](specs/SOP.md) — how to build features (3-agent workflow)

---

## Session Log

| Date | Task | Summary |
|------|------|---------|
| 2026-04-19 | Planning consolidated | Wrote `library-contract-v1.md`, `library-roadmap-v1.md`, `PROGRESS.md` |
| 2026-04-19 | F11 Masthead parser | Implemented `parse_masthead()`, extracts volume/issue/date/supplement |
| 2026-04-19 | F12 Trailing content detector | Implemented `detect_trailing_content_cutoff()`, truncates last notice before ads/pricing |
| 2026-04-19 | F13 Identity fields (implementation) | Added helpers `compute_pdf_sha256`, `make_gazette_issue_id`, `make_notice_id`. Modified `process_pdf` to stamp identity fields. All helper unit tests pass. Integration testing pending notebook execution. |
| 2026-04-19 | F13 Identity fields (completion) | Processed 3 test PDFs. All 6 integration tests PASS. Regression check PASS (no degradation). Gate 2 CLEARED (deterministic IDs confirmed). |
| 2026-04-19 | F14 Envelope versioning fields | Extended F13 helper cell with `LIBRARY_VERSION="0.1.0"`, `SCHEMA_VERSION="1.0"`, `make_extracted_at()`. Modified `process_pdf` to capture timestamp at top and add three envelope fields. Processed 3 test PDFs. All 4 tests (T1-T4) PASS. Regression check PASS (no degradation). Gate 2 still cleared (extracted_at excluded from identity). |
| 2026-04-20 | F15 Hand-label calibration sample | Manually labeled 26 notices in `tests/calibration_sample.yaml` (20 high-band, 6 medium-band). Ran `score_calibration()`. Results: High-band 100% precision (20/20 correct), exceeds 85% target. Medium-band 33.3% precision (2/6 correct), expected mixed quality. Verdict: Scoring well-calibrated, no weight tuning needed. Proceed to F16. |
| 2026-04-20 | F16 Capture regression baseline (initial) | Ran `update_regression_fixture()` to capture baseline scores in `tests/expected_confidence.json`. Ran `check_regression()`: PASS (all PDFs match baseline). Documented status in `tests/regression_baseline_notes.md`. Current baseline: 2 PDFs with F13/F14 fields (Vol CXINo 100: mean 0.990, Vol CXXIVNo 282: mean 0.968). 3 PDFs pending re-processing (missing F13/F14). Gate 1 CLEARED (partial). |
| 2026-04-20 | F16 Capture regression baseline (complete) | Re-processed 4 canonical PDFs (Vol CXINo 103, Vol CXIINo 76, Vol CXXVIINo 63, Vol CIINo 83 pre-2010) with F13/F14 fields. Ran `update_regression_fixture()` to capture complete baseline for all 6 PDFs. Ran `check_regression()`: all OK. Updated `tests/regression_baseline_notes.md` with full baseline table. Quality Gate 1 FULLY CLEARED (6/6 PDFs). All canonical PDFs now have deterministic baselines for regression detection. |
| 2026-04-20 | F17 Package skeleton | Created `kenya_gazette_parser/` with `__init__.py` (parse_file/parse_bytes stubs raising NotImplementedError), `__version__.py` (0.1.0), `py.typed` (PEP 561), `pyproject.toml` (setuptools backend, Apache-2.0 license, `docling+docling-core+openai` runtime deps, `dev` extra), and `LICENSE` (full Apache 2.0 text). `pip install -e .` succeeds in `.venv`. T1-T4 PASS (import, stub messages with required tokens, keyword-only `filename`, pyproject metadata incl. Apache-2.0/openai assertions). T5 regression PASS for all 6 canonical PDFs (baselines unchanged). Notebook, `requirements.txt`, and existing `README.md` untouched. `LIBRARY_VERSION` duplication between notebook and package documented for F20 cleanup. Helper scripts: `scripts/f17_smoke_tests.py`, `scripts/f17_regression_check.py`. |

*Add a row here at the end of every session.*
