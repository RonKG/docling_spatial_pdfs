#!/usr/bin/env python3
"""F25 TC2: Verify write_envelope code from README runs correctly."""

import tempfile
import os
from kenya_gazette_parser import parse_file, write_envelope

print("=== TC2: write_envelope example ===")

# First parse to get an envelope
pdf_path = "pdfs/Kenya Gazette Vol CXXIVNo 282.pdf"
env = parse_file(pdf_path)

# Write all default bundles to a temp directory
with tempfile.TemporaryDirectory() as out_dir:
    written = write_envelope(env, out_dir=out_dir, pdf_path=pdf_path)
    
    print(f"Files written to {out_dir}:")
    for name, path in written.items():
        size = os.path.getsize(path)
        print(f"  {name}: {path} ({size} bytes)")
    
    # Verify expected files
    expected_keys = {"gazette_spatial_json", "full_text", "docling_markdown", "spatial_markdown", "docling_json"}
    actual_keys = set(written.keys())
    
    assert actual_keys == expected_keys, f"Expected keys {expected_keys}, got {actual_keys}"
    
    # Verify all files exist and have content
    for name, path in written.items():
        assert os.path.exists(path), f"File {path} does not exist"
        assert os.path.getsize(path) > 0, f"File {path} is empty"

print()
print(f"TC2: PASS (wrote {len(written)} files)")
