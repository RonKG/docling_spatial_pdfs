"""F20 helper: patch notebook cell 29 to reference imported version constants.

The F14 inline test cell hardcoded ``"0.1.0"`` and ``"1.0"`` as comparison
literals. Rewire them to the imported ``LIBRARY_VERSION`` /
``SCHEMA_VERSION`` constants so TC5's grep returns zero and the test still
expresses the same intent.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "gazette_docling_pipeline_spatial.ipynb"


def main() -> int:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    src = "".join(nb["cells"][29]["source"])

    before = 'elif lib_versions[0] != "0.1.0" or schema_versions[0] != "1.0":'
    after = 'elif lib_versions[0] != LIBRARY_VERSION or schema_versions[0] != SCHEMA_VERSION:'
    assert before in src, "expected hardcoded version comparison not found"
    src = src.replace(before, after)

    before2 = (
        "f\"  PASS T4: All {len(records)} gazettes share library_version='0.1.0' "
        "and schema_version='1.0'\""
    )
    after2 = (
        "f\"  PASS T4: All {len(records)} gazettes share library_version={LIBRARY_VERSION!r} "
        "and schema_version={SCHEMA_VERSION!r}\""
    )
    if before2 in src:
        src = src.replace(before2, after2)

    nb["cells"][29]["source"] = src.splitlines(keepends=True)
    NOTEBOOK.write_text(
        json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Patched cell 29")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
