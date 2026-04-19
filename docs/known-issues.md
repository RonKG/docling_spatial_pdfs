# Known Issues -- Kenya Gazette PDF Extraction

Issues observed across Kenya Gazette PDFs when extracting text, tables, and notices. These are document-level problems independent of any specific extraction tool.

Each item notes whether it is **(mitigated)** by the confidence + structural passes in `gazette_docling_pipeline_spatial.ipynb`, **(flagged)** when extraction still happens but confidence is capped so downstream consumers can filter, or **(open)** when no mitigation is in place yet. See also `docs/data-quality-confidence-scoring.md` for the scoring contract.

---

## 1. Two-column text interleaving *(flagged)*

Most Gazette pages use a two-column layout. Extractors often read across both columns left-to-right instead of top-to-bottom within each column, producing interleaved text from unrelated notices.

*Mitigation:* `reorder_by_spatial_position_with_confidence` emits a per-page `layout_confidence`. Pages classified as `mixed` lower the document-level `layout` score, which feeds the composite.

**Example:** Page 3803 of Vol CXI No. 100 -- Notice 14096 in the left column and Notice 14097 in the right column are stitched together as alternating lines.

**Impact:** Every notice on a two-column page can be corrupted. Downstream splitting on "GAZETTE NOTICE NO." produces wrong boundaries and mixed content.

---

## 2. Mixed column layouts on a single page *(mitigated)*

Pages frequently alternate between column modes: full-width header, then two columns, then a full-width signature block, then two columns again. Some pages do this multiple times.

*Mitigation:* band-level clustering in `_cluster_y_bands` plus per-band classification via `_classify_band` surfaces hybrid pages as `mode: "hybrid (...)"` and lowers their `layout_confidence`.

**Example:** A page starts with a full-width act title ("THE CAPITAL MARKETS ACT"), followed by two columns of notices, then a full-width signature block ("STELLA KILONZO, Dated the 9th December"), then two more columns of notices below.

**Impact:** Any approach that classifies an entire page as "2-column" or "1-column" will fail on these hybrid pages. Column detection must be local, not global.

---

## 3. Notices spanning multiple pages *(mitigated)*

A gazette notice commonly starts mid-page (even mid-column) and continues onto the next page, sometimes spanning 2-3 pages.

*Mitigation:* `_stitch_multipage_notices` merges a trailing recovered-header block into the preceding notice when that notice lacks terminal punctuation. The merged notice records `provenance.stitched_from` so the join is auditable.

**Example:** Notice 14096 begins near the bottom of the left column on page 3803 and continues at the top of the right column. Multi-page notices are even more common with probate lists, land registration tables, and Environmental Impact Assessment notices.

**Impact:** Page-by-page extraction that treats each page independently will split a single notice into fragments at page boundaries.

---

## 4. Tables in multiple formats

Kenya Gazette PDFs contain several visually distinct table types:

- **Bordered tables** -- Cells with visible borders that extractors can detect structurally (GPS coordinate tables, financial statements, registered engineer lists).
- **Tab-aligned pseudo-tables** -- Text formatted with tabs/spaces to look columnar but stored as plain text blocks (appointment lists, name-and-ID lists in probate notices).
- **Impact/mitigation matrices** -- Tables with nested bullet points inside cells.
- **Multi-row headers** -- Some tables have 3+ header rows (GPS coordinate tables with separate rows for column group labels, column names, and units).

**Example from Vol CXXVII No. 63:** The Registered Engineers table (1400+ rows) has columns for serial number, registration number, name, postal address, and qualifications. Extraction frequently merges adjacent rows, producing entries like "625 626 | A4830 | Eng. Machio, Michael Malingu Eng. Machoka, Daniel Areba" where two separate engineers are fused into one row.

**Impact:** Pseudo-tables are invisible to structure-aware extractors and get treated as flowing text. Bordered tables have row-merging and column-alignment errors.

---

## 5. Tables spanning multiple pages

Tables frequently start mid-page (sometimes mid-column) and continue onto the next page, potentially switching from a two-column to a single-column layout at the page break.

**Example:** The Registered Engineers table in Vol CXXVII No. 63 spans approximately 35 pages. Column headers are repeated on continuation pages but there is no explicit "continued" marker in the PDF.

**Impact:** Page-based extraction treats each page's table fragment separately. Merging fragments requires detecting repeated headers and matching column alignment across pages.

---

## 6. Page furniture leaking into notice text *(mitigated)*

Headers ("THE KENYA GAZETTE"), footers ("Published by Authority of the Republic of Kenya"), page numbers, and price lines ("Price Sh. 50") appear on every page. These elements sometimes land in the middle of extracted notice text instead of being filtered out.

*Mitigation:* `RUNNING_HEADER_RES` was extended to cover "Published by Authority", "Price Sh.", "NAIROBI, <date>", the Vol/No banner, and the GPO registration line. `_strip_running_headers` filters these out wherever they appear in a body, not just at edges.

**Example from Vol CXII No. 76:** Notice 9104 contains the line "Published by Authority of the Republic of Kenya" and "Price Sh. 50" injected between the act title and the body of the notice.

**Impact:** Downstream notice splitting and entity extraction must ignore or strip these insertions, but they can appear at unpredictable positions.

---

## 7. OCR artifacts in scanned (pre-2010) PDFs *(flagged)*

Gazettes before approximately 2010 (Vol CII, CVII) are scanned images rather than digital text. OCR produces garbled text with character-level errors.

*Mitigation:* `_estimate_ocr_quality` sets `document_confidence.ocr_quality` from letter ratio, short-element ratio, and text density. When the score is below 0.5 every notice has its `boundary` capped at 0.6, so the composite reflects the unreliable source.

**Example from Vol CII No. 83:** The first page extracts as fragments like "V I CH- N.. 8 3", "Pr i c : ih. 40", and single characters ("t-", "/", "N", ")") instead of readable text.

**Impact:** Pre-2010 Gazettes require OCR, and the OCR quality is poor enough that notice detection regex ("GAZETTE NOTICE NO.") may fail entirely. These documents need a different extraction strategy.

---

## 8. OCR artifacts in digital PDFs *(mitigated)*

Even post-2010 digital PDFs occasionally produce OCR-like artifacts where characters or punctuation are misplaced.

*Mitigation:* `RECOVERED_HEAD_RE` matches notice headers embedded in noisy or pipe-separated lines. Recovered boundaries set `provenance.header_match = "recovered"` and boundary confidence is capped at 0.6.

**Example:** "GAZETTE NOTICE. NO. 14190" -- a spurious period between "NOTICE" and "NO" in Vol CXI No. 100. This breaks pattern matching that expects "GAZETTE NOTICE NO."

**Impact:** Notice-splitting regex must account for variant punctuation. Other subtle artifacts (extra spaces, missing hyphens) can affect entity extraction.

---

## 9. Stray image artifacts

The Kenya coat of arms and other decorative elements at the top of pages produce stray text characters when extracted.

**Example:** Single characters like "H", "M", or "> *" appear in the extracted text from the coat of arms image on title pages.

**Impact:** These fragments contaminate the beginning of page text and can confuse column detection (they have narrow bounding boxes that look like left-column content).

---

## 10. Headers misclassified by column position *(flagged)*

Narrow text elements (notice headers, section titles) positioned near the center of the page can be ambiguous -- they could belong to the right column or be a centered full-width element.

*Mitigation:* `_classify_band` counts ambiguous elements and marks bands with >30% ambiguity as `mixed`, dragging the page's layout confidence down.

**Example:** "GAZETTE NOTICE NO. 14097" has bbox left=309, right=404 on a 595-point-wide page. Its center (357) is close to the page midpoint (298), causing it to be classified as "centered" instead of "right column."

**Impact:** Misclassified headers appear in the wrong position in the reading order, breaking the continuity of the notice they belong to.

---

## 11. Table cell content merging *(mitigated)*

In large bordered tables, adjacent rows or columns are often merged during extraction, producing composite entries.

*Mitigation:* `_repair_merged_rows` in `_try_parse_s_no_table` detects adjacent serial numbers (`625 626` where `b - a == 1`) and splits the row. Repairs are recorded on the `derived_table.repairs` list and reflected in `score_table`.

**Example from Vol CXXVII No. 63, Registered Engineers table:**
- Row "625 626" merges serial numbers from two separate engineers
- "Eng. Macharia, Joseph Gituhia Eng. Macharia, Paul Gacheru" -- two distinct names fused into one cell
- "P.O. Box 12776 - 00100 Nairobi P.O. Box 70421-00400 Nairobi" -- two addresses in one cell

**Impact:** Entity extraction (names, addresses, registration numbers) produces incorrect records when rows are merged. Requires post-extraction splitting logic.

---

## 12. Non-contiguous notice numbering

Notice numbers within a single Gazette are not always sequential. Backward jumps and gaps are common.

**Example from Vol CXI No. 100:** Notice range 12337 to 12635, but the sequence is non-contiguous with backward jumps (e.g., 12612 followed by 12337 later in the document).

**Impact:** Cannot use sequential notice numbers to validate extraction completeness or detect missing notices without understanding the non-linear numbering pattern.

---

## 13. Signature blocks and dates contaminating columns *(flagged)*

Signature lines ("STELLA KILONZO"), dates ("Dated the 9th December"), and titles ("Chairman") at the bottom of notices are often left-aligned or right-aligned in the full-width zone below the two-column area. These get incorrectly assigned to a column.

*Mitigation:* band-level detection isolates full-width zones from column bands; ambiguous bottoms are classified as `mixed` and surface in `layout_confidence`.

**Example:** On page 3820 of Vol CXI No. 100, a left-aligned date (y=116.8) and right-aligned signature (y=93.8) in the full-width zone drag both column bottoms down, making column detection ineffective.

**Impact:** Column boundary detection algorithms that rely on the lowest element in each column will over-extend the column zone, misclassifying full-width bottom elements.

---

## 14. Multi-column financial tables merged into pipe-separated text *(mitigated)*

Large financial tables spanning both columns (receipts, expenditure statements) are extracted by Docling as pipe-separated text rows instead of proper table structures. Notice headers within these tables get embedded mid-line.

*Mitigation:* `RECOVERED_HEAD_RE` and `_find_recovered_boundaries` scan large gaps between strict headers for `GAZETTE NOTICE NO. <digits>` embedded in noisy lines, so these notices are no longer dropped. Their boundary confidence is capped at 0.6.

**Example from Vol CXI No. 103, page 3508:** Notice 13174 (OFFICE OF THE DEPUTY PRIME MINISTER financial statement) and Notice 13175 (Geologists Registration Act appointment) appear as:
```
GAZETTE NOTICE NO. 13174 | GAZETTE NOTICE NO. 13174 | GAZETTE NOTICE NO. 13174
...
*G. N. No. 12636 of 2009 is amended. GAZETTE NOTICE NO. 13175 THE GEOLOGISTS...
```

The notice header is repeated across columns (pipe-separated) or merged mid-line with other content.

**Impact:** Strict full-line notice header matching (`^GAZETTE NOTICE NO. \d+$`) fails because the line contains `|` separators or text before/after the header. These notices are missed entirely in the extraction output.
