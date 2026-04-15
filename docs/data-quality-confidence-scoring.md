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

## Composite Confidence Score

**Overall confidence** combines the four dimensions using weighted average:

```
composite_confidence = 
  (notice_no_confidence × 0.30) +
  (structure_confidence × 0.25) +
  (spatial_confidence × 0.25) +
  (boundary_confidence × 0.20)
```

**Weight rationale:**
- **Notice number (30%):** Most critical for notice identification and downstream processing
- **Structure (25%):** Indicates completeness and usability of extracted content
- **Spatial (25%):** Affects readability and text quality for human review or NLP
- **Boundary (20%):** Important but some legitimate edge cases (multi-page notices, corrigenda)

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

## Validation and Tuning

To validate confidence scores correlate with actual errors:

1. **Sample validation:** Manually review 50-100 notices spanning confidence ranges 0.0-1.0
2. **Error correlation:** Check if low-confidence notices actually have errors
3. **False positive rate:** Check if high-confidence notices are indeed correct
4. **Threshold tuning:** Adjust confidence thresholds and dimension weights based on findings
5. **Pattern refinement:** Add new signal patterns discovered during manual review

**Suggested validation process:**

```
1. Run confidence scoring on existing output
2. Extract 20 notices each from:
   - confidence 0.0-0.3 (expect high error rate)
   - confidence 0.3-0.5 (expect medium error rate)
   - confidence 0.5-0.7 (expect low error rate)
   - confidence 0.7-1.0 (expect very low error rate)
3. Manually review each notice for actual errors
4. Calculate precision/recall for each confidence band
5. Adjust weights and thresholds to optimize for workflow
```

---

## Known Limitations

1. **~~Corrigenda notices~~** *(Addressed)* Corrigenda are now extracted separately into a `corrigenda` array with structured fields (`referenced_notice_no`, `referenced_year`, `error_text`, `correction_text`). They no longer pollute the `gazette_notices` array.

2. **Multi-page notices:** Boundary confidence may be artificially low for notices that legitimately span pages and end mid-sentence.

3. **Table-heavy notices:** Structural markers may be sparse in notices that are mostly tables (engineer registration lists, land titles, GPS coordinates).

4. **Pre-2010 gazettes:** Older PDFs (different formatting, OCR quality) may need adjusted scoring parameters. See `output/Kenya Gazette Vol CIINo 83 - pre 2010/` for examples.

5. **~~False positives on "GAZETTE NOTICE"~~** *(Addressed)* The strict full-line, all-caps header regex now rejects inline references like "IN Gazette Notice No. 8756 of 2010, amend..." which are mixed-case and mid-sentence. Only standalone headers trigger notice splits.

---

## Next Steps

- [ ] Decide on implementation strategy (Option 1, 2, or 3)
- [ ] Implement confidence scoring functions with test cases
- [ ] Run on sample of existing output (10-20 PDFs)
- [ ] Perform manual validation on confidence score accuracy
- [ ] Tune weights and thresholds based on validation findings
- [x] ~~Document special cases (corrigenda, tables, multi-page)~~ — Corrigenda false positives addressed via strict header regex; table recovery added via `derived_table`
- [ ] Integrate into production pipeline
- [ ] Create review workflow for low-confidence notices

---

## References

- `docs/known-issues.md` -- Documents observed extraction errors
- `gazette_docling_pipeline_spatial.ipynb` -- Current extraction pipeline
- `output/*/‌*_gazette_spatial.json` -- Extracted notice JSON with structural metadata
