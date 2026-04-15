# Kenya Gazette Vol. CXXVII No. 266 — notice parsing reference

This document ties together the source materials used for extracting and structuring Kenya Gazette notices.

## Referenced files

| Role | File |
|------|------|
| Original publication (PDF) | [Kenya Gazette Vol CXXVIINo 266 (3).pdf](./Kenya%20Gazette%20Vol%20CXXVIINo%20266%20(3).pdf) |
| Plain text export (copy-paste from PDF) | [Kenya Gazette Vol CXXVIINo 266 (3).pdf.txt](./Kenya%20Gazette%20Vol%20CXXVIINo%20266%20(3).pdf.txt) |
| Search hit log (line numbers in the `.txt`) | [line number.txt](./line%20number.txt) |

## What each file is for

- **PDF** — The authoritative printed layout; use when verifying page breaks, tables, and typography.
- **`.pdf.txt`** — The working corpus for line-based parsing: notice boundaries, headings, body text, and table fragments after PDF-to-text conversion.
- **`line number.txt`** — A record of searching the `.txt` for the string `GAZETTE NOTICE NO.` (179 hits in the saved search). That count mixes **true notice headers** (full-line uppercase, for example line 119) with **in-text references** (for example lines 114, 117, 222), which are not separate notices.

## Related outputs (this folder)

- `parse_gazette_notices.py` — Splits the `.txt` on strict notice-header lines and emits JSON.
- `gazette_notices.json` — Structured output: preamble, 176 notices numbered 18996–19171, optional `derived_table` where patterns match.

## Header rule used for splitting

Treat a new notice only when a line matches a full-line heading such as `GAZETTE NOTICE NO. <number>` (and the OCR variant `GAZETE NOTICE NO. <number>`). Do not split on mixed-case phrases like `Gazette Notice No.` inside sentences.
