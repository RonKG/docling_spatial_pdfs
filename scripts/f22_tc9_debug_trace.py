#!/usr/bin/env python
"""F22 TC9: debug_trace bundle derivation.

Proves debug_trace derivation logic works.
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
            gazette_spatial_json=False,
            notices=False,
            corrigenda=False,
            debug_trace=True,
        )
        written = write_envelope(env, tmp_path, bundles=bundles)
        
        # Check debug_trace was written
        assert "debug_trace" in written, f"debug_trace not in written: {written.keys()}"
        
        # Check trace.json structure
        trace_path = written["debug_trace"]
        assert trace_path.exists(), f"File not written: {trace_path}"
        
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
        assert isinstance(trace_data, dict), "trace should be a dict"
        
        # Check required keys
        assert "warnings" in trace_data, "Missing warnings key"
        assert "layout_info" in trace_data, "Missing layout_info key"
        assert "per_notice_reasons" in trace_data, "Missing per_notice_reasons key"
        
        # Check per_notice_reasons structure
        per_notice = trace_data["per_notice_reasons"]
        assert isinstance(per_notice, list), "per_notice_reasons should be a list"
        assert len(per_notice) == 201, f"Expected 201 entries, got {len(per_notice)}"
        
        for entry in per_notice:
            assert "notice_id" in entry, f"Missing notice_id in entry: {entry}"
            assert "confidence_reasons" in entry, f"Missing confidence_reasons in entry"
        
        print(f"TC9 PASS: debug_trace derivation works "
              f"(warnings={len(trace_data['warnings'])}, "
              f"per_notice_reasons={len(per_notice)})")
        return 0


if __name__ == "__main__":
    sys.exit(main())
