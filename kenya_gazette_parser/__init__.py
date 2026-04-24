"""kenya_gazette_parser - parse Kenya Gazette PDFs into structured envelopes.

Public API (1.0):

- :func:`parse_file` - PDF path in, validated :class:`Envelope` out.
- :func:`parse_bytes` - same, but from raw bytes (uses a cross-platform
  :class:`tempfile.TemporaryDirectory` under the hood).
- :func:`write_envelope` - the only function that writes to disk.
- :class:`Envelope` - the top-level Pydantic model, re-exported from
  :mod:`kenya_gazette_parser.models`.
- :class:`GazetteConfig` - configuration object for parse_file / parse_bytes.
- :class:`Bundles` - bundle selection for write_envelope.
- :class:`LLMPolicy` - LLM configuration (F22 declares, M5/M6 implements).
- :class:`RuntimeOptions` - runtime tuning options (F22 declares, post-1.0 implements).

``parse_*`` functions are pure and never write to disk; callers who want
files on disk call :func:`write_envelope` explicitly. See
``docs/library-contract-v1.md`` section 5.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from kenya_gazette_parser.__version__ import __version__
from kenya_gazette_parser.io import write_envelope
from kenya_gazette_parser.models import Bundles, Envelope, GazetteConfig, LLMPolicy, RuntimeOptions
from kenya_gazette_parser.pipeline import build_envelope
from kenya_gazette_parser.schema import get_envelope_schema, validate_envelope_json, write_schema_file

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from docling.document_converter import DocumentConverter  # noqa: F401

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
    "write_schema_file",
]


def parse_file(
    path: "Path | str",
    config: "GazetteConfig | None" = None,
) -> Envelope:
    """Parse a Kenya Gazette PDF file into a validated :class:`Envelope`.

    Pure: never writes to disk, never prints. ``pydantic.ValidationError``
    from the F19 tail validation propagates uncaught (contract section 5
    + F19 rule).

    Parameters
    ----------
    path
        Filesystem path to a ``.pdf`` file. ``str`` or :class:`Path` both
        work.
    config
        Optional GazetteConfig. If None, defaults are used (LLM disabled,
        standard bundles). The config is stored but LLM stages are not
        invoked until M5/M6.
    """
    if config is None:
        config = GazetteConfig()
    return build_envelope(Path(path), config=config)


def parse_bytes(
    data: bytes,
    *,
    filename: str | None = None,
    config: "GazetteConfig | None" = None,
) -> Envelope:
    """Parse a Kenya Gazette PDF from raw bytes into a validated :class:`Envelope`.

    ``filename`` is used only for provenance/warnings - the ``pdf_sha256``
    is computed from ``data`` regardless of filename, so two callers with
    the same bytes get the same ``pdf_sha256``.

    Implementation writes ``data`` to a temporary file inside a
    :class:`tempfile.TemporaryDirectory` (delete-on-exit) and calls
    :func:`kenya_gazette_parser.pipeline.build_envelope` on the temp path.
    Cross-platform: does NOT use ``NamedTemporaryFile(delete=True)`` because
    that path fails on Windows when Docling re-opens the file with an
    exclusive lock.

    Parameters
    ----------
    data
        Raw PDF bytes.
    filename
        Optional display name for the bytes (propagates into
        ``Warning.where.pdf_file_name`` if the masthead fails). When
        ``None``, the synthetic name ``"anonymous.pdf"`` is used.
    config
        Optional GazetteConfig. If None, defaults are used (LLM disabled,
        standard bundles). The config is stored but LLM stages are not
        invoked until M5/M6.
    """
    if config is None:
        config = GazetteConfig()
    stem = (filename or "anonymous.pdf").replace("/", "_").replace("\\", "_")
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    with tempfile.TemporaryDirectory(prefix="kenya_gazette_parser_") as tmp_dir:
        tmp_path = Path(tmp_dir) / stem
        tmp_path.write_bytes(data)
        return build_envelope(tmp_path, config=config)
