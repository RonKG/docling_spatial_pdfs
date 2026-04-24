#!/usr/bin/env python
"""F22 TC8: tables bundle derivation.

Proves tables derivation logic works.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import parse_file, write_envelope, Bundles  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXXVIINo 63.pdf"


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    
    env = parse_file(PDF)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        bundles = Bundles(
            gazette_spatial_json=False,
            notices=False,
            corrigenda=False,
            tables=True,
        )
        written = write_envelope(env, tmp_path, bundles=bundles)
        
        # Check tables was written
        assert "tables" in written, f"tables not in written: {written.keys()}"
        
        # Check tables.json structure
        tables_path = written["tables"]
        assert tables_path.exists(), f"File not written: {tables_path}"
        
        tables_data = json.loads(tables_path.read_text(encoding="utf-8"))
        assert isinstance(tables_data, list), "tables should be a list"
        
        # Each entry should have notice_id and derived_table
        for entry in tables_data:
            assert "notice_id" in entry, f"Missing notice_id in entry: {entry}"
            assert "derived_table" in entry, f"Missing derived_table in entry: {entry}"
        
        print(f"TC8 PASS: tables derivation works (tables count={len(tables_data)})")
        return 0


if __name__ == "__main__":
    sys.exit(main())
