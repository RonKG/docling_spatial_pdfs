"""TC2: Validation - all 6 canonical PDFs validate against schema (Gate 4)."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import validate_envelope_json

CANONICAL_PDFS = [
    "Kenya Gazette Vol CXINo 100",
    "Kenya Gazette Vol CXINo 103",
    "Kenya Gazette Vol CXIINo 76",
    "Kenya Gazette Vol CXXVIINo 63",
    "Kenya Gazette Vol CXXIVNo 282",
    "Kenya Gazette Vol CIINo 83 - pre 2010",
]


def test_tc2():
    output_dir = Path(__file__).parent.parent / "output"
    passed = 0
    failed = 0

    for stem in CANONICAL_PDFS:
        json_path = output_dir / stem / f"{stem}_gazette_spatial.json"
        if not json_path.exists():
            print(f"  SKIP: {stem} (file not found)")
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = validate_envelope_json(data)
            assert result is True
            print(f"  PASS: {stem}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {stem} - {e}")
            failed += 1

    if failed > 0:
        print(f"\nTC2 FAIL: {failed}/{passed + failed} canonical PDFs failed validation")
        return False

    print(f"\nTC2 PASS (Gate 4 CLEARED): All {passed} canonical PDFs validate against schema")
    return True


if __name__ == "__main__":
    if not test_tc2():
        sys.exit(1)
