#!/usr/bin/env python
"""F22 TC1: parse_file with GazetteConfig — modern 2-column.

Proves config threading works; replaces F21's stub guard.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

from kenya_gazette_parser import Envelope, parse_file, GazetteConfig, LLMPolicy  # noqa: E402

PDF = REPO / "pdfs" / "Kenya Gazette Vol CXXIVNo 282.pdf"


def main() -> int:
    assert PDF.exists(), f"Missing canonical PDF: {PDF}"
    
    # Create a config with explicit LLM settings
    config = GazetteConfig(llm=LLMPolicy(mode="disabled"))
    
    # This should NOT raise NotImplementedError anymore (F22 replaces F21's guard)
    env = parse_file(PDF, config=config)
    
    assert isinstance(env, Envelope), (
        f"parse_file must return Envelope, got {type(env).__name__}"
    )
    assert env.issue.gazette_issue_id == "KE-GAZ-CXXIV-282-2022-12-23", (
        f"gazette_issue_id mismatch: got {env.issue.gazette_issue_id!r}"
    )
    n_notices = len(env.notices)
    assert n_notices == 201, f"Expected 201 notices, got {n_notices}"
    
    print(f"TC1 PASS: parse_file with GazetteConfig works (notices={n_notices})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
