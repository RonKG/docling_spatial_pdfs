# F12 Spec: Trailing Content Detector

## 1. What to Build

Detect and exclude non-notice trailing content that appears after the last valid gazette notice. Kenya Gazette issues often end with subscription pricing tables, advertisement rate cards, classified ads sections, index pages, or "Important Notice to Subscribers" boilerplate. The `split_gazette_notices` function currently treats everything from the last "GAZETTE NOTICE NO." marker to the end of the document as part of the final notice. This feature adds a post-processing step that identifies where the actual notice content ends and truncates the last notice before the trailing content begins, preventing pollution of the final notice's full_text with irrelevant material.

---

## 2. Interface Contract

| Aspect | Specification |
|--------|---------------|
| **Function** | `detect_trailing_content_cutoff(text: str, last_notice_start_line: int) -> int \| None` |
| **Input** | `text`: full plain text; `last_notice_start_line`: line index where last notice header appears |
| **Output** | Line index where trailing content begins, or `None` if no trailing content detected |
| **Error Rule** | Never raise. Return `None` if detection fails or patterns are ambiguous. |

| Aspect | Specification |
|--------|---------------|
| **Modified Function** | `split_gazette_notices()` — after building notices list, check last notice for trailing content |
| **Modification** | If trailing content detected, truncate `gazette_notice_full_text`, `body_segments`, and update `line_span` end index for last notice |
| **Preserve** | Original `gazette_notice_no`, `gazette_notice_header`, provenance metadata |

**Trailing Content Patterns to Detect (in priority order):**

1. **Subscription charges header**: Lines containing "SUBSCRIPTION AND ADVERTISEMENT CHARGES" or "SUBSCRIPTION CHARGES"
2. **Price table marker**: Lines starting with "Price: KSh." or similar pricing patterns repeated multiple times
3. **Important notice to subscribers**: "IMPORTANT NOTICE TO SUBSCRIBERS" or "IMPORTANT NOTICE TO SUBSCRIBERS TO THE KENYA GAZETTE"
4. **Government Printer signature block**: "Government Printer." signature at end (preceded by name like "MWENDA NJOKA")
5. **Index/contents marker**: "INDEX" or "CONTENTS" followed by page number columns when appearing after last notice
6. **Classified ads header**: "CLASSIFIED ADVERTISEMENT" or "CLASSIFIED ADS"

**Detection Rules:**
- Must appear after the last notice header (never cut mid-document)
- Must be below a minimum distance threshold (at least 20 lines after last notice start) to avoid false positives
- Multiple pattern matches increase confidence; single match is sufficient if unambiguous

---

## 3. Test Cases

| ID | Scenario | Source File | Expected Result |
|----|----------|-------------|-----------------|
| T1 | Happy path — pricing table at end | `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_spatial.txt` | Trailing content detected at line ~5828 ("SUBSCRIPTION AND ADVERTISEMENT CHARGES"). Last notice (15993) truncated before this point. Notice count unchanged. |
| T2 | Edge case — no trailing content | `output/Kenya Gazette Vol CXINo 100/Kenya Gazette Vol CXINo 100_spatial.txt` | No trailing content patterns found. Return original notices unchanged. |
| T3 | Degraded — ambiguous boundaries | Any file with corrupted end section | Return `None`, notices list unchanged, no exception raised. |
| T4 | Multiple trailing sections | Same as T1 source | Detects subscription section, excludes all content from that point forward (price tables, notice to subscribers, Government Printer signature). |

**Validation Steps:**
1. Run `split_gazette_notices` on T1 source before/after change
2. Verify last notice `gazette_notice_full_text` does not contain "SUBSCRIPTION AND ADVERTISEMENT CHARGES"
3. Verify `line_span[1]` end index reduced appropriately
4. Verify notice count unchanged (still 201 notices for CXXIVNo 282)
5. Run `check_regression()` — must pass

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F12: Trailing Content Detector**

Read this spec: `specs/F12-trailing-content-detector.md`

Implement in location: `split_gazette_notices` function in `gazette_docling_pipeline_spatial.ipynb`

Requirements:
1. Write helper function `detect_trailing_content_cutoff(text: str, last_notice_start_line: int) -> int | None` that scans for trailing content patterns (subscription charges, pricing tables, important notices, classified ads, index pages)
2. Modify `split_gazette_notices` to call this helper after building the notices list
3. If cutoff detected for last notice:
   - Truncate `gazette_notice_full_text` before cutoff point
   - Rebuild `body_segments` to exclude trailing content lines
   - Update `other_attributes["char_span_end_line"]` to cutoff line
   - Update `provenance["line_span"][1]` to cutoff line
4. Never raise. If detection ambiguous, return notices unchanged.
5. Run all 4 test cases (Section 3) — verify last notice content clean for T1, unchanged for T2/T3
6. After implementation, run `check_regression()` — must pass
7. Update PROGRESS.md: F12 status "⬜ Next" → "⬜ In Progress" → "✅ Complete"
8. Return final status: PASS (all tests pass) or FAIL (what broke)

**Build Report Format:**
```markdown
# Build Report: F12
## Implementation
- Location: `split_gazette_notices` function, notebook cell around line 569
- New helper: `detect_trailing_content_cutoff()` ~30-40 lines
- Modification: Post-processing loop after `_stitch_multipage_notices()`

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 | PASS/FAIL | Last notice truncated before subscription section |
| T2 | PASS/FAIL | No changes, notices unchanged |
| T3 | PASS/FAIL | Degraded handled gracefully |
| T4 | PASS/FAIL | Multiple trailing sections excluded |

## Regression
Status: PASS/FAIL

## Final Status: PASS/FAIL
```

---
