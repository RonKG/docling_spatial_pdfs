# Data Quality and Confidence Scoring for Gazette Notice Extraction

This document outlines a proposed confidence scoring system for automatically assessing the quality of parsed gazette notices. The goal is to assign numeric confidence metrics (0.0 to 1.0) to each extracted notice, enabling automated detection of parsing errors that currently require manual human review.

---

## Background

The gazette extraction pipeline performs several transformations:

1. **Docling extraction** -- Converts PDF to structured JSON with text, tables, and bounding boxes
2. **Spatial reordering** -- Fixes two-column reading order using bbox coordinates
3. **Notice splitting** -- Splits text by strict full-line, all-caps `GAZETTE NOTICE NO.` headers into individual notices, with title/body segmentation and running-header stripping

Each step can introduce errors. Currently, quality issues are caught through manual human review of output JSON and markdown files. This document proposes automated confidence scores based on observable signal patterns in the data.

---

## Confidence Dimensions

### 1. Notice Number Confidence (`notice_no_confidence`)

**Purpose:** Assess whether the extracted notice number is valid and follows expected patterns.

**Signals for HIGH confidence (0.8-1.0):**
- Notice number is pure digits (e.g., "9103", "14096")
- Length is reasonable (2-6 digits typical for Kenya gazettes)
- Matches known Kenya gazette numbering patterns

**Signals for MEDIUM confidence (0.4-0.7):**
- Contains slashes/hyphens but follows year/number format (e.g., "2009/123")
- Contains letters mixed with numbers (e.g., "9017A")
- Slightly longer than typical (7-10 characters)

**Signals for LOW confidence (0.0-0.3):**
- Empty or whitespace-only capture
- Single character (e.g., "s" -- often from regex capturing "Notice**s**" plural)
- Only special characters (e.g., ".", "/", "-")
- Extremely long (>15 characters) suggesting paragraph capture instead of number

**Observable examples from current output:**

```json
// HIGH confidence
{"gazette_notice_no": "9103"}       // confidence: 1.0
{"gazette_notice_no": "10453"}      // confidence: 1.0

// LOW confidence  
{"gazette_notice_no": "s"}          // confidence: 0.2 (from "Gazette Notices")
{"gazette_notice_no": ""}           // confidence: 0.0 (empty capture)
{"gazette_notice_no": "8756"}       // confidence: 1.0 BUT context shows this is 
                                    // referencing another notice, not a new one
```

**Known edge case:** Corrigenda notices that reference other notice numbers. These extract the referenced number instead of having their own. Pattern: notice starts with "Gazette Notice No. XXXX of YYYY, amend..."

---

### 2. Structural Completeness Confidence (`structure_confidence`)

**Purpose:** Assess whether the notice contains expected structural elements and has reasonable length.

**Signals for HIGH confidence (0.8-1.0):**
- Notice length is reasonable (200-20,000 characters typical for most notices)
- Contains multiple lines (>5 lines after header)
- Has non-empty `title_lines` (act name, chapter reference, subtitle extracted)
- Has `body_segments` with mixed `text` and `table` types (well-structured content)
- Contains expected Kenya gazette structural markers:
  - Date patterns (`Dated the 3rd August, 2010`)
  - Authority phrases (`IN EXERCISE of powers`, `IT IS NOTIFIED`)
  - Legal citations (`(Cap. 7)`, `(No. 9 of 2008)`)
  - Signature blocks (Minister/Chairman/Commissioner names)
  - Action verbs (`GIVEN`, `APPOINTED`, `TRANSFERRED`)

**Signals for MEDIUM confidence (0.4-0.7):**
- Short but complete (100-200 characters for simple notices like corrigenda)
- Contains some structural markers but missing key elements
- Has reasonable line count but lacks dates or signatures

**Signals for LOW confidence (0.0-0.3):**
- Very short (<50 characters) -- likely truncated or false positive
- Very long (>100,000 characters) -- likely multiple notices merged
- Only contains header line (`lines_in_body` < 3)
- Empty `title_lines` and no `body_segments` detected
- No structural markers detected
- Missing expected legal formatting

**Observable examples:**

```json
// HIGH confidence (Notice 9105 from CXIINo 76)
{
  "gazette_notice_no": "9105",
  "gazette_notice_full_text": "GAZETTE NOTICE NO. 9105\n\nTHE CONSTITUTION OF KENYA\n...\nIN EXERCISE of powers conferred by Regulation 6...\nDated the 2nd August, 2010.\n\nA. I. HASSAN,\nChairman,\nInterim Independent Electoral Commission.",
  "other_attributes": {
    "lines_after_header": 32,
    "char_span_start": 2135,
    "char_span_end": 3339
  }
}
// Confidence: 0.95 (has all markers, reasonable length, proper structure)

// LOW confidence (Notice "s" from CXIINo 76)
{
  "gazette_notice_no": "s",
  "gazette_notice_header": "Gazette Notice Nos. 8706, 8707...",
  "gazette_notice_full_text": "Gazette Notice Nos. 8706...to read 'A. I. HASSAN, Chairman'.\n\nDated the 3rd August, 2010...",
  "other_attributes": {
    "lines_after_header": 8,
    "char_span_start": 564,
    "char_span_end": 834
  }
}
// Confidence: 0.3 (no "GAZETTE NOTICE NO." start, references other notices)
```

---

### 3. Spatial Reading Order Confidence (`spatial_confidence`)

**Purpose:** Assess whether the spatial reordering algorithm successfully corrected two-column reading order.

**Signals for HIGH confidence (0.8-1.0):**
- No mid-sentence line breaks (line ends with punctuation or next line starts with capital)
- Smooth narrative flow (pronouns/conjunctions at expected positions)
- No repeated text chunks (which indicate column overlap errors)
- Consistent capitalization patterns

**Signals for MEDIUM confidence (0.4-0.7):**
- Some awkward line breaks but overall readable
- Minor punctuation oddities
- One or two suspicious transitions

**Signals for LOW confidence (0.0-0.3):**
- Multiple mid-sentence breaks without punctuation
- Repeated phrases (text appearing twice indicates column merge error)
- Random mid-sentence capitalization (suggests words from different columns merged)
- Numbers or list items out of sequence

**Detection patterns:**

```python
# Mid-sentence break pattern (LOW confidence signal)
Line: "The Commission hereby notifies"
Next: "conferred by section 38 the voters"
# Missing punctuation, lowercase start = likely column error

# Repeated chunk pattern (LOW confidence signal)
Text contains: "polling centre has been transferred"
Same text appears again 50 words later
# Indicates column overlap

# Good flow pattern (HIGH confidence signal)
Line: "Dated the 2nd August, 2010."
Next: "A. I. HASSAN,"
# Proper punctuation, capital start = good ordering
```

**Known issue reference:** See `docs/known-issues.md` section 1 (Two-column text interleaving) and section 2 (Mixed column layouts).

---

### 4. Boundary Detection Confidence (`boundary_confidence`)

**Purpose:** Assess whether notice start and end boundaries were correctly identified.

**Signals for HIGH confidence (0.8-1.0):**
- Notice starts with strict all-caps `GAZETTE NOTICE NO. <digits>` header (full-line match)
- Notice ends with complete sentence (punctuation present)
- Small or zero line gap to next notice (`char_span_end_line` close to next `char_span_start_line`)
- Reasonable span size relative to content

**Signals for MEDIUM confidence (0.4-0.7):**
- Starts with notice pattern but awkward header text
- Ends mid-sentence but may be legitimately continued on next page
- Moderate gap to next notice (<500 characters)

**Signals for LOW confidence (0.0-0.3):**
- Starts with "IN" or other mid-notice words (missed actual start)
- Very short span (<80 characters)
- Large gap to next notice (>1000 characters) suggesting missing content
- Ends abruptly without punctuation in obviously incomplete manner

**Observable examples:**

```json
// HIGH confidence boundary
{
  "gazette_notice_no": "9103",
  "gazette_notice_header": "GAZETTE NOTICE NO. 9103",
  "gazette_notice_full_text": "GAZETTE NOTICE NO. 9103\n\n...",
  "other_attributes": {
    "char_span_start": 36,
    "char_span_end": 564
  }
}
// Next notice starts at 564 (no gap)
// Confidence: 0.95

// LOW confidence boundary (starts mid-notice)
{
  "gazette_notice_no": "8756",
  "gazette_notice_header": "Gazette  Notice  No.  8756  of  2010 amend...",
  "gazette_notice_full_text": "Gazette  Notice  No.  8756  of  2010 amend and insert...",
  "other_attributes": {
    "char_span_start": 1245,
    "char_span_end": 2135
  }
}
// Missing "GAZETTE NOTICE NO." prefix -- this is a corrigendum reference
// Confidence: 0.4
```

**Known issue reference:** See `docs/known-issues.md` section 3 (Notices spanning multiple pages).

---

## Implemented JSON Surface

Every notice now carries these additive fields:

```json
"confidence_scores": {
  "notice_number": 0.0,
  "structure": 0.0,
  "spatial": 0.0,
  "boundary": 0.0,
  "table": 0.0,
  "composite": 0.0,
  "composite_enhanced": 0.0
},
"confidence_reasons": ["<prefix>: <short reason>", ...],
"provenance": {
  "header_match": "strict | recovered | inferred | none",
  "line_span": [start_line, end_line],
  "raw_header_line": "the original line that matched",
  "stitched_from": [<notice_no>, ...]
}
```

Every PDF's top-level record carries:

```json
"document_confidence": {
  "layout": 0.0,
  "ocr_quality": 0.0,
  "notice_split": 0.0,
  "composite": 0.0,
  "mean_composite": 0.0,
  "min_composite": 0.0,
  "counts": {"high": 0, "medium": 0, "low": 0},
  "n_notices": 0,
  "ocr_reasons": [...]
},
"layout_info": {
  "layout_confidence": 0.0,
  "n_pages": 0,
  "pages": [{"page_no": 1, "mode": "two_col|one_col|full_width|hybrid", "bands": [...]}]
}
```

## Composite Confidence Score

**Overall confidence** combines the dimensions using weighted average:

```
base = notice_number × 0.30 + structure × 0.25 + spatial × 0.25 + boundary × 0.20

If a derived_table is present:
    composite = base × 0.85 + table × 0.15
Else:
    composite = base
```

`table` is folded in only when a notice produced a `derived_table`, so notices without tables are not unfairly penalized.

**Weight rationale:**
- **Notice number (30%):** Most critical for notice identification and downstream processing
- **Structure (25%):** Indicates completeness and usability of extracted content
- **Spatial (25%):** Affects readability and text quality for human review or NLP
- **Boundary (20%):** Important but some legitimate edge cases (multi-page notices, corrigenda)
- **Table (15%, conditional):** Rewards clean structured-table recovery; only applied when `derived_table` exists

### Table Confidence Signals

`score_table(derived_table)` is 1.0 with no deductions when no table is present. When a `derived_table` exists:

- **HIGH (0.8-1.0):** Rows are sequentially numbered, name/position cell lengths are consistent, and no `repairs` were needed.
- **MEDIUM (0.5-0.7):** Some merged-row repairs applied (e.g. `625 626` split into two rows), or minor serial-number jumps.
- **LOW (0.0-0.4):** Many repairs, many non-sequential jumps, or cells with dramatically different lengths suggesting unrepaired merges.

**Optional LLM enhancement:** For notices scoring below 0.7, an LLM semantic check (see Option 4) can provide a fifth dimension (`llm_semantic`) that catches coherence/completeness issues invisible to rule-based scoring. The enhanced composite blends rule-based and LLM scores.

**Confidence score ranges:**
- **0.80-1.00:** High confidence -- likely correct, low priority for manual review
- **0.50-0.79:** Medium confidence -- possible issues, spot-check recommended
- **0.00-0.49:** Low confidence -- likely errors, requires manual review

---

## Implementation Strategy

### Option 1: Integrate into Pipeline (Recommended)

Modify `split_gazette_notices()` function in the notebook to calculate and include confidence scores in output JSON:

```python
def split_gazette_notices(full_text: str) -> list[dict[str, Any]]:
    # ... existing splitting logic (strict all-caps header regex) ...
    
    for bi, (start_idx, num) in enumerate(boundaries):
        # ... existing extraction with title/body segmentation ...
        
        # Calculate confidence scores using new structured fields
        notice_no_conf = score_notice_number_confidence(num)
        structure_conf = score_structural_confidence(
            title_lines, body_segments, derived_table
        )
        spatial_conf = score_spatial_confidence(body_text)
        boundary_conf = score_boundary_confidence(header_line, body_text, ...)
        
        composite_conf = calculate_composite_confidence(
            notice_no_conf, structure_conf, spatial_conf, boundary_conf
        )
        
        notices.append({
            "gazette_notice_no": num,
            "gazette_notice_header": header_line,
            "title_lines": title_lines,
            "gazette_notice_full_text": body_text,
            "body_segments": segments,
            "derived_table": derived,  # optional
            "confidence_scores": {
                "notice_number": notice_no_conf,
                "structure": structure_conf,
                "spatial": spatial_conf,
                "boundary": boundary_conf,
                "composite": composite_conf
            },
            "other_attributes": { ... }
        })
```

**Pros:** Every new extraction includes confidence scores automatically. No separate processing step.

**Cons:** Requires reprocessing all existing JSON files to add scores retroactively.

---

### Option 2: Separate Validation Module

Create standalone `validate_gazette_json.py` script that:
1. Reads existing `*_gazette_spatial.json` files
2. Calculates confidence scores for each notice
3. Outputs validation report with flagged low-confidence notices
4. Optionally updates JSON files with confidence scores

**Pros:** Can analyze existing output without rerunning extraction pipeline. Easier to iterate on scoring algorithms.

**Cons:** Separate step in workflow. May get out of sync with pipeline.

---

### Option 3: Confidence Report Dashboard

Build HTML report generator that:
- Scans all JSON files in `output/`
- Calculates confidence scores
- Generates summary statistics by PDF, by notice type
- Creates sortable table of low-confidence notices for review
- Highlights specific quality issues per dimension

**Pros:** Best for human review workflow. Visual prioritization of review tasks.

**Cons:** Most development effort. Requires HTML/JavaScript or notebook dashboard.

---

### Option 4: LLM-Enhanced Validation (Recommended Hybrid)

Use a lightweight LLM (GPT-4o-mini, Claude Haiku, Gemini Flash) as a second-pass validator for notices that score below a threshold (e.g., composite < 0.7). The LLM can detect semantic issues that rule-based heuristics miss.

**What LLM validation catches:**
- **Scrambled text** — "The Commission hereby notifies conferred by section 38 the voters" (column merge error)
- **Merged notices** — Body text suddenly switches topic mid-paragraph
- **Truncated content** — Notice ends abruptly without signature/date
- **OCR garbage** — Strings of non-words or garbled characters
- **Legal incoherence** — "IN EXERCISE of powers... IT IS NOTIFIED that the following have been appointed" but no list follows

**Suggested prompt structure:**

```
You are validating an extracted Kenya Gazette notice. Check for:
1. Text coherence — Does the text flow naturally or appear scrambled?
2. Completeness — Does the notice have a proper ending (date, signature)?
3. Single notice — Does this appear to be one notice or multiple merged?
4. Legal structure — Does it follow gazette notice patterns (preamble, body, closing)?

Notice:
---
{gazette_notice_full_text}
---

Respond with JSON:
{
  "coherence_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "single_notice_score": 0.0-1.0,
  "legal_structure_score": 0.0-1.0,
  "issues": ["list of specific problems found"],
  "needs_human_review": true/false
}
```

**Cost-efficient workflow:**

1. Run rule-based scoring on all notices (free, fast)
2. Filter to notices with `composite_confidence < 0.7` (~10-20% typically)
3. Send only those to LLM for semantic validation (~$0.001-0.003 per notice with GPT-4o-mini)
4. Merge LLM scores into final confidence; flag `needs_human_review` for manual queue

**Integration code sketch:**

```python
import openai  # or anthropic, google.generativeai

def llm_validate_notice(notice: dict, model: str = "gpt-4o-mini") -> dict:
    prompt = f"""You are validating an extracted Kenya Gazette notice...
    
Notice:
---
{notice["gazette_notice_full_text"][:4000]}  # truncate for token limits
---

Respond with JSON only."""

    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=200,
    )
    return json.loads(response.choices[0].message.content)


def enhance_confidence_with_llm(notices: list[dict], threshold: float = 0.7) -> list[dict]:
    for notice in notices:
        if notice["confidence_scores"]["composite"] < threshold:
            llm_result = llm_validate_notice(notice)
            notice["llm_validation"] = llm_result
            # Blend LLM scores into composite
            llm_avg = sum([
                llm_result["coherence_score"],
                llm_result["completeness_score"],
                llm_result["single_notice_score"],
                llm_result["legal_structure_score"],
            ]) / 4
            notice["confidence_scores"]["llm_semantic"] = llm_avg
            notice["confidence_scores"]["composite_enhanced"] = (
                notice["confidence_scores"]["composite"] * 0.6 + llm_avg * 0.4
            )
    return notices
```

**Pros:** Catches semantic errors invisible to regex. Low cost when filtered to low-confidence subset. Can explain *why* a notice is problematic.

**Cons:** Requires API key and network. Adds latency. LLM may hallucinate issues on valid notices (mitigate with temperature=0).

**Model recommendations:**
- **GPT-4o-mini** — Best balance of cost/quality for structured validation (~$0.15/1M input tokens)
- **Claude 3.5 Haiku** — Fast, good at following JSON schema (~$0.25/1M input)
- **Gemini 1.5 Flash** — Cheapest for high volume (~$0.075/1M input)

---

## Validation and Tuning

Two complementary tools live at the bottom of `gazette_docling_pipeline_spatial.ipynb` (the "Calibration and regression" section). They answer different questions and run on different cadences.

### Calibration -- "do I trust the scores?"

Use after every meaningful change to the scoring rules (new heuristic, changed weight, new regex). It tells you, per band, how often a "high confidence" label is actually correct and how often a "low confidence" label is actually wrong. Requires a human to read notices.

| Step | Who | Action |
| --- | --- | --- |
| 1. Generate sample | code | `sample_for_calibration()` walks `output/`, buckets every scored notice into bands (`high` >= 0.80, `medium` >= 0.50, `low` < 0.50), and draws up to 20 per band into `tests/calibration_sample.yaml`. Reproducible via `seed=42`. |
| 2. Hand-label | **you** | Open the YAML file. For each entry, find the notice in `output/<pdf>/<pdf>_spatial_markdown.md` (or the JSON), read it, and set `is_correct: true` or `is_correct: false`. Skip entries you cannot judge -- leave `null`. Even ~30 labels gives meaningful numbers. |
| 3. Score it | code | `score_calibration()` parses the YAML, prints a per-band table (n, correct, wrong, precision), and emits two specific warnings: high-band precision below 85% (scorer too generous) or low-band precision above 30% (scorer too strict). |
| 4. Decide | **you** | If a warning fires, edit weights in cell 6 (`composite_confidence` and the individual `score_*` functions), re-process the canonical PDFs, re-generate the sample, re-label, re-score. Iterate until precision stabilises. |

Notes:

- `sample_for_calibration()` **overwrites** the YAML on each call. The notebook keeps the call commented out so a top-to-bottom run does not erase your labels.
- The minimal YAML parser (`_parse_calibration_yaml`) only understands the shape `sample_for_calibration` writes -- no need for PyYAML. Keep edits to the existing fields.

### Regression -- "did I just break the scores?"

Use after every code change that touches scoring, splitting, OCR, or layout. It is a 30-second sanity check, no human labelling involved.

| Step | Who | Action |
| --- | --- | --- |
| 1. Capture baseline | **you**, once, when scores look good | Re-process the canonical PDFs through the pipeline, then run `update_regression_fixture()`. Writes `tests/expected_confidence.json` with mean composite, min composite, layout, OCR quality, and notice count for each canonical PDF. Re-run only when you intentionally accept a new baseline. |
| 2. Make a code change | **you** | Tune a regex, change a weight, fix a bug. Re-process the canonical PDFs so their JSON outputs reflect the new code. |
| 3. Compare | code | `check_regression()` recomputes mean composite per canonical PDF and prints `OK` or `REGRESSION` lines. Returns `True` if every PDF is within `tolerance` (default 0.05 = 5 percentage points), `False` otherwise -- handy if you wire it into CI. |
| 4. React | **you** | All `OK` -> ship. Any `REGRESSION` -> open the offending PDF's JSON, find notices whose composite dropped, read their `confidence_reasons` for clues. Fix or revert. |

The canonical PDF list is defined in cell 24 as `CANONICAL_PDFS` -- a deliberately small set chosen to cover clean, dense, table-heavy, and pre-2010 OCR cases. Add to the list to extend coverage; remove only if a PDF stops being representative.

---

## Known Limitations

1. **~~Corrigenda notices~~** *(Addressed)* Corrigenda are now extracted separately into a `corrigenda` array with structured fields (`referenced_notice_no`, `referenced_year`, `error_text`, `correction_text`). They no longer pollute the `gazette_notices` array.

2. **Multi-page notices:** Boundary confidence may be artificially low for notices that legitimately span pages and end mid-sentence.

3. **Table-heavy notices:** Structural markers may be sparse in notices that are mostly tables (engineer registration lists, land titles, GPS coordinates).

4. **Pre-2010 gazettes:** Older PDFs (different formatting, OCR quality) may need adjusted scoring parameters. See `output/Kenya Gazette Vol CIINo 83 - pre 2010/` for examples.

5. **~~False positives on "GAZETTE NOTICE"~~** *(Addressed)* The strict full-line, all-caps header regex now rejects inline references like "IN Gazette Notice No. 8756 of 2010, amend..." which are mixed-case and mid-sentence. Only standalone headers trigger notice splits.

---

## Next Steps

- [x] ~~Decide on implementation strategy~~ — Option 1 (pipeline integration) + Option 4 (LLM second pass) implemented in `gazette_docling_pipeline_spatial.ipynb`.
- [x] ~~Implement rule-based confidence scoring functions~~ — `score_notice_number`, `score_structure`, `score_spatial`, `score_boundary`, `score_table`, `composite_confidence`.
- [x] ~~Integrate into production pipeline~~ — `GazettePipeline.process_pdf` calls `score_notices` and `compute_document_confidence`.
- [x] ~~Document special cases (corrigenda, tables, multi-page)~~ — Corrigenda false positives addressed via strict header regex; table recovery added via `derived_table`; multi-page stitching post-process (`_stitch_multipage_notices`).
- [x] ~~Prototype LLM validation on low-confidence notices~~ — `llm_validate_notice` and `enhance_with_llm` with on-disk cache under `.llm_cache/`, gated by `ENABLE_LLM_VALIDATION` flag.
- [x] ~~Build calibration tooling~~ -- `sample_for_calibration()` and `score_calibration()` implemented; sample stub at `tests/calibration_sample.yaml`.
- [x] ~~Hand-label the existing calibration sample~~ -- **2026-04-20:** Labeled 26 notices (20 high, 6 medium). High-band precision 100% (exceeds 85% target). Medium-band 33.3% (expected). Scoring well-calibrated, no weight tuning needed. Re-run with new data as corpus evolves.
- [x] ~~Build regression tooling~~ -- `update_regression_fixture()` writes `tests/expected_confidence.json`; `check_regression()` compares current mean composite against baseline.
- [ ] Capture an accepted regression baseline once scoring is stable, then wire `check_regression()` into CI.
- [ ] Benchmark LLM accuracy vs manual review on 50-notice sample.
- [ ] Evaluate cost/latency tradeoffs for GPT-4o-mini vs Haiku vs Flash.

---

## References

- `docs/known-issues.md` -- Documents observed extraction errors
- `gazette_docling_pipeline_spatial.ipynb` -- Current extraction pipeline
- `output/*/‌*_gazette_spatial.json` -- Extracted notice JSON with structural metadata
