#!/usr/bin/env python
"""F24 TC5: End-to-end smoke test.

Calls parse_file on CXIINo 76 (small, 3 notices, stable),
validates envelope against JSON schema.

This test runs in a subprocess wrapper to handle potential
std::bad_alloc from Docling OCR (documented G1 gotcha).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


INNER_SCRIPT = '''
import sys
from pathlib import Path

repo_root = Path(r"{repo_root}")
pdf_path = repo_root / "pdfs" / "Kenya Gazette Vol CXIINo 76.pdf"

if not pdf_path.exists():
    print(f"FAIL: PDF not found at {{pdf_path}}")
    sys.exit(1)

print(f"Parsing {{pdf_path.name}}...")

from kenya_gazette_parser import parse_file, validate_envelope_json, Envelope

env = parse_file(pdf_path)

if not isinstance(env, Envelope):
    print(f"FAIL: parse_file returned {{type(env).__name__}}, expected Envelope")
    sys.exit(1)

print(f"  Returned Envelope with {{len(env.notices)}} notices")

if len(env.notices) != 3:
    print(f"FAIL: Expected 3 notices, got {{len(env.notices)}}")
    sys.exit(1)

print("Validating against JSON schema...")
env_dict = env.model_dump(mode="json")
result = validate_envelope_json(env_dict)

if result is not True:
    print(f"FAIL: validate_envelope_json returned {{result}}, expected True")
    sys.exit(1)

print("  Validation passed")
print("\\nTC5 OK")
'''


def main() -> None:
    repo_root = Path(__file__).parent.parent.resolve()
    pdf_path = repo_root / "pdfs" / "Kenya Gazette Vol CXIINo 76.pdf"
    
    if not pdf_path.exists():
        print(f"FAIL: PDF not found at {pdf_path}")
        sys.exit(1)
    
    print(f"Running TC5 in subprocess (G1 std::bad_alloc mitigation)...")
    print(f"  PDF: {pdf_path.name}")
    
    script = INNER_SCRIPT.format(repo_root=str(repo_root))
    
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=600,
    )
    
    print(result.stdout, end="")
    
    if result.returncode != 0:
        print(f"\nSubprocess stderr:\n{result.stderr}")
        print(f"\nFAIL: Subprocess exited with code {result.returncode}")
        sys.exit(1)
    
    if "TC5 OK" not in result.stdout:
        print("\nFAIL: TC5 OK not found in output")
        sys.exit(1)


if __name__ == "__main__":
    main()
