"""Trailing content detector (F12).

Detects where the last notice's body ends and non-notice trailer material
(subscription pricing, classified ads, INDEX pages, etc.) begins. Lifted
verbatim from the notebook. Stdlib-only (``re``).
"""

from __future__ import annotations

import re

__all__ = ["detect_trailing_content_cutoff"]


_PATTERNS: list[tuple[str, str, int]] = [
    (r"^\s*NOW\s+ON\s+SALE\b", "publications_catalog", 10),
    (r"SUBSCRIPTION\s+(?:AND\s+)?ADVERTISEMENT\s+CHARGES", "subscription", 20),
    (r"SUBSCRIPTION\s+CHARGES", "subscription", 20),
    (r"IMPORTANT\s+NOTICE\s+TO\s+SUBSCRIBERS", "important_notice", 20),
    (r"Government\s+Printer\.?\s*$", "govt_printer", 20),
    (r"^(?:INDEX|CONTENTS)\s*$", "index", 20),
    (r"CLASSIFIED\s+(?:ADVERTISEMENT|ADS)", "classified", 20),
]


def detect_trailing_content_cutoff(text: str, last_notice_start_line: int) -> int | None:
    """Detect where actual notice content ends and trailing material begins.

    Trailing content includes subscription pricing, classified ads, index pages,
    and other non-notice material that appears after the last valid gazette
    notice.

    Args:
        text: full plain text of the document.
        last_notice_start_line: line index where the last notice header appears.

    Returns:
        line index where trailing content begins, or ``None`` if no trailing
        content detected.
    """
    if not text or not text.strip():
        return None

    lines = text.splitlines()
    earliest_cutoff: int | None = None

    for i in range(len(lines)):
        if i <= last_notice_start_line:
            continue
        line_stripped = lines[i].strip()
        for pattern, _label, min_distance in _PATTERNS:
            if i - last_notice_start_line < min_distance:
                continue
            if re.search(pattern, line_stripped, re.I):
                if earliest_cutoff is None or i < earliest_cutoff:
                    earliest_cutoff = i
                break

    return earliest_cutoff
