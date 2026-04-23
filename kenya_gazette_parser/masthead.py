"""Masthead parser (F11).

Extracts ``volume``, ``issue_no``, ``publication_date``, ``supplement_no`` from
the first ~30 lines of spatially-ordered text. Lifted verbatim from the
notebook. Stdlib-only (``re``); no package-internal imports.
"""

from __future__ import annotations

import re

__all__ = ["parse_masthead"]


_VOL_ISSUE_RE = re.compile(
    r"Vol\.?\s*([IVXLC]+)\s*-?\s*No\.?\s*(\d+)",
    re.IGNORECASE,
)
_SUPPLEMENT_RE = re.compile(
    r"(?:Supplement\s+No\.?\s*(\d+)|-S(\d+))",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"(?:NAIROBI|Nairobi)\s*,?\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s*(\d{4})",
    re.IGNORECASE,
)

_MONTHS = {
    "january": "01", "february": "02", "march": "03",
    "april": "04", "may": "05", "june": "06",
    "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "sept": "09", "oct": "10", "nov": "11", "dec": "12",
}


def parse_masthead(text: str) -> dict:
    """Parse Kenya Gazette masthead to extract volume, issue_no, publication_date, supplement_no.

    Args:
        text: First ~30 lines of plain_spatial text from the PDF.

    Returns:
        dict with keys: ``volume`` (str|None), ``issue_no`` (int|None),
        ``publication_date`` (str "YYYY-MM-DD"|None), ``supplement_no`` (int|None).

    Rules:
        - Unparseable field -> ``None``. Never invent values. Never raise.
        - Volume: Roman numeral verbatim (e.g. ``"CXXIV"``).
        - Issue: integer parsed from "No. X" pattern.
        - Date: normalized to ISO ``YYYY-MM-DD`` (ordinals like ``23rd`` stripped).
        - Supplement: integer from ``Supplement No. X`` or ``-SX`` suffix.
    """
    result: dict = {
        "volume": None,
        "issue_no": None,
        "publication_date": None,
        "supplement_no": None,
    }

    lines = (text or "").split("\n")[:30]
    text_block = "\n".join(lines)

    vol_match = _VOL_ISSUE_RE.search(text_block)
    if vol_match:
        result["volume"] = vol_match.group(1).upper()
        result["issue_no"] = int(vol_match.group(2))

    supp_match = _SUPPLEMENT_RE.search(text_block)
    if supp_match:
        supp_num = supp_match.group(1) or supp_match.group(2)
        if supp_num:
            result["supplement_no"] = int(supp_num)

    date_match = _DATE_RE.search(text_block)
    if date_match:
        day = date_match.group(1)
        month_str = date_match.group(2).lower()
        year = date_match.group(3)
        month = _MONTHS.get(month_str)
        if month:
            day_padded = day.zfill(2)
            result["publication_date"] = f"{year}-{month}-{day_padded}"

    return result
