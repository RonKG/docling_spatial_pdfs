# F11 Spec: Masthead Parser

## 1. What to Build

Parse the Kenya Gazette masthead (title block) to extract identity fields: Volume (Roman numeral), Issue Number, Publication Date, and Supplement Number. Return a dict with these fields, normalized per contract rules. Unparseable fields become `None` — never invented, never raises.

This populates `GazetteIssue` fields per `library-contract-v1.md` Section 3. If all fields fail, degraded-mode triggers fallback ID and warning per Section 2.

---

## 2. Interface Contract

| Aspect | Specification |
|--------|---------------|
| **Function** | `parse_masthead(text: str) -> dict` |
| **Input** | First ~30 lines of `plain_spatial` string from `GazettePipeline.process_pdf` |
| **Output** | `{"volume": str \| None, "issue_no": int \| None, "publication_date": str \| None, "supplement_no": int \| None}` |
| **Error Rule** | Unparseable field → `None`. Never invent. Never raise. |

**Field Details:**
- `volume`: Roman numeral verbatim (e.g., "CXXIV"), or `None`
- `issue_no`: Integer parsed from "No. X" pattern, or `None`
- `publication_date`: ISO "YYYY-MM-DD" (e.g., "2022-12-23"), or `None`
- `supplement_no`: Integer if "Supplement No. X" or "-SX" detected, else `None`

**Integration:** Called in `process_pdf` after `plain_spatial` generated. Populates `GazetteIssue` model: `volume`, `issue_no`, `publication_date`, `supplement_no`, `masthead_text` (raw), `parse_confidence` (1.0=all good, 0.5=partial, 0.0=all None).

---

## 3. Test Cases

| ID | Scenario | Source File | Expected Result |
|----|----------|-------------|-----------------|
| T1 | Modern clean | `output/Kenya Gazette Vol CXXIVNo 282/Kenya Gazette Vol CXXIVNo 282_spatial.txt` | `{"volume": "CXXIV", "issue_no": 282, "publication_date": "2022-12-23", "supplement_no": None}` |
| T2 | Pre-2010 OCR degraded | `output/Kenya Gazette Vol CVIINo 90 - pre 2010/Kenya Gazette Vol CVIINo 90_spatial.txt` | `{"volume": "CVII", "issue_no": 90, "publication_date": "2005-12-30", "supplement_no": None}` |
| T3 | Special issue / weird layout | `output/Kenya Gazette Vol CXXVIINo 111/Kenya Gazette Vol CXXVIINo 111_spatial.txt` | `{"volume": "CXXVII", "issue_no": 111, "publication_date": "2025-06-03", "supplement_no": None}` |
| T4 | Boring baseline | `output/Kenya Gazette Vol CXXVIINo 63/Kenya Gazette Vol CXXVIINo 63_spatial.txt` | `{"volume": "CXXVII", "issue_no": 63, "publication_date": "2025-03-28", "supplement_no": None}` |
| T5 | Garbled / unreadable | (any output file, manually corrupt first 30 lines) | `{"volume": None, "issue_no": None, "publication_date": None, "supplement_no": None}` |

**Patterns to detect:**
- Volume: `Vol. [ROMAN]-` or `Vol. [ROMAN] No.` or standalone line with Roman numeral
- Issue: `No. [NUMBER]` (decimal integer)
- Date: `[CITY], [DAY] [Month], [YEAR]` → normalize to ISO (strip ordinals like "23rd" → "23")
- Supplement: `Supplement No. [N]` or `-S[N]` suffix on volume line

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F11: Masthead Parser**

Read this spec: `specs/F11-masthead-parser.md`

Implement in location: `gazette_docling_pipeline_spatial.ipynb` (new cell, before notice splitting)

Requirements:
1. Write `parse_masthead(text: str) -> dict` per Interface Contract (Section 2)
2. Handle all 5 test cases (Section 3) — verify by running on actual files in `output/`
3. Date normalization: strip ordinals ("23rd" → "23"), output "YYYY-MM-DD"
4. Roman numerals: preserve as string, no validation needed
5. Never raise. Unparseable → `None` for that field.
6. After implementation, run `check_regression()` — must pass
7. Update PROGRESS.md: F11 status "⬜ Next" → "⬜ In Progress" → "✅ Complete"
8. Return final status: PASS (all tests pass) or FAIL (what broke)

**Build Report Format:**
```markdown
# Build Report: F11
## Implementation
- Location: notebook cell after line ~1729
- Lines: ~50-80 lines of Python

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 | PASS/FAIL | |
| T2 | PASS/FAIL | |
| T3 | PASS/FAIL | |
| T4 | PASS/FAIL | |
| T5 | PASS/FAIL | |

## Regression
Status: PASS/FAIL

## Final Status: PASS/FAIL
```

---
