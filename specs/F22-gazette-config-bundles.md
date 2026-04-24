# F22 Spec: GazetteConfig + Bundles

## 1. What to Build

Introduce the four config Pydantic models from contract section 5 (`GazetteConfig`, `LLMPolicy`, `RuntimeOptions`, `Bundles`) plus the full eight-key bundle vocabulary, then wire them through `parse_file` / `parse_bytes` / `write_envelope` so callers can pass a config object and select contract-named output bundles. F22 completes milestone M3 by making the public API production-ready: `parse_file(path, config=GazetteConfig(...))` honours the config, and `write_envelope(env, out_dir, bundles=Bundles(notices=True, corrigenda=True, ...))` writes the contract-named files (`{stem}_notices.json`, `{stem}_corrigenda.json`, `{stem}_index.json`, `{stem}_tables.json`, `{stem}_trace.json`, plus the existing `{stem}_spatial_markdown.md` and `{stem}_spatial.txt`). The five legacy F21 bundle keys (`gazette_spatial_json`, `full_text`, `docling_markdown`, `spatial_markdown`, `docling_json`) remain valid for backward compatibility. F21's `NotImplementedError` guard on `config=<non-None>` is replaced with real handling. `images` bundle is declared in the model but raises `NotImplementedError` in F22 (image extraction is post-1.0).

**Scope boundaries (locked):**
- **In scope**: `GazetteConfig`, `LLMPolicy`, `RuntimeOptions`, `Bundles` models; extend `io._ALL_KNOWN_BUNDLES`; new derivation logic for `notices`, `corrigenda`, `document_index`, `tables`, `debug_trace`; remove F21's `NotImplementedError` guard; thread `config` through `parse_file`/`parse_bytes` to `build_envelope`; accept `Bundles` instance in `write_envelope` in addition to dict.
- **Out of scope**: `images` bundle implementation (raises `NotImplementedError` pointing at post-1.0); LLM stage execution (the `LLMPolicy` fields are stored but not acted on — LLM wiring is M5/M6); `RuntimeOptions.deterministic` and `RuntimeOptions.timeout_seconds` enforcement (fields exist but are no-ops until later); `RuntimeOptions.include_full_docling_dict` action (documented as deferred).
- **Invariants**: Gate 1 (regression at 0.05 tolerance) stays cleared; Gate 2 (notice_id stability) stays cleared; F21's five-key dict form still works; no new runtime dependencies; `StrictBase` / `extra="forbid"` pattern continues for all new models.

---

## 2. Interface Contract

### 2a. New files

| File | Purpose | Contents |
|------|---------|----------|
| `kenya_gazette_parser/models/config.py` | Config models | `GazetteConfig`, `LLMPolicy`, `RuntimeOptions` |
| `kenya_gazette_parser/models/bundles.py` | Bundle model | `Bundles` |

Both inherit from `StrictBase` (F18 pattern, `extra="forbid"`).

### 2b. Model definitions (exact — match contract section 5)

```python
# kenya_gazette_parser/models/config.py
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from kenya_gazette_parser.models.base import StrictBase


class LLMPolicy(StrictBase):
    """LLM configuration for optional validation stages.

    F22 declares the fields; actual LLM invocation is M5/M6 work.
    """
    mode: Literal["disabled", "optional", "required"] = "disabled"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    stages: dict[str, bool] = Field(default_factory=dict)
    cache_dir: Path | None = None


class RuntimeOptions(StrictBase):
    """Runtime tuning options.

    F22 declares the fields; `deterministic` and `timeout_seconds` are
    no-ops until post-1.0. `include_full_docling_dict` is also a no-op
    in F22 — reserved for an optimization that threads raw Docling
    artifacts through the pipeline.
    """
    deterministic: bool = False
    timeout_seconds: float | None = None
    include_full_docling_dict: bool = False


class GazetteConfig(StrictBase):
    """Top-level configuration object for parse_file / parse_bytes.

    Example usage::

        config = GazetteConfig(
            llm=LLMPolicy(mode="optional"),
            bundles=Bundles(notices=True, corrigenda=True, document_index=True),
        )
        env = parse_file("gazette.pdf", config=config)
        write_envelope(env, out_dir, bundles=config.bundles, pdf_path="gazette.pdf")
    """
    llm: LLMPolicy = Field(default_factory=LLMPolicy)
    runtime: RuntimeOptions = Field(default_factory=RuntimeOptions)
    bundles: "Bundles" = Field(default_factory=lambda: Bundles())
```

```python
# kenya_gazette_parser/models/bundles.py
from __future__ import annotations

from kenya_gazette_parser.models.base import StrictBase


class Bundles(StrictBase):
    """Which artifact files to write via write_envelope.

    Contract section 5 defines eight bundle names. F22 implements seven
    (images is post-1.0). F21's five legacy keys remain valid via a
    mapping in io.py.

    Bundle -> filename mapping:
        gazette_spatial_json -> {stem}_gazette_spatial.json (F21 legacy, full Envelope)
        notices              -> {stem}_notices.json
        corrigenda           -> {stem}_corrigenda.json
        document_index       -> {stem}_index.json
        full_text            -> {stem}_spatial.txt
        spatial_markdown     -> {stem}_spatial_markdown.md
        tables               -> {stem}_tables.json
        debug_trace          -> {stem}_trace.json
        images               -> NOT IMPLEMENTED (raises NotImplementedError in F22)
        docling_markdown     -> {stem}_docling_markdown.md (F21 legacy)
        docling_json         -> {stem}_docling.json (F21 legacy)
    """
    # Contract section 5 defaults: notices=True, corrigenda=True, others False
    notices: bool = True
    corrigenda: bool = True
    document_index: bool = False
    spatial_markdown: bool = False
    full_text: bool = False
    tables: bool = False
    debug_trace: bool = False
    images: bool = False

    # F21 legacy keys (not in contract section 5 but still supported)
    gazette_spatial_json: bool = True
    docling_markdown: bool = False
    docling_json: bool = False
```

### 2c. `models/__init__.py` extension

Add re-exports so callers can do `from kenya_gazette_parser.models import GazetteConfig, Bundles, ...`:

```python
from kenya_gazette_parser.models.bundles import Bundles
from kenya_gazette_parser.models.config import GazetteConfig, LLMPolicy, RuntimeOptions

__all__ = [
    # existing 12 names from F18
    "Envelope", "GazetteIssue", "Notice", "Corrigendum", "ConfidenceScores",
    "DocumentConfidence", "Provenance", "LayoutInfo", "BodySegment",
    "DerivedTable", "Warning", "Cost",
    # F22 additions
    "GazetteConfig", "LLMPolicy", "RuntimeOptions", "Bundles",
]
```

### 2d. `__init__.py` changes — drop `NotImplementedError`, thread config

Replace the F21 `if config is not None: raise NotImplementedError(...)` guard with real handling:

```python
def parse_file(
    path: "Path | str",
    config: "GazetteConfig | None" = None,
) -> Envelope:
    """Parse a Kenya Gazette PDF into a validated Envelope.

    Parameters
    ----------
    path
        Filesystem path to a .pdf file.
    config
        Optional GazetteConfig. If None, defaults are used (LLM disabled,
        standard bundles). The config is stored but LLM stages are not
        invoked until M5/M6.
    """
    if config is None:
        config = GazetteConfig()
    # In F22, config is validated and stored but not deeply acted upon.
    # LLM invocation, deterministic mode, timeout are M5/M6 work.
    return build_envelope(Path(path), config=config)


def parse_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    config: "GazetteConfig | None" = None,
) -> Envelope:
    """Parse a Kenya Gazette PDF from raw bytes."""
    if config is None:
        config = GazetteConfig()
    stem = (filename or "anonymous.pdf").replace("/", "_").replace("\\", "_")
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    with tempfile.TemporaryDirectory(prefix="kenya_gazette_parser_") as tmp_dir:
        tmp_path = Path(tmp_dir) / stem
        tmp_path.write_bytes(data)
        return build_envelope(tmp_path, config=config)
```

Also add to `__init__.py` re-exports:
```python
from kenya_gazette_parser.models import GazetteConfig, Bundles, LLMPolicy, RuntimeOptions
# expand __all__
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
]
```

### 2e. `pipeline.py` signature change

Extend `build_envelope` to accept `config`:

```python
def build_envelope(
    pdf_path: Path,
    *,
    converter: "DocumentConverter | None" = None,
    include_full_docling_dict: bool = False,
    config: "GazetteConfig | None" = None,
) -> Envelope:
    """Pure-compute path from PDF to validated Envelope.

    Parameters
    ----------
    config
        Optional GazetteConfig. In F22, stored for future LLM/runtime
        features but not acted upon (LLM stages are M5/M6).
    """
    # F22: config is threaded through but LLMPolicy.mode is not invoked.
    # The config could be used in future for deterministic seeding, etc.
    ...
```

### 2f. `io.py` changes — extended bundle vocabulary

#### Bundle key mapping (locked)

| Contract name | Filename template | Derivation logic | F21 legacy? |
|---------------|-------------------|------------------|-------------|
| `gazette_spatial_json` | `{stem}_gazette_spatial.json` | `env.model_dump(mode="json")` | Yes |
| `notices` | `{stem}_notices.json` | `[n.model_dump(mode="json") for n in env.notices]` | No (F22 new) |
| `corrigenda` | `{stem}_corrigenda.json` | `[c.model_dump(mode="json") for c in env.corrigenda]` | No (F22 new) |
| `document_index` | `{stem}_index.json` | Flat summary dict (see below) | No (F22 new) |
| `full_text` | `{stem}_spatial.txt` | Spatial reorder (unchanged) | Yes |
| `spatial_markdown` | `{stem}_spatial_markdown.md` | Highlighted spatial text (unchanged) | Yes |
| `tables` | `{stem}_tables.json` | `[{notice_id, derived_table} for n in env.notices if n.derived_table]` | No (F22 new) |
| `debug_trace` | `{stem}_trace.json` | Warnings + per-notice confidence_reasons | No (F22 new) |
| `images` | `{stem}_images/` | NOT IMPLEMENTED | No (post-1.0) |
| `docling_markdown` | `{stem}_docling_markdown.md` | Docling raw markdown (unchanged) | Yes |
| `docling_json` | `{stem}_docling.json` | Docling raw dict (unchanged) | Yes |

#### `document_index` shape (flat summary for catalog ingest)

```python
{
    "gazette_issue_id": env.issue.gazette_issue_id,
    "pdf_sha256": env.pdf_sha256,
    "library_version": env.library_version,
    "schema_version": env.schema_version,
    "extracted_at": env.extracted_at,  # ISO string
    "n_notices": len(env.notices),
    "n_corrigenda": len(env.corrigenda),
    "n_warnings": len(env.warnings),
    "document_confidence": {
        "layout": env.document_confidence.layout,
        "ocr_quality": env.document_confidence.ocr_quality,
        "notice_split": env.document_confidence.notice_split,
        "composite": env.document_confidence.composite,
        "mean_composite": env.document_confidence.mean_composite,
        "min_composite": env.document_confidence.min_composite,
    },
}
```

#### `debug_trace` shape

```python
{
    "warnings": [w.model_dump(mode="json") for w in env.warnings],
    "layout_info": env.layout_info.model_dump(mode="json"),
    "per_notice_reasons": [
        {"notice_id": n.notice_id, "confidence_reasons": n.confidence_reasons}
        for n in env.notices
    ],
}
```

#### `write_envelope` signature change

```python
def write_envelope(
    env: Envelope,
    out_dir: "Path | str",
    bundles: "Bundles | dict[str, bool] | None" = None,
    *,
    pdf_path: "Path | str | None" = None,
    converter: "DocumentConverter | None" = None,
) -> dict[str, Path]:
    """Materialize bundle files from a validated Envelope.

    F22 accepts both the Bundles Pydantic model and the F21 dict form.
    """
```

When `bundles` is a `Bundles` instance, convert it to dict for internal use:
```python
if isinstance(bundles, Bundles):
    bundles = bundles.model_dump()
```

#### Extend `_ALL_KNOWN_BUNDLES`

```python
_F21_LEGACY_BUNDLES = frozenset({
    "gazette_spatial_json",
    "full_text",
    "docling_markdown",
    "spatial_markdown",
    "docling_json",
})

_F22_CONTRACT_BUNDLES = frozenset({
    "notices",
    "corrigenda",
    "document_index",
    "tables",
    "debug_trace",
    "images",  # declared but raises NotImplementedError
})

_ALL_KNOWN_BUNDLES = _F21_LEGACY_BUNDLES | _F22_CONTRACT_BUNDLES

_ENV_ONLY_BUNDLES = frozenset({
    "gazette_spatial_json",
    "notices",
    "corrigenda",
    "document_index",
    "tables",
    "debug_trace",
})

_RAW_DOCLING_BUNDLES = frozenset({
    "full_text",
    "docling_markdown",
    "spatial_markdown",
    "docling_json",
})
```

#### `images` bundle guard

```python
if bundles.get("images"):
    raise NotImplementedError(
        "images bundle is not implemented in F22. "
        "Image extraction (page thumbnails, notice crops) is post-1.0 work."
    )
```

### 2g. Error handling matrix (consolidated)

| Situation | F22 behavior |
|-----------|--------------|
| `parse_file(path, config=GazetteConfig(...))` | Config validated, stored; parsing proceeds. LLM stages NOT invoked (no-op until M5/M6). |
| `parse_file(path, config={"llm": "optional"})` (plain dict) | Raises `pydantic.ValidationError` — must pass a `GazetteConfig` instance. |
| `write_envelope(env, out_dir, bundles=Bundles(...))` | Bundles converted to dict; writes requested files. |
| `write_envelope(env, out_dir, bundles={"notices": True})` | F21-style dict still works. |
| `write_envelope(..., bundles=Bundles(images=True))` | Raises `NotImplementedError` mentioning post-1.0. |
| `write_envelope(..., bundles={"bogus_key": True})` | Raises `ValueError` (unchanged from F21). |
| `Bundles(unknown_field=True)` | Raises `pydantic.ValidationError` (`extra="forbid"`). |
| `GazetteConfig(llm={"mode": "optional"})` | Pydantic auto-coerces nested dict to `LLMPolicy`. |

---

## 3. Test Cases

Source PDFs: the 6 canonical fixtures from `tests/expected_confidence.json`.

| ID | Scenario | Source | Input | Expected | Why |
|----|----------|--------|-------|----------|-----|
| TC1 | `parse_file` with `GazetteConfig` — modern 2-column | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `env = parse_file(path, config=GazetteConfig(llm=LLMPolicy(mode="disabled")))` | `isinstance(env, Envelope)` is True; `env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"`; `len(env.notices) == 201`; no `NotImplementedError`. | Proves config threading works; replaces F21's stub guard. |
| TC2 | `parse_file` with default `config=None` still works | `pdfs/Kenya Gazette Vol CXINo 100.pdf` | `env = parse_file(path)` (no config arg) | Returns valid `Envelope`; `env.pdf_sha256` is 64-hex; same behavior as F21. | Backward compatibility — F21 callers who don't pass config still work. |
| TC3 | `write_envelope` with `Bundles` instance | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `write_envelope(env, tmp, bundles=Bundles(notices=True, corrigenda=True, document_index=True, gazette_spatial_json=True))` | Returns dict with keys `{"gazette_spatial_json", "notices", "corrigenda", "document_index"}`; all four files exist on disk; `_notices.json` is a JSON array of 201 notice dicts; `_corrigenda.json` is a JSON array; `_index.json` is a flat dict with `gazette_issue_id`, `n_notices=201`. | Proves Bundles model accepted; new derivation logic works. |
| TC4 | `write_envelope` with F21-style dict — backward compat | `pdfs/Kenya Gazette Vol CXIINo 76.pdf` | `write_envelope(env, tmp, bundles={"gazette_spatial_json": True, "full_text": False, ...})` | Returns dict with `{"gazette_spatial_json": <path>}`; only one file in `tmp`. | F21 callers using dict form still work unchanged. |
| TC5 | `Bundles(images=True)` raises `NotImplementedError` | — | `write_envelope(env, tmp, bundles=Bundles(images=True))` | Raises `NotImplementedError` whose message contains `"images"` and `"post-1.0"`. | Guard documented in spec; prevents silent skip. |
| TC6 | `GazetteConfig` with nested LLMPolicy from dict | — | `cfg = GazetteConfig(llm={"mode": "optional", "model": "gpt-4o"})` | `cfg.llm.mode == "optional"`; `cfg.llm.model == "gpt-4o"`; no `ValidationError`. | Pydantic coercion of nested dicts. |
| TC7 | `Bundles` with unknown field raises `ValidationError` | — | `Bundles(mystery_key=True)` | Raises `pydantic.ValidationError` with `extra_forbidden` in error. | `StrictBase` pattern continues. |
| TC8 | `tables` bundle derivation | `pdfs/Kenya Gazette Vol CXXVIINo 63.pdf` | `env = parse_file(path); written = write_envelope(env, tmp, bundles=Bundles(tables=True))` | `_tables.json` exists; is a JSON array; each entry has `notice_id` and `derived_table` keys; len >= 0 (may be 0 if no derived_tables). | Proves tables derivation logic. |
| TC9 | `debug_trace` bundle derivation | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `write_envelope(env, tmp, bundles=Bundles(debug_trace=True))` | `_trace.json` exists; has keys `warnings`, `layout_info`, `per_notice_reasons`; `per_notice_reasons` is array of 201 dicts each with `notice_id` and `confidence_reasons`. | Proves debug_trace derivation. |
| TC10 | Gate 1 regression on 6 canonical PDFs | All 6 | Re-run `check_regression(tolerance=0.05)` after exercising `parse_file(path, config=GazetteConfig())` on each. | Returns `True` for all 6 PDFs. | Regression gate — F22 must not break scoring. |
| TC11 | Gate 2 notice_id stability | All 6 | Compare `notice_id` arrays against F21 on-disk baseline. | Element-wise equal (modulo documented CXXVIINo 63 `std::bad_alloc` tail). | Identity stability gate. |
| TC12 | Import smoke — all 16 models | — | `from kenya_gazette_parser.models import Envelope, ..., GazetteConfig, Bundles, LLMPolicy, RuntimeOptions` | Exits 0; no `ImportError`. | Circular-import guard. |

---

## 4. Implementation Prompt (for Agent 2)

COPY THIS EXACT PROMPT:

---

**Implement F22: GazetteConfig + Bundles**

Read this spec: `specs/F22-gazette-config-bundles.md`. Read `docs/library-contract-v1.md` section 5 — it defines the `GazetteConfig`, `LLMPolicy`, `RuntimeOptions`, `Bundles` shapes and the eight-key bundle vocabulary. Do NOT touch `gazette_docling_pipeline_spatial.ipynb`'s calibration, regression, `confidence_report`, or `enhance_with_llm` cells. Do NOT touch `pyproject.toml` — F22 adds no new dependencies. Do NOT touch anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/expected_confidence.json`. The notebook must keep running end-to-end so Gate 1 (regression on 6 canonical PDFs) stays cleared.

**Core files location:**
- Created: `kenya_gazette_parser/models/config.py`, `kenya_gazette_parser/models/bundles.py`
- Edited: `kenya_gazette_parser/models/__init__.py`, `kenya_gazette_parser/__init__.py`, `kenya_gazette_parser/io.py`, `kenya_gazette_parser/pipeline.py`
- Helper scripts: `scripts/f22_tc*.py`

**Requirements (do these in order):**

1. **Create `kenya_gazette_parser/models/config.py`** per spec section 2b. Classes: `LLMPolicy`, `RuntimeOptions`, `GazetteConfig`. All inherit from `StrictBase`. Use `Field(default_factory=...)` for mutable defaults (`stages: dict`, nested models). Import `Bundles` with a forward reference string to avoid circular import.

2. **Create `kenya_gazette_parser/models/bundles.py`** per spec section 2b. Class: `Bundles`. Inherits from `StrictBase`. Fields for all 11 bundle keys (8 contract + 3 F21 legacy) with contract-specified defaults.

3. **Edit `kenya_gazette_parser/models/__init__.py`** per spec section 2c. Add imports for `Bundles`, `GazetteConfig`, `LLMPolicy`, `RuntimeOptions`. Extend `__all__` to 16 names.

4. **Edit `kenya_gazette_parser/__init__.py`** per spec section 2d:
   - Remove the `if config is not None: raise NotImplementedError(...)` guards from both `parse_file` and `parse_bytes`.
   - Add `if config is None: config = GazetteConfig()` at the top of each function.
   - Pass `config=config` to `build_envelope(...)`.
   - Add `GazetteConfig`, `Bundles`, `LLMPolicy`, `RuntimeOptions` to imports and `__all__`.
   - Update type hints: `config: GazetteConfig | None = None`.

5. **Edit `kenya_gazette_parser/pipeline.py`** per spec section 2e. Add `config: GazetteConfig | None = None` parameter to `build_envelope`. The config is not acted upon in F22 (LLM invocation is M5/M6) but must be accepted without error.

6. **Edit `kenya_gazette_parser/io.py`** per spec section 2f:
   - Extend `_ALL_KNOWN_BUNDLES` with the six F22 contract bundles (`notices`, `corrigenda`, `document_index`, `tables`, `debug_trace`, `images`).
   - Update `_ENV_ONLY_BUNDLES` to include the new env-derivable bundles.
   - At the top of `write_envelope`, handle `bundles` being a `Bundles` instance: `if isinstance(bundles, Bundles): bundles = bundles.model_dump()`.
   - Add `images` guard: if `bundles.get("images")`, raise `NotImplementedError` with message containing `"images"` and `"post-1.0"`.
   - Add derivation logic for each new bundle:
     - `notices`: `json.dumps([n.model_dump(mode="json") for n in env.notices], ...)`
     - `corrigenda`: `json.dumps([c.model_dump(mode="json") for c in env.corrigenda], ...)`
     - `document_index`: flat dict per spec 2f (gazette_issue_id, pdf_sha256, counts, document_confidence subset)
     - `tables`: `json.dumps([{"notice_id": n.notice_id, "derived_table": n.derived_table.model_dump(mode="json")} for n in env.notices if n.derived_table], ...)`
     - `debug_trace`: per spec 2f (warnings, layout_info, per_notice_reasons)
   - Update the type hint on `bundles` parameter to `Bundles | dict[str, bool] | None`.

7. **Write helper scripts** under `scripts/f22_tc*.py`:
   - `scripts/f22_tc1_config_threading.py` (TC1)
   - `scripts/f22_tc2_default_config.py` (TC2)
   - `scripts/f22_tc3_bundles_model.py` (TC3)
   - `scripts/f22_tc4_dict_backward_compat.py` (TC4)
   - `scripts/f22_tc5_images_not_implemented.py` (TC5)
   - `scripts/f22_tc6_nested_coercion.py` (TC6)
   - `scripts/f22_tc7_bundles_extra_forbidden.py` (TC7)
   - `scripts/f22_tc8_tables_derivation.py` (TC8)
   - `scripts/f22_tc9_debug_trace.py` (TC9)
   - `scripts/f22_tc10_regression.py` (TC10)
   - `scripts/f22_tc11_notice_id_stability.py` (TC11)
   - `scripts/f22_tc12_import_smoke.py` (TC12)

8. **Run all 12 test cases in order.** Failure policy: first FAIL stops progress and is reported with full stderr.

9. **Update PROGRESS.md**:
   - **Today** block: change `**Current:** F22 — GazetteConfig + Bundles` to `**Current:** F23 — JSON Schema export`; update `**Previous:**` to `**Previous:** F22 ✅ — GazetteConfig + Bundles (four config models; eight-bundle vocabulary; config threading; backward-compat dict form)`.
   - **Work Items** table: F22 row Status `⬜ Not started` -> `✅ Complete`.
   - **Session Log**: append row with files created/edited, 12 TC results, gates status.

10. **Return the Build Report** (format below). If any TC fails, report the exact failure output and STOP.

**Build Report Format:**

```markdown
# Build Report: F22

## Implementation
- Files created:
  - `kenya_gazette_parser/models/config.py` (LLMPolicy, RuntimeOptions, GazetteConfig)
  - `kenya_gazette_parser/models/bundles.py` (Bundles with 11 keys)
  - `scripts/f22_tc*.py` (12 test scripts)
- Files edited:
  - `kenya_gazette_parser/models/__init__.py` (__all__ expanded to 16)
  - `kenya_gazette_parser/__init__.py` (NotImplementedError guard removed; config threading; __all__ expanded)
  - `kenya_gazette_parser/pipeline.py` (config parameter added)
  - `kenya_gazette_parser/io.py` (Bundles model support; 6 new bundle derivations; images guard)
  - `PROGRESS.md`
- Files NOT touched: `pyproject.toml`, `requirements.txt`, notebook (except PROGRESS.md update)

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| TC1 — parse_file with GazetteConfig | PASS/FAIL | |
| TC2 — parse_file default config=None | PASS/FAIL | |
| TC3 — write_envelope with Bundles model | PASS/FAIL | notices count, corrigenda count, index keys |
| TC4 — write_envelope with dict backward compat | PASS/FAIL | |
| TC5 — images bundle NotImplementedError | PASS/FAIL | |
| TC6 — nested LLMPolicy coercion | PASS/FAIL | |
| TC7 — Bundles extra_forbidden | PASS/FAIL | |
| TC8 — tables derivation | PASS/FAIL | tables count |
| TC9 — debug_trace derivation | PASS/FAIL | per_notice_reasons count |
| TC10 — Gate 1 regression (6 PDFs) | PASS/FAIL | |
| TC11 — Gate 2 notice_id stability | PASS/FAIL | |
| TC12 — import smoke (16 models) | PASS/FAIL | |

## Quality Gates
- Gate 1 (regression): STILL CLEARED
- Gate 2 (notice_id stability): STILL CLEARED
- Gate 3: STILL CLEARED (F21)
- Gate 4: NOT REACHED (needs F23)
- Gate 5: NOT REACHED (needs F24)

## PROGRESS.md
- F22 row: ⬜ Not started → ✅ Complete
- "Today" moved to F23 — JSON Schema export
- Session Log row appended

## Notes for F23
- 16 models now in kenya_gazette_parser.models; JSON Schema export should cover all.
- `images` bundle is declared but raises NotImplementedError — F23 schema should reflect this as an optional field.

## Final Status: PASS / FAIL
```

---

## 8. Open Questions / Risks

**Q1. Should `LLMPolicy` fields be acted upon in F22?** — **Recommend: No (deferred to M5/M6).** F22 declares the fields and threads the config, but `LLMPolicy.mode`, `stages`, `cache_dir` are no-ops. Invoking LLM stages requires significant plumbing (async calls, caching, retry logic) that is out of scope for M3. F22's job is to make the config object exist and pass cleanly; M5/M6 wire the LLM invocation.

**Q2. Should `RuntimeOptions.deterministic` be enforced in F22?** — **Recommend: No.** Deterministic mode would require freezing random seeds, stripping `extracted_at`, and controlling Docling's internal randomness — complex work with edge cases. F22 declares the field; enforcement is post-1.0.

**Q3. Should `RuntimeOptions.include_full_docling_dict` be wired in F22?** — **Recommend: No.** This optimization (single Docling conversion with artifacts threaded through) was flagged in F21 as F22 territory, but it requires changes to `build_envelope`'s return type or an internal cache. Keeping it as a no-op lets F22 focus on the config/bundle API; the optimization lands in a patch or F23+.

**Q4. Should `Bundles` inherit from `StrictBase` (extra="forbid") or allow extra keys for forward compat?** — **Recommend: StrictBase.** Matching F18's pattern keeps the package consistent. Future bundles are additive (new field on `Bundles` = MINOR bump). Unknown keys failing loudly is better than silent no-ops. Callers who want future-proofing should pin versions.

**Q5. Should `images` raise `NotImplementedError` or silently skip?** — **Recommend: Raise.** A loud error is better than a silent skip that leaves callers thinking their images were written. The error message names the post-1.0 roadmap item.

**Q6. Should `write_envelope` accept `Bundles` only or both `Bundles` and dict?** — **Recommend: Both.** F21 callers use dict; forcing them to change is breaking. Accept both: `if isinstance(bundles, Bundles): bundles = bundles.model_dump()`. Dict callers still hit the `_ALL_KNOWN_BUNDLES` guard for unknown keys.

**Q7. Should `GazetteConfig(llm={"mode": "optional"})` (nested dict) be auto-coerced?** — **Recommend: Yes, via Pydantic's default coercion.** Pydantic v2 auto-coerces nested dicts to model instances. No custom validator needed. TC6 verifies this.

**Q8. Should the contract's `spatial_markdown` and `full_text` bundle names replace the F21 keys entirely?** — **Recommend: Keep both.** F21's `full_text` and `spatial_markdown` are already the same as contract names — no rename needed. The F21 legacy keys (`gazette_spatial_json`, `docling_markdown`, `docling_json`) stay valid alongside the new contract keys.

**Q9. Circular import risk — `config.py` imports `Bundles` from `bundles.py`.** — **Recommend: Use forward reference string.** `bundles: "Bundles" = Field(default_factory=lambda: Bundles())` with `from __future__ import annotations` avoids import-time resolution. The import statement `from kenya_gazette_parser.models.bundles import Bundles` at module level is fine because `bundles.py` does not import `config.py`. Alternatively, a late import inside the field's default_factory lambda works.

**Q10. Should `document_index` include `publication_date` and `volume`?** — **Recommend: Yes, add them.** The catalog ingest use case benefits from having issue metadata inline. Extend the spec 2f shape to include `env.issue.volume`, `env.issue.issue_no`, `env.issue.publication_date` (as ISO string or null).
