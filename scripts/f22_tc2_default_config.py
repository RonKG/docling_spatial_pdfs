#!/usr/bin/env python
"""F22 TC2: parse_file with default config=None still works.

Backward compatibility — F21 callers who don't pass config still work.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import Envelope, parse_file  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXINo 100.pdf"


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    
    # No config argument — should use defaults
    env = parse_file(PDF)
    
    assert isinstance(env, Envelope), (
        f"parse_file must return Envelope, got {type(env).__name__}"
    )
    assert len(env.pdf_sha256) == 64, (
        f"pdf_sha256 must be 64-hex, got {len(env.pdf_sha256)} chars"
    )
    
    print(f"TC2 PASS: parse_file with default config=None works "
          f"(pdf_sha256={env.pdf_sha256[:12]}..., notices={len(env.notices)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
