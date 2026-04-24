#!/usr/bin/env python
"""F24 TC4: Model import smoke test.

Imports all 16 Pydantic models from kenya_gazette_parser.models and
verifies __all__ length.
"""
from __future__ import annotations

import sys


def main() -> None:
    print("Importing all 16 models from kenya_gazette_parser.models...")
    
    from kenya_gazette_parser.models import (
        Envelope,
        GazetteIssue,
        Notice,
        Corrigendum,
        ConfidenceScores,
        DocumentConfidence,
        Provenance,
        LayoutInfo,
        BodySegment,
        DerivedTable,
        Warning,
        Cost,
        GazetteConfig,
        LLMPolicy,
        RuntimeOptions,
        Bundles,
    )
    
    f18_models = [
        ("Envelope", Envelope),
        ("GazetteIssue", GazetteIssue),
        ("Notice", Notice),
        ("Corrigendum", Corrigendum),
        ("ConfidenceScores", ConfidenceScores),
        ("DocumentConfidence", DocumentConfidence),
        ("Provenance", Provenance),
        ("LayoutInfo", LayoutInfo),
        ("BodySegment", BodySegment),
        ("DerivedTable", DerivedTable),
        ("Warning", Warning),
        ("Cost", Cost),
    ]
    
    f22_models = [
        ("GazetteConfig", GazetteConfig),
        ("LLMPolicy", LLMPolicy),
        ("RuntimeOptions", RuntimeOptions),
        ("Bundles", Bundles),
    ]
    
    all_models = f18_models + f22_models
    print(f"  Imported {len(all_models)} models")
    print(f"  F18 models (12): {[name for name, _ in f18_models]}")
    print(f"  F22 models (4): {[name for name, _ in f22_models]}")
    
    import kenya_gazette_parser.models as models_module
    
    all_exports = models_module.__all__
    if len(all_exports) != 16:
        print(f"FAIL: __all__ has {len(all_exports)} items, expected 16")
        print(f"  __all__: {all_exports}")
        sys.exit(1)
    
    print(f"  __all__ length: {len(all_exports)}")
    
    for name, cls in all_models:
        if cls is None:
            print(f"FAIL: {name} is None")
            sys.exit(1)
        if not hasattr(cls, "model_validate"):
            print(f"FAIL: {name} missing model_validate (not a Pydantic model?)")
            sys.exit(1)
    
    print("\nTC4 OK")


if __name__ == "__main__":
    main()
