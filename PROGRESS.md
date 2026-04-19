# Kenya Gazette Library — Build Progress

**Project:** Kenya Gazette PDF -> structured library  
**Builder:** Solo, part-time  
**Target 1.0:** `pip install`-able package returning a validated `Envelope` from a PDF  
**Last updated:** 2026-04-19

---

## How to use this file

- This is the only doc you read at the start of a session.
- Update **Today** + **Status table** + **Session Log** at the end of every session before committing.
- Do not start a new feature until the previous one's "Done when..." is met.
- Reference docs (contract, roadmap, confidence-scoring) are read-once material; you do not need them open day-to-day.

**Session-start prompt template:**

> "Read `PROGRESS.md`. The next ⬜ row is what I'm working on. Build it exactly as described."

---

## Today (the only thing on your plate)

**Task:** F12 — Trailing content detector. Detect end of last notice; exclude classified ads, pricing, index pages from notices array.

- **Location:** Modify `split_gazette_notices` in `gazette_docling_pipeline_spatial.ipynb`.
- **Done when:** F12 spec written, implemented, tests passing, and PROGRESS.md updated.

**Previous:** F11 ✅ Complete — `parse_masthead()` implemented, extracts volume/issue/date/supplement from masthead."boring" baseline.
- **Size:** ~half a day. Most of the time is reading mastheads, not coding.

When this works, stop for the day and tick F11 to ✅. The next ⬜ row tells you what's next.

---

## Gates (do not skip)

| Gate | Condition | Status |
| --- | --- | --- |
| **Gate 0** | Pipeline runs end-to-end on a sample PDF and writes all 5 output files | ✅ Cleared |
| **Gate 1** | Regression baseline captured; `check_regression()` returns OK on canonical PDFs | ⬜ Not reached |
| **Gate 2** | Re-running the same PDF twice produces byte-identical `notice_id`s and `content_sha256`s | ⬜ Not reached |
| **Gate 3** | `from kenya_gazette import parse_file` works in a fresh Python session | ⬜ Not reached |
| **Gate 4** | `Envelope` instance validates against the published JSON Schema | ⬜ Not reached |
| **Gate 5** | A different machine can `pip install git+...`, run a 3-line script, get a valid `Envelope` back | ⬜ Not reached |

---

## Features Implementation Status

| Phase | ID | Name | Simple Explanation | Core files | Status | Latest commits |
| --- | --- | --- | --- | --- | --- | --- |
| Phase 0 | F1 | Docling extraction wrapper | Convert PDF to structured JSON, markdown,<br>and plain text using Docling | `gazette_docling_pipeline_spatial.ipynb`<br>(cells around line 1577-1729) | ✅ Complete | — |
| Phase 0 | F2 | Spatial reading-order reorder | Use bbox coordinates so two-column pages<br>read left-then-right; emit per-page<br>layout confidence | notebook<br>(lines 1146-1561) | ✅ Complete | — |
| Phase 0 | F3 | Notice splitting | Split flat text into individual notices;<br>strict + recovered headers; multi-page<br>stitching | notebook<br>(lines 79-505) | ✅ Complete | — |
| Phase 0 | F4 | Corrigenda extractor | Capture correction notices into<br>a separate array | notebook<br>(lines 520-598) | ✅ Complete | — |
| Phase 0 | F5 | Per-notice rule-based confidence | Score every notice on number / structure /<br>spatial / boundary / table dimensions | notebook<br>(lines 648-986) | ✅ Complete | — |
| Phase 0 | F6 | Per-document confidence aggregation | Weighted document score combining mean<br>composite, layout, and OCR quality | notebook<br>(lines 995-1034) | ✅ Complete | — |
| Phase 0 | F7 | Optional LLM semantic validation | Second-pass LLM check for low-confidence<br>notices, with disk cache | notebook<br>(lines 2634-2879), `.llm_cache/` | ✅ Complete | — |
| Phase 0 | F8 | Confidence report (CSV) | Sortable per-notice CSV across all outputs<br>for human triage | notebook<br>(lines 2385-2633),<br>`output/_confidence_report.csv` | ✅ Complete | — |
| Phase 0 | F9 | Calibration tooling | Sample notices into bands, hand-label,<br>score precision per band | notebook<br>(lines 2880-3065),<br>`tests/calibration_sample.yaml` | ✅ Complete (tooling) — labels still pending | — |
| Phase 0 | F10 | Regression tooling | Capture baseline of mean composite per<br>canonical PDF; check current vs baseline | notebook<br>(lines 3066-3163) | ✅ Complete (tooling) — baseline file not yet captured | — |
| Phase 1 | F11 | Masthead parser | Parse Volume, Number, publication date,<br>supplement from the title block | notebook<br>(new cell) | ✅ Complete | 35a9557 |
| **Phase 1** | **F12** | **Trailing content detector** | **Detect end of last notice; exclude classified<br>ads, pricing, index pages from notices array** | **notebook<br>(`split_gazette_notices` or new cell)** | **⬜ Next** | **—** |
| Phase 1 | F13 | Identity fields wired into record | Add `pdf_sha256`, `gazette_issue_id`,<br>`notice_id`, `content_sha256`; corrigendum<br>`scope` enum | notebook<br>(`process_pdf`, `split_gazette_notices`,<br>`extract_corrigenda`) | ⬜ Not started | — |
| Phase 1 | F14 | Envelope versioning fields | `library_version`, `schema_version`,<br>`output_format_version`, `extracted_at`<br>at top of record | notebook<br>(`process_pdf`) | ⬜ Not started | — |
| Phase 2 | F15 | Hand-label calibration sample | Open `tests/calibration_sample.yaml`, mark<br>`is_correct: true/false` for ~30 notices,<br>run `score_calibration()` | `tests/<br>calibration_sample.yaml` | ⬜ Not started | — |
| Phase 2 | F16 | Capture regression baseline | Run `update_regression_fixture()` once scoring<br>is stable; clears Gate 1 | `tests/<br>expected_confidence.json` (new) | ⬜ Not started | — |
| Phase 3 | F17 | Package skeleton | Create `kenya_gazette/` with `pyproject.toml`,<br>`models/`, empty submodules | `kenya_gazette/`,<br>`pyproject.toml` | ⬜ Not started | — |
| Phase 3 | F18 | Pydantic models from contract | Translate [`library-contract-v1.md`](docs/library-contract-v1.md)<br>section 3 sketches into real classes | `kenya_gazette/<br>models/*.py` | ⬜ Not started | — |
| Phase 3 | F19 | Validate at end of `process_pdf` | Notebook calls `Envelope.model_validate(record)`<br>before writing JSON; clears Gate 2 | notebook<br>(`process_pdf`) | ⬜ Not started | — |
| Phase 4 | F20 | Move logic into modules | Copy notebook helpers into `kenya_gazette/<br>{spatial,notices,confidence,llm,corrigenda,quality}/`;<br>notebook becomes import-only | `kenya_gazette/**` | ⬜ Not started | — |
| Phase 4 | F21 | Public API + I/O split | `parse_file`, `parse_bytes`, `write_envelope`<br>separated from disk side effects | `kenya_gazette/<br>__init__.py`,<br>`kenya_gazette/pipeline.py` | ⬜ Not started | — |
| Phase 4 | F22 | `GazetteConfig` + `Bundles` | Config object with LLM policy, runtime<br>options, bundle projection | `kenya_gazette/<br>config.py` | ⬜ Not started | — |
| Phase 5 | F23 | JSON Schema export | Generate `Envelope.model_json_schema()` JSON<br>file; check into `kenya_gazette/schemas/`;<br>clears Gate 4 | `kenya_gazette/<br>schemas/envelope.schema.json` | ⬜ Not started | — |
| Phase 5 | F24 | Installable package smoke test | `pip install git+...` in a fresh venv; 3-line<br>script returns valid `Envelope`; clears Gate 5 | external venv | ⬜ Not started | — |
| Phase 5 | F25 | README points at `parse_file` | Replace notebook-centric README with<br>library quickstart | `README.md` | ⬜ Not started | — |

**1.0 ships when F11-F25 are all ✅ and Gates 1-5 are all cleared.**

---

## Phase 6+ (post-1.0, not on the critical path)

Listed for context only. Do not let these creep into the 1.0 work above.

| Phase | ID | Name | Simple Explanation |
| --- | --- | --- | --- |
| Phase 6 | F26 | Stage `Protocol`s | Define `Splitter`, `LayoutDetector`, `TableExtractor`, `ConfidenceScorer`, `LLMValidator` interfaces; existing rules wrap as defaults |
| Phase 6 | F27 | ML alternative for one stage | Train + ship an ML implementation of one stage (likely `Splitter` or `TableExtractor`); rules stay default |
| Phase 6 | F28 | CLI | `kenya-gazette parse <pdf> --bundles notices,corrigenda --out ./out` |
| Phase 6 | F29 | PyPI publish | Real `pip install kenya-gazette` from public index |
| Phase 6 | F30 | Multi-stage LLM repair | LLM helps repair tables and classify notices, not just validate |

**Schema evolution note:** `body_segments` in 1.0 only emits `"text"` and `"blank"` types. Richer detection (tables, signatures, citations) lands in 2.x (F27). The schema is designed so adding new segment types is a **MINOR** bump — old consumers keep working. See contract section 3 and roadmap M5 for the design rationale.

---

## Reference docs (read once, point back when needed)

- [`docs/library-contract-v1.md`](docs/library-contract-v1.md) — the spec. Output shape and public API.
- [`docs/library-roadmap-v1.md`](docs/library-roadmap-v1.md) — long-form milestone view including post-1.0.
- [`docs/data-quality-confidence-scoring.md`](docs/data-quality-confidence-scoring.md) — confidence scoring + calibration workflow.
- [`docs/known-issues.md`](docs/known-issues.md) — observed extraction bugs; useful when something looks off.
- [`docs/spatial_reorder_changelog.md`](docs/spatial_reorder_changelog.md) — history of layout-detection tweaks.

You should not need any of these to know what to do next. This file is the answer.

---

## Session Log

| Date | Task | Feature(s) | Summary |
| --- | --- | --- | --- |
| 2026-04-19 | Planning consolidated | — | Wrote `docs/library-contract-v1.md` (Envelope + API spec) and `docs/library-roadmap-v1.md` (architecture options + MVP scope + M0-M6 milestones). Replaced `next steps.md` with this `PROGRESS.md`. F11 (`parse_masthead`) is the next concrete task. |
| 2026-04-19 | Doc reshuffle | — | Moved `library-contract-v1.md`, `library-roadmap-v1.md`, and `spatial_reorder_changelog.md` into `docs/`; updated all references in PROGRESS, README, and the `docs` skill. |

*Add a row here at the end of every session.*
