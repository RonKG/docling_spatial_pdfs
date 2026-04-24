#!/usr/bin/env python
"""F24 TC2: Public API import smoke test.

Imports all public exports from package root and verifies __version__.
"""
from __future__ import annotations

import sys


def main() -> None:
    print("Importing all public exports from kenya_gazette_parser...")
    
    from kenya_gazette_parser import (
        __version__,
        parse_file,
        parse_bytes,
        write_envelope,
        Envelope,
        GazetteConfig,
        Bundles,
        LLMPolicy,
        RuntimeOptions,
        get_envelope_schema,
        validate_envelope_json,
        write_schema_file,
    )
    
    imports = [
        ("__version__", __version__),
        ("parse_file", parse_file),
        ("parse_bytes", parse_bytes),
        ("write_envelope", write_envelope),
        ("Envelope", Envelope),
        ("GazetteConfig", GazetteConfig),
        ("Bundles", Bundles),
        ("LLMPolicy", LLMPolicy),
        ("RuntimeOptions", RuntimeOptions),
        ("get_envelope_schema", get_envelope_schema),
        ("validate_envelope_json", validate_envelope_json),
        ("write_schema_file", write_schema_file),
    ]
    
    print(f"  Imported {len(imports)} public exports")
    
    if __version__ != "0.1.0":
        print(f"FAIL: __version__ == {__version__!r}, expected '0.1.0'")
        sys.exit(1)
    
    print(f"  __version__ == {__version__!r}")
    
    import kenya_gazette_parser
    all_exports = kenya_gazette_parser.__all__
    print(f"  __all__ has {len(all_exports)} items: {all_exports}")
    
    for name, obj in imports:
        if obj is None:
            print(f"FAIL: {name} is None")
            sys.exit(1)
    
    print("\nTC2 OK")


if __name__ == "__main__":
    main()
