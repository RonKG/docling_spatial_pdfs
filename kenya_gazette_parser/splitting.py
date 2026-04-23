"""Notice splitter + related helpers (F3).

Splits the spatially-ordered plain text of a gazette into notice-shaped
dicts. Lifted verbatim from the notebook.

The only package-internal dependency is on ``trailing.detect_trailing_content_cutoff``
(the last-notice cutoff scan). Spec F20 section 2a files ``trailing.py`` as
its own module; ``splitting.py`` imports it rather than duplicating the
detector. This keeps the dependency graph a DAG
(``splitting -> trailing -> stdlib``).
"""

from __future__ import annotations

import re
from typing import Any

from kenya_gazette_parser.trailing import detect_trailing_content_cutoff

__all__ = ["split_gazette_notices"]


_NOTICE_HEAD_RE = re.compile(
    r"^(?:GAZETTE|GAZETE)\s+NOTICE\.?\s+NO\.?\s*(\d+)\s*$"
)

_RECOVERED_HEAD_RE = re.compile(
    r"(?:^|\s|\|)\s*(?:GAZETTE|GAZETE)\s+NOTICE\.?\s+NO\.?\s*(\d+)(?:\s|\|)"
)

_RUNNING_HEADER_RES = [
    re.compile(r"^\s*THE KENYA GAZETTE\s*$", re.I),
    re.compile(r"^\s*\d{1,2}(?:st|nd|rd|th)\s+\w+,?\s+\d{4}\s*$"),
    re.compile(r"^\s*\d{4,5}\s*$"),
    re.compile(r"^\s*CONTENTS\s*$", re.I),
    re.compile(r"^\s*Published\s+by\s+Authority\s+of\s+the\s+Republic\s+of\s+Kenya\s*$", re.I),
    re.compile(r"^\s*Price\s+Sh\.?\s*\d+[\.,]?\d*\s*$", re.I),
    re.compile(r"^\s*\(Registered\s+as\s+a\s+Newspaper\s+at\s+the\s+G\.?P\.?O\.?\)\s*$", re.I),
    re.compile(r"^\s*Vol\.?\s*[IVXLC]+\s*-+\s*No\.?\s*\d+\s*$", re.I),
    re.compile(r"^\s*NAIROBI\s*,?\s+\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4}\s*$", re.I),
]

_BODY_START_RE = re.compile(
    r"^(PURSUANT|NOTICE\s+is|NOTICE\s+OF|IT\s+IS\s+|IN\s+EXERCISE\s+|"
    r"IN\s+PURSUANCE\s+|WHEREAS\s+|TAKE\s+NOTICE\s+|THE\s+following\s+)",
    re.I,
)

_TERMINAL_PUNCT = (".", "!", "?", '"', "'", ")", "]")

_TWO_SERIAL_RE = re.compile(r"^\s*(\d+)\s+(\d+)\.?\s*$")


def _strip_running_headers(lines: list[str]) -> list[str]:
    return [ln for ln in lines if not any(r.match(ln) for r in _RUNNING_HEADER_RES)]


def _split_on_multiple_spaces(line: str) -> list[str]:
    return [p for p in re.split(r" {2,}", line.strip()) if p]


def _extract_title_stack(body_lines: list[str]) -> tuple[list[str], list[str]]:
    """Heading lines run from the start of the notice body until a line that
    clearly begins statutory text (PURSUANT, IN EXERCISE, IT IS, ...)."""
    titles: list[str] = []
    for idx, ln in enumerate(body_lines):
        s = ln.strip()
        if not s:
            if titles:
                return titles, body_lines[idx + 1:]
            continue
        if _BODY_START_RE.match(s):
            return titles, body_lines[idx:]
        titles.append(ln)
    return titles, []


def _segment_body_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Split notice body into text vs table-like blocks.
    Consecutive lines that split into 2+ columns (separated by 2+ spaces)
    become a table."""
    blocks: list[dict[str, Any]] = []
    i = 0
    n = len(lines)

    while i < n:
        ln = lines[i]
        if not ln.strip():
            blocks.append({"type": "blank", "lines": []})
            i += 1
            continue

        parts = _split_on_multiple_spaces(ln)
        is_table_start = (
            (len(parts) >= 2 and not re.match(r"^[A-Z][a-z]", (ln.strip()[:20] or "")))
            or re.match(r"^S\.?\s*/?\s*No\.?", ln.strip(), re.I)
        )
        if is_table_start:
            table_lines: list[str] = []
            j = i
            while j < n:
                row = lines[j]
                if not row.strip():
                    break
                p2 = _split_on_multiple_spaces(row)
                if len(p2) < 2 and j > i:
                    if len(table_lines) >= 3 and len(row) > 120:
                        break
                if len(p2) >= 2:
                    table_lines.append(row)
                    j += 1
                    continue
                if table_lines and len(row) < 100:
                    table_lines.append(row)
                    j += 1
                    continue
                break

            if len(table_lines) >= 2:
                rows = [_split_on_multiple_spaces(x) for x in table_lines]
                blocks.append({"type": "table", "raw_lines": table_lines, "rows": rows})
                i = j
                continue

        para: list[str] = [ln]
        i += 1
        while i < n:
            nxt = lines[i]
            if not nxt.strip():
                break
            p2 = _split_on_multiple_spaces(nxt)
            if len(p2) >= 2:
                break
            para.append(nxt)
            i += 1
        blocks.append({"type": "text", "lines": para})

    return blocks


def _repair_merged_rows(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    """Split rows where adjacent serial numbers were fused (e.g. "625 626")."""
    repaired: list[dict[str, str]] = []
    reasons: list[str] = []
    for row in rows:
        s = (row.get("s_no") or "").strip()
        m = _TWO_SERIAL_RE.match(s)
        if not m:
            repaired.append(row)
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if b - a != 1:
            repaired.append(row)
            continue
        name = (row.get("name") or "").strip()
        pos = (row.get("position") or "").strip()
        split_name = re.split(r"(?<=\S)\s{2,}(?=\S)", name, maxsplit=1)
        split_pos = re.split(r"(?<=\S)\s{2,}(?=\S)", pos, maxsplit=1)
        name_a = split_name[0] if split_name else name
        name_b = split_name[1] if len(split_name) > 1 else ""
        pos_a = split_pos[0] if split_pos else pos
        pos_b = split_pos[1] if len(split_pos) > 1 else ""
        repaired.append({"s_no": str(a), "name": name_a, "position": pos_a})
        repaired.append({"s_no": str(b), "name": name_b, "position": pos_b})
        reasons.append(f"split merged row {a}/{b}")
    return repaired, reasons


def _try_parse_s_no_table(lines: list[str]) -> dict[str, Any] | None:
    """Recover rows when PDF text has split table columns into separate lines."""
    start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^S/No\.?\s+Name", s, re.I):
            start = i
            break
    if start is None:
        return None

    i = start + 1
    if i >= len(lines) or lines[i].strip().lower() != "position":
        return None

    rows: list[dict[str, str]] = []
    i += 1
    while i < len(lines):
        block = lines[i].strip()
        if not block or not (re.match(r"^\d+\.?$", block) or _TWO_SERIAL_RE.match(block)):
            break
        idx = block.rstrip(".")
        i += 1
        if i >= len(lines):
            break
        name = lines[i].strip()
        i += 1
        if i >= len(lines):
            rows.append({"s_no": idx, "name": name, "position": ""})
            break
        position = lines[i].strip()
        if position.lower().startswith("as ") and len(position) > 80:
            rows.append({"s_no": idx, "name": name, "position": ""})
            break
        i += 1
        rows.append({"s_no": idx, "name": name, "position": position})

    if not rows:
        return None

    repaired, repair_reasons = _repair_merged_rows(rows)
    result: dict[str, Any] = {
        "format": "s_no_name_position_lines",
        "rows": repaired,
    }
    if repair_reasons:
        result["repairs"] = repair_reasons
    return result


def _ends_with_terminal_punct(text: str) -> bool:
    s = text.rstrip()
    if not s:
        return False
    return s[-1] in _TERMINAL_PUNCT


def _find_recovered_boundaries(
    raw_lines: list[str],
    strict_boundaries: list[tuple[int, str]],
    min_gap_lines: int = 40,
) -> list[tuple[int, str, str]]:
    """Scan gaps between strict boundaries for recovered header matches.

    Returns boundaries as ``(line_idx, notice_no, header_kind)`` where
    ``header_kind`` is either ``"strict"`` or ``"recovered"``.
    """
    merged: list[tuple[int, str, str]] = [(i, n, "strict") for i, n in strict_boundaries]
    if not merged:
        return merged

    gaps: list[tuple[int, int]] = []
    for bi in range(len(merged) - 1):
        a = merged[bi][0]
        b = merged[bi + 1][0]
        if b - a > min_gap_lines:
            gaps.append((a + 1, b))
    last = merged[-1][0]
    if len(raw_lines) - last > min_gap_lines:
        gaps.append((last + 1, len(raw_lines)))

    recovered: list[tuple[int, str, str]] = []
    seen_nums: set[str] = {n for _, n, _ in merged}
    for lo, hi in gaps:
        for i in range(lo, hi):
            line = raw_lines[i]
            for m in _RECOVERED_HEAD_RE.finditer(line):
                num = m.group(1)
                if num in seen_nums:
                    continue
                recovered.append((i, num, "recovered"))
                seen_nums.add(num)
                break

    merged.extend(recovered)
    merged.sort(key=lambda t: t[0])
    return merged


def _stitch_multipage_notices(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge notices that end mid-sentence into the next block when that block
    has no strict header of its own."""
    if not notices:
        return notices
    out: list[dict[str, Any]] = []
    for entry in notices:
        if not out:
            out.append(entry)
            continue
        prev = out[-1]
        prev_prov = prev.get("provenance") or {}
        curr_prov = entry.get("provenance") or {}
        prev_text = prev.get("gazette_notice_full_text") or ""
        prev_ends_clean = _ends_with_terminal_punct(prev_text)
        curr_is_recovered = curr_prov.get("header_match") == "recovered"
        if not prev_ends_clean and curr_is_recovered:
            stitched_from = list(prev_prov.get("stitched_from") or [])
            stitched_from.append(entry.get("gazette_notice_no"))
            prev["gazette_notice_full_text"] = (
                prev_text + "\n" + (entry.get("gazette_notice_full_text") or "")
            ).strip()
            prev.setdefault("body_segments", []).extend(entry.get("body_segments") or [])
            prev_prov["stitched_from"] = stitched_from
            prev["provenance"] = prev_prov
            prev_other = prev.setdefault("other_attributes", {})
            entry_other = entry.get("other_attributes") or {}
            prev_other["char_span_end_line"] = entry_other.get(
                "char_span_end_line", prev_other.get("char_span_end_line")
            )
            prev_other["lines_in_body"] = prev_other.get("lines_in_body", 0) + (
                entry_other.get("lines_in_body") or 0
            )
            continue
        out.append(entry)
    return out


def split_gazette_notices(full_text: str) -> list[dict[str, Any]]:
    """Split flat text into structured notice blocks.

    Uses strict full-line, all-caps header matching first to avoid false
    positives from inline references. A second pass then scans gaps for
    recovered headers embedded in noisy lines (pipe-separated financial
    tables or lines with prefixes). Each notice gets title extraction, body
    segmentation, running-header stripping, optional derived-table recovery,
    and a provenance block recording ``header_match`` kind and line span.
    """
    if not full_text or not full_text.strip():
        return []

    raw_lines = full_text.splitlines()

    strict: list[tuple[int, str]] = []
    for i, line in enumerate(raw_lines):
        m = _NOTICE_HEAD_RE.match(line.strip())
        if m:
            strict.append((i, m.group(1)))

    boundaries = _find_recovered_boundaries(raw_lines, strict)

    if not boundaries:
        return [
            {
                "gazette_notice_no": None,
                "gazette_notice_header": None,
                "title_lines": [],
                "gazette_notice_full_text": full_text.strip(),
                "body_segments": [],
                "other_attributes": {
                    "reason": "no GAZETTE NOTICE NO. markers found; entire text returned as one block",
                },
                "provenance": {"header_match": "none", "line_span": [0, len(raw_lines)]},
            }
        ]

    notices: list[dict[str, Any]] = []
    for bi, (start_idx, num, kind) in enumerate(boundaries):
        end_idx = boundaries[bi + 1][0] if bi + 1 < len(boundaries) else len(raw_lines)
        body_start = start_idx + 1 if kind == "strict" else start_idx
        chunk = _strip_running_headers(raw_lines[body_start:end_idx])

        titles, body_only = _extract_title_stack(chunk)
        body_for_segments = body_only if body_only else chunk
        segments = _segment_body_lines(body_for_segments)
        derived = _try_parse_s_no_table(chunk)

        header_line = raw_lines[start_idx].strip()
        body_text = "\n".join(chunk).strip()

        if kind == "strict":
            display_header = header_line
            notice_text = f"{header_line}\n{body_text}" if body_text else header_line
        else:
            display_header = f"GAZETTE NOTICE NO. {num}"
            notice_text = f"{display_header}\n{body_text}" if body_text else display_header

        entry: dict[str, Any] = {
            "gazette_notice_no": num,
            "gazette_notice_header": display_header,
            "title_lines": [t.strip() for t in titles],
            "gazette_notice_full_text": notice_text,
            "body_segments": segments,
            "other_attributes": {
                "char_span_start_line": start_idx,
                "char_span_end_line": end_idx,
                "lines_in_body": len(chunk),
            },
            "provenance": {
                "header_match": kind,
                "line_span": [start_idx, end_idx],
                "raw_header_line": header_line,
                "stitched_from": [],
            },
        }
        if derived:
            entry["derived_table"] = derived
        notices.append(entry)

    notices = _stitch_multipage_notices(notices)

    if notices and full_text:
        last_notice = notices[-1]
        last_prov = last_notice.get("provenance") or {}
        last_line_span = last_prov.get("line_span") or [0, 0]
        last_notice_start = last_line_span[0]
        last_notice_original_end = last_line_span[1]

        cutoff = detect_trailing_content_cutoff(full_text, last_notice_start)

        if cutoff is not None and cutoff < last_notice_original_end:
            raw_lines = full_text.splitlines()
            last_kind = last_prov.get("header_match", "strict")
            body_start_line = last_notice_start + 1 if last_kind == "strict" else last_notice_start

            chunk = _strip_running_headers(raw_lines[body_start_line:cutoff])
            header_line = raw_lines[last_notice_start].strip()
            body_text = "\n".join(chunk).strip()

            if last_kind == "strict":
                display_header = header_line
                notice_text = f"{header_line}\n{body_text}" if body_text else header_line
            else:
                num = last_notice.get("gazette_notice_no")
                display_header = f"GAZETTE NOTICE NO. {num}"
                notice_text = f"{display_header}\n{body_text}" if body_text else display_header

            last_notice["gazette_notice_full_text"] = notice_text
            last_notice["body_segments"] = _segment_body_lines(chunk)

            last_other = last_notice.setdefault("other_attributes", {})
            last_other["char_span_end_line"] = cutoff
            last_other["lines_in_body"] = len(chunk)

            last_prov["line_span"] = [last_notice_start, cutoff]
            last_notice["provenance"] = last_prov

    return notices
