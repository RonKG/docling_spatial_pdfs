#!/usr/bin/env python
"""F24 TC3: Schema file package-data test.

Verifies envelope.schema.json is accessible from the installed package
via Path(__file__).parent (standard pattern for package data).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    print("Importing kenya_gazette_parser.schema...")
    
    import kenya_gazette_parser.schema as schema_module
    
    schema_dir = Path(schema_module.__file__).parent
    schema_path = schema_dir / "envelope.schema.json"
    
    print(f"  Schema module location: {schema_module.__file__}")
    print(f"  Looking for: {schema_path}")
    
    if not schema_path.exists():
        print(f"FAIL: envelope.schema.json not found at {schema_path}")
        sys.exit(1)
    
    print(f"  File exists: {schema_path.stat().st_size} bytes")
    
    print("Loading schema JSON...")
    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL: Invalid JSON: {e}")
        sys.exit(1)
    
    if "$schema" not in schema:
        print(f"FAIL: Missing '$schema' key in schema")
        print(f"  Keys present: {list(schema.keys())}")
        sys.exit(1)
    
    print(f"  $schema: {schema['$schema']}")
    
    if "$defs" in schema:
        print(f"  $defs count: {len(schema['$defs'])}")
    
    if "properties" in schema:
        print(f"  Top-level properties: {len(schema['properties'])}")
    
    print("\nTC3 OK")


if __name__ == "__main__":
    main()
