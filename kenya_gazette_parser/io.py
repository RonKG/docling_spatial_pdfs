"""F21: ``write_envelope`` and the private markdown-highlight helper.

This module is the single home for library I/O. ``parse_file`` and
``parse_bytes`` are pure (never touch disk); callers who want on-disk
artifacts call :func:`write_envelope` from this module explicitly.

The bundle vocabulary in F21 is a deliberate subset of contract section 5's
eight-key ``Bundles``: the five legacy filenames that F20's notebook shim
produced (``gazette_spatial_json``, ``full_text``, ``docling_markdown``,
``spatial_markdown``, ``docling_json``). Keeping the vocabulary narrow keeps
the 6-PDF regression comparing byte-for-byte against the F20 output tree
(Gate 1) and defers the full rename to F22's ``Bundles`` Pydantic model.

The ``_highlight_gazette_notices_in_markdown`` helper was lifted verbatim
from the notebook (same regex, same inline style). F20 spec section 2b
explicitly deferred this move to F21; this file executes the move.
"""

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
    "gazette_spatial_json": True,   # {stem}_gazette_spatial.json — the validated Envelope
    "full_text":            True,   # {stem}_spatial.txt
    "docling_markdown":     True,   # {stem}_docling_markdown.md
    "spatial_markdown":     True,   # {stem}_spatial_markdown.md
    "docling_json":         True,   # {stem}_docling.json
}

_ENV_ONLY_BUNDLES = frozenset({"gazette_spatial_json"})
_RAW_DOCLING_BUNDLES = frozenset({
    "full_text",
    "docling_markdown",
    "spatial_markdown",
    "docling_json",
})
_ALL_KNOWN_BUNDLES = _ENV_ONLY_BUNDLES | _RAW_DOCLING_BUNDLES


_GAZETTE_NOTICE_MD_LINE = re.compile(
    r"^(\#\# )?(GAZETTE NOTICE NO\. \d+)\s*$",
    re.MULTILINE,
)
_GAZETTE_NOTICE_HIGHLIGHT_STYLE = (
    'style="background-color:#fff3cd;color:#1a1a1a;padding:0.15em 0.35em;'
    'border-radius:3px;font-weight:600;"'
)


def _highlight_gazette_notices_in_markdown(md: str) -> str:
    """Wrap standalone ``GAZETTE NOTICE NO.`` lines for Markdown HTML preview.

    Private helper lifted from the notebook (F20 spec section 2b deferred
    this move to F21). Body is byte-identical to the notebook original.
    """

    def repl(m: "re.Match[str]") -> str:
        notice = m.group(2)
        inner = f'<span {_GAZETTE_NOTICE_HIGHLIGHT_STYLE}>{notice}</span>'
        if m.group(1):
            return f"## {inner}"
        return inner

    return _GAZETTE_NOTICE_MD_LINE.sub(repl, md)


def _stem_fallback(env: Envelope) -> str:
    """Derive a deterministic stem when ``pdf_path`` is not provided.

    Used only for ``gazette_spatial_json``-only calls. Format:
    ``{first-12-chars-of-pdf_sha256}``.
    """
    return env.pdf_sha256[:12]


def write_envelope(
    env: Envelope,
    out_dir: "Path | str",
    bundles: "dict[str, bool] | None" = None,
    *,
    pdf_path: "Path | str | None" = None,
    converter: "DocumentConverter | None" = None,
) -> dict[str, Path]:
    """Materialize bundle files from a validated :class:`Envelope`.

    Parameters
    ----------
    env
        The validated :class:`Envelope` (return value of
        :func:`kenya_gazette_parser.parse_file` or
        :func:`kenya_gazette_parser.parse_bytes`).
    out_dir
        Directory to write into. ``Path`` or ``str`` both work; coerced at
        the top of the function. Created with ``parents=True,
        exist_ok=True`` if missing.
    bundles
        Dict of ``{bundle_name: bool}``. ``None`` defaults to all five keys
        set to ``True``. Unknown keys raise :class:`ValueError`. F22 will
        accept a ``Bundles`` Pydantic model in addition.
    pdf_path
        Required when any bundle in ``{"full_text", "docling_markdown",
        "spatial_markdown", "docling_json"}`` is requested. ``write_envelope``
        re-invokes Docling on this path to regenerate the raw diagnostic
        payload (matches the F20 shim's double conversion). Optional when
        only ``gazette_spatial_json`` is requested.
    converter
        Optional pre-built :class:`DocumentConverter` to reuse when
        ``write_envelope`` re-invokes Docling. ``None`` means construct a
        new one on demand.

    Returns
    -------
    dict[str, Path]
        Mapping from bundle name to the written file path. Only keys for
        bundles that were actually written are present.

    Raises
    ------
    ValueError
        If ``bundles`` contains an unknown key, or if a raw-Docling bundle
        is requested without ``pdf_path``.
    FileNotFoundError
        If ``pdf_path`` is set but the file does not exist (propagates from
        Docling).
    """
    if bundles is None:
        bundles = _DEFAULT_BUNDLES.copy()

    unknown = set(bundles) - _ALL_KNOWN_BUNDLES
    if unknown:
        raise ValueError(
            f"Unknown bundle keys: {sorted(unknown)}. "
            f"Known keys in F21: {sorted(_ALL_KNOWN_BUNDLES)}."
        )

    requested_raw = sorted(k for k, v in bundles.items() if v and k in _RAW_DOCLING_BUNDLES)
    if requested_raw and pdf_path is None:
        raise ValueError(
            f"Bundles {requested_raw} require pdf_path; pass "
            f"pdf_path=<path-to-pdf>. Only gazette_spatial_json is "
            f"derivable from the Envelope alone."
        )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if pdf_path is not None:
        stem = Path(pdf_path).stem
    else:
        stem = _stem_fallback(env)

    written: dict[str, Path] = {}

    if bundles.get("gazette_spatial_json"):
        path = out_dir / f"{stem}_gazette_spatial.json"
        path.write_text(
            json.dumps(env.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written["gazette_spatial_json"] = path

    if requested_raw:
        if converter is None:
            from docling.document_converter import DocumentConverter  # lazy
            converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        doc = result.document
        doc_dict: dict[str, Any] = doc.export_to_dict()

        plain_spatial: str | None = None
        if bundles.get("full_text") or bundles.get("spatial_markdown"):
            plain_spatial, _layout = reorder_by_spatial_position_with_confidence(doc_dict)

        if bundles.get("full_text"):
            assert plain_spatial is not None
            path = out_dir / f"{stem}_spatial.txt"
            path.write_text(plain_spatial, encoding="utf-8")
            written["full_text"] = path

        if bundles.get("docling_markdown"):
            md = doc.export_to_markdown()
            path = out_dir / f"{stem}_docling_markdown.md"
            path.write_text(
                _highlight_gazette_notices_in_markdown(md),
                encoding="utf-8",
            )
            written["docling_markdown"] = path

        if bundles.get("spatial_markdown"):
            assert plain_spatial is not None
            path = out_dir / f"{stem}_spatial_markdown.md"
            path.write_text(
                _highlight_gazette_notices_in_markdown(plain_spatial),
                encoding="utf-8",
            )
            written["spatial_markdown"] = path

        if bundles.get("docling_json"):
            path = out_dir / f"{stem}_docling.json"
            path.write_text(
                json.dumps(doc_dict, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            written["docling_json"] = path

    return written
