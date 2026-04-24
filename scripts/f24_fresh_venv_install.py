#!/usr/bin/env python
"""F24 TC1: Fresh venv installation test.

Creates a temporary venv, installs the package from local path,
verifies all 5 runtime deps resolve (docling, docling-core, openai, pydantic, jsonschema).

Windows note: Uses direct path to venv Python (<venv>/Scripts/python.exe)
instead of activation scripts per Q7.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).parent.parent.resolve()
    
    with tempfile.TemporaryDirectory(prefix="f24_venv_test_") as tmp_dir:
        venv_dir = Path(tmp_dir) / "test_venv"
        venv_python = venv_dir / "Scripts" / "python.exe"
        
        print(f"Creating venv at {venv_dir}...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"FAIL: venv creation failed\n{result.stderr}")
            sys.exit(1)
        
        if not venv_python.exists():
            print(f"FAIL: venv Python not found at {venv_python}")
            sys.exit(1)
        
        print(f"Installing package from {repo_root}...")
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", str(repo_root)],
            capture_output=True,
            text=True,
        )
        
        combined_output = result.stdout + result.stderr
        
        if result.returncode != 0:
            print(f"FAIL: pip install failed (exit code {result.returncode})")
            print(f"stdout:\n{result.stdout}")
            print(f"stderr:\n{result.stderr}")
            sys.exit(1)
        
        if "Successfully installed" not in combined_output:
            if "Requirement already satisfied" not in combined_output:
                print(f"WARN: Expected 'Successfully installed' in output")
                print(f"Output:\n{combined_output}")
        
        print("Verifying kenya_gazette_parser imports...")
        import_check = subprocess.run(
            [
                str(venv_python), "-c",
                "from kenya_gazette_parser import parse_file, get_envelope_schema, __version__; "
                "print(f'Version: {__version__}')"
            ],
            capture_output=True,
            text=True,
        )
        
        if import_check.returncode != 0:
            print(f"FAIL: import check failed")
            print(f"stdout:\n{import_check.stdout}")
            print(f"stderr:\n{import_check.stderr}")
            sys.exit(1)
        
        print(f"Import check: {import_check.stdout.strip()}")
        
        print("Verifying 5 runtime deps are installed...")
        deps_check = subprocess.run(
            [
                str(venv_python), "-c",
                "import docling; import docling_core; import openai; "
                "import pydantic; import jsonschema; print('All 5 deps OK')"
            ],
            capture_output=True,
            text=True,
        )
        
        if deps_check.returncode != 0:
            print(f"FAIL: dependency check failed")
            print(f"stderr:\n{deps_check.stderr}")
            sys.exit(1)
        
        print(f"Deps check: {deps_check.stdout.strip()}")
        
        print("\nTC1 OK")


if __name__ == "__main__":
    main()
