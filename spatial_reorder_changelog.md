# Spatial Reorder — Bug Log and Changelog

Reference document for issues found and fixes applied to the spatial reading-order
post-processor in `gazette_docling_pipeline_spatial.ipynb`.

The original, unmodified pipeline is preserved in `gazette_docling_pipeline.ipynb`.

---

## Issue 1: Two-column notice split across columns (page 3803)

**Reported:** 2026-04-11  
**Page:** 3803 (Docling page_no 9)  
**Notices affected:** 14096, 14097, 14098

**Problem:**  
Notice 14096 starts at the bottom of the left column and continues at the top of
the right column. Docling's internal reading-order predictor reads left column
partially, jumps to the right column continuation, and labels it as a separate
notice (14098). The real 14098 (PROBATE AND ADMINISTRATION at the bottom of the
page) gets absorbed into 14097.

**Root cause:**  
Docling's `ReadingOrderPredictor` uses spatial heuristics that don't reliably
handle text flowing from the bottom of one column to the top of the next.

**Fix:**  
Created `reorder_by_spatial_position()` — a post-processor that uses bounding-box
coordinates from `doc.export_to_dict()` to reconstruct reading order per page:
left column top-to-bottom, then right column top-to-bottom, then full-width zone.

**Files changed:** `gazette_docling_pipeline_spatial.ipynb` (new notebook, cells 5-6)

---

## Issue 2: "GAZETTE NOTICE NO. 14097" header misclassified as centered

**Reported:** 2026-04-11  
**Page:** 3803 (Docling page_no 9)  
**Notice affected:** 14097

**Problem:**  
The 14097 header (bbox l=309.5, r=404.1, center_x=356.8) was classified as
"centered" because its center was within 80 points of the page midpoint (297.6)
and its width (94.6) was narrow. This put it in the full-width zone instead of
the right column, so it appeared after all column content.

**Root cause:**  
The "centered" heuristic was too broad — it didn't check whether the element was
entirely on one side of the page.

**Fix:**  
Added early classification checks: if `el.left >= mid_x` the element is
unambiguously in the right column; if `el.right <= mid_x` it is in the left
column. These checks run before the centered/full-width heuristics. Also
tightened the centered condition to require `spans_both` (element must actually
straddle the midpoint).

**Files changed:** `gazette_docling_pipeline_spatial.ipynb` cell 6 (`_reorder_page`)

---

## Issue 3: Stray signatures drag column boundaries too low (page 3820)

**Reported:** 2026-04-12  
**Page:** 3820 (Docling page_no 26)  
**Notices affected:** 14187, 14189

**Problem:**  
Notice 14187 was truncated — it lost its "And further take notice..." closing
paragraphs. Notice 14189 (THE CAPITAL MARKETS ACT, full-width at the bottom)
absorbed leftover text from the right column continuation.

The page has left-aligned ("Dated the 9th December" at y=116.8) and right-aligned
("STELLA KILONZO" at y=93.8) elements in the full-width zone at the bottom.
These dragged both column bottoms down to y~63-108, so the "shorter column"
heuristic (`col_zone_bottom`) was ineffective — almost nothing got reclassified.

**Root cause:**  
The original algorithm detected the column-zone boundary using
`max(min(left_bottoms), min(right_bottoms))`. Stray elements (dates, signatures)
positioned in the full-width zone but aligned to one side contaminated the
column-bottom calculation.

**Fix:**  
Replaced the "shorter column" heuristic with a **centered-element anchor**
approach. If the page has centered or full-width spanning body elements (like
"THE CAPITAL MARKETS ACT" at y=292.8), the topmost such element marks the
full-width zone boundary. Everything at or below that y-coordinate (plus a
50-point tolerance) is reclassified into the full-width group.

A guard ensures this only applies when the anchor is in the lower portion of the
page (below the median y of column candidates), preventing false triggers from
centered headings at the top of a page.

The old "shorter column" heuristic is kept as a fallback for pages with no
centered/full-width anchors.

**Files changed:** `gazette_docling_pipeline_spatial.ipynb` cell 6 (`_reorder_page`)

---

## Issue 4: Single-column pages scrambled (page 3821)

**Reported:** 2026-04-12  
**Page:** 3821 (Docling page_no 27)  
**Notice affected:** 14190 (THE ANTI-CORRUPTION AND ECONOMIC CRIMES ACT)

**Problem:**  
This is a full-page, single-column notice. Narrow headings like
"1. BACKGROUND" (l=57.5, r=141.9) were classified as left-column candidates,
while wider paragraphs (l=57.5, r=539.5) were classified as full-width. With no
right-column elements, the algorithm output all left elements first, then all
full-width elements — completely scrambling the interleaved headings and body
paragraphs.

**Root cause:**  
The two-column sorting logic (left col, then right col, then full-width) was
applied even when only one "column" existed.

**Fix:**  
Added an early return at the top of `_reorder_page`: if either `left_candidates`
or `right_candidates` is empty, the page is single-column. All body elements are
merged into one list and sorted top-to-bottom.

**Files changed:** `gazette_docling_pipeline_spatial.ipynb` cell 6 (`_reorder_page`)

---

## Issue 5: "GAZETTE NOTICE. NO. 14190" not detected by notice splitter

**Reported:** 2026-04-12  
**Notice affected:** 14190

**Problem:**  
Notice 14190 appeared as "GAZETTE NOTICE. NO. 14190" in the Docling output
(spurious period after NOTICE). The notice splitter regex expected
`GAZETTE\s+NOTICE\s+NO` but the period between NOTICE and the whitespace broke
the match. Notice 14190's entire text was absorbed into notice 14189.

**Root cause:**  
Docling OCR artifact — the period glyph between "NOTICE" and "NO" was
misrecognized or the PDF source itself had this formatting.

**Fix:**  
Added `\.?` after `NOTICE` in the `NOTICE_PATTERN` regex:

```
Before: r"(?is)\bGAZETTE\s+NOTICE\s+NO\.?\s*[:\-]?\s*([0-9A-Za-z\/\-]*)"
After:  r"(?is)\bGAZETTE\s+NOTICE\.?\s+NO\.?\s*[:\-]?\s*([0-9A-Za-z\/\-]*)"
```

This handles both "GAZETTE NOTICE NO." and "GAZETTE NOTICE. NO." variants.

**Files changed:** `gazette_docling_pipeline_spatial.ipynb` cell 4 (`NOTICE_PATTERN`)

---

## Summary of tunable constants

All defined in cell 6 of `gazette_docling_pipeline_spatial.ipynb`:

| Constant | Value | Purpose |
|---|---|---|
| `_FULLWIDTH_RATIO` | 0.55 | Min fraction of text-area width for an element to be classified as full-width |
| `_FW_TRANSITION_TOLERANCE` | 50.0 | Points above the first centered anchor to extend the full-width zone boundary |
| Centered detection: `abs(center_x - mid_x) < 80` | 80pt | Max horizontal offset from page center for an element to be considered centered |
| Centered detection: `width < text_area_width * 0.45` | 45% | Max width for a centered element (wider = full-width spanning) |
