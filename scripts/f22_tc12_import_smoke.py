#!/usr/bin/env python
"""F22 TC12: Import smoke test for all 16 models.

Verifies no circular import issues and all models are accessible.
"""
import sys

def main() -> int:
    try:
        from kenya_gazette_parser.models import (
            BodySegment,
            Bundles,
            ConfidenceScores,
            Corrigendum,
            Cost,
            DerivedTable,
            DocumentConfidence,
            Envelope,
            GazetteConfig,
            GazetteIssue,
            LayoutInfo,
            LLMPolicy,
            Notice,
            Provenance,
            RuntimeOptions,
            Warning,
        )
        
        # Verify all 16 are actually classes
        models = [
            BodySegment, Bundles, ConfidenceScores, Corrigendum, Cost,
            DerivedTable, DocumentConfidence, Envelope, GazetteConfig,
            GazetteIssue, LayoutInfo, LLMPolicy, Notice, Provenance,
            RuntimeOptions, Warning,
        ]
        
        for m in models:
            assert hasattr(m, "model_fields"), f"{m.__name__} is not a Pydantic model"
        
        print(f"TC12 PASS: All 16 models imported successfully: {[m.__name__ for m in models]}")
        return 0
    except ImportError as e:
        print(f"TC12 FAIL: ImportError - {e}")
        return 1
    except Exception as e:
        print(f"TC12 FAIL: {type(e).__name__} - {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
