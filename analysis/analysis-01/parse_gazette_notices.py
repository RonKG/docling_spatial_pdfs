#!/usr/bin/env python3
"""
Split Kenya Gazette plain-text exports into per-notice JSON.

Real notice headings are lines matching:
  ^(?:GAZETTE|GAZETE) NOTICE NO. <digits>$
References inside prose (e.g. "IN Gazette Notice No.", "Gazette Notice No.")
do not match because they are not all-caps at line start.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

# Primary heading: whole line, all-caps GAZETTE (or common OCR typo GAZETE).
NOTICE_HEAD_RE = re.compile(
    r"^(?:GAZETTE|GAZETE)\s+NOTICE\s+NO\.\s*(\d+)\s*$"
)

# Lines that are running headers / page furniture (optional strip).
RUNNING_HEADER_RES = [
    re.compile(r"^\s*THE KENYA GAZETTE\s*$", re.I),
    re.compile(r"^\s*24th .+ 202[0-9]\s*$"),
    re.compile(r"^\s*\d{4}\s*$"),  # page column numbers like 9237
    re.compile(r"^\s*217\s*$"),
    re.compile(r"^\s*CONTENTS\s*$", re.I),
]


def strip_running_headers(lines: list[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        if any(r.match(ln) for r in RUNNING_HEADER_RES):
            continue
        out.append(ln)
    return out


def split_on_multiple_spaces(line: str) -> list[str]:
    parts = [p for p in re.split(r" {2,}", line.strip()) if p]
    return parts


def looks_like_table_row(parts: list[str], min_parts: int = 2) -> bool:
    if len(parts) < min_parts:
        return False
    # Short cells, often starts with digit or code
    return True


def segment_body_lines(lines: list[str]) -> list[dict[str, Any]]:
    """
    Split notice body into text vs table-like blocks using a light heuristic:
    consecutive lines that split into 2+ columns (2+ spaces) become a table.
    """
    blocks: list[dict[str, Any]] = []
    i = 0
    n = len(lines)

    while i < n:
        ln = lines[i]
        if not ln.strip():
            blocks.append({"type": "blank", "line": ln})
            i += 1
            continue

        parts = split_on_multiple_spaces(ln)
        # Start table run if this line has multiple columns OR looks like S/No header
        if (
            len(parts) >= 2
            and not re.match(r"^[A-Z][a-z]", ln.strip()[:20] or "")
        ) or re.match(r"^S\.?\s*/?\s*No\.?", ln.strip(), re.I):
            table_lines: list[str] = []
            j = i
            while j < n:
                row = lines[j]
                if not row.strip():
                    break
                p2 = split_on_multiple_spaces(row)
                # Stop table if we hit obvious prose (single long sentence column)
                if len(p2) < 2 and j > i:
                    # allow continuation rows that are single column if previous was table
                    if len(table_lines) >= 3 and len(row) > 120:
                        break
                if len(p2) >= 2:
                    table_lines.append(row)
                    j += 1
                    continue
                # Single-column line inside table region (wrapped cell)
                if table_lines and len(row) < 100:
                    table_lines.append(row)
                    j += 1
                    continue
                break

            if len(table_lines) >= 2:
                rows = [split_on_multiple_spaces(x) for x in table_lines]
                blocks.append(
                    {
                        "type": "table",
                        "raw_lines": table_lines,
                        "rows": rows,
                    }
                )
                i = j
                continue

        # Paragraph / prose: accumulate until blank or table start
        para: list[str] = [ln]
        i += 1
        while i < n:
            nxt = lines[i]
            if not nxt.strip():
                break
            p2 = split_on_multiple_spaces(nxt)
            if len(p2) >= 2:
                # Next line may be a table row — end this text block
                break
            para.append(nxt)
            i += 1
        blocks.append({"type": "text", "lines": para})

    return blocks


BODY_START_RE = re.compile(
    r"^(PURSUANT|NOTICE\s+is|NOTICE\s+OF|IT\s+IS\s+|IN\s+EXERCISE\s+|IN\s+PURSUANCE\s+|WHEREAS\s+)",
    re.I,
)


def extract_title_stack(body_lines: list[str]) -> tuple[list[str], list[str]]:
    """
    Heading lines run from the start of the notice body until a line that clearly
    begins statutory text (PURSUANT, IN EXERCISE, IT IS, …). Blank line after
    headings yields the remainder after the blank.
    """
    titles: list[str] = []
    for idx, ln in enumerate(body_lines):
        s = ln.strip()
        if not s:
            if titles:
                return titles, body_lines[idx + 1 :]
            continue
        if BODY_START_RE.match(s):
            return titles, body_lines[idx:]
        titles.append(ln)
    return titles, []


def try_parse_s_no_table(lines: list[str]) -> dict[str, Any] | None:
    """
    Recover rows when PDF text has split columns into separate lines, e.g.:

        S/No. Name
        Position
        1
        Jane Doe
        Chairperson
        2
        ...
    """
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
        if not block or not re.match(r"^\d+\.?$", block):
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
        # Stop if this looks like narrative continuation (e.g. "as Chairperson and Members...")
        if position.lower().startswith("as ") and len(position) > 80:
            rows.append({"s_no": idx, "name": name, "position": ""})
            break
        i += 1
        rows.append({"s_no": idx, "name": name, "position": position})

    if not rows:
        return None
    return {"format": "s_no_name_position_lines", "rows": rows}


def parse_notices(text: str, *, strip_headers: bool = False) -> tuple[list[str], list[dict[str, Any]]]:
    raw_lines = text.splitlines()
    boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(raw_lines):
        m = NOTICE_HEAD_RE.match(line.strip())
        if m:
            boundaries.append((i, m.group(1)))

    preamble = raw_lines[: boundaries[0][0]] if boundaries else raw_lines[:]

    notices: list[dict[str, Any]] = []
    for bi, (start_idx, num) in enumerate(boundaries):
        end_idx = boundaries[bi + 1][0] if bi + 1 < len(boundaries) else len(raw_lines)
        chunk = raw_lines[start_idx + 1 : end_idx]
        if strip_headers:
            chunk = strip_running_headers(chunk)

        titles, body_only = extract_title_stack(chunk)
        body_for_segments = body_only if body_only else chunk
        segments = segment_body_lines(body_for_segments)
        derived = try_parse_s_no_table(chunk)

        entry: dict[str, Any] = {
            "notice_no": num,
            "title_lines": titles,
            "body_lines": chunk,
            "body_segments": segments,
            "body_text": "\n".join(chunk).strip(),
        }
        if derived:
            entry["derived_table"] = derived
        notices.append(entry)

    return preamble, notices


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse Kenya Gazette txt into JSON notices.")
    ap.add_argument("input_txt", type=Path, help="Plain text export of the Gazette")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON path (default: <input>.notices.json)",
    )
    ap.add_argument(
        "--strip-running-headers",
        action="store_true",
        help="Drop common page headers / page numbers between notice lines",
    )
    ap.add_argument(
        "--compact",
        action="store_true",
        help="Omit body_segments and body_lines; keep body_text only",
    )
    args = ap.parse_args()

    text = args.input_txt.read_text(encoding="utf-8", errors="replace")
    preamble, notices = parse_notices(text, strip_headers=args.strip_running_headers)

    out: dict[str, Any] = {
        "source_file": str(args.input_txt.resolve()),
        "preamble_lines": preamble,
        "notice_count": len(notices),
        "notices": notices,
    }

    if args.compact:
        for n in out["notices"]:
            n.pop("body_segments", None)
            n.pop("body_lines", None)

    out_path = args.output or args.input_txt.with_suffix(args.input_txt.suffix + ".notices.json")
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(notices)} notices to {out_path}")


if __name__ == "__main__":
    main()
