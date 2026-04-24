#!/usr/bin/env python
"""F22 TC4: write_envelope with F21-style dict — backward compat.

F21 callers using dict form still work unchanged.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import parse_file, write_envelope  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXIINo 76.pdf"


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    
    env = parse_file(PDF)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # F21-style dict form
        bundles = {
            "gazette_spatial_json": True,
            "full_text": False,
            "docling_markdown": False,
            "spatial_markdown": False,
            "docling_json": False,
        }
        written = write_envelope(env, tmp_path, bundles=bundles, pdf_path=PDF)
        
        # Check only gazette_spatial_json was written
        assert set(written.keys()) == {"gazette_spatial_json"}, (
            f"Expected only gazette_spatial_json, got {set(written.keys())}"
        )
        
        # Check file exists
        path = written["gazette_spatial_json"]
        assert path.exists(), f"File not written: {path}"
        
        # Count files in directory
        files = list(tmp_path.iterdir())
        assert len(files) == 1, f"Expected 1 file in tmp, got {len(files)}"
        
        print(f"TC4 PASS: write_envelope with dict backward compat works "
              f"(1 file: {files[0].name})")
        return 0


if __name__ == "__main__":
    sys.exit(main())
