# F21 Spec: Public API + I/O split

## 1. What to Build

Finish milestone M3 (library-roadmap-v1.md) by wiring the library's public API (`parse_file`, `parse_bytes`) into the F20 pure-compute `pipeline.build_envelope` and lifting every on-disk side effect out of the notebook into a new library function `write_envelope`. After F21, the complete library usage is:

```python
from kenya_gazette_parser import parse_file, write_envelope, Envelope

env = parse_file("pdfs/Kenya Gazette Vol CXXIVNo 282.pdf")     # validated Envelope, no disk writes
write_envelope(env, out_dir=Path("output/Kenya Gazette Vol CXXIVNo 282"), pdf_path=Path("pdfs/Kenya Gazette Vol CXXIVNo 282.pdf"))
```

Concrete deliverables:

1. **Replace the F17 `parse_file` / `parse_bytes` stubs** in `kenya_gazette_parser/__init__.py` with real implementations that call `kenya_gazette_parser.pipeline.build_envelope`. Return type tightens from `dict` (F17) to `Envelope` (F21) — matching the F17 stub's docstring promise ("F18 will tighten it to `Envelope`") and contract section 5 verbatim.
2. **Create `kenya_gazette_parser/io.py`** with `write_envelope(env, out_dir, bundles=None, *, pdf_path=None) -> dict[str, Path]`. This is the single function that writes to disk in 1.0. It materializes up to five named files matching the F20 notebook baseline (`_gazette_spatial.json`, `_spatial.txt`, `_docling_markdown.md`, `_spatial_markdown.md`, `_docling.json`) so Gate 1 (regression) and Gate 2 (notice_id stability) both stay cleared.
3. **Move `highlight_gazette_notices_in_markdown` from the notebook into `kenya_gazette_parser/io.py`** as a private helper `_highlight_gazette_notices_in_markdown`. F20 spec section 2b explicitly deferred this move to F21 ("Revisit when F21 introduces `write_envelope`") — this is that moment.
4. **Collapse the notebook's `GazettePipeline.process_pdf` shim** to literally `env = parse_file(pdf_path); write_envelope(env, out_dir, pdf_path=pdf_path); return env.model_dump(mode="json")`. The double-Docling conversion that F20's shim currently performs (once inside `build_envelope`, once inside the shim for side files) stays — `write_envelope` inherits it when raw-text bundles are requested. Optimizing that re-convert is post-F21.
5. **Expand `kenya_gazette_parser/__init__.py` `__all__`** to include `parse_file`, `parse_bytes`, `write_envelope`, `Envelope`, `__version__`. `from kenya_gazette_parser import Envelope` becomes a supported import at F21 (F18 landed `Envelope` under the `models` submodule; F21 lifts it to the package root).
6. **Clear Quality Gate 3** (`from kenya_gazette_parser import parse_file` works end-to-end): after F21, calling `parse_file("path.pdf")` on any canonical PDF returns a validated `Envelope`. F17 partially cleared Gate 3 (import succeeds); F21 fully clears it (call succeeds and returns a validated Envelope).

**Explicit non-goals for F21** (deferred to F22 or later):
- No `GazetteConfig` / `LLMPolicy` / `RuntimeOptions` / `Bundles` Pydantic models. F22 ships those. F21's `config` parameter on `parse_file` / `parse_bytes` accepts `None` only; passing any non-None value raises `NotImplementedError` with a pointer to F22.
- No new bundle types beyond the five legacy files. Contract section 5 lists eight bundle names (`notices`, `corrigenda`, `document_index`, `spatial_markdown`, `full_text`, `tables`, `debug_trace`, `images`) — F22 wires those. F21's bundle vocabulary is the five file-name stems the notebook already writes (keeps the F20 output tree byte-compatible and lets regression PASS unchanged).
- No renaming of the five legacy files to contract section 5 names (`{stem}_notices.json`, etc.). F22's `Bundles` is the right place to introduce the contract filenames; F21 keeps the F20 filenames so existing consumers of `output/{stem}/` do not break.
- No CLI, no `write_envelope` as a `console_scripts` entrypoint. F26 (post-1.0) introduces the CLI.
- No JSON Schema export. F23 handles that.
- No `pip install git+...` verification on a different machine. F24 handles that.

**Invariants that must survive F21** (regression and identity):
- `check_regression(tolerance=0.05)` returns `True` on all 6 canonical PDFs (Gate 1).
- `notice_id` arrays on the 6 canonical PDFs are element-wise equal to the F20 on-disk baseline, save the documented CXXVIINo 63 `std::bad_alloc` tail-page truncation already noted in PROGRESS.md F20 session log (Gate 2).
- `pdf_sha256` for every canonical PDF is byte-identical to the F20 baseline. `parse_bytes(open(...).read())` and `parse_file(...)` on the same PDF produce identical `pdf_sha256` (Gate 2 extension).
- `Envelope.model_validate` still succeeds on all 6 canonical PDFs — ValidationError propagates uncaught from inside `parse_file` / `parse_bytes`, matching the F19 rule.
- `extracted_at` is the one field legitimately differing across runs (G2); all other fields are byte-stable.
- `Warning` class still shadows Python's built-in; any new F21 code that needs it must alias (`from kenya_gazette_parser.models import Warning as GazetteWarning`) or skip the import (G3).
- `StrictBase` strictness unchanged; F21 adds no new dicts that feed strict models (`write_envelope` consumes a validated `Envelope` — everything downstream is already constrained) (G4).
- F19 self-tracking warnings (`corrigendum_scope_defaulted` total 16, `table_coerced_to_text` total 186) unchanged; F21 touches neither the adapter nor the extractor.

---

## 2. Interface Contract

F21 creates one new module, edits one existing module, and deletes two notebook helpers. The public API surface after F21 is exactly three callables and one model class re-exported at the package root.

### 2a. Target module layout

```
kenya_gazette_parser/
  __init__.py             # EDITED — parse_file/parse_bytes real impls; Envelope re-export; __all__ expanded
  __version__.py          # unchanged from F20
  py.typed                # unchanged
  models/                 # unchanged from F18
    __init__.py
    base.py
    envelope.py
    notice.py
  identity.py             # unchanged from F20
  masthead.py             # unchanged from F20
  spatial.py              # unchanged from F20
  splitting.py            # unchanged from F20
  trailing.py             # unchanged from F20
  corrigenda.py           # unchanged from F20
  scoring.py              # unchanged from F20
  envelope_builder.py     # unchanged from F20
  pipeline.py             # unchanged from F20
  io.py                   # NEW — write_envelope + _highlight_gazette_notices_in_markdown helper
```

### 2b. `kenya_gazette_parser/__init__.py` — real implementations

After F21, `__init__.py` hosts real `parse_file` and `parse_bytes` that wrap `pipeline.build_envelope`, plus the `write_envelope` and `Envelope` re-exports. Exact shape:

```python
"""kenya_gazette_parser - parse Kenya Gazette PDFs into structured envelopes.

Public API (1.0):

- ``parse_file(path)`` — PDF path in, validated :class:`Envelope` out.
- ``parse_bytes(data, *, filename=None)`` — same, but from raw bytes.
- ``write_envelope(env, out_dir, bundles=None, *, pdf_path=None)`` — the only
  function that writes to disk.
- ``Envelope`` — the top-level Pydantic model from :mod:`kenya_gazette_parser.models`.

``parse_*`` functions are pure and never write to disk; callers who want files
call ``write_envelope`` explicitly. See contract section 5.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kenya_gazette_parser.__version__ import __version__
from kenya_gazette_parser.io import write_envelope
from kenya_gazette_parser.models import Envelope
from kenya_gazette_parser.pipeline import build_envelope

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

__all__ = [
    "__version__",
    "parse_file",
    "parse_bytes",
    "write_envelope",
    "Envelope",
]


def parse_file(path: "Path | str", config: Any | None = None) -> Envelope:
    """Parse a Kenya Gazette PDF file into a validated :class:`Envelope`.

    Pure: never writes to disk, never prints. ``ValidationError`` from the
    F19 tail validation propagates uncaught (contract section 5 + F19 rule).

    Parameters
    ----------
    path
        Filesystem path to a ``.pdf`` file. ``str`` or :class:`Path` both work.
    config
        Reserved for F22 (``GazetteConfig``). Must be ``None`` in F21; passing
        any non-None value raises ``NotImplementedError`` pointing at F22.
    """
    if config is not None:
        raise NotImplementedError(
            "parse_file(config=...) is reserved for F22 (GazetteConfig + Bundles). "
            "Pass config=None in F21."
        )
    return build_envelope(Path(path))


def parse_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    config: Any | None = None,
) -> Envelope:
    """Parse a Kenya Gazette PDF from raw bytes into a validated :class:`Envelope`.

    ``filename`` is used only for provenance/warnings — the PDF sha256 is
    computed from ``data`` regardless of filename.

    Implementation writes ``data`` to a temporary file inside a
    ``tempfile.TemporaryDirectory`` (delete-on-exit) and calls
    :func:`build_envelope` on the temp path. Cross-platform; does NOT use
    ``NamedTemporaryFile(delete=True)`` because that path fails on Windows
    when Docling re-opens the file with an exclusive lock.
    """
    if config is not None:
        raise NotImplementedError(
            "parse_bytes(config=...) is reserved for F22 (GazetteConfig + Bundles). "
            "Pass config=None in F21."
        )
    stem = (filename or "anonymous.pdf").replace("/", "_").replace("\\", "_")
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    with tempfile.TemporaryDirectory(prefix="kenya_gazette_parser_") as tmp_dir:
        tmp_path = Path(tmp_dir) / stem
        tmp_path.write_bytes(data)
        return build_envelope(tmp_path)
```

Notes on signature decisions (locked, must not drift):

- **`parse_file(path, config=None) -> Envelope`** — matches contract section 5 verbatim. Return type tightens from F17's `dict` to `Envelope` (F17 stub's docstring promised this).
- **`parse_bytes(data, *, filename=None, config=None) -> Envelope`** — keyword-only `filename` preserved from F17 (pinned by the F17 spec "must not drift" rule).
- **`config=None` check raises `NotImplementedError`**: protects F21 from accidentally shipping a silent no-op config. Callers who pre-write code against F22 will see a clear error and know to wait for F22.
- **Temp-file strategy for `parse_bytes`**: `TemporaryDirectory` is cross-platform safe. Docling's `DocumentConverter.convert(str(path))` expects a readable file path; writing bytes to a temp file and calling through keeps the implementation trivial and avoids Docling-internal bytes-handling.
- **`filename` does NOT affect `pdf_sha256`**: `build_envelope` always calls `compute_pdf_sha256(tmp_path)` on the bytes written to temp. Pass `filename=None` and two callers with the same bytes get the same `pdf_sha256` — required for Gate 2 parity across `parse_file` and `parse_bytes`.
- **`ValidationError` propagates**: no `try/except` around `build_envelope(...)`. F19 rule.
- **`Envelope` re-exported at package root**: `from kenya_gazette_parser import Envelope` becomes supported. Callers who want the full models submodule still have `from kenya_gazette_parser.models import GazetteIssue, Notice, ...`.

### 2c. `kenya_gazette_parser/io.py` — `write_envelope`

New module. Hosts one public function (`write_envelope`) and one private helper (`_highlight_gazette_notices_in_markdown`, moved from the notebook). Exact public signature:

```python
# kenya_gazette_parser/io.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kenya_gazette_parser.models import Envelope
from kenya_gazette_parser.spatial import reorder_by_spatial_position_with_confidence

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter

__all__ = ["write_envelope"]


# F21 bundle vocabulary (five keys). F22 will replace this with a Pydantic
# Bundles model whose names come from contract section 5 (notices, corrigenda,
# document_index, spatial_markdown, full_text, tables, debug_trace, images).
# F21 keeps the F20 filenames byte-for-byte so Gate 1 / Gate 2 stay cleared.
_DEFAULT_BUNDLES: dict[str, bool] = {
    "gazette_spatial_json": True,  # {stem}_gazette_spatial.json — the validated Envelope
    "full_text":            True,  # {stem}_spatial.txt
    "docling_markdown":     True,  # {stem}_docling_markdown.md
    "spatial_markdown":     True,  # {stem}_spatial_markdown.md
    "docling_json":         True,  # {stem}_docling.json
}

_ENV_ONLY_BUNDLES      = frozenset({"gazette_spatial_json"})
_RAW_DOCLING_BUNDLES   = frozenset({"full_text", "docling_markdown", "spatial_markdown", "docling_json"})
_ALL_KNOWN_BUNDLES     = _ENV_ONLY_BUNDLES | _RAW_DOCLING_BUNDLES


def write_envelope(
    env: Envelope,
    out_dir: Path,
    bundles: "dict[str, bool] | None" = None,
    *,
    pdf_path: "Path | str | None" = None,
    converter: "DocumentConverter | None" = None,
) -> dict[str, Path]:
    """Materialize bundle files from a validated :class:`Envelope`.

    Parameters
    ----------
    env
        The validated Envelope (return value of :func:`parse_file` or
        :func:`parse_bytes`).
    out_dir
        Directory to write into. Created with ``parents=True, exist_ok=True``
        if missing. The stem used for filenames comes from the pdf_path's stem
        (or a fallback — see ``pdf_path``).
    bundles
        Dict of ``{bundle_name: bool}``. ``None`` defaults to all five keys
        ``True``. Unknown keys raise ``ValueError``. In F22 this parameter
        will accept a :class:`Bundles` Pydantic model (duck-typed the same way
        — ``bundles.get(name, False)``).
    pdf_path
        Required when any bundle in ``{"full_text", "docling_markdown",
        "spatial_markdown", "docling_json"}`` is requested. ``write_envelope``
        re-invokes Docling on this path to regenerate the raw diagnostic
        payload. Docling conversion is deterministic on the 6 canonical PDFs
        per the F20 baseline; the re-convert matches the F20 shim's double
        conversion and costs ~5-15 seconds per PDF. Optional when only
        ``gazette_spatial_json`` is requested (the Envelope is self-sufficient
        for that bundle).
    converter
        Optional pre-built :class:`DocumentConverter` to reuse when
        ``write_envelope`` re-invokes Docling. ``None`` means construct a new
        one on demand. Reusing a converter across multiple PDFs in the same
        session saves Docling's cold-start time.

    Returns
    -------
    dict[str, Path]
        Mapping from bundle name to the written file path. Only keys for
        bundles that were actually written are present (e.g. if ``bundles``
        set ``full_text=False``, the returned dict has no ``full_text`` key).

    Raises
    ------
    ValueError
        If ``bundles`` contains an unknown key, or if a raw-Docling bundle
        is requested without ``pdf_path``.
    FileNotFoundError
        If ``pdf_path`` is set but the file does not exist.
    """
```

Implementation algorithm (pseudo-code — Agent 2 expands):

```
1. if bundles is None: bundles = _DEFAULT_BUNDLES.copy()
2. unknown = set(bundles) - _ALL_KNOWN_BUNDLES
   if unknown: raise ValueError(f"Unknown bundle keys: {sorted(unknown)}")
3. requested_raw = [k for k, v in bundles.items() if v and k in _RAW_DOCLING_BUNDLES]
   if requested_raw and pdf_path is None:
       raise ValueError(
           f"Bundles {sorted(requested_raw)} require pdf_path; pass "
           f"pdf_path=<path-to-pdf>. Only gazette_spatial_json is derivable "
           f"from the Envelope alone."
       )
4. out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
5. stem = Path(pdf_path).stem if pdf_path is not None else _stem_fallback(env)
   # _stem_fallback derives a stem from env.pdf_sha256[:12] when pdf_path is
   # None. Used only for gazette_spatial_json-only calls.
6. written: dict[str, Path] = {}
7. if bundles.get("gazette_spatial_json"):
       path = out_dir / f"{stem}_gazette_spatial.json"
       path.write_text(
           json.dumps(env.model_dump(mode="json"), ensure_ascii=False, indent=2),
           encoding="utf-8",
       )
       written["gazette_spatial_json"] = path
8. if requested_raw:
       # single Docling conversion, re-used for every raw bundle
       if converter is None:
           from docling.document_converter import DocumentConverter
           converter = DocumentConverter()
       result = converter.convert(str(pdf_path))
       doc = result.document
       doc_dict = doc.export_to_dict()
       if bundles.get("full_text") or bundles.get("spatial_markdown"):
           plain_spatial, _ = reorder_by_spatial_position_with_confidence(doc_dict)
       if bundles.get("full_text"):
           path = out_dir / f"{stem}_spatial.txt"
           path.write_text(plain_spatial, encoding="utf-8")
           written["full_text"] = path
       if bundles.get("docling_markdown"):
           md = doc.export_to_markdown()
           path = out_dir / f"{stem}_docling_markdown.md"
           path.write_text(_highlight_gazette_notices_in_markdown(md), encoding="utf-8")
           written["docling_markdown"] = path
       if bundles.get("spatial_markdown"):
           path = out_dir / f"{stem}_spatial_markdown.md"
           path.write_text(_highlight_gazette_notices_in_markdown(plain_spatial), encoding="utf-8")
           written["spatial_markdown"] = path
       if bundles.get("docling_json"):
           path = out_dir / f"{stem}_docling.json"
           path.write_text(
               json.dumps(doc_dict, ensure_ascii=False, indent=2),
               encoding="utf-8",
           )
           written["docling_json"] = path
9. return written
```

And the private helper lifted verbatim from the notebook (same regex, same style string):

```python
_GAZETTE_NOTICE_MD_LINE = re.compile(
    r"^(\#\# )?(GAZETTE NOTICE NO\. \d+)\s*$",
    re.MULTILINE,
)
_GAZETTE_NOTICE_HIGHLIGHT_STYLE = (
    'style="background-color:#fff3cd;color:#1a1a1a;padding:0.15em 0.35em;'
    'border-radius:3px;font-weight:600;"'
)


def _highlight_gazette_notices_in_markdown(md: str) -> str:
    """Wrap standalone GAZETTE NOTICE NO. lines for Markdown HTML preview."""

    def repl(m: re.Match) -> str:
        notice = m.group(2)
        inner = f'<span {_GAZETTE_NOTICE_HIGHLIGHT_STYLE}>{notice}</span>'
        if m.group(1):
            return f"## {inner}"
        return inner

    return _GAZETTE_NOTICE_MD_LINE.sub(repl, md)


def _stem_fallback(env: Envelope) -> str:
    """Derive a deterministic stem when pdf_path is not provided.

    Used only for gazette_spatial_json-only calls. Format:
    ``{first-12-chars-of-pdf_sha256}``. Mirrors the common "sha-prefix"
    pattern; does not invent a human-readable name.
    """
    return env.pdf_sha256[:12]
```

Notes on `write_envelope` design decisions (locked):

- **Five-key bundle vocabulary** is a deliberate F21 subset of contract section 5's eight-key `Bundles`. The F21 keys map one-to-one to the legacy filenames that F20's shim wrote; F22 will add/rename keys to the contract names (`notices`, `corrigenda`, `document_index`, `tables`, `debug_trace`, `images`) when it introduces the `Bundles` Pydantic model. Keeping F21 narrow means the 6-PDF regression continues to compare byte-for-byte against the F20 output tree (Gate 1).
- **Unknown bundle key raises `ValueError`**: mirrors `StrictBase`'s `extra="forbid"` philosophy — typos or renames cannot silently become no-ops. F22 can widen the set without breaking F21 callers (they pass explicit keys, which F22 keeps valid).
- **`pdf_path` is positional-or-keyword, not positional-only**: allows `write_envelope(env, out_dir, pdf_path=path)` which reads naturally. Keyword-only on the F21 side (`*,` before it) so F22 can insert new positional parameters (e.g. a `GazetteConfig`) between `bundles` and `pdf_path` without breaking F21 callers.
- **Single Docling re-convert per `write_envelope` call**: even if all four raw bundles are requested, Docling runs once. Matches F20 shim behavior (the shim also runs it once).
- **`converter` kwarg for session reuse**: lets a notebook loop over N PDFs pass a shared `DocumentConverter` to avoid N cold-starts. Forward-compatible: F22's `RuntimeOptions` may wrap this.
- **Return type `dict[str, Path]`** matches contract section 5 verbatim.
- **`_highlight_gazette_notices_in_markdown` is private** (underscore-prefixed). The contract section 5 `Bundles` doesn't expose a rendering function; F21 treats it as an internal helper. If F22 or later needs a public API for this, it can unprefix it at that point.
- **`reorder_by_spatial_position_with_confidence` is the single package-internal import** from `io.py`. Dependency graph stays DAG — `io.py` sits next to `pipeline.py` in the "depends on leaves" layer, not at root.
- **No LLM re-validation in F21**: the notebook's `enhance_with_llm` path runs AFTER `process_pdf` today. F22+ can wire LLM into `write_envelope` via `GazetteConfig.llm`.
- **No cost metering in F21**: `Envelope.cost` stays `None` unless already populated. F22's LLM integration is the right place to start tracking cost.
- **No idempotency guarantee across runs**: two `write_envelope` calls on the same `env` overwrite the output files. Callers who want atomicity write to a staging dir and rename.

### 2d. Notebook collapse — `GazettePipeline` after F21

The notebook's F20 shim currently has two Docling conversions (one inside `build_envelope`, one inside the shim for side files) and ~50 lines of disk-write code. After F21, the shim shrinks to:

```python
# gazette_docling_pipeline_spatial.ipynb — post-F21 demo cell
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from kenya_gazette_parser import parse_file, write_envelope


@dataclass
class GazettePipeline:
    """Thin notebook convenience wrapper around parse_file + write_envelope.

    Kept so existing demo cells that do ``pipeline = GazettePipeline()`` and
    ``run_pdfs(pipeline, ...)`` keep working without rewrites. The heavy
    lifting lives in ``kenya_gazette_parser.parse_file`` +
    ``kenya_gazette_parser.write_envelope``.
    """
    converter: DocumentConverter = field(default_factory=DocumentConverter)
    include_full_docling_dict: bool = False  # reserved; routed via write_envelope in F22

    def process_pdf(self, pdf_path: Path) -> dict[str, Any]:
        pdf_path = Path(pdf_path).resolve()
        env = parse_file(pdf_path)
        written = write_envelope(
            env,
            out_dir=OUTPUT_DIR / pdf_path.stem,
            pdf_path=pdf_path,
            converter=self.converter,
        )
        for bundle_name, path in written.items():
            print(f"Wrote: {path}")
        return env.model_dump(mode="json")
```

`run_pdfs`, `run_folder`, `resolve_pdf_selection`, the visual-inspection cells, the `confidence_report` CSV cell, the `enhance_with_llm` cell, the calibration + regression cells all stay — they are notebook UX/tooling, not library logic. `highlight_gazette_notices_in_markdown` (and the `_GAZETTE_NOTICE_MD_LINE` + `_GAZETTE_NOTICE_HIGHLIGHT_STYLE` constants it depends on) are **deleted** from the notebook — the single definition now lives in `kenya_gazette_parser/io.py`.

**Double-Docling-conversion note**: after F21, the shim still re-invokes Docling inside `write_envelope` (for the four raw bundles). This matches F20 shim behavior; regression numbers do not move. Optimizing to a single conversion requires threading raw artifacts through the `Envelope` or a companion object — F22's `RuntimeOptions` or a post-1.0 `parse_file_with_artifacts` helper is the natural home. F21 does NOT attempt it.

### 2e. Public API surface after F21

After F21 lands, these are the full set of names a 1.0 consumer can reach from the top-level package:

| Name | Kind | Source |
|------|------|--------|
| `kenya_gazette_parser.__version__` | `str` constant (F17) | `__version__.py` |
| `kenya_gazette_parser.parse_file` | function (F21 real impl) | `__init__.py` |
| `kenya_gazette_parser.parse_bytes` | function (F21 real impl) | `__init__.py` |
| `kenya_gazette_parser.write_envelope` | function (F21 new) | `io.py` (re-exported) |
| `kenya_gazette_parser.Envelope` | Pydantic model class (F18, F21 re-export) | `models/envelope.py` (re-exported) |

Submodule imports (`from kenya_gazette_parser.models import GazetteIssue, Notice, ...`) still work; F21 does not change the submodule layout — only the root re-exports.

`__all__` on `__init__.py` is the exact five-element list above. `from kenya_gazette_parser import *` pulls exactly these five names.

### 2f. Error handling matrix (consolidated)

| Situation | F21 behavior |
|-----------|--------------|
| `parse_file(path)` where `path` does not exist | Raises `FileNotFoundError` (propagates from Docling or from `compute_pdf_sha256`). Not caught. |
| `parse_file(path, config=<non-None>)` | Raises `NotImplementedError("...reserved for F22...")`. |
| `parse_bytes(data, *, filename=None, config=<non-None>)` | Same as above. |
| `parse_bytes(data=b"")` or zero-byte input | Whatever Docling raises propagates. F21 does not invent a pre-check. |
| `parse_bytes(data=<not-a-pdf>)` | Whatever Docling raises propagates. |
| `Envelope.model_validate` fails inside `build_envelope` | `pydantic.ValidationError` propagates through `parse_file` / `parse_bytes` uncaught. F19 rule. |
| `write_envelope(env, out_dir)` where `out_dir` does not exist | Created with `parents=True, exist_ok=True`. Succeeds. |
| `write_envelope(env, out_dir, bundles={"bogus_key": True})` | Raises `ValueError("Unknown bundle keys: ['bogus_key']")`. |
| `write_envelope(env, out_dir, bundles={"full_text": True})` with `pdf_path=None` | Raises `ValueError` enumerating which bundles need `pdf_path`. |
| `write_envelope(env, out_dir, pdf_path=<nonexistent>)` with any raw bundle | Raises `FileNotFoundError` from Docling. |
| `write_envelope` called after `parse_bytes` (no original file path) | Caller passes `pdf_path=None` and `bundles={"gazette_spatial_json": True}`; succeeds. For raw bundles, caller must persist bytes to disk first. Documented in `write_envelope` docstring. |

No `write_envelope` variant silently swallows errors. No `parse_*` function ever writes to disk.

### 2g. `pyproject.toml` / dependency changes

**None required.** F21 adds no new runtime dependencies. All imports it introduces (`tempfile`, `pathlib`, `re`, `json`) are stdlib; `docling.document_converter.DocumentConverter` is already a pinned runtime dep (F17); `kenya_gazette_parser.models.Envelope`, `kenya_gazette_parser.pipeline.build_envelope`, `kenya_gazette_parser.spatial.reorder_by_spatial_position_with_confidence` are package-internal (F18/F20).

---

## 3. Links to Canonical Docs

| Doc | Section | Why it matters |
|-----|---------|----------------|
| `docs/library-contract-v1.md` | Section 5 (Public API sketch) | Locks the `parse_file` / `parse_bytes` / `write_envelope` signatures F21 implements. |
| `docs/library-contract-v1.md` | Section 3 (`Envelope` model) | `parse_file` return type tightens to `Envelope`; `write_envelope` consumes `Envelope`. |
| `docs/library-contract-v1.md` | Section 7 (Versioning rules) | `write_envelope` writes a dump that must preserve `output_format_version=1` and `schema_version="1.0"` verbatim — no re-stamping by F21. |
| `docs/library-contract-v1.md` | Section 8 Open Question ("`parse_bytes` and hashing") | F21 resolves the "when `filename` is `None`, `pdf_sha256` is still computed from `data`" open item — `parse_bytes` accepts anonymous bytes (see 2b). |
| `docs/library-roadmap-v1.md` | M3 ("I/O split + GazetteConfig + Bundles") | F21 is the first half of M3: `parse_file` / `parse_bytes` / `write_envelope` land. F22 is the second half: `GazetteConfig` / `LLMPolicy` / `RuntimeOptions` / full `Bundles`. |
| `docs/library-roadmap-v1.md` | Blueprint 2 (package sketch) | Confirms `write_envelope` belongs in `__init__.py`-adjacent land; F21 creates `io.py` as the concrete home. |
| `PROGRESS.md` | F21 row (Today) | Original definition: "Wire `parse_file` / `parse_bytes` to call `pipeline.build_envelope`; lift the five `output/{stem}/` file writes from the notebook shim into a `write_envelope` library function (Bundles)." |
| `PROGRESS.md` | Quality Gates table | Gate 3 (`from kenya_gazette_parser import parse_file` works) fully clears at F21. Gates 1, 2, 4, 5 status constraints govern the pass/fail criteria. |
| `PROGRESS.md` | G1-G5 | G1 (0.05 tolerance), G2 (extracted_at excluded from identity), G3 (`Warning` shadows built-in), G4 (`extra="forbid"` everywhere), G5 (orphan notice_id uses line_span not list index) all hold through F21. |
| `specs/F17-package-skeleton.md` | Section 2 (exact stub signatures, `keyword-only filename` lock) | F21 replaces the stubs without drifting the signatures. `config: Any \| None = None` and `*, filename: str \| None = None` stay. |
| `specs/F18-pydantic-models-from-contract.md` | Section 2 (models) | `Envelope` is what `parse_file` returns and what `write_envelope` consumes. `StrictBase` / `extra="forbid"` still applies downstream. |
| `specs/F19-validate-at-end-of-process-pdf.md` | Section 2 ("Strictness, error rule, and write order") | F19 rule: `ValidationError` re-raised, never swallowed — F21 inherits this through `parse_file` / `parse_bytes`. |
| `specs/F20-move-logic-into-modules.md` | Section 2d (`pipeline.build_envelope` signature) | F21's `parse_file` calls `build_envelope(Path(path))` — the exact signature F20 locked. `include_full_docling_dict` stays default-False; F21 does not expose it on `parse_file`. |
| `specs/F20-move-logic-into-modules.md` | Section 2b (notebook helpers NOT moved in F20) | Explicitly lists `highlight_gazette_notices_in_markdown` as deferred to F21. This spec executes that deferred move. |

---

## 4. Test Case Matrix

Source PDFs are the 6 canonical fixtures in `tests/expected_confidence.json`. Baseline `mean_composite` values (carried from F20): CXINo 100 = 0.990, CXINo 103 = 0.989, CXIINo 76 = 0.963, CXXVIINo 63 = 0.977 (F20 measured 0.976 — both within 0.05 tolerance), CXXIVNo 282 = 0.968, CIINo 83 pre-2010 = 0.253. Tolerance stays 0.05 (G1).

All tests run from `.venv\Scripts\python.exe` at repo root. Helper scripts live under `scripts/f21_*.py` following the F18-F20 pattern.

| ID | Scenario | Source | Input | Expected | Why |
|----|----------|--------|-------|----------|-----|
| TC1 | `parse_file` happy path — modern 2-column | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `env = parse_file("pdfs/Kenya Gazette Vol CXXIVNo 282.pdf")` | `isinstance(env, Envelope)` is True; `env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23"`; `len(env.notices) == 201`; `env.document_confidence.mean_composite` within 0.05 of 0.968; `env.output_format_version == 1`; no `ValidationError` | Proves the wired `parse_file` reproduces F20 behaviour on the densest fixture. Same assertions F19/F20 TC1 used. |
| TC2 | `parse_bytes` parity with `parse_file` | `pdfs/Kenya Gazette Vol CXINo 100.pdf` | `data = Path("pdfs/Kenya Gazette Vol CXINo 100.pdf").read_bytes(); env_b = parse_bytes(data, filename="Kenya Gazette Vol CXINo 100.pdf"); env_f = parse_file("pdfs/Kenya Gazette Vol CXINo 100.pdf")` | `env_b.pdf_sha256 == env_f.pdf_sha256`; `[n.notice_id for n in env_b.notices] == [n.notice_id for n in env_f.notices]`; `env_b.issue.gazette_issue_id == env_f.issue.gazette_issue_id`; `env_b.document_confidence.mean_composite == env_f.document_confidence.mean_composite`; both are `Envelope` instances | Proves `parse_bytes` is a byte-equivalent path to `parse_file` — required for Gate 2 extension to raw-bytes ingestion. Also validates the `TemporaryDirectory` temp-file dance on Windows. |
| TC3 | `write_envelope` default bundles — byte-compat with F20 output tree | `pdfs/Kenya Gazette Vol CXXIVNo 282.pdf` | `env = parse_file(...); written = write_envelope(env, out_dir=tmp, pdf_path="pdfs/...CXXIVNo 282.pdf")` | `set(written.keys()) == {"gazette_spatial_json", "full_text", "docling_markdown", "spatial_markdown", "docling_json"}`; all five files exist on disk at the exact F20 filenames (`{stem}_gazette_spatial.json`, `{stem}_spatial.txt`, `{stem}_docling_markdown.md`, `{stem}_spatial_markdown.md`, `{stem}_docling.json`); `json.load(written["gazette_spatial_json"])["notices"][0]["notice_id"]` matches F20 on-disk baseline's `notices[0].notice_id`; the four text/markdown files are byte-identical to F20 baseline (excepting any `extracted_at` that leaked into the JSON — only the JSON bundle carries `extracted_at`, the four raw bundles do not) | Proves the five-file output tree survives the move from notebook shim into `write_envelope`. Gate 1 continues to clear on the 6-PDF regression because the files consumed by `check_regression()` are byte-stable. |
| TC4 | `write_envelope` selective bundles — only `gazette_spatial_json` | `pdfs/Kenya Gazette Vol CXIINo 76.pdf` | `env = parse_file(...); written = write_envelope(env, out_dir=tmp, bundles={"gazette_spatial_json": True, "full_text": False, "docling_markdown": False, "spatial_markdown": False, "docling_json": False})` | `written == {"gazette_spatial_json": tmp / "Kenya Gazette Vol CXIINo 76_gazette_spatial.json"}`; `list(tmp.iterdir())` has exactly one file (the JSON); `pdf_path=None` was NOT passed and no `ValueError` was raised (env-only bundle doesn't need it) | Proves the `bundles` dict API filters correctly and the env-only shortcut works. Covers the "library caller who just wants the JSON and consumes notices in-process" scenario (contract section 6 "Minimal offline" example). |
| TC5 | `write_envelope` error — raw bundle without `pdf_path` | `pdfs/Kenya Gazette Vol CXINo 103.pdf` | `env = parse_file(...); write_envelope(env, out_dir=tmp, bundles={"full_text": True}, pdf_path=None)` | Raises `ValueError` whose message contains `"full_text"` and `"pdf_path"` | Proves the error-handling matrix (row "raw bundle + pdf_path=None") is enforced; caller gets an actionable message instead of a silent skip or a confusing Docling error. |
| TC6 | `write_envelope` error — unknown bundle key | — | `write_envelope(env, out_dir=tmp, bundles={"bogus_key": True})` | Raises `ValueError` whose message contains `"bogus_key"` | Proves the `_ALL_KNOWN_BUNDLES` guard catches typos; mirrors `StrictBase`'s `extra="forbid"` philosophy at the I/O boundary. |
| TC7 | `parse_file(config=<non-None>)` raises `NotImplementedError` | — | `parse_file("pdfs/Kenya Gazette Vol CIINo 83 - pre 2010.pdf", config={"llm": "optional"})` | Raises `NotImplementedError` whose message contains `"F22"` and `"GazetteConfig"` | Prevents F21 from silently accepting a config that does nothing. Forward-compatibility guard for F22. Same check for `parse_bytes(data, config=...)`. |
| TC8 | Gate 1 regression on 6 canonical PDFs via the new notebook shim | All 6 canonical PDFs in `pdfs/` | Re-run the notebook demo cell (`run_pdfs(GazettePipeline(), CANONICAL_PDFS)`); then `check_regression(tolerance=0.05)` | Returns `True` for all 6 PDFs. Per-PDF `mean_composite` within 0.05 of F20 baseline (CXINo 100 = 0.990, CXINo 103 = 0.989, CXIINo 76 = 0.963, CXXVIINo 63 = 0.977, CXXIVNo 282 = 0.968, CIINo 83 pre-2010 = 0.253) | Gate 1 — the non-negotiable quality gate. If TC8 fails, F21 broke something in the collapse from shim to `write_envelope`. |
| TC9 | Gate 2 notice_id stability across F20 -> F21 | All 6 canonical PDFs | For each PDF: read the F20 on-disk baseline `output/{stem}/{stem}_gazette_spatial.json`; re-run via the new shim; compare `[n["notice_id"] for n in old["notices"]]` element-wise to the new envelope's notice_ids, excluding `extracted_at` (G2) | Lists match exactly for 5/6 PDFs. CXXVIINo 63 produces the documented 146-id strict prefix of the 153-id baseline (same G1 OCR non-determinism behavior noted in F20 session log); not a regression | Gate 2 — notice_id byte stability. Because `build_envelope` is unchanged in F21 and `parse_file` is a one-line wrapper, the notice_id values must be byte-identical (modulo the documented CXXVIINo 63 std::bad_alloc tail). |
| TC10 | Gate 3 clears — `from kenya_gazette_parser import parse_file` works end-to-end | `pdfs/Kenya Gazette Vol CIINo 83 - pre 2010.pdf` (chosen because it's the OCR-heavy pre-2010 scanned edge case — the most fragile fixture) | `python -c "from kenya_gazette_parser import parse_file, write_envelope, Envelope; env = parse_file('pdfs/Kenya Gazette Vol CIINo 83 - pre 2010.pdf'); assert isinstance(env, Envelope); assert len(env.notices) == 1; print('TC10 OK')"` | Exits 0, prints `TC10 OK`. No `ImportError`, no `NotImplementedError`, no `ValidationError` | Gate 3 fully clears (F17 partially cleared it on import; F21 clears the "works end-to-end" part). |
| TC11 | Notebook-source scan — notebook no longer hosts `highlight_gazette_notices_in_markdown` | `gazette_docling_pipeline_spatial.ipynb` | `grep -n 'def highlight_gazette_notices_in_markdown\|_GAZETTE_NOTICE_MD_LINE\|_GAZETTE_NOTICE_HIGHLIGHT_STYLE' gazette_docling_pipeline_spatial.ipynb` on `"source"` strings | Zero matches in source cells; the helper and its two supporting regex/style constants have moved into `kenya_gazette_parser/io.py`. Matches in `"outputs"` (from pre-F21 runs) do not count | Proves F20's deferred "Revisit when F21 introduces `write_envelope`" work actually landed; the notebook has exactly one copy of the helper, not two. |
| TC12 | Import-smoke for `io.py` and updated `__init__.py` | — | `python -c "from kenya_gazette_parser import parse_file, parse_bytes, write_envelope, Envelope, __version__; import kenya_gazette_parser.io as io_mod; assert 'write_envelope' in io_mod.__all__"` | Exits 0. No `ImportError`. `__all__` on both modules includes the expected names | Cheap circular-import and typo guard. Catches Open Question Q4 (circular-import risk from `io.py` -> `spatial.py`) if it materializes. |

Minimum required: TC1-TC8. TC9 (Gate 2), TC10 (Gate 3), TC11 (notebook collapse verification), TC12 (import smoke) are added because F21 is the public-API-surface feature and the two quality gates plus the notebook-collapse are the explicit `Done when` criteria from PROGRESS.md.

**Helper scripts** (one per test where scripted, following the F19/F20 pattern):

- `scripts/f21_tc1_parse_file_happy.py` (TC1)
- `scripts/f21_tc2_parse_bytes_parity.py` (TC2)
- `scripts/f21_tc3_write_envelope_default.py` (TC3)
- `scripts/f21_tc4_write_envelope_selective.py` (TC4)
- `scripts/f21_tc5_tc6_write_envelope_errors.py` (TC5 + TC6 combined — both are ValueError cases)
- `scripts/f21_tc7_config_not_implemented.py` (TC7)
- `scripts/f21_tc8_regression.py` (TC8 — subprocess-per-PDF mirror of F20's `scripts/f20_run_pipeline.py` to avoid the documented CXXVIINo 63 `std::bad_alloc`)
- `scripts/f21_tc9_notice_id_stability.py` (TC9)
- `scripts/f21_tc10_gate3.py` (TC10)
- `scripts/f21_tc11_grep_notebook.py` (TC11)
- `scripts/f21_tc12_import_smoke.py` (TC12)

TC11 is a simple grep; TC12 is inline `python -c`.

---

## 5. Integration Point

### Called by (consumers of F21-produced API)

- **Notebook demo cell** — `GazettePipeline.process_pdf` shrinks to `parse_file(pdf_path)` + `write_envelope(env, out_dir, pdf_path=pdf_path)`. `run_pdfs`, `run_folder`, `resolve_pdf_selection` unchanged.
- **External library consumers** — after F21, any Python caller can do `from kenya_gazette_parser import parse_file, write_envelope, Envelope` and parse a PDF with two function calls. Required for F24 (installable smoke test) and F25 (README quickstart).
- **F22 (next feature)** — `GazetteConfig` / `LLMPolicy` / `RuntimeOptions` / full `Bundles` Pydantic models. F22 wires them through by:
  - Accepting a non-None `config` on `parse_file` / `parse_bytes` (removing F21's `NotImplementedError` guard).
  - Accepting a `Bundles` instance in addition to the plain dict on `write_envelope`.
  - Widening the `_ALL_KNOWN_BUNDLES` set with the contract's eight names.
  - Adding a `config.runtime.include_full_docling_dict` hookup into `build_envelope`.
  F22 must not break any F21 caller; `config=None` and `bundles=<dict>` continue to work.

### Calls (dependencies each new / edited module has)

| Module | Calls into |
|--------|------------|
| `kenya_gazette_parser/__init__.py` (edited) | stdlib (`tempfile`, `pathlib`, `typing`); `kenya_gazette_parser.__version__.__version__`; `kenya_gazette_parser.io.write_envelope`; `kenya_gazette_parser.models.Envelope`; `kenya_gazette_parser.pipeline.build_envelope`. No direct `docling` import (kept lazy inside `build_envelope` / `write_envelope`). |
| `kenya_gazette_parser/io.py` (new) | stdlib (`json`, `re`, `pathlib`, `typing`); `kenya_gazette_parser.models.Envelope`; `kenya_gazette_parser.spatial.reorder_by_spatial_position_with_confidence`; lazy `docling.document_converter.DocumentConverter` inside `write_envelope` (only imported when a raw bundle is requested and `converter is None`). |

Dependency graph stays a DAG:

```
__init__.py
  -> io.py
       -> spatial.py (stdlib-only)
       -> models (stdlib-only)
  -> pipeline.py
       -> identity, masthead, spatial, splitting, trailing, corrigenda, scoring,
          envelope_builder, models (all as in F20)
  -> models
```

No cycles. `io.py` and `pipeline.py` are peers; neither imports the other. `__init__.py` imports both.

### Side effects

- **`parse_file` / `parse_bytes`**: zero side effects by design. No disk writes, no logs, no warnings (except the envelope-internal warnings list, which is not a side effect). Pure functions.
- **`parse_bytes` writes a temp file** into a `TemporaryDirectory` that is auto-deleted on context exit. No persisted side effect.
- **`write_envelope`**: the only function that writes to disk. Creates `out_dir` if missing (`parents=True, exist_ok=True`). Writes up to five files with deterministic names. Does not touch any path outside `out_dir`. No caches, no logs, no network.
- **Notebook**: retains its current UX prints ("Wrote: <path>") via the shim iterating over the `written` dict. Regenerating output/{stem}/ trees is a regression-test prerequisite and expected.

### Model wiring

- `Envelope` — return type of `parse_file` / `parse_bytes`; input to `write_envelope`. Populated exactly as in F20 (no field shape change). The JSON bundle is `env.model_dump(mode="json")` — no re-serialization magic.
- `GazetteIssue`, `Notice`, `Corrigendum`, `LayoutInfo`, `Warning`, `Cost`, `DocumentConfidence`, `ConfidenceScores`, `Provenance`, `BodySegment`, `DerivedTable` — unchanged.
- No new `Warning.kind` values in F21. The three existing ones (`masthead.parse_failed`, `corrigendum_scope_defaulted`, `table_coerced_to_text`) keep emitting through `build_envelope` unchanged.
- `output_format_version` still hard-coded `1` inside `envelope_builder.build_envelope_dict`. F21 does not touch the adapter.

---

## 6. Pass/Fail Criteria

| Check | How to verify |
|-------|---------------|
| `parse_file` returns `Envelope` on canonical PDF | TC1 |
| `parse_bytes` parity with `parse_file` | TC2 (pdf_sha256, notice_id list, gazette_issue_id, mean_composite all equal) |
| `write_envelope` default writes five legacy files | TC3 (set of written keys, files exist on disk, F20 baseline parity on the four non-JSON files) |
| `write_envelope` bundle selection filters correctly | TC4 (only requested keys in `written`, only one file on disk) |
| `write_envelope` guards missing `pdf_path` for raw bundles | TC5 (`ValueError` with actionable message) |
| `write_envelope` guards unknown bundle keys | TC6 (`ValueError` mentioning the typo) |
| `parse_file(config=...)` guards F22 forward-compat | TC7 (`NotImplementedError` mentioning F22) |
| Regression still clears (Gate 1) | TC8 (`check_regression(0.05) == True` on 6 PDFs) |
| Notice_id stability (Gate 2) | TC9 (element-wise compare against F20 on-disk baseline) |
| Gate 3 fully clears | TC10 (`from kenya_gazette_parser import parse_file` + call + `isinstance(env, Envelope)`) |
| Notebook `highlight_*` helper moved, not copied | TC11 (grep returns zero source matches) |
| Imports clean; no circular | TC12 (smoke import) |
| `output_format_version` still stamped `1` | TC1 + TC3 both assert `env.output_format_version == 1` and that the JSON file on disk has the same value |
| `schema_version` still `"1.0"`, `library_version` still `"0.1.0"` | TC1 assertions on `env.schema_version == "1.0"` and `env.library_version == "0.1.0"` |
| Idempotency | Two consecutive `parse_file(path)` calls produce envelopes equal on every field except `extracted_at` (G2); two consecutive `write_envelope(env, out_dir)` calls produce byte-identical files |
| No `Warning` shadowing (G3) | `io.py` and the edited `__init__.py` do NOT import `Warning` from `kenya_gazette_parser.models`. Grep proves it: `grep -rn 'from kenya_gazette_parser.models import .*Warning' kenya_gazette_parser/__init__.py kenya_gazette_parser/io.py` returns zero matches |
| No new `extra` keys leak (G4) | `write_envelope` consumes a validated `Envelope` — everything downstream is already strict. Nothing in `io.py` constructs a `StrictBase` subclass |

---

## 7. Definition of Done

- [ ] `kenya_gazette_parser/io.py` created with `write_envelope` + `_highlight_gazette_notices_in_markdown` + `_stem_fallback`. `__all__ = ["write_envelope"]`.
- [ ] `kenya_gazette_parser/__init__.py` edited: real `parse_file` + real `parse_bytes` + re-export of `write_envelope` + re-export of `Envelope`. `__all__` = `["__version__", "parse_file", "parse_bytes", "write_envelope", "Envelope"]`.
- [ ] F17 `_NOT_IMPLEMENTED_MSG` constant deleted from `__init__.py`.
- [ ] Notebook `GazettePipeline.process_pdf` collapsed to `parse_file` + `write_envelope` per 2d.
- [ ] Notebook `highlight_gazette_notices_in_markdown` and its two supporting constants (`_GAZETTE_NOTICE_MD_LINE`, `_GAZETTE_NOTICE_HIGHLIGHT_STYLE`) deleted from source cells (TC11 grep returns zero matches).
- [ ] TC1-TC12 all pass.
- [ ] `check_regression(tolerance=0.05)` returns `True` on all 6 canonical PDFs (Gate 1).
- [ ] Gate 2 holds: notice_id arrays element-wise equal to F20 on-disk baseline (modulo documented CXXVIINo 63 `std::bad_alloc` tail).
- [ ] Gate 3 fully clears (TC10).
- [ ] Gate 4, Gate 5 unchanged (F23 / F24 respectively — out of scope for F21).
- [ ] `pyproject.toml` untouched (F21 adds no new deps).
- [ ] PROGRESS.md row F21 updated to `✅ Complete`; Today moved to F22 — GazetteConfig + Bundles; Session Log row appended.
- [ ] Quality Gates table: Gate 3 moved from `⬜ Partially unblocked` to `✅ Cleared`.
- [ ] Build Report notes the double-Docling re-convert survives into F21 (matches F20) and flags it as a post-1.0 optimization for F22's `RuntimeOptions`.

---

## 8. Open Questions / Risks

Answered here with recommended resolutions. Agent 0 drives the human checkpoint off this section — each Q below has either a recommended answer (for the builder to accept or override) or a RESOLVED marker (for items the spec already locks).

**Q1. Does `parse_file` return `Envelope` or `dict` in F21?** — **Recommend: `Envelope`.** The F17 stub docstring explicitly said "F18 will tighten it to `Envelope`" (ref spec F17 section 2, `_NOT_IMPLEMENTED_MSG` + `parse_file` docstring). Contract section 5 locks `-> Envelope`. Returning `dict` would require callers to do `Envelope.model_validate(result)` themselves, defeating the point of F18-F19. Callers who need a dict do `env.model_dump(mode="json")` — one line.

**Q2. F21 `config` parameter — raise on non-None, or silently accept and ignore?** — **Recommend: raise `NotImplementedError` with a message pointing at F22.** Silently ignoring is worse: a caller who pre-writes code against F22's `GazetteConfig` would get silent no-ops in F21 and rude surprises when F22 starts honoring the config. Loud failure is safer. F22 removes the guard; the argument name and typing stay stable.

**Q3. `parse_bytes` — require `filename` or accept anonymous bytes?** — **Recommend: accept anonymous bytes.** Contract section 8 Open Question ("`parse_bytes` and hashing") explicitly flags this as "decide whether to require `filename` or accept anonymous bytes". Accepting anonymous bytes keeps the API flexible for in-memory pipelines (e.g. S3 byte streams) at the cost of a slightly less informative warning when `filename=None`. `pdf_sha256` is computed from bytes so content identity is preserved; only `Warning.where.pdf_file_name` loses information, which is annotation-only. If F24 smoke tests or F25 README need filename-carrying calls, they pass `filename=`.

**Q4. `write_envelope` + raw-text bundles — where does the raw Docling text come from?** — **Recommend: `write_envelope` re-invokes Docling when any raw bundle is requested AND `pdf_path` is provided.** The alternative (thread artifacts through the Envelope) breaks `StrictBase` or adds a non-contract field. The alternative (return `tuple[Envelope, Artifacts]` from `parse_file`) breaks the contract section 5 signature. Re-invoking Docling matches the F20 shim's current double conversion (zero regression cost) and keeps `parse_file` pure. F22 or a post-1.0 helper can optimize to single-conversion via `RuntimeOptions` or a `parse_file_with_artifacts` private function. F21 keeps the 2-convert cost.

**Q5. Circular-import risk — does `io.py` importing from `spatial.py` risk a cycle?** — **RESOLVED: no.** `spatial.py` is stdlib-only (F20 spec section 5); it does not import from `io.py`, `pipeline.py`, or anything upward. Graph stays a DAG. TC12 (import smoke) catches any regression if a later edit adds an upward edge.

**Q6. Five bundle names vs eight bundle names — does F21 adopt the contract's `Bundles` vocabulary early?** — **Recommend: no. Keep the five legacy-filename keys in F21 (`gazette_spatial_json`, `full_text`, `docling_markdown`, `spatial_markdown`, `docling_json`).** The contract's eight names (`notices`, `corrigenda`, `document_index`, `spatial_markdown`, `full_text`, `tables`, `debug_trace`, `images`) describe a future shape that requires new derivation logic (e.g. `document_index` is a flat-record CSV-ready summary; `tables` is `derived_table` extraction; `debug_trace` is a reason aggregator; `images` requires image rendering). Building all that in F21 bloats the feature past its PROGRESS.md scope ("lift the five `output/{stem}/` file writes"). F22 introduces the full eight-name `Bundles` Pydantic model and the new derivations. F21's five-key dict is forward-compatible: F22 renames/adds keys in `_ALL_KNOWN_BUNDLES` without breaking F21 callers (who pass explicit keys, which stay valid by design).

**Q7. Should F21 delete `GazettePipeline` entirely or keep a thin shim?** — **Recommend: keep a thin shim** (per 2d). Reason: existing demo cells (`pipeline = GazettePipeline(); run_pdfs(pipeline, CANONICAL_PDFS)`) would require rewrites if `GazettePipeline` vanished — scope creep for the notebook surgery. The shim is ~15 lines of `parse_file` + `write_envelope` glue; it's a convenience wrapper, not a maintenance burden. F22 may choose to kill it when `GazetteConfig` lands (at which point demo cells use `parse_file(pdf, config=GazetteConfig(...))` directly). F21 does not preemptively strip it.

**Q8. `highlight_gazette_notices_in_markdown` — move it to `io.py` private, or to a new `rendering.py` module?** — **Recommend: move to `io.py` as `_highlight_gazette_notices_in_markdown`.** A new module per rendering helper is premature abstraction — today it's one 10-line function with two supporting constants. If M5 (richer body segments) or F22 (more bundles) adds a second rendering helper, that's the right moment to spin up `rendering.py`. Packing it into `io.py` private alongside `write_envelope` is correct for F21 and matches F20 spec section 2b's deferred guidance ("Revisit when F21 introduces `write_envelope`").

**Q9. Windows temp-file dance — `NamedTemporaryFile(delete=True)` or `TemporaryDirectory`?** — **RESOLVED: `TemporaryDirectory`.** `NamedTemporaryFile(delete=True)` on Windows fails when Docling re-opens the file with an exclusive lock (documented Windows-specific quirk: the underlying Win32 handle must be closed before another process can open the file). `TemporaryDirectory` sidesteps this because we create a named child file, close our handle immediately after writing, and let Docling open it fresh; cleanup on context exit removes both the file and the directory. Cross-platform safe.

**Q10. `write_envelope` atomicity — should it stage writes to a `.tmp` directory and rename at the end?** — **Recommend: no for F21.** Atomicity adds complexity (rename semantics differ across OS, and we'd need to handle partial `output/{stem}/` trees mid-stage) for a concern the current notebook doesn't handle either. If a mid-write crash leaves partial files, re-running `write_envelope` overwrites cleanly. If a consumer needs atomicity (e.g. a production ingest pipeline), they stage to a temp dir and rename the whole `{stem}/` folder themselves. Revisit in F22 or when F24's install-smoke-test requires it.

**Q11. Double-Docling conversion — is it acceptable to re-convert inside `write_envelope` after `parse_file` already converted?** — **Recommend: yes for F21.** F20's notebook shim already does this; regression numbers are flat. The cost is ~5-15 seconds per PDF on the 6-PDF regression run (noticeable in aggregate but acceptable for a notebook demo; not a bottleneck for library callers who skip raw bundles). F22's `RuntimeOptions.include_full_docling_dict` + an internal artifact cache is the natural optimization path. F21 flags this in the Build Report notes-for-F22 so it does not slip.

**Q12. Notebook-side deletion — should the F11 `test_parse_masthead()` inline smoke-test cell (line 178 area) and similar test cells stay in the notebook?** — **RESOLVED: out of scope for F21.** F20 spec 2g marked those cells "Implementer choice: keep as documentation of the F11 fixtures OR delete". F21 does not touch them either way. Scope creep prevention.

**Q13. Does `write_envelope` accept a `Path` or `str` for `out_dir`?** — **Recommend: both, via `Path` coercion at the top of the function.** Matches Python norms (`Path | str` inputs, `Path` outputs). Mirrors `parse_file`'s `path: Path | str` signature. Tests pass either form.

**Q14. Should `write_envelope` print "Wrote: <path>" lines like the F20 shim?** — **Recommend: no.** `write_envelope` is a library function; printing is a notebook UX concern. The notebook shim iterates `written.items()` and prints explicitly (per 2d). Keeps the library silent and the notebook verbose — the right split.

**Q15. G5 reminder — orphan notice_id uses `provenance.line_span[0]` for stability.** F21 does not touch identity stamping (it happens inside `build_envelope`, which F21 does not edit). The invariant survives by construction. Called out here so a careless F21 edit that tried to "simplify" identity stamping via `parse_file`-level code would trip the reviewer.

**Q16. If `parse_bytes` is called with `filename=None` AND the PDF masthead parse fails (triggering the `masthead.parse_failed` warning), what populates `Warning.where.pdf_file_name`?** — **RESOLVED: the temp-file name.** `build_envelope` reads `pdf_path.name` for the warning's `where` field (F20 code); the temp file's name is `stem + ".pdf"` where `stem` is a cleaned version of `filename or "anonymous.pdf"`. When `filename=None`, the warning carries `pdf_file_name="anonymous.pdf"`. Consumers who want a specific name pass `filename=`. Matches the "accept anonymous bytes" resolution from Q3.

---

## 9. Implementation Prompt (for Agent 2)

*(Numbered 9 to avoid collision with section 4 "Test Case Matrix"; Agent 1 role doc's "section 4 = Implementation Prompt" convention is honoured by this being the final section that Agent 2 copy-pastes. Agent 0 reads section 8 for the human checkpoint.)*

COPY THIS EXACT PROMPT:

---

**Implement F21: Public API + I/O split**

Read this spec: `specs/F21-public-api-io-split.md`. Read `docs/library-contract-v1.md` section 5 — it locks the `parse_file` / `parse_bytes` / `write_envelope` signatures. Do NOT touch `gazette_docling_pipeline_spatial.ipynb`'s calibration, regression, `confidence_report`, or `enhance_with_llm` cells. Do NOT touch `pyproject.toml` — F21 adds no new dependencies. Do NOT touch anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/expected_confidence.json`. The notebook must keep running end-to-end so Gate 1 (regression on 6 canonical PDFs) stays cleared.

**Core files location:**
- Edited: `kenya_gazette_parser/__init__.py`, `gazette_docling_pipeline_spatial.ipynb`
- Created: `kenya_gazette_parser/io.py` + 11 helper scripts under `scripts/f21_*.py`

**Requirements (do these in order):**

1. **Create `kenya_gazette_parser/io.py`** per spec section 2c. Public surface:
   - `write_envelope(env: Envelope, out_dir: Path, bundles: dict[str, bool] | None = None, *, pdf_path: Path | str | None = None, converter: DocumentConverter | None = None) -> dict[str, Path]`
   - Private helpers: `_highlight_gazette_notices_in_markdown`, `_stem_fallback`, `_GAZETTE_NOTICE_MD_LINE`, `_GAZETTE_NOTICE_HIGHLIGHT_STYLE`, `_DEFAULT_BUNDLES`, `_ENV_ONLY_BUNDLES`, `_RAW_DOCLING_BUNDLES`, `_ALL_KNOWN_BUNDLES`.
   - `__all__ = ["write_envelope"]`.
   - Lift `highlight_gazette_notices_in_markdown` + its two supporting constants verbatim from the notebook (gazette_docling_pipeline_spatial.ipynb lines 155-183 area) into `_highlight_gazette_notices_in_markdown`; the function name gets an underscore prefix but its body is byte-identical.
   - Algorithm per spec section 2c's pseudo-code.
   - `ValueError` messages must name both the offending key(s) and the required fix (e.g. "Bundles ['full_text'] require pdf_path; pass pdf_path=<path-to-pdf>.").
   - `docling.document_converter.DocumentConverter` is imported LAZILY inside the `if requested_raw:` branch — importing `kenya_gazette_parser.io` must not force a Docling module load.

2. **Edit `kenya_gazette_parser/__init__.py`** per spec section 2b:
   - Delete the `_NOT_IMPLEMENTED_MSG` constant.
   - Replace `parse_file` body: check `config is not None` -> raise `NotImplementedError` with message containing "F22" and "GazetteConfig"; otherwise `return build_envelope(Path(path))`.
   - Replace `parse_bytes` body: same `config` check; use `tempfile.TemporaryDirectory(prefix="kenya_gazette_parser_")`; write bytes to `Path(tmp_dir) / stem` where `stem = (filename or "anonymous.pdf")` with path separators sanitized and `.pdf` appended if missing; call `build_envelope(tmp_path)`; the `TemporaryDirectory` context cleans up.
   - Add top-level imports: `import tempfile`; `from kenya_gazette_parser.io import write_envelope`; `from kenya_gazette_parser.models import Envelope`; `from kenya_gazette_parser.pipeline import build_envelope`.
   - Update `__all__ = ["__version__", "parse_file", "parse_bytes", "write_envelope", "Envelope"]`.
   - Update the module docstring to describe the public API (5 names). Drop the "F20-F21 land" language (those have landed).
   - Update the `parse_file` / `parse_bytes` docstrings: change "F17 stub. Always raises `NotImplementedError`." to the real behavior per spec 2b.
   - Tighten return type annotations from `-> dict` to `-> Envelope`.

3. **Do NOT touch `kenya_gazette_parser/pipeline.py`, `kenya_gazette_parser/models/*`, any of the nine F20 submodules, `kenya_gazette_parser/__version__.py`, `kenya_gazette_parser/py.typed`, or `pyproject.toml`.** F21 is a public-surface feature, not a re-plumbing of internals.

4. **Notebook surgery** (`gazette_docling_pipeline_spatial.ipynb`). Use `nbformat` via a script (mirror F20's `scripts/f20_rewrite_notebook.py`) — do not hand-edit the JSON:
   - **Delete** the `highlight_gazette_notices_in_markdown` def, the `_GAZETTE_NOTICE_MD_LINE` constant, and the `_GAZETTE_NOTICE_HIGHLIGHT_STYLE` constant from the source cell that currently hosts them (notebook cell around line 160-183 area; also check for any duplicate copies).
   - **Collapse** the `GazettePipeline` shim cell per spec section 2d. Keep the `@dataclass` decorator, the `converter` field (default `field(default_factory=DocumentConverter)`), and the `include_full_docling_dict` field (reserved; routed via F22). `process_pdf` body:
     ```python
     pdf_path = Path(pdf_path).resolve()
     env = parse_file(pdf_path)
     written = write_envelope(
         env,
         out_dir=OUTPUT_DIR / pdf_path.stem,
         pdf_path=pdf_path,
         converter=self.converter,
     )
     for bundle_name, path in written.items():
         print(f"Wrote: {path}")
     return env.model_dump(mode="json")
     ```
   - **Update imports** in the notebook top imports cell: add `from kenya_gazette_parser import parse_file, write_envelope` and `Envelope` if used for type hints. Keep the existing F20 imports block otherwise unchanged.
   - **Do NOT delete** `run_pdfs`, `run_folder`, `resolve_pdf_selection`, the `PDF_SELECTION_MODE` / `SELECTED_PDF_NAMES` cells, the visual-inspection cells, `confidence_report`, `_iter_output_gazette_jsons`, the LLM cells, the calibration cells, or the regression cells.
   - **Do NOT delete** the `extract_title_from_docling`, `docling_export_summary` notebook helpers — those are out-of-scope for F21 (F20 spec 2b says so and F21 does not revisit them).

5. **Test cases — run all 12 in order.** Each TCx lives in `scripts/f21_tc<n>_<name>.py` except TC11 (grep) and TC12 (inline `-c`). Failure policy: run tests left to right; the first FAIL stops progress and is reported with full stderr. Do not skip or soft-pass.

   - `.\.venv\Scripts\python.exe scripts\f21_tc1_parse_file_happy.py` — must print `TC1 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc2_parse_bytes_parity.py` — must print `TC2 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc3_write_envelope_default.py` — must print `TC3 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc4_write_envelope_selective.py` — must print `TC4 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc5_tc6_write_envelope_errors.py` — must print `TC5 OK` then `TC6 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc7_config_not_implemented.py` — must print `TC7 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc8_regression.py` — subprocess-per-PDF runner (mirror F20's `scripts/f20_run_pipeline.py` structure to avoid CXXVIINo 63 `std::bad_alloc`); must print `TC8 OK (6/6 within 0.05)`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc9_notice_id_stability.py` — must print `TC9 OK (5/6 exact; CXXVIINo 63 = 146-prefix-of-153 documented)` OR `TC9 OK (6/6 exact)` if CXXVIINo 63 happens to converge on the baseline this run.
   - `.\.venv\Scripts\python.exe scripts\f21_tc10_gate3.py` — must print `TC10 OK`.
   - `.\.venv\Scripts\python.exe scripts\f21_tc11_grep_notebook.py` — must print `TC11 OK (0 matches)`.
   - `.\.venv\Scripts\python.exe -c "from kenya_gazette_parser import parse_file, parse_bytes, write_envelope, Envelope, __version__; import kenya_gazette_parser.io as io_mod; assert 'write_envelope' in io_mod.__all__; print('TC12 OK')"` — must print `TC12 OK`.

6. **Re-run the canonical PDFs through the collapsed notebook shim** (via `scripts/f21_tc8_regression.py` already does this). Confirm the 6 `output/{stem}/{stem}_gazette_spatial.json` trees are regenerated and `check_regression(tolerance=0.05)` returns OK. The four non-JSON side files (`_spatial.txt`, `_docling_markdown.md`, `_spatial_markdown.md`, `_docling.json`) should be byte-identical to the F20 baseline (except for timestamps in JSON; the four raw files do not carry `extracted_at`). If CXXVIINo 63 produces the 146-id strict-prefix pattern, note it; it is not a regression (documented in F20 session log).

7. **Update PROGRESS.md** in this exact order:
   - **Today** block: change `**Current:** F21 — Public API + I/O split` to `**Current:** F22 — GazetteConfig + Bundles`; update `**Previous:** F20 ✅ — Move logic into modules ...` to `**Previous:** F21 ✅ — Public API + I/O split (parse_file/parse_bytes wired to build_envelope; kenya_gazette_parser/io.py houses write_envelope with 5-bundle dict; notebook shim collapsed to parse_file + write_envelope; Gate 3 cleared)`. Update the `**What:**`, `**Where:**`, `**Done when:**` lines to F22's scope.
   - **Work Items** table: F21 row Status `⬜ Not started` -> `✅ Complete`; leave the Commit column blank (Agent 3 stamps it after commit).
   - **Quality Gates** table: Gate 3 Status cell `⬜ Partially unblocked (...parse_file fully clears at F21)` -> `✅ Cleared (F21)`.
   - **Known Debt** table: no changes. D3, D4, D5, D6 unchanged. Neither D1 nor D2 changed (still obsolete as F20 resolved them).
   - **Session Log** row (today's date, 2026-04-22 or later): paragraph covering — files edited (`__init__.py`), files created (`io.py`), notebook collapse status (lines removed, `GazettePipeline` shim size), helper moved (`highlight_gazette_notices_in_markdown` -> `_highlight_gazette_notices_in_markdown` in `io.py`), 12 TC results, Gate 3 clearance, any notable discrepancies (e.g. CXXVIINo 63 notice_id count this run), the flagged F22 optimization (single-Docling-conversion via RuntimeOptions), and a closing note that `pyproject.toml` untouched.

8. **Return the Build Report** (format below). If any TC fails, report the exact failure output and STOP — do not proceed to PROGRESS.md edits or to F22.

**Build Report Format:**

```markdown
# Build Report: F21

## Implementation
- Files created:
  - `kenya_gazette_parser/io.py` (write_envelope + _highlight_gazette_notices_in_markdown + _stem_fallback; __all__ = ["write_envelope"])
  - `scripts/f21_tc1_parse_file_happy.py`
  - `scripts/f21_tc2_parse_bytes_parity.py`
  - `scripts/f21_tc3_write_envelope_default.py`
  - `scripts/f21_tc4_write_envelope_selective.py`
  - `scripts/f21_tc5_tc6_write_envelope_errors.py`
  - `scripts/f21_tc7_config_not_implemented.py`
  - `scripts/f21_tc8_regression.py`
  - `scripts/f21_tc9_notice_id_stability.py`
  - `scripts/f21_tc10_gate3.py`
  - `scripts/f21_tc11_grep_notebook.py`
- Files edited:
  - `kenya_gazette_parser/__init__.py` (real parse_file / parse_bytes; re-export write_envelope + Envelope; __all__ expanded)
  - `gazette_docling_pipeline_spatial.ipynb` (GazettePipeline.process_pdf collapsed; highlight_gazette_notices_in_markdown + _GAZETTE_NOTICE_MD_LINE + _GAZETTE_NOTICE_HIGHLIGHT_STYLE deleted from source cells; top imports extended with parse_file/write_envelope)
  - `PROGRESS.md` (F21 row -> ✅; Today moved to F22; Quality Gate 3 cleared; Session Log row appended)
- Files NOT touched: `pyproject.toml`, `requirements.txt`, `kenya_gazette_parser/pipeline.py`, `kenya_gazette_parser/models/*`, any of the 9 F20 submodules, `kenya_gazette_parser/__version__.py`, `kenya_gazette_parser/py.typed`, anything under `output/`, `pdfs/`, `.llm_cache/`, `tests/expected_confidence.json`.
- Notebook cell-level summary:
  - Lines deleted: <N> (highlight_* helper + two constants)
  - Shim cell line count: <M> (down from ~50 pre-F21)
  - Imports added: `from kenya_gazette_parser import parse_file, write_envelope`
  - Cells visited: <list of cell ids / line ranges touched>

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| TC1 — parse_file happy path (CXXIVNo 282, 201 notices) | PASS/FAIL | mean_composite = <value> (baseline 0.968) |
| TC2 — parse_bytes parity (CXINo 100) | PASS/FAIL | pdf_sha256 match, notice_id list match |
| TC3 — write_envelope default bundles (CXXIVNo 282) | PASS/FAIL | all 5 files written; 4 raw files byte-match F20 baseline |
| TC4 — write_envelope selective bundles (CXIINo 76) | PASS/FAIL | only 1 file in out_dir |
| TC5 — write_envelope raw without pdf_path | PASS/FAIL | ValueError message check |
| TC6 — write_envelope unknown key | PASS/FAIL | ValueError message check |
| TC7 — parse_file(config=<dict>) | PASS/FAIL | NotImplementedError message check |
| TC8 — Gate 1 regression (6 PDFs) | PASS/FAIL | per-PDF mean_composite deltas: <list> |
| TC9 — Gate 2 notice_id stability (6 PDFs vs F20 baseline) | PASS/FAIL | CXXVIINo 63 notice count this run: <N> (F20 baseline: 146 prefix of 153) |
| TC10 — Gate 3 end-to-end (CIINo 83 pre-2010) | PASS/FAIL | 1 notice |
| TC11 — notebook grep (0 hits on highlight_* defs / constants) | PASS/FAIL | <N> matches (must be 0) |
| TC12 — import smoke | PASS/FAIL | |

## Quality Gates
- Gate 1 (regression): STILL CLEARED (TC8 PASS)
- Gate 2 (deterministic notice_id): STILL CLEARED (TC9 PASS modulo documented CXXVIINo 63 tail)
- Gate 3 (`from kenya_gazette_parser import parse_file` works end-to-end): NOW CLEARED (TC10 PASS) — was PARTIAL after F17, fully green after F21
- Gate 4 (Envelope validates against JSON Schema): NOT REACHED (needs F23)
- Gate 5 (`pip install git+...` works): NOT REACHED (needs F24)

## PROGRESS.md
- F21 row: ⬜ Not started → ✅ Complete
- "Today" moved to F22 — GazetteConfig + Bundles
- Quality Gate 3 cell: ⬜ Partially unblocked → ✅ Cleared (F21)
- Session Log row appended

## Notes for F22
- `write_envelope`'s double-Docling-conversion cost survives into F21 (unchanged from F20 shim). F22's `RuntimeOptions` is the natural place to add a single-conversion optimization: `parse_file` could cache raw artifacts keyed by `env.pdf_sha256`, and `write_envelope` could look them up. Or a private `parse_file_with_artifacts` helper can return `tuple[Envelope, Artifacts]` for internal callers. Decide at F22 start.
- F21's `_DEFAULT_BUNDLES` has five keys (`gazette_spatial_json`, `full_text`, `docling_markdown`, `spatial_markdown`, `docling_json`). Contract section 5's `Bundles` has eight (`notices`, `corrigenda`, `document_index`, `spatial_markdown`, `full_text`, `tables`, `debug_trace`, `images`). F22 must reconcile — likely by widening `_ALL_KNOWN_BUNDLES` to both sets, accepting the F21 dict form for backward compat, and adding new derivations (`notices` as `{stem}_notices.json` from `env.notices`, `corrigenda` likewise, etc.).
- F21 `parse_file(config=<non-None>)` raises `NotImplementedError`. F22 replaces that guard with the real `GazetteConfig` handling. The test asserting the error (TC7) will need updating at F22 to assert config-honoring behavior.

## Final Status: PASS / FAIL
```

---
