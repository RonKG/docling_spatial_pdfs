# F24 Spec: Installable Package Smoke Test

## 1. What to Build

Verify that the Kenya Gazette parser library installs correctly from a git URL (or local path as proxy) on a fresh virtual environment and that all public exports work. This feature clears **Quality Gate 5** (`pip install git+...` works on different machine) and addresses **D3** (consolidate ad-hoc `scripts/f*_*.py` test scripts into a proper `tests/` folder with pytest).

**Scope (locked):**
1. **Fresh venv installation test** — Create a fresh venv, install the package from the local repo path (as proxy for `pip install git+https://github.com/.../docling_spatial_pdfs.git`), and verify the install succeeds with all dependencies resolved (`docling`, `docling-core`, `openai`, `pydantic`, `jsonschema`).
2. **Public API import smoke** — After install, verify all public exports are importable: `parse_file`, `parse_bytes`, `write_envelope`, `Envelope`, `GazetteConfig`, `Bundles`, `LLMPolicy`, `RuntimeOptions`, `get_envelope_schema`, `validate_envelope_json`, `__version__`.
3. **Schema file package-data check** — Verify the checked-in `kenya_gazette_parser/schema/envelope.schema.json` is accessible from the installed package via `importlib.resources` or `Path(__file__).parent`.
4. **Model import smoke** — Verify all 16 Pydantic models import from `kenya_gazette_parser.models`: the original 12 from F18 (`Envelope`, `GazetteIssue`, `Notice`, `Corrigendum`, `ConfidenceScores`, `DocumentConfidence`, `Provenance`, `LayoutInfo`, `BodySegment`, `DerivedTable`, `Warning`, `Cost`) plus the 4 F22 config models.
5. **Optional: pytest consolidation** — Consolidate the scattered `scripts/f*_*.py` test scripts into a proper `tests/` folder with pytest fixtures and a `pyproject.toml` pytest config section. Addresses D3. This is optional for Gate 5 clearance but recommended for project hygiene.

**Integration constraints:**
- F17 created the package skeleton with `pyproject.toml` declaring `package-data` for `py.typed`.
- F23 added `kenya_gazette_parser/schema/envelope.schema.json` — this file must be included in the installed package. The `pyproject.toml` `[tool.setuptools.package-data]` block needs to include `"*.json"` or `"schema/*.json"`.
- The venv test runs in a subprocess or separate shell to avoid polluting the current development environment.

**What F24 does NOT do:**
- No actual `pip install git+...` from a remote Git host (CI/CD concern, not F24).
- No wheel build and upload to PyPI (F26+ territory).
- No testing on multiple Python versions (CI/CD concern).
- No testing on non-Windows platforms (documented as a limitation; maintainer's machine is Windows).

**Gate 5 clearance conditions:**
- `pip install .` (or `pip install -e .` as proxy) in a fresh venv succeeds.
- `from kenya_gazette_parser import parse_file, get_envelope_schema` executes without error.
- The installed package includes the schema JSON file in its package data.

---

## 2. Interface Contract

F24 creates test scripts and optionally a `tests/` folder structure. No changes to the `kenya_gazette_parser/` package source code itself (unless `pyproject.toml` needs a `package-data` fix for the schema JSON file).

### 2a. Test script deliverables

| File | Purpose | Contents |
|------|---------|----------|
| `scripts/f24_fresh_venv_install.py` | TC1 — Fresh venv install test | Creates a temp venv, installs package, verifies success |
| `scripts/f24_public_api_smoke.py` | TC2 — Public API import smoke | Imports all 11 public exports from package root |
| `scripts/f24_schema_package_data.py` | TC3 — Schema file accessibility | Verifies `envelope.schema.json` is in installed package |
| `scripts/f24_model_import_smoke.py` | TC4 — All 16 models import | Imports all models from `kenya_gazette_parser.models` |
| `scripts/f24_end_to_end_smoke.py` | TC5 — End-to-end parse + validate | Calls `parse_file` on a canonical PDF, validates against schema |

### 2b. pyproject.toml package-data fix (if needed)

Current `pyproject.toml` (from F17):
```toml
[tool.setuptools.package-data]
kenya_gazette_parser = ["py.typed"]
```

Required after F23:
```toml
[tool.setuptools.package-data]
kenya_gazette_parser = ["py.typed", "schema/*.json"]
```

The `schema/*.json` glob ensures `envelope.schema.json` (and any future `config.schema.json`) is included in wheel/sdist distributions.

### 2c. Optional pytest consolidation (D3)

If implemented, create:
- `tests/conftest.py` — pytest fixtures for canonical PDF paths, temp directories
- `tests/test_smoke.py` — consolidated smoke tests from F24
- `tests/test_regression.py` — consolidated regression checks from prior features
- `pyproject.toml` `[tool.pytest.ini_options]` section

### 2d. Error handling rules

| Situation | F24 behavior |
|-----------|--------------|
| Fresh venv pip install fails (resolution, network, etc.) | TC1 FAIL with pip stderr |
| Any public export raises `ImportError` | TC2 FAIL with traceback |
| `envelope.schema.json` not found in installed package | TC3 FAIL |
| Any of 16 models fails to import | TC4 FAIL with specific model name |
| `parse_file` raises on canonical PDF | TC5 FAIL (indicates Gate 3 regression) |
| `validate_envelope_json` rejects fresh envelope | TC5 FAIL (indicates Gate 4 regression) |

---

## 3. Test Cases

Source PDFs: the 6 canonical fixtures from `tests/expected_confidence.json`. Primary test PDF: `pdfs/Kenya Gazette Vol CXIINo 76.pdf` (chosen because it's the smallest/fastest of the 6).

| ID | Scenario | Source | Expected Result |
|----|----------|--------|-----------------|
| **TC1** | Fresh venv installation | Local repo path | `pip install .` exits 0; stdout contains `Successfully installed kenya-gazette-parser-0.1.0`; all 5 runtime deps installed (`docling`, `docling-core`, `openai`, `pydantic`, `jsonschema`) |
| **TC2** | Public API import smoke | — | `from kenya_gazette_parser import parse_file, parse_bytes, write_envelope, Envelope, GazetteConfig, Bundles, LLMPolicy, RuntimeOptions, get_envelope_schema, validate_envelope_json, __version__` succeeds; `__version__ == "0.1.0"` |
| **TC3** | Schema file in package data | — | `import kenya_gazette_parser.schema` succeeds; `Path(kenya_gazette_parser.schema.__file__).parent / "envelope.schema.json"` exists and is valid JSON with `$schema` key |
| **TC4** | All 16 models import | — | `from kenya_gazette_parser.models import Envelope, GazetteIssue, Notice, Corrigendum, ConfidenceScores, DocumentConfidence, Provenance, LayoutInfo, BodySegment, DerivedTable, Warning, Cost, GazetteConfig, LLMPolicy, RuntimeOptions, Bundles` succeeds; `len(models.__all__) == 16` |
| **TC5** | End-to-end parse + schema validate | `pdfs/Kenya Gazette Vol CXIINo 76.pdf` | `env = parse_file(path)` returns `Envelope` with `len(env.notices) == 3`; `validate_envelope_json(env.model_dump(mode="json"))` returns `True`; no exceptions |
| **TC6** | Gate 1 regression (inherited from prior features) | All 6 canonical PDFs | `check_regression(tolerance=0.05)` returns `True` for all 6 PDFs |
| **TC7** | Gate 2 notice_id stability | All 6 canonical PDFs | Notice IDs unchanged from F23 baseline |

**Note:** TC6 and TC7 are inherited checks that prove F24 did not regress Gates 1 and 2. They run via the existing notebook `check_regression()` infrastructure, not new F24 scripts.

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F24: Installable Package Smoke Test**

Read this spec: `specs/F24-installable-package-smoke-test.md`

Implement in location: `scripts/f24_*.py` test scripts; optionally `tests/` folder; `pyproject.toml` package-data fix if needed.

**Requirements:**

1. **Check and fix `pyproject.toml` package-data** — Verify `[tool.setuptools.package-data]` includes `"schema/*.json"` so the F23 schema file is packaged. If missing, add it. Re-install with `pip install -e .` to verify.

2. **Create `scripts/f24_fresh_venv_install.py`** (TC1):
   - Create a temporary directory with `tempfile.TemporaryDirectory()`
   - Create a venv with `python -m venv <temp_dir>/test_venv`
   - Activate and install: `<venv_python> -m pip install <repo_root>` (local path install as proxy for `git+...`)
   - Assert exit code 0 and "Successfully installed kenya-gazette-parser" in stdout
   - Clean up temp directory
   - Print `TC1 OK` on success

3. **Create `scripts/f24_public_api_smoke.py`** (TC2):
   - Import all 11 public exports: `parse_file`, `parse_bytes`, `write_envelope`, `Envelope`, `GazetteConfig`, `Bundles`, `LLMPolicy`, `RuntimeOptions`, `get_envelope_schema`, `validate_envelope_json`, `__version__`
   - Assert `__version__ == "0.1.0"`
   - Print `TC2 OK` on success

4. **Create `scripts/f24_schema_package_data.py`** (TC3):
   - Import `kenya_gazette_parser.schema`
   - Locate `envelope.schema.json` via `Path(kenya_gazette_parser.schema.__file__).parent / "envelope.schema.json"`
   - Assert file exists
   - Load as JSON, assert `"$schema"` key present
   - Print `TC3 OK` on success

5. **Create `scripts/f24_model_import_smoke.py`** (TC4):
   - Import all 16 models from `kenya_gazette_parser.models`
   - Assert `len(kenya_gazette_parser.models.__all__) == 16`
   - Print `TC4 OK` on success

6. **Create `scripts/f24_end_to_end_smoke.py`** (TC5):
   - Import `parse_file`, `validate_envelope_json`, `Envelope`
   - Call `env = parse_file("pdfs/Kenya Gazette Vol CXIINo 76.pdf")`
   - Assert `isinstance(env, Envelope)`
   - Assert `len(env.notices) == 3` (known count for this PDF)
   - Call `validate_envelope_json(env.model_dump(mode="json"))`
   - Assert returns `True`
   - Print `TC5 OK` on success

7. **Run all test cases in order**:
   - `.\.venv\Scripts\python.exe scripts\f24_fresh_venv_install.py` → TC1 OK
   - `.\.venv\Scripts\python.exe scripts\f24_public_api_smoke.py` → TC2 OK
   - `.\.venv\Scripts\python.exe scripts\f24_schema_package_data.py` → TC3 OK
   - `.\.venv\Scripts\python.exe scripts\f24_model_import_smoke.py` → TC4 OK
   - `.\.venv\Scripts\python.exe scripts\f24_end_to_end_smoke.py` → TC5 OK
   - In notebook: `check_regression(tolerance=0.05)` → all 6 PDFs OK (TC6)
   - Notice IDs unchanged from F23 (TC7, spot-check via TC5 or notebook)

8. **Update PROGRESS.md**:
   - **Today** block: change `**Current:** F24 — Installable package smoke test` to `**Current:** F25 — README points at parse_file`; update `**Previous:**` to `**Previous:** F24 ✅ — Installable package smoke test (fresh venv install; public API smoke; schema package-data; Gate 5 cleared)`
   - **Work Items** table: F24 row Status `⬜ Not started` → `✅ Complete`
   - **Quality Gates** table: Gate 5 Status `⬜ Not reached (needs F24)` → `✅ Cleared (F24)`
   - **Known Debt** table: D3 row — mark as resolved if pytest consolidation was done, or update Target to F25/post-1.0 if deferred
   - **Session Log** row: files created, TC1-TC7 results, Gate 5 clearance, D3 status

9. **Return the Build Report** (format below). If any TC fails, report the exact failure output and STOP.

**Build Report Format:**

```markdown
# Build Report: F24

## Implementation
- Files created:
  - `scripts/f24_fresh_venv_install.py`
  - `scripts/f24_public_api_smoke.py`
  - `scripts/f24_schema_package_data.py`
  - `scripts/f24_model_import_smoke.py`
  - `scripts/f24_end_to_end_smoke.py`
- Files edited:
  - `pyproject.toml` (if package-data fix needed: added `"schema/*.json"`)
  - `PROGRESS.md`
- Files NOT touched: `kenya_gazette_parser/*.py`, notebook, anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/expected_confidence.json`

## Package-data status
- `[tool.setuptools.package-data]` includes: py.typed, schema/*.json (or just py.typed if no fix needed)
- `envelope.schema.json` accessible from installed package: YES/NO

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| TC1 — Fresh venv install | PASS/FAIL | pip exit code, deps resolved |
| TC2 — Public API smoke (11 exports) | PASS/FAIL | __version__ check |
| TC3 — Schema package-data | PASS/FAIL | envelope.schema.json found |
| TC4 — Model import smoke (16 models) | PASS/FAIL | __all__ length |
| TC5 — End-to-end parse + validate | PASS/FAIL | CXIINo 76, 3 notices |
| TC6 — Gate 1 regression | PASS/FAIL | 6/6 within 0.05 |
| TC7 — Gate 2 notice_id stability | PASS/FAIL | spot-check |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (TC6 PASS)
- Gate 2 (notice_id stability): STILL CLEARED (TC7 PASS)
- Gate 3 (parse_file works): STILL CLEARED (TC5 PASS)
- Gate 4 (schema validation): STILL CLEARED (TC5 PASS)
- Gate 5 (pip install works): NOW CLEARED (TC1 PASS)

## PROGRESS.md
- F24 row: ⬜ Not started → ✅ Complete
- "Today" moved to F25 — README points at parse_file
- Quality Gate 5 cell: ⬜ Not reached → ✅ Cleared (F24)
- D3 debt: <resolved/deferred>
- Session Log row appended

## D3 Status
- pytest consolidation: <implemented/deferred to F25/post-1.0>
- If deferred, reason: <scope control / time>

## Notes for F25
- All 5 Quality Gates now cleared
- Package is installable from git URL
- F25 should update README.md with quickstart using `parse_file`

## Final Status: PASS / FAIL
```

---

## 8. Open Questions / Risks

**Q1. Should TC1 use a real `git+https://...` URL or a local path as proxy?** — **Recommend: Local path.** Testing `git+...` requires network access and depends on the repo being pushed to a specific remote. Local `pip install <repo_root>` exercises the same packaging machinery (sdist/wheel build, dependency resolution) and is more reliable for automated testing. Document that real `git+...` testing is a CI/CD concern, not F24.

**Q2. Should F24 create the `tests/` folder and consolidate scripts (D3)?** — **Recommend: Optional / defer to post-1.0.** D3 consolidation is nice-to-have but not blocking for Gate 5. The current `scripts/f*_*.py` pattern works. If time permits, create `tests/test_f24_smoke.py` as a pytest-compatible version of TC1-TC5, but don't refactor all prior scripts. Mark D3 as "target F24" but allow deferral if scope balloons.

**Q3. What if the fresh venv install fails due to Docling's heavy native dependencies (PyTorch, etc.)?** — **Recommend: Document as a known limitation.** Docling pulls in PyTorch and other heavy ML packages. On constrained systems, pip install may fail due to disk space or download timeouts. F24 tests on the maintainer's machine (Windows, 16GB+ RAM, SSD); failure on smaller systems is expected and not a Gate 5 blocker. The fix is users installing in a proper environment with sufficient resources.

**Q4. Should TC5 run on all 6 canonical PDFs or just one?** — **Recommend: Just one (CXIINo 76).** Full 6-PDF parsing takes 5-15 minutes due to Docling's OCR. TC5's purpose is to verify the installed package can parse and validate — one PDF suffices. TC6 (regression) via the notebook covers all 6 PDFs.

**Q5. What if `pyproject.toml` already includes `schema/*.json` in package-data?** — **RESOLVED by inspection.** Check the current `pyproject.toml`. If F23 already added it, no fix needed. If missing, add it. Either way, document the state in the build report.

**Q6. Should F24 test on a different Python version (e.g., 3.11)?** — **Recommend: No.** Multi-version testing is a CI/CD concern. F24 tests on the maintainer's Python version (3.10+). `pyproject.toml` already declares `requires-python = ">=3.10"` so version mismatches are caught at install time.

**Q7. What if the fresh venv approach fails on Windows due to `venv` activation issues in subprocess?** — **Recommend: Use direct path to venv Python.** Instead of activating the venv, invoke `<venv>/Scripts/python.exe -m pip install ...` and `<venv>/Scripts/python.exe -c "import kenya_gazette_parser"` directly. This avoids shell-specific activation scripts.

**Q8. Risk — Docling's `std::bad_alloc` crashes on large PDFs.** — **Mitigated.** TC5 uses CXIINo 76 (3 notices, small), which is stable. The G1 OCR non-determinism documented in PROGRESS.md affects CXXVIINo 63 and occasionally others on memory-constrained runs, but CXIINo 76 is reliable.
