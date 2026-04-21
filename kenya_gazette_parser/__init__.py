"""kenya_gazette_parser - parse Kenya Gazette PDFs into structured envelopes.

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
