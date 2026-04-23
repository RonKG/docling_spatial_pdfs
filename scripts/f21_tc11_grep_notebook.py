r"""F21 TC11: the notebook no longer defines the Markdown highlight helper.

Walks ``gazette_docling_pipeline_spatial.ipynb`` ``"source"`` strings
(ignoring ``"outputs"``) and counts occurrences of:

* ``def highlight_gazette_notices_in_markdown``
* ``_GAZETTE_NOTICE_MD_LINE``
* ``_GAZETTE_NOTICE_HIGHLIGHT_STYLE``

All three must be zero. The single canonical copy now lives in
``kenya_gazette_parser/io.py`` as ``_highlight_gazette_notices_in_markdown``
+ the two supporting constants.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"

NEEDLES = (
    "def highlight_gazette_notices_in_markdown",
    "_GAZETTE_NOTICE_MD_LINE",
    "_GAZETTE_NOTICE_HIGHLIGHT_STYLE",
)


def main() -> int:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    hits: dict[str, list[tuple[int, int, str]]] = {n: [] for n in NEEDLES}
    for idx, cell in enumerate(nb.get("cells") or []):
        src_list = cell.get("source") or []
        if isinstance(src_list, list):
            src = "".join(src_list)
        else:
            src = str(src_list)
        for line_no, line in enumerate(src.splitlines(), start=1):
            for needle in NEEDLES:
                if needle in line:
                    hits[needle].append((idx, line_no, line.strip()))

    total = sum(len(v) for v in hits.values())
    if total == 0:
        print("TC11 OK (0 matches)")
        return 0

    print(f"TC11 FAIL ({total} matches across {sum(1 for v in hits.values() if v)} needles)")
    for needle, rows in hits.items():
        if rows:
            print(f"  {needle!r}: {len(rows)} hits")
            for cell_idx, line_no, text in rows[:5]:
                print(f"    cell[{cell_idx}] line {line_no}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
