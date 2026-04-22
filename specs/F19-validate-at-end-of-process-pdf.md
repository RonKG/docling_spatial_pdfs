# F19 Spec: Validate at end of process_pdf

## 1. What to Build

Wire the F18 Pydantic models into `gazette_docling_pipeline_spatial.ipynb` by calling `Envelope.model_validate(record)` at the very tail of `GazettePipeline.process_pdf` — after the record is built, before any JSON file is written, and re-raising any `ValidationError`. Three carry-over fixes are non-negotiable and must land before the validation call so the existing `_gazette_spatial.json` outputs become a strict subset of the contract `Envelope`:

1. **Body-segment shape fix at source.** In `_segment_body_lines` (the notebook helper called by `split_gazette_notices`), rewrite the blank branch so it emits `{"type": "blank", "lines": []}` (plural list) instead of `{"type": "blank", "line": ln}` (singular string). This brings every `BodySegment` produced by the notebook into the `lines: list[str]` shape the contract requires, and makes the F18 `adapt_notice_to_contract()` helper in `scripts/f18_validate_real_notice.py` obsolete (delete it). After the rename, all 6 canonical `_gazette_spatial.json` outputs must be re-generated so the on-disk shape matches the new in-memory shape.
2. **`content_sha256` stamping per notice.** The contract requires `Notice.content_sha256: str` (non-optional) and the notebook does not emit it today. Inside `process_pdf`, after notices are split and scored and identity fields stamped, but before the Envelope adapter runs, stamp every notice with `notice["content_sha256"] = hashlib.sha256(notice["gazette_notice_full_text"].encode("utf-8")).hexdigest()`.
3. **Flat-to-nested Envelope adapter.** Today's `record` is a flat top-level dict (`gazette_notices`, `volume`, `issue_no`, `publication_date`, `supplement_no`, `masthead_text`, `parse_confidence` siblings to `pdf_sha256`, plus several pipeline-internal keys like `pdf_title`, `pdf_path`, `docling`, `pages`). The contract `Envelope` requires those issue fields nested under `issue: GazetteIssue`, the notice list under `notices` (not `gazette_notices`), and a brand-new top-level `output_format_version: int = 1`. Since every model except `DerivedTable` sets `extra="forbid"`, every stray key currently emitted by `process_pdf` must be either routed to a contract field, dropped, or pushed into a model `other_attributes`/`raw` carrier. A new helper, `build_envelope_dict(record_flat)`, performs that triage; `process_pdf` returns and writes the nested-shape dict directly so future loads round-trip cleanly through `Envelope.model_validate(...)`.

**Self-tracking sentinel warning for corrigenda.** Because the corrigendum sub-adapter has to invent two contract-required fields (`scope` and `provenance`) for every corrigendum the notebook produces today, the adapter must emit one `Warning` per sentinel-stamped corrigendum and append it to `Envelope.warnings`. The warning makes the deferred work visible to consumers and to F31 (a new post-1.0 work item that replaces the sentinel with real extraction). Same self-tracking pattern is recommended for the `"table"` body-segment coercion path (also a deferred fix; see roadmap M5), but the corrigendum warning is the one that must land in F19. Exact `Warning` field mapping is in section 2.

This is roadmap milestone M2.5: prove the contract fits real PDFs without changing pipeline behavior. No work moves into `kenya_gazette_parser/` modules (that is F20), no JSON Schema is exported (F23), and `parse_file` stays an F17 stub (until F21). All 6 canonical PDFs must validate cleanly via `Envelope.model_validate(record)` and `check_regression()` must remain PASS.

---

## 2. Interface Contract

### Affected callables

| Callable | Location | Input | Output | Error Rule |
|----------|----------|-------|--------|------------|
| `_segment_body_lines(lines: list[str])` | notebook, around line 322 | unchanged | `list[dict]` where every `{"type": "blank", ...}` segment now carries `"lines": list[str]` (empty list for a truly blank line; never a singular `"line"` key) | none — pure refactor; behaviour for `"text"` / `"table"` segments unchanged |
| `build_envelope_dict(record_flat: dict) -> dict` | NEW helper in same notebook cell as `process_pdf` | the flat top-level dict that `process_pdf` builds today (post-content_sha256 stamping) | a dict shaped exactly like the contract `Envelope` (see triage tables below) | raises `KeyError` only if a documented required source key is missing; never silently swaps fields. Adapter is a pure function, no I/O. |
| `process_pdf(self, pdf_path: Path) -> dict` | notebook, around line 1960 | unchanged | the validated, nested-shape `Envelope` dict (i.e. `Envelope.model_validate(...).model_dump(mode="json")` is the return value AND what is written to `_gazette_spatial.json`) | `pydantic.ValidationError` is **re-raised**, never swallowed. No fallback, no partial write. The JSON file is written only if validation passes. |
| `adapt_notice_to_contract(notice)` (F18) | `scripts/f18_validate_real_notice.py` | n/a | n/a | **Deleted.** The helper exists only to bridge the F18 / F19 gap; once the body-segment fix lands, its sole transformation is a no-op. F18 T2 must still pass without it. |

### Top-level record key triage (locked)

Source: every key currently set on `record` inside `GazettePipeline.process_pdf` (notebook lines 2050-2079).

| Source key (flat record) | Destination | Notes |
|--------------------------|-------------|-------|
| `pdf_title` | **dropped** | Pipeline-internal; not in `Envelope`. |
| `pdf_file_name` | **dropped** | Available via `pdf_sha256` + caller's path. |
| `pdf_path` | **dropped** | Same as above. |
| `pdf_size_bytes` | **dropped** | Not in `Envelope`. |
| `pdf_sha256` | `Envelope.pdf_sha256` | Pass through. |
| `gazette_issue_id` | `Envelope.issue.gazette_issue_id` | Removed from top level; lives only under `issue`. |
| `library_version` | `Envelope.library_version` | Pass through. |
| `schema_version` | `Envelope.schema_version` | Pass through. |
| `extracted_at` | `Envelope.extracted_at` | Pydantic v2 parses the ISO string emitted by `make_extracted_at()` to `datetime`. |
| `warnings` | `Envelope.warnings` | Pass through; already a `list[dict]` in `Warning` shape. |
| `pages` | **dropped** | Page count is implicit in `layout_info.pages`. |
| `volume` | `Envelope.issue.volume` | Optional; may be `None`. |
| `issue_no` | `Envelope.issue.issue_no` | Optional; coerced to `int` by Pydantic if string. |
| `publication_date` | `Envelope.issue.publication_date` | Optional ISO `YYYY-MM-DD` string; Pydantic parses to `date`. |
| `supplement_no` | `Envelope.issue.supplement_no` | Optional; default `None`. |
| `masthead_text` | `Envelope.issue.masthead_text` | Required by `GazetteIssue`. |
| `parse_confidence` | `Envelope.issue.parse_confidence` | Required by `GazetteIssue`. |
| `document_confidence` | `Envelope.document_confidence` | Pass through; verify `counts` keys are exactly `{"high","medium","low"}`. |
| `layout_info` | `Envelope.layout_info` | Pass through; `LayoutInfo.pages` is `list[dict[str, Any]]` so per-page dict shape is unconstrained. |
| `docling` (whole sub-tree: `export_summary`, `full_markdown`, `full_plain_text`, `full_plain_text_spatial`, optional `full_docling_document_dict`) | **dropped** | Pipeline diagnostics; not in `Envelope`. The notebook still writes `_docling.json`, `_spatial.txt`, `_spatial_markdown.md`, `_docling_markdown.md` from local variables — those side files are unchanged. |
| `corrigenda` | `Envelope.corrigenda` after corrigenda adapter (below) | Default `[]` if list empty. |
| `gazette_notices` | `Envelope.notices` after per-notice adapter (below) | Renamed key. |
| (none today) | `Envelope.output_format_version` | **NEW**, hard-coded `1` in the adapter. First locked envelope schema. |
| (none today) | `Envelope.cost` | Optional, omit (=None) until LLM stages run. |

### Per-notice key triage

Source: every key currently set on each notice dict by `split_gazette_notices` + `score_notices` + the F13 stamping loop in `process_pdf`.

| Source key (per notice) | Destination | Notes |
|-------------------------|-------------|-------|
| `gazette_notice_no` | `Notice.gazette_notice_no` | Optional. |
| `gazette_notice_header` | `Notice.gazette_notice_header` | Optional. |
| `title_lines` | `Notice.title_lines` | Pass through. |
| `gazette_notice_full_text` | `Notice.gazette_notice_full_text` | Required. |
| `body_segments` | `Notice.body_segments` | After carry-over 1 fix, every entry is a valid `BodySegment` dict (`type` in `{"text","blank"}`, `lines: list[str]`). See "Risk: `type=table`" below. |
| `derived_table` | `Notice.derived_table` | Optional. `DerivedTable` is the only `extra="allow"` model — pass through verbatim. |
| `other_attributes` (currently: `char_span_start_line`, `char_span_end_line`, `lines_in_body`, optional `reason`) | `Notice.other_attributes` | Pass through; the field is typed `dict[str, Any]`. |
| `provenance` (currently: `header_match`, `line_span`, `raw_header_line`, `stitched_from`, optional `ocr_quality`) | `Notice.provenance` | Pass through; matches `Provenance` exactly. `line_span` arrives as `list[int, int]`; Pydantic coerces to `tuple[int, int]`. |
| `confidence_scores` | `Notice.confidence_scores` | Pass through. |
| `confidence_reasons` | `Notice.confidence_reasons` | Pass through. |
| `gazette_issue_id` | `Notice.gazette_issue_id` | Pass through (stamped in F13). |
| `notice_id` | `Notice.notice_id` | Pass through (stamped in F13). |
| (none today) | `Notice.content_sha256` | **NEW** per carry-over 2; computed in `process_pdf` before adapter. |

### Per-corrigendum key triage (REQUIRED — current notebook shape does NOT match the contract)

Source: `extract_corrigenda` in the notebook (lines 829-836) emits a different shape from contract `Corrigendum`.

| Source key (current corrigendum dict) | Destination on `Corrigendum` | Notes |
|---------------------------------------|------------------------------|-------|
| `referenced_notice_no` (str) | `target_notice_no` | Rename. |
| `referenced_year` (str) | `target_year` (int) | Rename and coerce: `int(value)` (Pydantic will also coerce numeric strings, but adapter does it explicitly to avoid surprises). |
| `correction_text` (str \| None) | `amendment` | Rename. |
| `error_text` (str \| None) | **dropped** | Not in contract; `raw_text` carries the full corrigendum. |
| `what_corrected` (str \| None) | **dropped** | Not in contract. |
| `raw_text` (str) | `raw_text` | Pass through. |
| `gazette_issue_id` (added in F13) | **dropped** | Not in `Corrigendum` (the contract `Corrigendum` has no `gazette_issue_id`; the FK lives on the parent `Envelope.issue`). |
| (none today) | `scope` | **NEW required field.** Adapter stamps a default of `"notice_references_other"` (matches the actual current extraction semantics — every notebook-emitted corrigendum is a preamble entry that names another notice; see the `CORRIGENDUM_RE` regex around line 805). Implementer must NOT invent `"issue_level"` or `"notice_is_corrigendum"` until a richer detector lands. |
| (none today) | `provenance` | **NEW required field.** Synthesize a minimal `Provenance` placeholder: `{"header_match": "inferred", "line_span": [0, 0], "raw_header_line": None, "stitched_from": []}`. Note the current corrigendum extractor does not record line spans; the contract requires the field, so we stamp a sentinel and record this gap as a known limitation in the build report. F19 does not improve corrigendum extraction — that is F31. |
| (adapter side-effect, not a Corrigendum field) | Append one `Warning` to `Envelope.warnings` per sentinel-stamped corrigendum | **REQUIRED.** Every time the adapter stamps the default `scope` and the placeholder `provenance` (i.e. for every corrigendum the current notebook emits, since none of them carry real values today), append a `Warning` instance with: `kind="corrigendum_scope_defaulted"`, `message="Corrigendum scope and provenance defaulted; real extraction deferred to F31"`, `where={"notice_no": <source corrigendum's referenced_notice_no or None>, "page_no": <best-available page_no or None — None today since the corrigendum extractor does not record page; revisit in F31>}`. Field-name reminder: the F18 `Warning` model is `Warning(kind: str, message: str, where: dict[str, Any] | None = None)` (see `kenya_gazette_parser/models/envelope.py`). The user-shorthand "code" maps to `kind`; "notice_no" / "page_no" go inside the `where` dict. Do NOT add new fields to `Warning`. |

### Strictness, error rule, and write order

| Boundary | Rule |
|----------|------|
| Adapter encounters an unknown key | Adapter does NOT silently route to `other_attributes` for top-level / GazetteIssue / Corrigendum — it raises `KeyError` so new keys cannot leak. (For per-notice keys, the existing `other_attributes` dict already absorbs notebook-internal carry-throughs; adapter does not re-shape it.) |
| Required contract field missing on adapter input | Adapter raises `KeyError` with the source key name. |
| `Envelope.model_validate(record)` fails | `pydantic.ValidationError` propagates out of `process_pdf`. **No JSON file is written.** Caller sees the validation error verbatim. |
| `process_pdf` return value | `Envelope.model_validate(record).model_dump(mode="json")` — i.e. the return value is the validated, normalized dict (not the raw `record`). This is also the dict written to `_gazette_spatial.json`. |
| Side files (`_spatial.txt`, `_spatial_markdown.md`, `_docling_markdown.md`, `_docling.json`) | Unchanged. They are written from local variables (`plain_spatial`, `md`, `doc_dict`), not from `record`. F19 does not touch them. |

### Known risk to flag in the build report (not blocking)

- `_segment_body_lines` can also emit `{"type": "table", "raw_lines": [...], "rows": [[...]]}` blocks (notebook line 365). The contract `BodySegment.type: Literal["text", "blank"]` rejects `"table"`. F18 T2 only validated the first notice of Vol CXXIVNo 282 and happened not to hit one. **Implementer must run a smoke check across all 6 canonical PDFs before finalizing the adapter.** If any notice contains a `type=="table"` body_segment, the implementer must either (a) coerce the `"table"` block to `{"type": "text", "lines": block["raw_lines"]}` inside the per-notice adapter, or (b) drop it from `body_segments` and rely on the existing `derived_table` field. Pick (a) — text-with-multiple-lines is the closest 1.0-legal representation and preserves the row text. Document the coercion in the build report. Richer table segment types arrive in 2.x per roadmap M5.

### Non-goals for F19

- No changes under `kenya_gazette_parser/` (that is F20).
- No JSON Schema export (F23).
- No `parse_file` / `parse_bytes` wiring (F21).
- No new `GazetteConfig`, `Bundles`, `LLMPolicy` types (F22).
- No improvement to corrigendum extraction quality — only a shape adapter (M2.x or later).
- No new `_gazette_spatial.json` siblings, no schema migration utility.

---

## 3. Test Cases

Run from repo root with `.\.venv\Scripts\python.exe`. Real-file tests anchor on `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json` (same primary as F18). All 6 canonical PDFs are: `Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`.

| ID | Scenario | Source / Trigger | Expected Result |
|----|----------|------------------|-----------------|
| **T1** | **Happy path — Vol CXXIVNo 282 produces a clean Envelope.** Run `process_pdf` on `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` end-to-end. | Notebook cell that calls `pipeline.process_pdf(Path("pdfs/Kenya Gazette Vol CXXIVNo 282.pdf"))` after the new adapter and validation are in place. | `process_pdf` returns a dict; `env = Envelope.model_validate(record)` succeeds with no `ValidationError`; `env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"`; `len(env.notices) > 0`; `len(env.notices[0].content_sha256) == 64` and is hex-only (`re.fullmatch(r"[0-9a-f]{64}", env.notices[0].content_sha256)`); at least one body segment in `env.notices[0].body_segments` has `lines` as a `list[str]` (no segment carries a `"line"` key). `env.output_format_version == 1`. |
| **T2** | **Edge case — zero corrigenda still produces `corrigenda == []`.** Pick any canonical PDF whose `extract_corrigenda(plain_spatial)` returns `[]` (Vol CXINo 100 typically has none — implementer verifies and substitutes if needed). | Run `process_pdf` on that PDF, then `env = Envelope.model_validate(record)`. | `env.corrigenda == []` (empty list, not missing key). `Envelope.model_validate` does not raise. The JSON file written to disk includes `"corrigenda": []`. |
| **T3** | **Degraded — bad notice raises `ValidationError`.** Inside the notebook (or a `scripts/f19_degraded.py` helper), monkey-patch `process_pdf` for one run so the `content_sha256` stamping step is skipped on the first notice (e.g. `del notices[0]["content_sha256"]` after stamping, before the adapter). Process Vol CXXIVNo 282. | Adapter still runs; validation runs at tail. | `pydantic.ValidationError` is raised at the tail of `process_pdf`. Error message mentions `content_sha256` and `missing`. **No `_gazette_spatial.json` is written for this run** — confirm by `stat`-ing the file's mtime before and after. |
| **T4** | **Round-trip — every freshly written `_gazette_spatial.json` re-validates from disk.** After re-running the pipeline on all 6 canonical PDFs, load each `output/<stem>/<stem>_gazette_spatial.json` from disk and call `Envelope.model_validate(json.load(f))`. | `scripts/f19_round_trip.py` iterating the 6 canonical stems. | All 6 PDFs validate cleanly. For each, assert `env.output_format_version == 1`, `env.pdf_sha256` is 64-hex, every `Notice.content_sha256` is 64-hex, every `BodySegment.type in {"text","blank"}` (proves carry-over 1 fix landed), and `env.issue.gazette_issue_id == record["issue"]["gazette_issue_id"]`. Print `T4 OK (6/6)`. |
| **T5** | **Gate 1 regression — `check_regression()` PASS on all 6 canonical PDFs.** After the body-segment shape fix and re-processing, run the notebook cell defining `check_regression()` (after running its setup cells). | `check_regression()` in `gazette_docling_pipeline_spatial.ipynb`. | Returns / prints OK for all 6 canonical PDFs. Confidence numbers in `tests/expected_confidence.json` are unchanged because the body-segment key rename does not feed into any score (`score_*` functions do not inspect body-segment internals beyond counting). If any PDF degrades, F19 broke a scoring path — investigate before committing. |
| **T6** | **F18 helper cleanup — `scripts/f18_validate_real_notice.py` works without `adapt_notice_to_contract`.** Delete (or stub to identity `return notice`) the `adapt_notice_to_contract()` helper in `scripts/f18_validate_real_notice.py` and re-run the script. | `.\.venv\Scripts\python.exe scripts\f18_validate_real_notice.py` after the on-disk `_gazette_spatial.json` for Vol CXXIVNo 282 is regenerated. | Prints `T2 OK`. (T2 here means F18's T2, asserted at the end of the F18 script.) Proves the source-of-truth fix replaces the runtime adapter. |
| **T7** | **Corrigendum sentinel warnings emitted 1:1.** Process a PDF known to have at least one corrigendum and assert that for every entry in `env.corrigenda`, there is a matching `Warning` in `env.warnings` with `kind == "corrigendum_scope_defaulted"`. Confirm before running by checking `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json` has a non-empty `corrigenda` list (it does as of the last F18 baseline; if not, swap to another canonical PDF with non-empty `corrigenda`). | `scripts/f19_corrigendum_warnings.py` (or a notebook cell): load the freshly written nested-shape `_gazette_spatial.json` for Vol CXXIVNo 282, validate via `Envelope.model_validate(...)`, then assert `len([w for w in env.warnings if w.kind == "corrigendum_scope_defaulted"]) == len(env.corrigenda)`. | Equality holds. For each warning, `w.where["notice_no"]` matches the corresponding corrigendum's `target_notice_no` (or both are `None`). If the chosen PDF has zero corrigenda, T7 trivially passes (zero matching warnings expected). Print `T7 OK (<N> warnings for <N> corrigenda)`. |

**Helper scripts recommended** (under `scripts/`):

- `scripts/f19_degraded.py` (T3 — drives `process_pdf` with a monkey-patched notice).
- `scripts/f19_round_trip.py` (T4 — iterates the 6 canonical `_gazette_spatial.json` files).
- `scripts/f19_corrigendum_warnings.py` (T7 — asserts 1:1 sentinel warning emission).
- T1 and T2 are notebook cells. T5 is the existing `check_regression()` notebook cell. T6 is a 1-line shell command after editing `scripts/f18_validate_real_notice.py`.

**Not tested in F19** (deferred): no `parse_file` end-to-end (F21); no JSON Schema validation (F23); no smoke test of installed package on a different machine (F24); no LLM/Cost path (post-1.0).

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F19: Validate at end of `process_pdf`**

Read this spec: `specs/F19-validate-at-end-of-process-pdf.md`. Read `docs/library-contract-v1.md` section 3 — the source of truth for the `Envelope`, `GazetteIssue`, `Notice`, `BodySegment`, `Provenance`, `Corrigendum` shapes. The F18 Pydantic models live in `kenya_gazette_parser/models/`; F19 imports them from there. Edit only `gazette_docling_pipeline_spatial.ipynb` and the F18 helper script `scripts/f18_validate_real_notice.py` (delete the `adapt_notice_to_contract` helper). Do NOT touch any file under `kenya_gazette_parser/`, `pdfs/`, `output/` source PDFs, `.llm_cache/`, or `tests/expected_confidence.json`. Re-running PDFs DOES regenerate the per-PDF folders under `output/` — that is expected.

**Core file location:** `gazette_docling_pipeline_spatial.ipynb` (the notebook is the editable target — F20 moves logic into the package, not F19).

**Carry-overs (must land — not optional):**

1. **Body-segment shape fix at source.** In the notebook cell that defines `_segment_body_lines` (search for `"type": "blank"` around line 331), change `blocks.append({"type": "blank", "line": ln})` to `blocks.append({"type": "blank", "lines": []})`. The empty list is correct because a truly blank line carries no content; if the implementer prefers to preserve the (whitespace-only) original line, use `{"type": "blank", "lines": [ln] if ln else []}` — both are 1.0-legal because `BodySegment.lines: list[str]` accepts any list including empty. Pick `[]`; it round-trips identically to the previous `""` and is one less surprise for downstream readers.
2. **`content_sha256` stamping.** In `GazettePipeline.process_pdf` (around line 1960), add `import hashlib` to the top-of-cell imports if not already imported, then immediately after the F13 stamping loop (the `for notice in notices:` block that sets `notice["gazette_issue_id"]` and `notice["notice_id"]`) add:
   ```python
   for notice in notices:
       notice["content_sha256"] = hashlib.sha256(
           notice["gazette_notice_full_text"].encode("utf-8")
       ).hexdigest()
   ```
   Do this before the corrigenda block and before the adapter. (Stamping after `notice_id` is set keeps the relative order obvious and matches the F18 helper's behavior.)
3. **Flat-to-nested adapter + validation call.** Add a new helper `build_envelope_dict(record_flat: dict) -> dict` in the same cell as `process_pdf` (just above the class). Implement it according to the three triage tables in section 2 of the spec (top-level, per-notice, per-corrigendum). At the very tail of `process_pdf`, after `record` is built and `content_sha256` is stamped, call:
   ```python
   from kenya_gazette_parser.models import Envelope
   record_nested = build_envelope_dict(record)
   env = Envelope.model_validate(record_nested)
   record = env.model_dump(mode="json")
   ```
   then write `record` to `_gazette_spatial.json` and `return record`. Do not catch `ValidationError`; let it propagate. The other side files (`_spatial.txt`, `_spatial_markdown.md`, `_docling_markdown.md`, `_docling.json`) keep writing from their local variables — no change there.

**Order of operations (run in this order):**

1. Edit `_segment_body_lines` per carry-over 1. Restart the notebook kernel; do NOT re-run any PDFs yet.
2. Re-process all 6 canonical PDFs (`Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`) so the on-disk `_gazette_spatial.json` files pick up the new body-segment shape. Run `check_regression()` immediately after — it must PASS (the body-segment key rename does not feed into any score).
3. Add the `content_sha256` stamping per carry-over 2.
4. Smoke-check across all 6 freshly regenerated `_gazette_spatial.json` files: any notice with `body_segments[i]["type"] == "table"`? If yes, the per-notice adapter must coerce table blocks to `{"type": "text", "lines": block["raw_lines"]}` before validation (see the "Known risk" note in section 2 of the spec). Document either way in the build report.
5. Implement `build_envelope_dict()` and the corrigendum sub-adapter. Keep the function pure (no I/O, no logging side effects). **Sub-requirement (REQUIRED):** the corrigendum sub-adapter must, for every corrigendum it stamps with the sentinel `scope="notice_references_other"` and placeholder `provenance`, also append one `Warning` to the envelope's `warnings` list with `kind="corrigendum_scope_defaulted"`, `message="Corrigendum scope and provenance defaulted; real extraction deferred to F31"`, and `where={"notice_no": <source corrigendum's referenced_notice_no or None>, "page_no": None}` (page tracking is out of scope until F31). This warning is the bridge to F31: it makes the deferred work visible to consumers and gives F31 a measurable baseline (the `warnings` count). Use the `Warning` model from `kenya_gazette_parser.models` — do NOT add new fields. The same self-tracking pattern is recommended for the `"table"` body-segment coercion (`kind="table_coerced_to_text"`) but is not blocking for F19 acceptance.
6. Wire `Envelope.model_validate(...)` at the tail of `process_pdf` per carry-over 3. Make `process_pdf` return the validated dump, write the validated dump to disk.
7. Re-run all 6 canonical PDFs. Each must complete without `ValidationError`. Each `_gazette_spatial.json` is now in nested-shape (top-level keys: `library_version`, `schema_version`, `output_format_version`, `extracted_at`, `pdf_sha256`, `issue`, `notices`, `corrigenda`, `document_confidence`, `layout_info`, `warnings`, optionally `cost`).
8. Run `check_regression()` again — must still PASS for all 6.
9. Run T4 (`scripts/f19_round_trip.py`) — must print `T4 OK (6/6)`.
10. Delete `adapt_notice_to_contract()` from `scripts/f18_validate_real_notice.py` (replace its body with `return notice` and add a one-line comment "F19 fixed body-segment shape at source; helper retained as identity for backward compatibility" — OR remove the function and its single call site entirely; pick one). Re-run `scripts\f18_validate_real_notice.py`; must still print `T2 OK`.

**Top-level record key triage** (apply verbatim — do not re-litigate):

- DROP: `pdf_title`, `pdf_file_name`, `pdf_path`, `pdf_size_bytes`, `pages`, `docling` (the whole sub-tree including `export_summary`, `full_markdown`, `full_plain_text`, `full_plain_text_spatial`, `full_docling_document_dict` if present), `gazette_issue_id` (top-level duplicate; stays only under `issue`).
- PASS THROUGH at top level: `pdf_sha256`, `library_version`, `schema_version`, `extracted_at`, `warnings`, `document_confidence`, `layout_info`.
- RENAME: `gazette_notices` → `notices`.
- NEST under `issue`: `gazette_issue_id` (from top-level), `volume`, `issue_no`, `publication_date`, `supplement_no`, `masthead_text`, `parse_confidence`.
- NEW: `output_format_version: int = 1`.
- ADAPT: `corrigenda` (per the per-corrigendum triage table — rename + drop + synthesize `scope` and `provenance`).
- ADAPT: each notice in `notices` (stamp `content_sha256`; everything else already matches contract `Notice`).

**Test commands (run after each step that changes behavior):**

- T1: in the notebook, after re-processing Vol CXXIVNo 282, eyeball that `process_pdf` returned a dict with `issue`, `notices`, `output_format_version` keys (not `gazette_notices` / flat issue fields).
- T2: in the notebook, find a canonical PDF whose corrigenda list comes back empty and assert the validated `record["corrigenda"] == []`.
- T3: `.\.venv\Scripts\python.exe scripts\f19_degraded.py` — must raise `ValidationError`.
- T4: `.\.venv\Scripts\python.exe scripts\f19_round_trip.py` — must print `T4 OK (6/6)`.
- T5: in the notebook, run `check_regression()` — must report OK for all 6 canonical PDFs.
- T6: `.\.venv\Scripts\python.exe scripts\f18_validate_real_notice.py` after gutting the adapter — must print `T2 OK`.
- T7: `.\.venv\Scripts\python.exe scripts\f19_corrigendum_warnings.py` — must print `T7 OK (<N> warnings for <N> corrigenda)` on Vol CXXIVNo 282 (or another canonical PDF with non-empty `corrigenda`).

**Update `PROGRESS.md`** (in this exact order):

- In the **Today** block, change `**Current:** F19 ...` to `**Current:** F20 — Move logic into modules` and update `**Previous:** F18 ✅ ...` to `**Previous:** F19 ✅ — Validate at end of process_pdf (Envelope.model_validate at tail of process_pdf; body_segments fixed at source; content_sha256 stamped; flat-to-nested adapter; output_format_version=1)`.
- In the **Work Items** table, change F19's row Status from `⬜ Not started` to `✅ Complete`.
- In the **Work Items** table, append a **new row immediately after** the existing collapsed `*F26-F30* | *Post-1.0 items*` row, with the same italic / `⬜ Post-1.0` styling convention so it sits as a sibling under the post-1.0 block. New row content: `**F31** | Corrigendum scope + provenance extraction | Replace F19 sentinel `scope="notice_references_other"` and placeholder `provenance` with real values extracted from the source corrigendum text and page layout. Emitted as `Warning(kind="corrigendum_scope_defaulted", ...)` per corrigendum in F19; replace those warnings with real extraction here. | ⬜ Post-1.0 | —`. Do NOT change the `*F26-F30*` row itself; F31 is a sibling, not a replacement.
- In the **Quality Gates** table, leave Gate 4 as `⬜ Not reached` — Gate 4 requires F23 (JSON Schema) too. F19 alone does not clear it.
- In **Session Log**, append a row dated today with: carry-over 1 fix (body_segment shape), carry-over 2 (content_sha256 stamping site), carry-over 3 (`build_envelope_dict` + `Envelope.model_validate` at tail), table-segment coercion decision (drop vs coerce), all 6 canonical PDFs revalidated, T1-T6 results, regression PASS, F18 helper status (deleted vs stubbed).

**Build Report Format:**

```markdown
# Build Report: F19

## Implementation
- Files edited:
  - `gazette_docling_pipeline_spatial.ipynb` (changes: `_segment_body_lines` blank branch; `process_pdf` adds `content_sha256` stamping, `build_envelope_dict` helper, `Envelope.model_validate` at tail; new top-of-cell imports `hashlib`, `from kenya_gazette_parser.models import Envelope`)
  - `scripts/f18_validate_real_notice.py` (deleted / stubbed `adapt_notice_to_contract`)
  - `PROGRESS.md` (F19 row → ✅; Today moved to F20; session log row appended)
- Files created:
  - `scripts/f19_degraded.py`
  - `scripts/f19_round_trip.py`
- Files NOT touched: anything under `kenya_gazette_parser/`, `pyproject.toml`, `requirements.txt`, `tests/expected_confidence.json`, source PDFs.
- Output folders regenerated: 6 (one per canonical PDF). Each `_gazette_spatial.json` is now in nested Envelope shape.

## Adapter triage decisions
- Top-level keys dropped: pdf_title, pdf_file_name, pdf_path, pdf_size_bytes, pages, docling.*, top-level gazette_issue_id
- output_format_version: 1
- Corrigendum scope default: notice_references_other (every preamble entry today)
- Corrigendum provenance synthesis: header_match=inferred, line_span=[0,0]
- table-segment body blocks found in (PDFs): <list> — handled via: <coerce to text / not encountered>

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 — Vol CXXIVNo 282 envelope validates | PASS/FAIL | |
| T2 — empty corrigenda case | PASS/FAIL | PDF used: <name> |
| T3 — degraded notice raises ValidationError | PASS/FAIL | error message excerpt |
| T4 — round-trip 6/6 from disk | PASS/FAIL | |
| T5 — check_regression() OK on 6 PDFs | PASS/FAIL | |
| T6 — F18 T2 OK without adapter | PASS/FAIL | |
| T7 — corrigendum_scope_defaulted warnings 1:1 with corrigenda | PASS/FAIL | PDF used: <name>; warnings emitted: <N>; corrigenda count: <N> |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (T5 PASS)
- Gate 2 (deterministic notice_id): STILL CLEARED (notice_id stamping unchanged)
- Gate 3 (`from kenya_gazette_parser import parse_file` works): still PARTIAL (Gate 3 fully clears at F21)
- Gate 4 (Envelope validates against JSON Schema): NOT REACHED (still needs F23)

## PROGRESS.md
- F19 row: ⬜ Not started → ✅ Complete
- "Today" moved to F20 — Move logic into modules
- Session Log row appended

## Notes for F20
- The notebook now has a clean `build_envelope_dict()` + `Envelope.model_validate()` boundary at the tail of `process_pdf`. F20 should lift `build_envelope_dict`, the corrigendum sub-adapter, and the per-notice `content_sha256` stamping into `kenya_gazette_parser/pipeline.py` (or a sibling module). The notebook can then become a thin demo per roadmap M2/M3.
- The F18 `adapt_notice_to_contract` helper is gone / inert. Body-segment shape is now consistent end-to-end.

## Notes for F31 (baseline)
- `corrigendum_scope_defaulted` warning counts after F19 lands, per canonical PDF (this is the baseline F31 must drive to zero by replacing the sentinel with real extraction):
  | PDF | corrigenda | corrigendum_scope_defaulted warnings |
  |-----|-----------|--------------------------------------|
  | Kenya Gazette Vol CXINo 100 | <N> | <N> |
  | Kenya Gazette Vol CXINo 103 | <N> | <N> |
  | Kenya Gazette Vol CXIINo 76 | <N> | <N> |
  | Kenya Gazette Vol CXXVIINo 63 | <N> | <N> |
  | Kenya Gazette Vol CXXIVNo 282 | <N> | <N> |
  | Kenya Gazette Vol CIINo 83 - pre 2010 | <N> | <N> |
  | **Total** | <SUM> | <SUM> |
- F31 done-when: total `corrigendum_scope_defaulted` warnings drops to 0 across the 6 canonical PDFs because every corrigendum carries a real extracted `scope` and a real `provenance.line_span`.

## Final Status: PASS / FAIL
```

---

### Discrepancy / risk notes (none blocking, but flagged per Agent 1 SOP)

- **Contract vs notebook — corrigendum shape mismatch.** Contract section 3 `Corrigendum` requires `scope` and `provenance` (and uses `target_notice_no` / `target_year` / `amendment` keys). Notebook today emits `referenced_notice_no` / `referenced_year` / `correction_text` plus `error_text` / `what_corrected` and no `scope` / `provenance`. F19 adapter bridges the gap with sensible defaults; richer corrigendum extraction is post-F19 work.
- **Contract vs notebook — `BodySegment.type` enum.** Contract locks `Literal["text", "blank"]` for 1.0; notebook can emit `"table"` blocks too. F19 must either coerce or drop those before validation; preferred coercion is `{"type": "text", "lines": raw_lines}`. Roadmap M5 promotes `"table"` to a first-class segment type via MINOR bump.
- **Roadmap vs PROGRESS — milestone wording.** PROGRESS.md "Done when" for F19 says "All 6 canonical PDFs produce envelopes that validate cleanly." Roadmap M2 says the notebook "imports them and calls `Envelope.model_validate(record)` before writing JSON. No behavior change". Aligned. F19 spec adds the explicit body-segment / content_sha256 / nested-shape carry-overs the user-supplied prompt enumerated; these are the implicit prerequisites the roadmap line glosses over.
