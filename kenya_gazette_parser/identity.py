"""Identity and versioning helpers for kenya_gazette_parser.

Lifted from the notebook (F11/F13/F14). The module is deliberately stdlib-only
so it has no package-internal dependencies.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kenya_gazette_parser.__version__ import LIBRARY_VERSION, SCHEMA_VERSION

__all__ = [
    "LIBRARY_VERSION",
    "SCHEMA_VERSION",
    "make_extracted_at",
    "compute_pdf_sha256",
    "make_gazette_issue_id",
    "make_notice_id",
]


def make_extracted_at() -> str:
    """Return current UTC timestamp as ISO 8601 string with ``Z`` suffix.

    Format: ``YYYY-MM-DDTHH:MM:SSZ`` (whole-second precision).
    Never raises: returns Unix epoch string on any failure.
    """
    try:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return "1970-01-01T00:00:00Z"


def compute_pdf_sha256(pdf_path: Path) -> str:
    """Compute SHA-256 hex digest of PDF file bytes.

    Returns lowercase hex string (length 64). On read failure, returns a
    deterministic ``unknown_{name}`` fallback so callers still get a stable
    identity string.
    """
    try:
        pdf_bytes = Path(pdf_path).read_bytes()
        return hashlib.sha256(pdf_bytes).hexdigest()
    except Exception:
        return f"unknown_{Path(pdf_path).name}"


def make_gazette_issue_id(masthead: dict, pdf_sha256: str) -> tuple[str, bool]:
    """Build canonical gazette issue ID from masthead fields.

    Returns ``(issue_id, is_fallback)``. Canonical form:
        ``KE-GAZ-{volume}-{issue_no}-{publication_date}[-S{n}]``
    Fallback (when required fields missing):
        ``KE-GAZ-UNKNOWN-{pdf_sha256[:12]}``

    Required fields: ``volume``, ``issue_no``, ``publication_date``
    Optional field: ``supplement_no`` (appended as ``-S{n}`` when present and
    non-zero).
    """
    volume = masthead.get("volume")
    issue_no = masthead.get("issue_no")
    pub_date = masthead.get("publication_date")
    supplement_no = masthead.get("supplement_no")

    if volume is None or issue_no is None or pub_date is None:
        fallback_id = f"KE-GAZ-UNKNOWN-{pdf_sha256[:12]}"
        return (fallback_id, True)

    issue_id = f"KE-GAZ-{volume}-{issue_no}-{pub_date}"
    if supplement_no is not None and supplement_no != 0:
        issue_id = f"{issue_id}-S{supplement_no}"
    return (issue_id, False)


def make_notice_id(
    gazette_issue_id: str,
    gazette_notice_no: Any,
    line_span_start: int,
) -> str:
    """Build notice ID from gazette issue ID and notice number.

    For keyed notices (``gazette_notice_no`` is not ``None``):
        ``{gazette_issue_id}:{gazette_notice_no}``
    For orphan blocks (``gazette_notice_no`` is ``None``):
        ``{gazette_issue_id}:_orphan_{line_span_start}``

    ``line_span_start`` defaults to 0 if ``None``. Orphan IDs deliberately use
    ``provenance.line_span[0]`` (never list index) to keep ``notice_id`` stable
    across runs (PROGRESS.md G5).
    """
    if line_span_start is None:
        line_span_start = 0
    if gazette_notice_no is None:
        return f"{gazette_issue_id}:_orphan_{line_span_start}"
    return f"{gazette_issue_id}:{gazette_notice_no}"
