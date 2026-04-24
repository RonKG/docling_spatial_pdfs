"""TC10: Round-trip - Envelope.model_dump validates against schema.

This test uses subprocess to avoid memory issues from Docling.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import os

PYTHON = Path(__file__).parent.parent / ".venv" / "Scripts" / "python.exe"
PDF_PATH = Path(__file__).parent.parent / "pdfs" / "Kenya Gazette Vol CXXIVNo 282.pdf"
PROJECT_ROOT = Path(__file__).parent.parent


def test_tc10():
    if not PDF_PATH.exists():
        print(f"TC10 SKIP: PDF not found at {PDF_PATH}")
        return True

    # Create a temp script file
    script_content = f'''
import sys
sys.path.insert(0, r"{PROJECT_ROOT}")

from kenya_gazette_parser import parse_file
from kenya_gazette_parser.schema import validate_envelope_json
from pathlib import Path

pdf_path = Path(r"{PDF_PATH}")
print(f"Parsing: {{pdf_path.name}}")

env = parse_file(pdf_path)
print(f"  Notices: {{len(env.notices)}}")

data = env.model_dump(mode="json")
result = validate_envelope_json(data)
print(f"  Validation: {{"PASS" if result else "FAIL"}}")

sys.exit(0 if result else 1)
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(script_content)
        temp_script = f.name

    try:
        result = subprocess.run(
            [str(PYTHON), temp_script],
            capture_output=True,
            text=True,
            timeout=300,
        )

        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr[:500]}")

        if result.returncode == 0:
            print("TC10 PASS: Fresh Envelope.model_dump() validates against schema")
            return True
        else:
            print(f"TC10 FAIL: Exit code {result.returncode}")
            return False
    finally:
        os.unlink(temp_script)


if __name__ == "__main__":
    if not test_tc10():
        sys.exit(1)
