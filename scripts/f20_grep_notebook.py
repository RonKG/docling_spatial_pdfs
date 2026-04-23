"""F20 TC5 helper: grep the notebook's source cells for D1 residue."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"

TARGET_VERSION = '"0.1.0"'
TARGET_SCHEMA_RE = re.compile(r'SCHEMA_VERSION\s*=\s*"1\.0"')


def main() -> int:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    version_hits: list[tuple[int, int, str]] = []
    schema_hits: list[tuple[int, int, str]] = []
    for cell_idx, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        for ln_idx, line in enumerate(src.splitlines()):
            if TARGET_VERSION in line:
                version_hits.append((cell_idx, ln_idx, line))
            if TARGET_SCHEMA_RE.search(line):
                schema_hits.append((cell_idx, ln_idx, line))
    print(f"'0.1.0' literal hits in source cells: {len(version_hits)}")
    for h in version_hits:
        print("  cell", h[0], "line", h[1], ":", repr(h[2]))
    print(f"SCHEMA_VERSION = \"1.0\" declaration hits: {len(schema_hits)}")
    for h in schema_hits:
        print("  cell", h[0], "line", h[1], ":", repr(h[2]))
    return 0 if (not version_hits and not schema_hits) else 1


if __name__ == "__main__":
    sys.exit(main())
