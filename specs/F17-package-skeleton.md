# F17 Spec: Package Skeleton

## 1. What to Build

Create the **minimal installable Python package** so that `pip install -e .` from the repo root succeeds and `from kenya_gazette_parser import parse_file, parse_bytes, __version__` works. This is the **gateway** that unblocks F18 (Pydantic models), F19 (envelope validation), F20 (logic migration), F21 (public API split), F23 (JSON Schema export), and F24 (install smoke test). It is also the precondition for **Quality Gate 3** (`from kenya_gazette_parser import parse_file` works).

**Scope is intentionally tiny.** F17 creates five files: `kenya_gazette_parser/__init__.py`, `kenya_gazette_parser/__version__.py`, `kenya_gazette_parser/py.typed`, `pyproject.toml`, and a one-paragraph `README.md` stub at the repo root. It does **not** copy any logic out of the notebook. The exposed `parse_file` and `parse_bytes` are deliberate **stubs that raise `NotImplementedError`** with a message that points the user at `gazette_docling_pipeline_spatial.ipynb` for now and at F20-F21 for the real implementation. Logic migration is F18-F21's job; F17 only proves the package can be installed and imported.

**Package name decision (locked).** The directory and import name is `kenya_gazette_parser` (underscores). The PyPI distribution name is `kenya-gazette-parser` (dashes). This is the canonical choice — chosen for clarity ("parser" is the verb), PyPI namespace availability, and disambiguation from any unrelated `kenya_gazette` package. Older planning docs (`PROGRESS.md` row F17, `library-roadmap-v1.md` Blueprint 2 sketch) still say `kenya_gazette/`; those are pre-rename artifacts and **F17 supersedes them**. PROGRESS.md will be updated to read `kenya_gazette_parser/` as part of F17's Definition of Done.

**Version single source of truth.** `kenya_gazette_parser/__version__.py` contains `__version__ = "0.1.0"` and `pyproject.toml` carries `version = "0.1.0"`. The notebook's `LIBRARY_VERSION = "0.1.0"` (from F14) **stays as-is in F17** so the notebook keeps running unchanged and Gate 1 (regression) is not disturbed; the notebook will switch to `from kenya_gazette_parser import __version__ as LIBRARY_VERSION` at F20 when logic migration starts. Until then, the two `"0.1.0"` strings must match by hand — F17 documents this as a known short-lived duplication.

**Determinism / regression invariant (Gate 1, Gate 2).** F17 touches no pipeline logic. `check_regression()` must continue to pass for all 6 canonical PDFs after F17 lands; `notice_id`s must be byte-identical across runs. If either gate drops, F17 is incorrect.

---

## 2. Interface Contract

**Licensing note.** Project is licensed under **Apache License 2.0**. F17 declares `license = { text = "Apache-2.0" }` in `pyproject.toml` (SPDX identifier) and the `License :: OSI Approved :: Apache Software License` classifier. A `LICENSE` file with the full Apache 2.0 text and the copyright line `Copyright 2026 Ronald Wahome` is written at the repo root so setuptools includes it in built distributions (required by Apache 2.0 redistribution clause 4(a)).

### Files created (all five, exact paths)

| File | Purpose | Contents (summary) |
|------|---------|-------------------|
| `kenya_gazette_parser/__init__.py` | Public package surface | Re-exports `__version__`, defines stub `parse_file`, `parse_bytes`; sets `__all__` |
| `kenya_gazette_parser/__version__.py` | Single source of truth for version | `__version__ = "0.1.0"` |
| `kenya_gazette_parser/py.typed` | PEP 561 marker — tells type checkers this package ships its own type info | Empty file (zero bytes) |
| `pyproject.toml` | Package metadata, dependencies, build config | setuptools backend, name/version, runtime deps (incl. `openai`), `dev` extra |
| `README.md` | One-paragraph project stub | Project name, one-sentence description, alpha status, install command |

No other files. No `setup.py`, no `setup.cfg`, no `MANIFEST.in`, no `LICENSE` (deferred). setuptools' `pyproject.toml`-only mode handles everything.

### `kenya_gazette_parser/__version__.py` — exact contents

```python
"""Single source of truth for the kenya_gazette_parser version string.

Both ``kenya_gazette_parser.__version__`` and ``pyproject.toml`` read from here.
The notebook's ``LIBRARY_VERSION`` constant (F14) will switch to importing this
value at F20; until then the two ``"0.1.0"`` strings must be kept in sync by hand.
"""

__version__ = "0.1.0"
```

### `kenya_gazette_parser/__init__.py` — exact contents

```python
"""kenya_gazette_parser — parse Kenya Gazette PDFs into structured envelopes.

This is the F17 package skeleton. The real parsing logic still lives in
``gazette_docling_pipeline_spatial.ipynb`` and migrates into this package
across F18-F21. ``parse_file`` and ``parse_bytes`` are stubs that raise
``NotImplementedError`` until F20-F21 land.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kenya_gazette_parser.__version__ import __version__

if TYPE_CHECKING:
    from typing import Any

__all__ = ["__version__", "parse_file", "parse_bytes"]


_NOT_IMPLEMENTED_MSG = (
    "kenya_gazette_parser.{name} is an F17 skeleton stub. "
    "Real implementation lands in F20-F21 (logic migration + public API split). "
    "For now, run the pipeline via gazette_docling_pipeline_spatial.ipynb."
)


def parse_file(path: "Path | str", config: "Any | None" = None) -> dict:
    """Parse a Kenya Gazette PDF file into an envelope dict.

    F17 stub. Always raises ``NotImplementedError``. Real implementation
    lands in F20 (logic migration) and F21 (public API + I/O split). The
    return type is ``dict`` for now; F18 will tighten it to ``Envelope``.
    """
    raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="parse_file"))


def parse_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    config: "Any | None" = None,
) -> dict:
    """Parse a Kenya Gazette PDF from raw bytes into an envelope dict.

    F17 stub. Always raises ``NotImplementedError``. Real implementation
    lands in F20 (logic migration) and F21 (public API + I/O split). The
    return type is ``dict`` for now; F18 will tighten it to ``Envelope``.
    """
    raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="parse_bytes"))
```

Notes on signature decisions (locked, must not drift):
- `parse_file` and `parse_bytes` signatures match `docs/library-contract-v1.md` section 5 exactly, except return type is `dict` (F17) instead of `Envelope` (F18+) — keeping the dict return type makes F17 implementable before Pydantic models exist.
- `config` is typed `Any | None` in F17 because `GazetteConfig` does not exist yet (lands in F22). The parameter is present so callers can write the call site once and never change it.
- `parse_bytes` keeps `filename` as a **keyword-only** argument (note the `*,`) — matches the contract sketch and pins the call shape now so F21 cannot accidentally widen it.
- `__all__` is explicit so `from kenya_gazette_parser import *` only pulls these three names.

### `kenya_gazette_parser/py.typed` — exact contents

Empty file (zero bytes). PEP 561 marker. Required for downstream consumers (mypy, pyright) to honor inline type annotations from this package once F18 lands real Pydantic models.

### `pyproject.toml` — exact contents

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "kenya-gazette-parser"
version = "0.1.0"
description = "Parse Kenya Gazette PDFs into structured, validated envelopes."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
authors = [
    { name = "Ronald Wahome" },
]
keywords = ["kenya", "gazette", "pdf", "docling", "legal", "parsing"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Legal Industry",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Text Processing :: Markup",
    "Typing :: Typed",
]
dependencies = [
    "docling>=2.86.0,<3",
    "docling-core>=2.0.0",
    "openai>=1.40.0",
]

[project.optional-dependencies]
dev = [
    "jupyter>=1.1.0",
    "ipykernel>=7.0.0",
    "pytest>=8.0.0",
    "pyyaml>=6.0",
]

[project.urls]
Homepage = "https://github.com/RonKG/docling_spatial_pdfs"
Repository = "https://github.com/RonKG/docling_spatial_pdfs"

[tool.setuptools.packages.find]
where = ["."]
include = ["kenya_gazette_parser*"]
exclude = ["tests*", "docs*", "specs*", "output*", "pdfs*", ".llm_cache*"]

[tool.setuptools.package-data]
kenya_gazette_parser = ["py.typed"]
```

Justifications (so Agent 2 does not second-guess the choices):
- **Build backend:** setuptools >= 68 supports `pyproject.toml`-only configuration with no `setup.py` shim. No new tooling required.
- **PyPI name vs import name:** `kenya-gazette-parser` (dashes) is the project name; `kenya_gazette_parser` (underscores) is the import. Setuptools handles the mapping automatically.
- **`requires-python = ">=3.10":`** notebook already uses 3.10+ syntax (`dict | None`, `X | Y` unions in the F14 helper, `from __future__ import annotations`).
- **Runtime deps:** `docling`, `docling-core`, and `openai` are the third-party imports the live pipeline needs. `docling-core` lower bound set to `>=2.0.0` (loose; F18 may tighten).
- **`docling>=2.86.0,<3` is intentionally narrow:** the lower bound mirrors `requirements.txt` (the version the notebook is actually tested against). Loosening risks breaking Gate 1 because docling has API drift across minor versions; the upper cap `<3` blocks an unannounced major.
- **`openai` is a runtime dep, not an extra:** the user always runs the pipeline with LLM validation enabled, so `openai` is required at install time. Lower bound `>=1.40.0` because the OpenAI Python SDK had breaking API changes through 1.0-1.39 (`responses` API stabilized in 1.40+); pinning the modern client surface avoids surprise breakage. `pip install -e .` adds ~5 MB; acceptable for this project.
- **Optional `dev` extra:** `jupyter` + `ipykernel` (notebook execution), `pytest` (future automated tests under `tests/`), `pyyaml` (calibration today parses YAML by hand but F22+ may switch to PyYAML; carrying it as dev keeps the door open without forcing a runtime dep).
- **Excludes:** `tests/`, `docs/`, `specs/`, `output/`, `pdfs/`, `.llm_cache/` are explicitly excluded so they never end up in built wheels. The `kenya_gazette_parser*` include pattern is positive-only (no accidental sibling packages).
- **`py.typed` is package data:** the `[tool.setuptools.package-data]` block ensures the marker file is included in built distributions; without it `pip install` from a wheel would lose the PEP 561 signal.

### `README.md` — exact contents

`pyproject.toml` declares `readme = "README.md"`. setuptools reads this file to populate the `Description` metadata field, so the file **must exist** or the build fails. F17 ships a one-paragraph stub; the real consumer-facing README is owned by F25.

````markdown
# kenya-gazette-parser

Parse Kenya Gazette PDFs into structured, validated envelopes.

**Status:** Alpha (pre-1.0). API and output schema may change. See [PROGRESS.md](PROGRESS.md) for current milestone.

## Install (editable, from repo root)

```bash
pip install -e ".[dev]"
```

## Usage

The real `parse_file()` lands in F20-F21. For now, run the pipeline via `gazette_docling_pipeline_spatial.ipynb`.

## License

Apache License 2.0. See [LICENSE](LICENSE) for full text.
````

(Note: the outer fence is four backticks so the inner triple-backtick `bash` block renders correctly when this spec is viewed; Agent 2 should write the file with normal triple backticks around the `bash` block, no four-backtick wrapper.)

### Error handling rules (consolidated)

| Boundary | Rule |
|----------|------|
| `import kenya_gazette_parser` | Must never raise. Empty package surface, no side effects. |
| `kenya_gazette_parser.__version__` access | Always present, always returns `"0.1.0"` as a `str`. |
| `parse_file(path, config=None)` | **Always raises `NotImplementedError`** in F17. The message must include the strings `"F17"`, `"F20-F21"`, and `"gazette_docling_pipeline_spatial.ipynb"` so a confused caller knows where to go. |
| `parse_bytes(data, *, filename=None, config=None)` | Same as `parse_file` — always raises `NotImplementedError` with the same message tokens. |
| `pip install -e .` | Must succeed in the project venv. Resolution failures must surface as the standard pip error (do not swallow). |

### Notebook impact (must be zero)

- The notebook's helper cell at line ~1822 keeps `LIBRARY_VERSION = "0.1.0"` and `SCHEMA_VERSION = "1.0"` as hardcoded constants. F17 does **not** edit the notebook.
- `process_pdf` keeps using the local `LIBRARY_VERSION` constant; no import from the new package is added in F17.
- The duplication between `kenya_gazette_parser.__version__` and the notebook's `LIBRARY_VERSION` is **expected and acceptable for F17**, with the migration path locked: F20 will replace the notebook constant with `from kenya_gazette_parser import __version__ as LIBRARY_VERSION`. Until F20 lands, both strings must read `"0.1.0"`.

### `requirements.txt` impact (must be zero)

`requirements.txt` stays untouched. It remains the supported way to set up the notebook environment without touching the package. `pyproject.toml` is additive: developers who want the package install run `pip install -e ".[dev]"`; developers who only want the notebook keep using `pip install -r requirements.txt`. F24 will revisit unification.

---

## 3. Test Cases

All five tests must pass. Run them in the project venv (`.venv` at repo root) after creating the five files above.

| ID | Scenario | Command / Assertion | Expected Result |
|----|----------|---------------------|-----------------|
| **T1** | Package importable, version present | `python -c "import kenya_gazette_parser; assert kenya_gazette_parser.__version__ == '0.1.0', kenya_gazette_parser.__version__; print('T1 OK', kenya_gazette_parser.__version__)"` | Prints `T1 OK 0.1.0`. Exit code `0`. No traceback. |
| **T2** | `parse_file` stub raises with helpful message | `python -c "from kenya_gazette_parser import parse_file; import sys\ntry:\n    parse_file('anything.pdf')\nexcept NotImplementedError as e:\n    msg = str(e); assert 'F17' in msg and 'F20-F21' in msg and 'gazette_docling_pipeline_spatial.ipynb' in msg, msg; print('T2 OK')\nelse:\n    print('T2 FAIL: no exception'); sys.exit(1)"` | Prints `T2 OK`. Exit code `0`. The raised exception is `NotImplementedError`, and its message contains `F17`, `F20-F21`, and `gazette_docling_pipeline_spatial.ipynb`. |
| **T3** | `parse_bytes` stub also present and raises | `python -c "from kenya_gazette_parser import parse_bytes; import sys\ntry:\n    parse_bytes(b'%PDF-1.4 fake', filename='x.pdf')\nexcept NotImplementedError as e:\n    msg = str(e); assert 'F17' in msg and 'parse_bytes' in msg, msg; print('T3 OK')\nelse:\n    print('T3 FAIL'); sys.exit(1)"` | Prints `T3 OK`. Exit code `0`. The raised exception mentions `parse_bytes` (so callers can tell which stub fired). |
| **T4** | `pyproject.toml` is valid TOML, declares the right metadata, and `pip install -e .` succeeds | Step 1: `python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); assert data['project']['name'] == 'kenya-gazette-parser'; assert data['project']['version'] == '0.1.0'; assert data['project']['license']['text'] == 'Apache-2.0'; assert 'openai' in str(data['project']['dependencies']); print('T4a OK')"`. Step 2: `pip install -e .` (run from repo root inside `.venv`). | Step 1 prints `T4a OK` (catches accidental regressions on the Apache-2.0 license and openai-as-runtime-dep choices). Step 2 ends with `Successfully installed kenya-gazette-parser-0.1.0` (or a line that includes that string). Exit code `0`. No `ResolutionImpossible` errors. |
| **T5** | No regression — notebook still produces identical output | In Jupyter, run the cell that defines `check_regression()` and then call `check_regression()`. | Returns/prints OK (no degradation) for all **6 canonical PDFs** listed in `tests/expected_confidence.json`: `Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`. Gate 1 stays cleared. |

**Bonus check (Gate 3 readiness, not strictly required but recommended):** after T4 succeeds, run `python -c "import kenya_gazette_parser; print(kenya_gazette_parser.__file__)"` and confirm the printed path is inside `kenya_gazette_parser/__init__.py` under the repo (not a stale site-packages copy). This proves the editable install wired up correctly.

**What is explicitly NOT tested in F17 (deferred to F18+):**
- No Pydantic model instantiation (F18).
- No envelope validation (F19).
- No real PDF parsing through the package (F20).
- No `write_envelope` function exists yet (F21).
- No `GazetteConfig` (F22).
- No JSON Schema export (F23).
- No cross-machine `pip install git+...` (F24).

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F17: Package Skeleton**

Read this spec: `specs/F17-package-skeleton.md`.

This is a **skeleton-only** feature. You are not migrating any logic out of the notebook. You are creating five files so that `pip install -e .` works and `from kenya_gazette_parser import __version__, parse_file, parse_bytes` succeeds. The stubs raise `NotImplementedError`. The notebook stays exactly as it is — do not edit it.

**Requirements (do these in order):**

1. **Create the package directory** `kenya_gazette_parser/` at the repo root (sibling of `gazette_docling_pipeline_spatial.ipynb`, `docs/`, `specs/`, `tests/`, `output/`, `pdfs/`).

2. **Create `kenya_gazette_parser/__version__.py`** with the exact contents from Section 2 of the spec. The single line of code is `__version__ = "0.1.0"`.

3. **Create `kenya_gazette_parser/__init__.py`** with the exact contents from Section 2 of the spec. It must:
   - Re-export `__version__` from `kenya_gazette_parser.__version__`.
   - Define `parse_file(path, config=None) -> dict` that always raises `NotImplementedError` whose message contains the literal substrings `"F17"`, `"F20-F21"`, and `"gazette_docling_pipeline_spatial.ipynb"`.
   - Define `parse_bytes(data, *, filename=None, config=None) -> dict` that always raises `NotImplementedError`. The message must contain `"parse_bytes"` so the caller can tell which stub fired (use the `_NOT_IMPLEMENTED_MSG.format(name=...)` pattern from the spec).
   - Set `__all__ = ["__version__", "parse_file", "parse_bytes"]`.
   - The `*,` in `parse_bytes`'s signature is mandatory — `filename` must be keyword-only.

4. **Create `kenya_gazette_parser/py.typed`** as an empty zero-byte file (PEP 561 marker).

5. **Create `pyproject.toml`** at the repo root with the exact contents from Section 2 of the spec. Do not change the dependency lower bounds, the classifiers, or the `[tool.setuptools.packages.find]` block. Do not add a `[tool.setuptools.dynamic]` block — the version is static. Confirm `license = { text = "Apache-2.0" }`, the `License :: OSI Approved :: Apache Software License` classifier, and `openai>=1.40.0` in `[project].dependencies` are present (these are tested by T4). Also write the full Apache 2.0 text to a `LICENSE` file at the repo root (setuptools auto-detects it; the `Copyright 2026 Ronald Wahome` line goes in the Appendix boilerplate near the bottom of the file).

6. **Create `README.md`** at the repo root with the exact contents from the "`README.md` — exact contents" subsection of Section 2. It is required by setuptools because `pyproject.toml` declares `readme = "README.md"`; if missing, `pip install -e .` will fail with a metadata error. Write it with normal triple-backtick fences (the spec wraps the example in four backticks only so the inner code block renders).

7. **Do not create** any of: `setup.py`, `setup.cfg`, `MANIFEST.in`, or any `kenya_gazette_parser/<submodule>/` folders. F18-F21 will create those. (`LICENSE` is created in step 5 above now that the project uses Apache 2.0.)

8. **Do not edit** `gazette_docling_pipeline_spatial.ipynb`. Do not edit `requirements.txt`. Do not edit any file in `output/`, `pdfs/`, or `.llm_cache/`. The only edits outside the five new files are to `PROGRESS.md` (step 15 below).

9. **Install the package** in the project's `.venv` (Windows PowerShell): from the repo root run `.\.venv\Scripts\python.exe -m pip install -e .` (or activate the venv first and run `pip install -e .`). Confirm the install ends with `Successfully installed kenya-gazette-parser-0.1.0` (and may pull `openai`, `docling`, `docling-core` plus their transitives if not already present in the venv).

10. **Run T1 (smoke test):** `.\.venv\Scripts\python.exe -c "import kenya_gazette_parser; assert kenya_gazette_parser.__version__ == '0.1.0'; print('T1 OK', kenya_gazette_parser.__version__)"`. Must print `T1 OK 0.1.0`.

11. **Run T2 (parse_file stub):** the inline Python from Section 3 T2 of the spec. Must print `T2 OK`. If the assertion fails on the message tokens, fix the message in `__init__.py` and retry.

12. **Run T3 (parse_bytes stub):** the inline Python from Section 3 T3 of the spec. Must print `T3 OK`.

13. **Run T4 (pyproject parse + license/openai assertions + install):** the two-step T4 from Section 3 of the spec. Step 1 must print `T4a OK` (asserts name, version, `license.text == "Apache-2.0"`, and `openai` present in dependencies). Step 2 (the `pip install -e .`) is already done in step 9 above, but re-run it once after T1-T3 pass to confirm idempotency.

14. **Run T5 (regression check):** in Jupyter, open `gazette_docling_pipeline_spatial.ipynb`, run the cell defining `check_regression()` (and any setup cells it depends on), then call `check_regression()`. It must report OK for **all 6 canonical PDFs** in `tests/expected_confidence.json`: `Kenya Gazette Vol CXINo 100`, `Kenya Gazette Vol CXINo 103`, `Kenya Gazette Vol CXIINo 76`, `Kenya Gazette Vol CXXVIINo 63`, `Kenya Gazette Vol CXXIVNo 282`, `Kenya Gazette Vol CIINo 83 - pre 2010`. If any PDF degrades, F17 is broken (since F17 changes nothing in the notebook, a regression here means an env / install side effect — investigate before continuing).

15. **Update `PROGRESS.md`** in this exact order of edits:
    - In the **Today** block (top of file), change `**Current:** F17 ...` to `**Current:** F18 — Pydantic models from contract` and update `**Previous:** F16 ...` to `**Previous:** F17 ✅ — Package skeleton (kenya_gazette_parser/ created, pip install -e . works)`.
    - In the **Work Items** table, change F17's row from `⬜ Not started` to `✅ Complete`. Also update F17's "Simple Explanation" cell from the placeholder `Create kenya_gazette/ with pyproject.toml` to `Create kenya_gazette_parser/ with pyproject.toml` (note the rename to the canonical underscore name).
    - In **Quality Gates**, leave Gate 3 as `⬜ Not reached (needs F17)` if `parse_file` is still a stub — Gate 3 only clears when the real implementation lands at F21. Do not flip Gate 3 to cleared in F17.
    - In **Session Log**, append a row: `| 2026-04-20 | F17 Package skeleton | Created kenya_gazette_parser/ with __init__.py (parse_file/parse_bytes stubs), __version__.py (0.1.0), py.typed (PEP 561), pyproject.toml (setuptools backend, Apache-2.0 license, docling+openai runtime deps, dev extra), LICENSE (Apache 2.0 full text), and README.md stub. pip install -e . succeeds. T1-T4 pass. T5 regression PASS for all 6 canonical PDFs. Notebook untouched; LIBRARY_VERSION duplication documented for F20 cleanup. |`

16. **Return a Build Report** in the format below. If any test fails, report the exact failure output and stop — do not move on to F18 yourself; that is the human's call.

**Build Report Format:**

```markdown
# Build Report: F17

## Implementation
- Files created:
  - `kenya_gazette_parser/__init__.py` (~50 lines, stubs + __all__)
  - `kenya_gazette_parser/__version__.py` (1 statement)
  - `kenya_gazette_parser/py.typed` (empty)
  - `pyproject.toml` (~50 lines, setuptools backend, Apache-2.0 license, docling+openai runtime deps, dev extra)
  - `LICENSE` (full Apache 2.0 text with Copyright 2026 Ronald Wahome)
  - `README.md` (~12 lines, alpha stub; required because pyproject.toml declares readme="README.md")
- Files NOT touched: gazette_docling_pipeline_spatial.ipynb, requirements.txt
- Known short-lived duplication: notebook LIBRARY_VERSION="0.1.0" and kenya_gazette_parser.__version__="0.1.0" both hardcoded; F20 will collapse this.

## Install
- Command: `.\.venv\Scripts\python.exe -m pip install -e .`
- Result: Successfully installed kenya-gazette-parser-0.1.0  (or paste the exact final line)

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 — import + version | PASS/FAIL | __version__ == "0.1.0" |
| T2 — parse_file stub | PASS/FAIL | message tokens "F17", "F20-F21", "gazette_docling_pipeline_spatial.ipynb" all present |
| T3 — parse_bytes stub | PASS/FAIL | message contains "parse_bytes" |
| T4 — pyproject + install | PASS/FAIL | tomllib parses; pip install -e . idempotent |
| T5 — regression on 6 PDFs | PASS/FAIL | check_regression() OK for CXINo 100, CXINo 103, CXIINo 76, CXXVIINo 63, CXXIVNo 282, CIINo 83 pre-2010 |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (T5 passes)
- Gate 2 (deterministic notice_id): STILL CLEARED (notebook untouched)
- Gate 3 (`from kenya_gazette_parser import parse_file` works): PARTIALLY UNBLOCKED — import works, but `parse_file()` still raises NotImplementedError; Gate 3 fully clears at F21.

## PROGRESS.md
- F17 row: ⬜ Not started → ✅ Complete
- "Today" moved to F18
- Session Log row appended

## Notes for F18
- Skeleton in place. F18 should add `kenya_gazette_parser/models/` with Pydantic v2 classes from `docs/library-contract-v1.md` section 3 (Envelope, GazetteIssue, Notice, Corrigendum, ConfidenceScores, Provenance, DocumentConfidence, LayoutInfo, Warning, Cost). F18 should bump pyproject.toml dependencies to add `pydantic>=2.0`.
- F20 (logic migration) is the milestone where `parse_file` stops raising and starts working. Until then, callers must use the notebook.

## Final Status: PASS / FAIL
```

---
