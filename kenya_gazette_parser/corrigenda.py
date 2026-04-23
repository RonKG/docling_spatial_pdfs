"""Corrigenda extractor (F4).

Captures correction notices from the CORRIGENDA section (or from the
preamble in its absence) that appears before the first numbered
``GAZETTE NOTICE NO.`` header. Lifted verbatim from the notebook.
Stdlib-only (``re``).

The notebook-shape corrigenda dict produced here is fed to
``kenya_gazette_parser.envelope_builder.build_envelope_dict``, which is the
sub-adapter that synthesizes contract-compliant ``scope`` / ``provenance``
fields and emits one ``corrigendum_scope_defaulted`` warning per corrigendum
(the F31 bridge).
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["extract_corrigenda"]


_NOTICE_HEAD_RE = re.compile(
    r"^(?:GAZETTE|GAZETE)\s+NOTICE\.?\s+NO\.?\s*(\d+)\s*$"
)

_CORRIGENDUM_RE = re.compile(
    r"(?:IN\s+)?Gazette\s+Notice\s+No\.?\s*(\d+)\s+of\s+(\d{4})",
    re.I,
)

_QUOTE_CLASS = "[\"'\u201c\u201d\u2018\u2019]"

_AMEND_PATTERN_RE = re.compile(
    r"amend\s+(?:the\s+)?(.+?)\s+(?:printed\s+as\s+)?"
    + _QUOTE_CLASS + r"(.+?)" + _QUOTE_CLASS
    + r"\s+to\s+read\s+"
    + _QUOTE_CLASS + r"(.+?)" + _QUOTE_CLASS,
    re.I | re.DOTALL,
)


def extract_corrigenda(full_text: str) -> list[dict[str, Any]]:
    """Extract corrigenda (correction notices) from the preamble section.

    Corrigenda appear before the first ``GAZETTE NOTICE NO.`` header and
    reference other notice numbers with corrections like:
        ``IN Gazette Notice No. 14152 of 2025, amend the expression printed as "X" to read "Y"``
    """
    if not full_text or not full_text.strip():
        return []

    raw_lines = full_text.splitlines()

    first_notice_idx = len(raw_lines)
    for i, line in enumerate(raw_lines):
        if _NOTICE_HEAD_RE.match(line.strip()):
            first_notice_idx = i
            break

    preamble_text = "\n".join(raw_lines[:first_notice_idx])

    corrigenda_start: int | None = None
    for i, line in enumerate(raw_lines[:first_notice_idx]):
        if re.match(r"^\s*CORRIGEND[AE]\s*$", line.strip(), re.I):
            corrigenda_start = i
            break

    if corrigenda_start is None:
        corrigenda_text = preamble_text
    else:
        corrigenda_text = "\n".join(raw_lines[corrigenda_start:first_notice_idx])

    corrigenda: list[dict[str, Any]] = []
    segments = re.split(
        r"(?=(?:IN\s+)?Gazette\s+Notice\s+No\.?\s*\d)",
        corrigenda_text,
        flags=re.I,
    )
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        ref_match = _CORRIGENDUM_RE.search(seg)
        if not ref_match:
            continue
        referenced_no = ref_match.group(1)
        referenced_year = ref_match.group(2)

        amend_match = _AMEND_PATTERN_RE.search(seg)
        if amend_match:
            what_field = amend_match.group(1).strip()
            error_text = amend_match.group(2).strip()
            correction_text = amend_match.group(3).strip()
        else:
            what_field = None
            error_text = None
            correction_text = None

        raw_text = " ".join(seg.split())

        corrigenda.append({
            "referenced_notice_no": referenced_no,
            "referenced_year": referenced_year,
            "what_corrected": what_field,
            "error_text": error_text,
            "correction_text": correction_text,
            "raw_text": raw_text,
        })

    return corrigenda
