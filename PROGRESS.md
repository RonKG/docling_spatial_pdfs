# Kenya Gazette Library — Build Progress

**Project:** Kenya Gazette PDF -> structured library  
**Builder:** Solo, part-time  
**Target 1.0:** `pip install`-able package returning a validated `Envelope` from a PDF  
**Last updated:** 2026-04-19

---

## How to use this file

- This is the only doc you read at the start of a session.
- Update **Today** + **Work Items** + **Session Log** at the end of every session.
- Do not start a new item until the current "⬜ Next" is marked "✅ Complete".

**Session-start prompt:**
> "Read `PROGRESS.md`. The ⬜ Next item is what I work on. Build it."

---

## Today (the only thing on your plate)

**Current:** F14 — Envelope versioning fields  
**What:** Add `library_version`, `schema_version`, `extracted_at` to every record  
**Where:** Modify `process_pdf` in `gazette_docling_pipeline_spatial.ipynb`  
**Done when:** Spec written, implemented, tests passing, this file updated.

**Previous:** F13 ✅ — Identity fields wired into record (complete, all tests pass)

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
| **F13** | Identity fields wired into record | Add `pdf_sha256`, `gazette_issue_id`, `notice_id` | ✅ Complete | — |
| **F14** | Envelope versioning fields | Add `library_version`, `schema_version`, `extracted_at` | ⬜ Not started | — |
| **F15** | Hand-label calibration sample | Label ~30 notices, run scoring | ⬜ Not started | — |
| **F16** | Capture regression baseline | Create `expected_confidence.json` | ⬜ Not started | — |
| **F17** | Package skeleton | Create `kenya_gazette/` with `pyproject.toml` | ⬜ Not started | — |
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
| **Gate 1** | `check_regression()` returns OK on canonical PDFs | ⬜ Not reached (needs F16) |
| **Gate 2** | Re-running same PDF produces identical `notice_id`s | ✅ Cleared |
| **Gate 3** | `from kenya_gazette import parse_file` works | ⬜ Not reached (needs F17) |
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

*Add a row here at the end of every session.*
