# F25 Spec: README Points at `parse_file`

## 1. What to Build

Replace the existing `README.md` with a library-focused quickstart that shows users how to install and use the `kenya-gazette-parser` package. This is the **final feature for 1.0** — all 5 Quality Gates are already cleared (F17-F24 delivered package skeleton, Pydantic models, validation, modules, public API, config, schema export, and install smoke tests). F25's job is to document the library for first-time users.

**Scope (locked):**
- **In scope**: Project title, one-line description, installation instructions (git URL + local dev install), quickstart code example showing `parse_file` returning `Envelope`, brief mention of `write_envelope`, brief mention of `GazetteConfig`, link to JSON Schema, Apache-2.0 license badge.
- **Out of scope**: Full API documentation (post-1.0 docs site), CLI documentation (F26), exhaustive model reference, performance tuning guide, contribution guidelines.
- **Invariants**: Gate 1-5 remain cleared; no code changes to `kenya_gazette_parser/`; the README must be accurate (code examples must actually work).

**Target audience**: A Python developer who wants to parse Kenya Gazette PDFs programmatically. They should be able to install, run the quickstart, and get structured output within 5 minutes of reading the README.

**File to edit**: `README.md` at repo root (replacing the F17 stub and older notebook-focused content).

---

## 2. Interface Contract

F25 creates no new code. It edits one file: `README.md`. The content must be accurate relative to the F24 API surface.

### 2a. Required sections in new README

| Section | Required content |
|---------|-----------------|
| **Title + badge row** | `# kenya-gazette-parser` + Apache-2.0 license badge (shields.io) + Python version badge (>=3.10) |
| **One-liner** | "Parse Kenya Gazette PDFs into structured, validated JSON envelopes." |
| **Installation** | Two methods: (1) `pip install git+https://github.com/rwahome/docling_spatial_pdfs.git` for users, (2) `pip install -e ".[dev]"` for contributors |
| **Quickstart** | Code block: `from kenya_gazette_parser import parse_file; env = parse_file("gazette.pdf")` then inspect `env.issue`, `env.notices`, `env.document_confidence` |
| **Writing output** | Code block showing `write_envelope(env, out_dir, pdf_path=pdf_path)` |
| **Configuration** | Brief mention of `GazetteConfig`, `Bundles`; link to `docs/library-contract-v1.md` section 5 for details |
| **JSON Schema** | Mention `get_envelope_schema()` and `validate_envelope_json()`; note schema file at `kenya_gazette_parser/schema/envelope.schema.json` |
| **License** | "Apache License 2.0. See [LICENSE](LICENSE)." |
| **Status** | "Alpha (0.1.0). API stable for 1.0; schema locked at `schema_version: '1.0'`." |

### 2b. Code examples must be runnable

The quickstart code example must work when copy-pasted by a user who has:
1. Installed the package via `pip install git+...`
2. A Kenya Gazette PDF file in their working directory

The example should show:
```python
from kenya_gazette_parser import parse_file, write_envelope

# Parse a PDF into a validated Envelope
env = parse_file("path/to/gazette.pdf")

# Inspect the results
print(f"Issue: {env.issue.gazette_issue_id}")
print(f"Notices: {len(env.notices)}")
print(f"Document confidence: {env.document_confidence.mean_composite:.3f}")

# Write output files
written = write_envelope(env, out_dir="output/", pdf_path="path/to/gazette.pdf")
print(f"Wrote: {list(written.keys())}")
```

### 2c. What the README does NOT include

| Excluded content | Reason |
|------------------|--------|
| Full API reference for all 12 public exports | Post-1.0 docs site |
| `parse_bytes` example | Quickstart focuses on file-based usage; `parse_bytes` is for advanced use |
| LLM configuration details | LLM stages are M5/M6 work; `LLMPolicy` exists but does nothing in 1.0 |
| CLI usage | F26 introduces CLI |
| Notebook usage instructions | Legacy; the notebook is now a demo, not the primary interface |
| Contribution guidelines | Post-1.0 |
| CI badges | No CI set up yet |

### 2d. Formatting rules

- Use GitHub-flavored Markdown
- Code blocks with `python` language tag
- No trailing whitespace
- Single blank line between sections
- Badge images use shields.io URLs
- Internal links use relative paths (`[LICENSE](LICENSE)`, `[docs/library-contract-v1.md](docs/library-contract-v1.md)`)

---

## 3. Test Cases

F25 is a documentation feature. Test cases verify the README is accurate and the code examples work.

| ID | Scenario | How to verify | Expected result |
|----|----------|---------------|-----------------|
| **TC1** | Quickstart code runs | Copy the quickstart example from the new README, run in `.venv` with a canonical PDF (`pdfs/Kenya Gazette Vol CXIINo 76.pdf`) | Prints `Issue: KE-GAZ-CXII-76-2010-09-17`, `Notices: 3`, `Document confidence: 0.963` (within 0.05 tolerance) |
| **TC2** | `write_envelope` example runs | Copy the write_envelope example, run with a temp output directory | Creates 5 files in `out_dir`; prints bundle keys |
| **TC3** | Installation command works | In a fresh venv, run `pip install git+https://github.com/rwahome/docling_spatial_pdfs.git` (or local equivalent `pip install .`) | Installs successfully; `from kenya_gazette_parser import parse_file` works |
| **TC4** | Schema link is valid | Check that `kenya_gazette_parser/schema/envelope.schema.json` exists and is valid JSON | File exists, contains `$schema` key |
| **TC5** | License link is valid | Check that `LICENSE` file exists at repo root | File exists, contains "Apache License" text |
| **TC6** | All required sections present | Grep README for section headers | All 8 sections from 2a are present |
| **TC7** | No broken internal links | Check all `[text](path)` links point to existing files | All links resolve |
| **TC8** | Badge URLs are valid | Curl the shields.io badge URLs | Return 200 OK |

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F25: README Points at `parse_file`**

Read this spec: `specs/F25-readme-quickstart.md`

Implement in location: `README.md` (repo root — replace existing content)

**Requirements (do these in order):**

1. **Read the existing `README.md`** to understand what's there (mostly notebook-focused content from pre-F17 era plus F17's minimal stub at the top).

2. **Write a completely new `README.md`** with these sections in order:

   a. **Title + badges**:
   ```markdown
   # kenya-gazette-parser
   
   [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
   [![Python](https://img.shields.io/badge/python-≥3.10-blue.svg)](https://www.python.org/downloads/)
   ```
   
   b. **One-liner**: "Parse Kenya Gazette PDFs into structured, validated JSON envelopes."
   
   c. **Installation** section with two subsections:
   - "Install from GitHub" (for users): `pip install git+https://github.com/rwahome/docling_spatial_pdfs.git`
   - "Install for development" (for contributors): `git clone ... && pip install -e ".[dev]"`
   
   d. **Quickstart** section with a complete working example:
   ```python
   from kenya_gazette_parser import parse_file, write_envelope
   
   # Parse a PDF into a validated Envelope
   env = parse_file("path/to/gazette.pdf")
   
   # Inspect the results
   print(f"Issue: {env.issue.gazette_issue_id}")
   print(f"Notices: {len(env.notices)}")
   print(f"Document confidence: {env.document_confidence.mean_composite:.3f}")
   
   # Access individual notices
   for notice in env.notices[:3]:
       print(f"  - {notice.notice_id}: {notice.gazette_notice_header or '(no header)'}")
   ```
   
   e. **Writing output files** section:
   ```python
   from kenya_gazette_parser import write_envelope
   
   # Write all default bundles to disk
   written = write_envelope(env, out_dir="output/", pdf_path="path/to/gazette.pdf")
   for name, path in written.items():
       print(f"{name}: {path}")
   ```
   Brief note: "Pass `bundles={...}` to select specific outputs. See `Bundles` model for options."
   
   f. **Configuration** section:
   Brief paragraph: "Pass a `GazetteConfig` to customize parsing. LLM validation stages are declared but inactive in 1.0."
   ```python
   from kenya_gazette_parser import parse_file, GazetteConfig, Bundles
   
   config = GazetteConfig(bundles=Bundles(notices=True, document_index=True))
   env = parse_file("gazette.pdf", config=config)
   ```
   Link: "See [docs/library-contract-v1.md](docs/library-contract-v1.md) section 5 for full API."
   
   g. **JSON Schema** section:
   Brief paragraph: "The output envelope conforms to a JSON Schema. Use it to validate outputs from other tools or languages."
   ```python
   from kenya_gazette_parser import get_envelope_schema, validate_envelope_json
   import json
   
   # Get the schema
   schema = get_envelope_schema()
   
   # Validate a JSON file
   with open("gazette_spatial.json") as f:
       data = json.load(f)
   validate_envelope_json(data)  # Raises if invalid
   ```
   Note: "Schema file: `kenya_gazette_parser/schema/envelope.schema.json`"
   
   h. **Status** section:
   "**Version:** 0.1.0 (alpha)  
   **Schema version:** 1.0 (locked)  
   API is stable for 1.0. See [PROGRESS.md](PROGRESS.md) for roadmap."
   
   i. **License** section:
   "Apache License 2.0. See [LICENSE](LICENSE)."

3. **Do NOT include** any of the old notebook-focused content (Usage with `gazette_docling_pipeline_spatial.ipynb`, Environment variables for LLM, etc.). The README should present `kenya-gazette-parser` as a self-contained library.

4. **Verify TC1**: Copy the quickstart code, adjust the PDF path to `"pdfs/Kenya Gazette Vol CXIINo 76.pdf"`, run it. Confirm it prints something like:
   ```
   Issue: KE-GAZ-CXII-76-2010-09-17
   Notices: 3
   Document confidence: 0.963
   ```

5. **Verify TC2-TC8**: Run through the remaining test cases from the spec.

6. **Update PROGRESS.md**:
   - **Today** block: No change needed (F25 is the last feature before 1.0)
   - **Work Items** table: F25 row Status `⬜ Not started` → `✅ Complete`
   - **Session Log** row: Append with date, files edited (README.md), TC1-TC8 results, note that all 5 Gates remain cleared, 1.0 complete.

7. **Return the Build Report** (format below).

**Build Report Format:**

```markdown
# Build Report: F25

## Implementation
- Files edited:
  - `README.md` (replaced ~45 lines of old content with ~100 lines of library quickstart)
  - `PROGRESS.md` (F25 row → ✅ Complete, Session Log row appended)
- Files NOT touched: `kenya_gazette_parser/*`, `pyproject.toml`, notebook, anything under `output/`, `pdfs/`, `tests/`

## README Sections
| Section | Lines | Content summary |
|---------|-------|-----------------|
| Title + badges | 1-5 | kenya-gazette-parser + Apache-2.0 + Python badges |
| One-liner | 7 | Parse Kenya Gazette PDFs... |
| Installation | 9-20 | GitHub install + dev install |
| Quickstart | 22-40 | parse_file example |
| Writing output | 42-55 | write_envelope example |
| Configuration | 57-70 | GazetteConfig example |
| JSON Schema | 72-85 | get_envelope_schema / validate_envelope_json |
| Status | 87-90 | Version, schema version |
| License | 92-93 | Apache 2.0 |

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| TC1 — Quickstart code runs | PASS/FAIL | CXIINo 76: 3 notices, mean_composite ~0.963 |
| TC2 — write_envelope example | PASS/FAIL | 5 files written |
| TC3 — Installation command | PASS/FAIL | Already verified in F24 |
| TC4 — Schema link valid | PASS/FAIL | envelope.schema.json exists |
| TC5 — License link valid | PASS/FAIL | LICENSE exists |
| TC6 — All sections present | PASS/FAIL | 8/8 sections |
| TC7 — No broken links | PASS/FAIL | All internal links resolve |
| TC8 — Badge URLs valid | PASS/FAIL | shields.io returns 200 |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (no code changes)
- Gate 2 (notice_id stability): STILL CLEARED (no code changes)
- Gate 3 (parse_file works): STILL CLEARED (TC1 proves it)
- Gate 4 (schema validation): STILL CLEARED (no schema changes)
- Gate 5 (pip install works): STILL CLEARED (TC3 references F24)

## PROGRESS.md
- F25 row: ⬜ Not started → ✅ Complete
- Session Log row appended
- **1.0 COMPLETE** — all features F11-F25 marked ✅

## Notes
- The README is intentionally concise (~100 lines) to serve as a quickstart, not full documentation.
- Old notebook-focused content removed; notebook remains as a demo but is no longer the documented entry point.
- Post-1.0 work (F26 CLI, PyPI publish, full docs site) can expand documentation.

## Final Status: PASS / FAIL
```

---

## 8. Open Questions / Risks

**Q1. Should the README preserve any content from the old notebook-focused README?** — **Recommend: No.** The old README (from pre-F17 plus F17's stub) describes the notebook workflow and mentions features like LLM validation that are not part of the 1.0 library API. Starting fresh with a library-focused quickstart is cleaner. Users who want the notebook workflow can still find it in the repo.

**Q2. Should the README include a "Features" or "What does it do" section?** — **Recommend: Implicit via quickstart.** The quickstart shows `env.issue`, `env.notices`, `env.document_confidence` — that demonstrates what the library does. A separate bulleted feature list adds length without adding clarity for the target audience (developers who learn by example).

**Q3. Should the installation instructions use `pip install kenya-gazette-parser` (PyPI name)?** — **Recommend: No, use `git+...` URL.** The package is not published to PyPI (F26+ territory). Using the git URL is accurate for 1.0. When PyPI publishing happens, F26 or a post-1.0 patch updates the README.

**Q4. Should the quickstart show error handling (try/except)?** — **Recommend: No.** Quickstart examples are for the happy path. Error handling details belong in full documentation. The library raises `pydantic.ValidationError` on malformed PDFs (F19 rule) — documenting that is post-1.0.

**Q5. Should the README show `parse_bytes` usage?** — **Recommend: No.** `parse_bytes` is for advanced use cases (in-memory PDFs, S3 streams). The quickstart focuses on `parse_file` which covers 95% of users. `parse_bytes` is documented in the contract and discoverable via `help(parse_bytes)`.

**Q6. Risk — Code examples become stale if API changes.** — **Mitigated:** The API is locked for 1.0 (`schema_version: "1.0"`). Any breaking change requires a MAJOR version bump (2.0) and would update the README at that point. TC1-TC2 catch staleness during builds.

**Q7. Should the README include sample output JSON?** — **Recommend: No.** Showing full JSON output bloats the README. The quickstart shows how to access `env.issue`, `env.notices` — users can `print(env.model_dump_json(indent=2))` to see the full structure. The JSON Schema link provides the authoritative shape.

**Q8. Risk — User tries to run quickstart without a PDF file.** — **Mitigated:** The quickstart says `"path/to/gazette.pdf"` as a placeholder. Users understand they need their own file. Adding a "Download sample PDF" link is nice but out of scope for F25 (would require hosting PDFs externally).

**Q9. Should the README mention Docling as the underlying OCR engine?** — **Recommend: Brief mention in one line.** E.g., "Built on [Docling](https://github.com/DS4SD/docling) for PDF extraction." Gives credit and helps users understand the dependency. Not a detailed explanation.

**Q10. Should badges link to external services (PyPI, CI) that don't exist yet?** — **Recommend: No.** Only include badges for things that exist: License badge (points to LICENSE file), Python version badge (static). No PyPI badge (not published), no CI badge (no CI), no coverage badge (no coverage).

---
