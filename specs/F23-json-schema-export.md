# F23 Spec: JSON Schema Export

## 1. What to Build

Export a JSON Schema from the 16 Pydantic models that comprise the Kenya Gazette library's output envelope, enabling external tooling and documentation to validate envelopes without loading Python. The primary deliverables are:

1. **A public function `get_envelope_schema() -> dict`** in a new module `kenya_gazette_parser/schema.py` that returns the JSON Schema for the `Envelope` model. Uses Pydantic v2's `model_json_schema()` under the hood. The schema is generated at runtime (not from a cached file) so it always reflects the current model definitions.

2. **A checked-in schema file `kenya_gazette_parser/schema/envelope.schema.json`** containing the canonical JSON Schema for `Envelope`. This file is regenerated during development (via a helper script) and committed so non-Python consumers can access it without calling Python. Includes `$schema`, `$id`, and `title` fields for tooling compatibility.

3. **A validation helper `validate_envelope_json(data: dict) -> bool`** in the same module that validates a raw dict against the generated schema using the `jsonschema` library. Returns `True` on success; raises `jsonschema.ValidationError` on failure (same pattern as Pydantic's `model_validate` — loud errors, not silent failures).

4. **Gate 4 clearance**: after F23, `Envelope` validates against its own JSON Schema on all 6 canonical PDFs. Test cases prove this by loading each `_gazette_spatial.json` from disk and validating via `validate_envelope_json`.

**Scope boundaries (locked):**
- **In scope**: `Envelope` schema (the primary schema for 1.0); `get_envelope_schema()`; `validate_envelope_json()`; checked-in `envelope.schema.json`; optional `get_config_schema()` for the F22 config models.
- **Out of scope**: CLI for schema generation (F26); automatic schema regeneration on model changes (manual via helper script); schema evolution/migration utilities (post-1.0); per-model schema files for `Notice`, `GazetteIssue`, etc. (they are embedded as `$defs` in the Envelope schema).
- **Invariants**: Gate 1 (regression at 0.05 tolerance) stays cleared; Gate 2 (notice_id stability) stays cleared; Gate 3 (parse_file works) stays cleared; no new Pydantic fields added to existing models.

---

## 2. Interface Contract

### 2a. New files

| File | Purpose | Contents |
|------|---------|----------|
| `kenya_gazette_parser/schema.py` | Schema export module | `get_envelope_schema()`, `get_config_schema()`, `validate_envelope_json()` |
| `kenya_gazette_parser/schema/envelope.schema.json` | Checked-in Envelope schema | JSON file generated from `Envelope.model_json_schema()` |
| `kenya_gazette_parser/schema/__init__.py` | Package marker | Empty or minimal (makes `schema/` a subpackage for the JSON file to live alongside) |
| `scripts/f23_regenerate_schema.py` | Dev helper | Regenerates `envelope.schema.json` from current models; run manually after model changes |

### 2b. Public API in `schema.py`

```python
# kenya_gazette_parser/schema.py
"""JSON Schema export for kenya_gazette_parser.

Provides runtime schema generation from Pydantic models and validation helpers.
Gate 4 requires Envelope to validate against its own schema on all canonical PDFs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Lazy import to avoid circular deps and heavy loads at import time
_ENVELOPE_SCHEMA_CACHE: dict | None = None


def get_envelope_schema(*, use_cache: bool = True) -> dict[str, Any]:
    """Return the JSON Schema for the Envelope model.

    Parameters
    ----------
    use_cache
        If True (default), returns a cached schema dict after first call.
        If False, regenerates from the Pydantic model each time.

    Returns
    -------
    dict
        A JSON-serializable dict conforming to JSON Schema Draft 2020-12.
        Contains `$defs` for all nested models (GazetteIssue, Notice, etc.).
    """
    global _ENVELOPE_SCHEMA_CACHE
    if use_cache and _ENVELOPE_SCHEMA_CACHE is not None:
        return _ENVELOPE_SCHEMA_CACHE

    from kenya_gazette_parser.models import Envelope

    schema = Envelope.model_json_schema(mode="serialization")
    # Add standard JSON Schema metadata
    schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
    schema.setdefault("$id", "https://kenya-gazette-parser/schema/envelope.schema.json")
    schema.setdefault("title", "Kenya Gazette Envelope")

    if use_cache:
        _ENVELOPE_SCHEMA_CACHE = schema
    return schema


def get_config_schema() -> dict[str, Any]:
    """Return the JSON Schema for the GazetteConfig model.

    Separate from Envelope because config is input to parse_file, not output.
    """
    from kenya_gazette_parser.models import GazetteConfig

    schema = GazetteConfig.model_json_schema(mode="serialization")
    schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
    schema.setdefault("$id", "https://kenya-gazette-parser/schema/config.schema.json")
    schema.setdefault("title", "Kenya Gazette Config")
    return schema


def validate_envelope_json(data: dict[str, Any]) -> bool:
    """Validate a raw dict against the Envelope JSON Schema.

    Parameters
    ----------
    data
        A dict loaded from a `_gazette_spatial.json` file or produced by
        `Envelope.model_dump(mode="json")`.

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    jsonschema.ValidationError
        If the data does not conform to the Envelope schema.
    jsonschema.SchemaError
        If the schema itself is invalid (should not happen with Pydantic output).
    """
    import jsonschema

    schema = get_envelope_schema()
    jsonschema.validate(instance=data, schema=schema)
    return True


def write_schema_file(
    out_path: Path | str | None = None,
    *,
    model: str = "envelope",
) -> Path:
    """Write the JSON Schema to a file.

    Parameters
    ----------
    out_path
        Output file path. If None, uses the default location:
        `kenya_gazette_parser/schema/{model}.schema.json`.
    model
        Which schema to write: "envelope" (default) or "config".

    Returns
    -------
    Path
        The path to the written file.
    """
    if model == "envelope":
        schema = get_envelope_schema(use_cache=False)
        default_name = "envelope.schema.json"
    elif model == "config":
        schema = get_config_schema()
        default_name = "config.schema.json"
    else:
        raise ValueError(f"Unknown model: {model!r}. Use 'envelope' or 'config'.")

    if out_path is None:
        # Default: kenya_gazette_parser/schema/{model}.schema.json
        out_path = Path(__file__).parent / "schema" / default_name
    else:
        out_path = Path(out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
```

### 2c. `__init__.py` extension

Add re-exports to `kenya_gazette_parser/__init__.py` so callers can do `from kenya_gazette_parser import get_envelope_schema`:

```python
from kenya_gazette_parser.schema import get_envelope_schema, validate_envelope_json

__all__ = [
    "__version__",
    "parse_file",
    "parse_bytes",
    "write_envelope",
    "Envelope",
    "GazetteConfig",
    "Bundles",
    "LLMPolicy",
    "RuntimeOptions",
    # F23 additions
    "get_envelope_schema",
    "validate_envelope_json",
]
```

### 2d. Dependency bump

`pyproject.toml` edit (exact diff in `[project].dependencies`):

```toml
dependencies = [
    "docling>=2.86.0,<3",
    "docling-core>=2.0.0",
    "openai>=1.40.0",
    "pydantic>=2.0",
    "jsonschema>=4.0",
]
```

The `jsonschema` library is the standard Python implementation of JSON Schema validation. Version `>=4.0` supports JSON Schema Draft 2020-12 which Pydantic v2 generates.

### 2e. Checked-in schema file

The file `kenya_gazette_parser/schema/envelope.schema.json` is generated by running:

```bash
python scripts/f23_regenerate_schema.py
```

And committed to version control. The file is NOT auto-generated at runtime; it's a static artifact that non-Python consumers can fetch directly from the repo. The runtime `get_envelope_schema()` function generates an identical schema from the live models.

Format requirements for the checked-in file:
- Pretty-printed with 2-space indent
- UTF-8 encoding
- Trailing newline
- Contains `$schema`, `$id`, `title` at the top level
- `$defs` section with all nested model definitions

### 2f. Error handling matrix

| Situation | F23 behavior |
|-----------|--------------|
| `get_envelope_schema()` called | Returns dict; Pydantic import happens on first call (lazy). |
| `validate_envelope_json(valid_data)` | Returns `True`. |
| `validate_envelope_json(invalid_data)` | Raises `jsonschema.ValidationError` with path to failing field. |
| `validate_envelope_json(data)` where data has extra keys | Depends on schema: Pydantic's `extra="forbid"` translates to `additionalProperties: false` — validation fails. |
| `write_schema_file()` called | Writes file to default location; creates `schema/` dir if missing. |
| `write_schema_file(out_path="custom.json")` | Writes to custom path. |

### 2g. Non-goals for F23

- No CLI (`kenya-gazette schema` command). That is F26 or post-1.0.
- No schema migration between versions (post-1.0).
- No automatic regeneration of `envelope.schema.json` on model changes — run the helper script manually.
- No separate schema files for `Notice.schema.json`, `GazetteIssue.schema.json`, etc. — they are embedded as `$defs` in the Envelope schema.
- No `validate_config_json()` function (GazetteConfig validation is rare; callers use Pydantic directly).

---

## 3. Links to Canonical Docs

| Doc | Section | Why it matters |
|-----|---------|----------------|
| `docs/library-contract-v1.md` | Section 3 (Envelope and Notice Pydantic models) | Defines the 12 core models whose schemas F23 exports. |
| `docs/library-contract-v1.md` | Section 5 (Public API sketch) | Schema export extends the public API. |
| `docs/library-contract-v1.md` | Section 7 (Versioning rules) | `schema_version` field in Envelope ties to JSON Schema. |
| `docs/library-roadmap-v1.md` | M2 block | Mentions "JSON Schemas generated from the Pydantic models, checked into `kenya_gazette/schemas/`". F23 implements this. |
| `docs/library-roadmap-v1.md` | Blueprint 2 (package sketch) | Lists `schemas/` as a target directory for generated JSON Schemas. |
| `PROGRESS.md` | F23 row | Original definition: "Export a JSON Schema from the Pydantic models". |
| `PROGRESS.md` | Quality Gates table | Gate 4: `Envelope` validates against JSON Schema. |
| `specs/F18-pydantic-models-from-contract.md` | Section 2 (Module layout) | Defines the 12 F18 models F23 schemas. |
| `specs/F22-gazette-config-bundles.md` | Section 2b (Model definitions) | Defines the 4 F22 config models F23 optionally schemas. |

---

## 4. Test Cases

Source PDFs: the 6 canonical fixtures. For each, the `output/{stem}/{stem}_gazette_spatial.json` file is loaded and validated.

| ID | Scenario | Source | Input | Expected | Why |
|----|----------|--------|-------|----------|-----|
| TC1 | Schema generation — `get_envelope_schema()` returns valid JSON Schema | — | Call `get_envelope_schema()` | Returns a dict with keys `$schema`, `$id`, `title`, `type`, `properties`, `$defs`; `$defs` contains entries for `GazetteIssue`, `Notice`, `Corrigendum`, etc. (at least 10 `$defs` entries covering nested models); `type == "object"`; `properties` has keys `library_version`, `schema_version`, `output_format_version`, `extracted_at`, `pdf_sha256`, `issue`, `notices`, `corrigenda`, `document_confidence`, `layout_info`, `warnings`, `cost`. | Proves Pydantic's `model_json_schema()` is wired correctly and the schema has the expected structure. |
| TC2 | Validation — all 6 canonical PDFs validate against schema | All 6 canonical PDFs | For each PDF: `data = json.load(open(output/{stem}/{stem}_gazette_spatial.json))`, then `validate_envelope_json(data)` | Returns `True` for all 6 PDFs; no `ValidationError` raised. | **Gate 4 clearance test.** Proves the generated schema matches the actual Envelope output shape. |
| TC3 | Validation failure — invalid envelope raises `ValidationError` | — | `validate_envelope_json({"pdf_sha256": "short"})` (missing required fields, wrong sha length) | Raises `jsonschema.ValidationError`; error message mentions `library_version` or `schema_version` (first missing required field) | Proves validation actually rejects non-conforming data. |
| TC4 | Validation failure — extra field on strict model | — | `validate_envelope_json({**valid_envelope, "unknown_field": "value"})` | Raises `jsonschema.ValidationError` with message mentioning `additionalProperties` or `unknown_field` | Proves `extra="forbid"` from Pydantic's `StrictBase` translates to JSON Schema's `additionalProperties: false`. |
| TC5 | Checked-in schema file matches runtime schema | `kenya_gazette_parser/schema/envelope.schema.json` | Load the checked-in JSON file and compare to `get_envelope_schema(use_cache=False)` | Schemas are equal (deep dict compare, ignoring key order) | Proves the checked-in file is in sync with the models. If this fails, run `python scripts/f23_regenerate_schema.py` and commit. |
| TC6 | Config schema generation | — | Call `get_config_schema()` | Returns a dict with keys `$schema`, `$id`, `title`, `type`, `properties`; `properties` has `llm`, `runtime`, `bundles`; `$defs` contains `LLMPolicy`, `RuntimeOptions`, `Bundles` | Proves the F22 config models also have accessible schemas. |
| TC7 | `write_schema_file()` creates file | Temp directory | `write_schema_file(out_path=tmp / "test.schema.json")` | File exists; contents parse as valid JSON; contains `$schema` key | Proves the helper script can write schemas to disk. |
| TC8 | Import smoke — no circular imports | — | `from kenya_gazette_parser import get_envelope_schema, validate_envelope_json` | Exits 0; no `ImportError` | Proves the schema module doesn't introduce circular imports. |
| TC9 | Gate 1 regression — 6 canonical PDFs still pass `check_regression(0.05)` | All 6 | Run existing regression check | Returns `True` for all 6 PDFs | F23 must not break scoring/regression. |
| TC10 | Round-trip — Envelope.model_dump validates against schema | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `env = parse_file(path); data = env.model_dump(mode="json"); validate_envelope_json(data)` | Returns `True` | Proves fresh Envelope output from `parse_file` validates against the schema. |

---

## 5. Integration Point

### Called by (consumers of F23 API)

- **External tooling** — non-Python consumers can load `envelope.schema.json` from the repo to validate Gazette envelopes.
- **Documentation generators** — tools like `json-schema-to-md` can convert the schema to Markdown docs.
- **CI pipelines** — can validate output JSONs against the schema without loading the full Python library.
- **F24 (install smoke test)** — may use `validate_envelope_json` as part of the smoke test.
- **F25 (README)** — documents the schema export API as a library feature.

### Calls (dependencies)

| Module | Calls into |
|--------|------------|
| `kenya_gazette_parser/schema.py` | stdlib (`json`, `pathlib`, `typing`); `kenya_gazette_parser.models.Envelope`, `kenya_gazette_parser.models.GazetteConfig` (lazy imports); `jsonschema` (external). |

### Side effects

- **`get_envelope_schema()`**: Pure; caches result in module-level variable for performance.
- **`get_config_schema()`**: Pure; no caching.
- **`validate_envelope_json()`**: Pure read; no side effects.
- **`write_schema_file()`**: Writes to disk; creates directories if missing.

### Model wiring

No changes to existing models. F23 only reads model schemas, does not modify them.

---

## 6. Pass/Fail Criteria

| Check | How to verify |
|-------|---------------|
| `get_envelope_schema()` returns valid JSON Schema | TC1 — structure checks |
| All 6 canonical JSONs validate | TC2 — Gate 4 clearance |
| Invalid data raises `ValidationError` | TC3, TC4 |
| Checked-in schema matches runtime | TC5 |
| Config schema accessible | TC6 |
| Schema file can be written | TC7 |
| No circular imports | TC8 |
| Gate 1 regression passes | TC9 |
| Fresh parse output validates | TC10 |
| `pyproject.toml` has `jsonschema>=4.0` | Manual check |
| `kenya_gazette_parser/schema/envelope.schema.json` committed | `git status` shows file |
| `__all__` in `__init__.py` includes new exports | Manual check |

---

## 7. Definition of Done

- [ ] `kenya_gazette_parser/schema.py` created with `get_envelope_schema()`, `get_config_schema()`, `validate_envelope_json()`, `write_schema_file()`.
- [ ] `kenya_gazette_parser/schema/__init__.py` created (package marker).
- [ ] `kenya_gazette_parser/schema/envelope.schema.json` generated and committed.
- [ ] `pyproject.toml` updated to add `jsonschema>=4.0` to dependencies.
- [ ] `kenya_gazette_parser/__init__.py` updated to re-export `get_envelope_schema`, `validate_envelope_json`.
- [ ] `scripts/f23_regenerate_schema.py` created (dev helper).
- [ ] TC1-TC10 all pass.
- [ ] Gate 4 cleared (Envelope validates against JSON Schema on all 6 canonical PDFs).
- [ ] PROGRESS.md row F23 updated to `✅ Complete`; Today moved to F24; Session Log row appended.
- [ ] Quality Gates table: Gate 4 moved from `⬜ Not reached` to `✅ Cleared (F23)`.

---

## 8. Open Questions / Risks

**Q1. Should the schema file live at `kenya_gazette_parser/schema/envelope.schema.json` or `kenya_gazette_parser/schemas/envelope.schema.json` (plural)?** — **Recommend: singular `schema/`.** The roadmap Blueprint 2 says "schemas/" (plural) but singular reads better for a directory that will only ever have 1-2 files (envelope + optionally config). Either works; pick singular for conciseness. The module is `schema.py` (singular) so the sibling directory matching it is natural.

**Q2. Should we include config models (`GazetteConfig`, `LLMPolicy`, `RuntimeOptions`, `Bundles`) in the same schema file or separate?** — **Recommend: separate `config.schema.json` file, optionally generated.** The config models are input to `parse_file`, not part of the output envelope. Mixing them in the same schema would confuse consumers validating envelope output. Provide `get_config_schema()` and `write_schema_file(model="config")` but don't auto-generate `config.schema.json` at initial commit (envelope is the priority). Leave the config schema as an opt-in for users who want it.

**Q3. Should `validate_envelope_json()` be strict (additionalProperties=false) or lenient?** — **Recommend: strict.** Pydantic's `StrictBase` with `extra="forbid"` generates `additionalProperties: false` in JSON Schema. This is intentional — unknown fields in an envelope indicate a version mismatch or data corruption. Consumers who want lenient validation can pass `additional_properties=True` in a custom schema or use Pydantic's `.model_validate()` instead.

**Q4. Should we add `jsonschema` to runtime dependencies or `[dev]` extras?** — **Recommend: runtime dependencies.** The public `validate_envelope_json()` function requires it. If it were dev-only, any user calling `validate_envelope_json()` would hit `ImportError`. The library is small (~1MB) and has no heavy native dependencies.

**Q5. Should `get_envelope_schema()` generate the schema each time or cache it?** — **Recommend: cache by default, with opt-out.** Schema generation involves model introspection which is not free. Caching at module level (after first call) is safe because models don't change at runtime. The `use_cache=False` parameter lets developers regenerate during testing.

**Q6. What JSON Schema draft should we target?** — **Recommend: Draft 2020-12.** Pydantic v2's `model_json_schema()` generates Draft 2020-12 compatible output by default. The `jsonschema` library v4+ supports it. Older drafts (Draft 4, Draft 7) are possible via Pydantic's `schema_generator` kwarg but unnecessary — Draft 2020-12 is the current standard.

**Q7. Should the checked-in schema file include pretty-printing or be minified?** — **Recommend: pretty-printed (2-space indent).** Diff-readability in git is more valuable than the ~2KB size savings from minification. Matches the existing `_gazette_spatial.json` output style.

**Q8. What if a model changes but the schema file is not regenerated?** — **Recommend: TC5 catches this.** The test comparing runtime schema to checked-in file will fail. Developer runs `python scripts/f23_regenerate_schema.py`, commits the updated file. No CI automation in F23 scope; add in F24 or later if needed.

**Q9. Should `DerivedTable`'s `extra="allow"` exception be reflected in the schema?** — **RESOLVED: Yes, automatically.** Pydantic's `model_json_schema()` respects `extra="allow"` and does NOT emit `additionalProperties: false` for `DerivedTable`. The schema will correctly allow extra keys on that model while forbidding them elsewhere.

**Q10. Risk — Pydantic's schema output format may change between Pydantic versions.** — **Mitigated by pinning `pydantic>=2.0`.** Pydantic v2's schema output is stable within the 2.x series. If Pydantic 3 changes the format, that's a major version and would require a library update anyway.

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F23: JSON Schema Export**

Read this spec: `specs/F23-json-schema-export.md`. Read `docs/library-contract-v1.md` section 3 (Envelope models) and section 7 (versioning). Do NOT touch `gazette_docling_pipeline_spatial.ipynb`'s calibration, regression, or scoring cells. Do NOT touch anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/expected_confidence.json`. The notebook must keep running end-to-end so Gate 1 (regression on 6 canonical PDFs) stays cleared.

**Core files location:**
- Created: `kenya_gazette_parser/schema.py`, `kenya_gazette_parser/schema/__init__.py`, `kenya_gazette_parser/schema/envelope.schema.json`, `scripts/f23_regenerate_schema.py`, `scripts/f23_tc*.py`
- Edited: `pyproject.toml`, `kenya_gazette_parser/__init__.py`

**Requirements (do these in order):**

1. **Bump `pyproject.toml` dependencies.** Add `"jsonschema>=4.0"` to `[project].dependencies` after `"pydantic>=2.0"`.

2. **Re-install the package** so the venv picks up jsonschema: `.\.venv\Scripts\python.exe -m pip install -e .`

3. **Create `kenya_gazette_parser/schema/__init__.py`** — empty file or minimal docstring. Makes `schema/` a Python package.

4. **Create `kenya_gazette_parser/schema.py`** per spec section 2b:
   - `get_envelope_schema(*, use_cache: bool = True) -> dict[str, Any]`
   - `get_config_schema() -> dict[str, Any]`
   - `validate_envelope_json(data: dict[str, Any]) -> bool`
   - `write_schema_file(out_path: Path | str | None = None, *, model: str = "envelope") -> Path`
   - Module-level cache `_ENVELOPE_SCHEMA_CACHE`
   - Lazy imports for `kenya_gazette_parser.models` and `jsonschema` to avoid circular deps

5. **Edit `kenya_gazette_parser/__init__.py`** per spec section 2c:
   - Add `from kenya_gazette_parser.schema import get_envelope_schema, validate_envelope_json`
   - Extend `__all__` to include `"get_envelope_schema"`, `"validate_envelope_json"`

6. **Create `scripts/f23_regenerate_schema.py`**:
   ```python
   """Regenerate the checked-in envelope.schema.json file.
   
   Run this after any model changes:
       python scripts/f23_regenerate_schema.py
   Then commit the updated schema file.
   """
   from pathlib import Path
   import sys
   sys.path.insert(0, str(Path(__file__).parent.parent))
   
   from kenya_gazette_parser.schema import write_schema_file
   
   if __name__ == "__main__":
       path = write_schema_file()
       print(f"Wrote: {path}")
   ```

7. **Generate the initial schema file**: Run `python scripts/f23_regenerate_schema.py`. Verify `kenya_gazette_parser/schema/envelope.schema.json` exists and contains valid JSON with `$schema`, `$id`, `title`, `type`, `properties`, `$defs`.

8. **Write test scripts** under `scripts/f23_tc*.py`:
   - `scripts/f23_tc1_schema_structure.py` (TC1)
   - `scripts/f23_tc2_validate_canonical.py` (TC2 — Gate 4)
   - `scripts/f23_tc3_invalid_envelope.py` (TC3)
   - `scripts/f23_tc4_extra_field.py` (TC4)
   - `scripts/f23_tc5_schema_sync.py` (TC5)
   - `scripts/f23_tc6_config_schema.py` (TC6)
   - `scripts/f23_tc7_write_schema.py` (TC7)
   - `scripts/f23_tc8_import_smoke.py` (TC8)
   - `scripts/f23_tc9_regression.py` (TC9)
   - `scripts/f23_tc10_round_trip.py` (TC10)

9. **Run all 10 test cases in order.** Failure policy: first FAIL stops progress and is reported with full stderr.

10. **Update PROGRESS.md**:
    - **Today** block: change `**Current:** F23 — JSON Schema export` to `**Current:** F24 — Installable package smoke test`; update `**Previous:**` to `**Previous:** F23 ✅ — JSON Schema export (get_envelope_schema / validate_envelope_json / envelope.schema.json; jsonschema>=4.0 dep; Gate 4 cleared)`.
    - **Work Items** table: F23 row Status `⬜ Not started` -> `✅ Complete`.
    - **Quality Gates** table: Gate 4 Status `⬜ Not reached (needs F19+F23)` -> `✅ Cleared (F23)`.
    - **Session Log** row: files created/edited, 10 TC results, Gate 4 clearance.

11. **Return the Build Report** (format below). If any TC fails, report the exact failure output and STOP.

**Build Report Format:**

```markdown
# Build Report: F23

## Implementation
- Files created:
  - `kenya_gazette_parser/schema.py` (get_envelope_schema, get_config_schema, validate_envelope_json, write_schema_file)
  - `kenya_gazette_parser/schema/__init__.py` (package marker)
  - `kenya_gazette_parser/schema/envelope.schema.json` (generated, ~N KB)
  - `scripts/f23_regenerate_schema.py`
  - `scripts/f23_tc*.py` (10 test scripts)
- Files edited:
  - `pyproject.toml` (added jsonschema>=4.0)
  - `kenya_gazette_parser/__init__.py` (added schema exports to __all__)
  - `PROGRESS.md`
- Files NOT touched: `gazette_docling_pipeline_spatial.ipynb`, `requirements.txt`, `kenya_gazette_parser/models/*`, anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/`.

## Install
- Command: `.\.venv\Scripts\python.exe -m pip install -e .`
- jsonschema version installed: <exact version>

## Schema Summary
- Envelope schema $defs count: <N> (should be ~10-12)
- Envelope schema properties: <list of top-level property names>
- Schema file size: <N> KB

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| TC1 — schema structure | PASS/FAIL | $defs count, properties check |
| TC2 — validate 6 canonical PDFs (Gate 4) | PASS/FAIL | all 6 pass |
| TC3 — invalid envelope raises | PASS/FAIL | ValidationError raised |
| TC4 — extra field raises | PASS/FAIL | additionalProperties check |
| TC5 — schema sync (checked-in matches runtime) | PASS/FAIL | |
| TC6 — config schema | PASS/FAIL | llm, runtime, bundles properties |
| TC7 — write_schema_file | PASS/FAIL | file created |
| TC8 — import smoke | PASS/FAIL | |
| TC9 — Gate 1 regression | PASS/FAIL | 6/6 within 0.05 |
| TC10 — round-trip validation | PASS/FAIL | fresh Envelope validates |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (TC9 PASS)
- Gate 2 (notice_id stability): STILL CLEARED (no changes to models)
- Gate 3 (parse_file works): STILL CLEARED (no changes to parse_file)
- Gate 4 (Envelope validates against JSON Schema): NOW CLEARED (TC2 PASS)
- Gate 5 (pip install works): NOT REACHED (needs F24)

## PROGRESS.md
- F23 row: ⬜ Not started → ✅ Complete
- "Today" moved to F24 — Installable package smoke test
- Quality Gate 4 cell: ⬜ Not reached → ✅ Cleared (F23)
- Session Log row appended

## Notes for F24
- `jsonschema>=4.0` is now a runtime dependency; F24's `pip install` smoke test should verify it installs correctly.
- `get_envelope_schema()` and `validate_envelope_json()` are public API; F25 README should document them.

## Final Status: PASS / FAIL
```

---
