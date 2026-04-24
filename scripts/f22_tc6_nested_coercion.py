#!/usr/bin/env python
"""F22 TC6: Test GazetteConfig with nested LLMPolicy from dict.

Pydantic auto-coerces nested dicts to model instances.
"""
import sys

from kenya_gazette_parser.models import GazetteConfig

def main() -> int:
    cfg = GazetteConfig(llm={"mode": "optional", "model": "gpt-4o"})
    
    assert cfg.llm.mode == "optional", f"Expected 'optional', got {cfg.llm.mode!r}"
    assert cfg.llm.model == "gpt-4o", f"Expected 'gpt-4o', got {cfg.llm.model!r}"
    
    print("TC6 PASS: GazetteConfig with nested LLMPolicy from dict coerces correctly")
    return 0

if __name__ == "__main__":
    sys.exit(main())
