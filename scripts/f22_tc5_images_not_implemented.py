#!/usr/bin/env python
"""F22 TC5: Test Bundles(images=True) raises NotImplementedError.

Images bundle is declared but not implemented (post-1.0 work).
"""
import sys
import tempfile
from pathlib import Path

from kenya_gazette_parser.models import Bundles, Envelope, GazetteIssue, DocumentConfidence, LayoutInfo
from kenya_gazette_parser.io import write_envelope

def main() -> int:
    # Create a minimal envelope for testing
    env = Envelope(
        pdf_sha256="a" * 64,
        library_version="0.1.0",
        schema_version="1.0",
        extracted_at="2026-04-23T12:00:00Z",
        output_format_version=1,
        issue=GazetteIssue(
            gazette_issue_id="KE-GAZ-TEST-1-2026-04-23",
            masthead_text="Test masthead",
            parse_confidence=1.0,
        ),
        notices=[],
        corrigenda=[],
        warnings=[],
        document_confidence=DocumentConfidence(
            layout=1.0,
            ocr_quality=1.0,
            notice_split=1.0,
            composite=1.0,
            mean_composite=1.0,
            min_composite=1.0,
            counts={"high": 0, "medium": 0, "low": 0},
            n_notices=0,
        ),
        layout_info=LayoutInfo(layout_confidence=1.0, pages=[]),
    )
    
    with tempfile.TemporaryDirectory() as tmp:
        try:
            write_envelope(env, tmp, bundles=Bundles(images=True))
            print("TC5 FAIL: Expected NotImplementedError for images bundle")
            return 1
        except NotImplementedError as e:
            error_str = str(e)
            if "images" in error_str and "post-1.0" in error_str:
                print("TC5 PASS: Bundles(images=True) raises NotImplementedError with correct message")
                return 0
            else:
                print(f"TC5 FAIL: NotImplementedError raised but wrong message: {e}")
                return 1

if __name__ == "__main__":
    sys.exit(main())
