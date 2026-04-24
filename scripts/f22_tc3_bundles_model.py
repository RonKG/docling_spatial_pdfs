#!/usr/bin/env python
"""F22 TC3: write_envelope with Bundles instance.

Proves Bundles model accepted; new derivation logic works.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import parse_file, write_envelope, Bundles  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXXIVNo 282.pdf"


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    
    env = parse_file(PDF)
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        bundles = Bundles(
            notices=True,
            corrigenda=True,
            document_index=True,
            gazette_spatial_json=True,
        )
        written = write_envelope(env, tmp_path, bundles=bundles, pdf_path=PDF)
        
        # Check returned keys
        expected_keys = {"gazette_spatial_json", "notices", "corrigenda", "document_index"}
        actual_keys = set(written.keys())
        assert actual_keys == expected_keys, (
            f"Expected keys {expected_keys}, got {actual_keys}"
        )
        
        # Check all files exist
        for key, path in written.items():
            assert path.exists(), f"File not written: {path}"
        
        # Check notices.json
        notices_path = written["notices"]
        notices_data = json.loads(notices_path.read_text(encoding="utf-8"))
        assert isinstance(notices_data, list), "notices should be a list"
        assert len(notices_data) == 201, f"Expected 201 notices, got {len(notices_data)}"
        
        # Check corrigenda.json
        corrigenda_path = written["corrigenda"]
        corrigenda_data = json.loads(corrigenda_path.read_text(encoding="utf-8"))
        assert isinstance(corrigenda_data, list), "corrigenda should be a list"
        
        # Check index.json
        index_path = written["document_index"]
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        assert isinstance(index_data, dict), "index should be a dict"
        assert index_data.get("gazette_issue_id") == "KE-GAZ-CXXIV-282-2022-12-23", (
            f"Index gazette_issue_id mismatch: {index_data.get('gazette_issue_id')}"
        )
        assert index_data.get("n_notices") == 201, (
            f"Index n_notices mismatch: {index_data.get('n_notices')}"
        )
        
        print(f"TC3 PASS: write_envelope with Bundles model works "
              f"(notices={len(notices_data)}, corrigenda={len(corrigenda_data)}, "
              f"index keys={list(index_data.keys())})")
        return 0


if __name__ == "__main__":
    sys.exit(main())
