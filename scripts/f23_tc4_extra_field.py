"""TC4: Validation failure - extra field on strict model raises ValidationError."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import validate_envelope_json
import jsonschema


def test_tc4():
    # Load a valid envelope first
    output_dir = Path(__file__).parent.parent / "output"
    json_path = output_dir / "Kenya Gazette Vol CXXIVNo 282" / "Kenya Gazette Vol CXXIVNo 282_gazette_spatial.json"

    if not json_path.exists():
        print("TC4 SKIP: Canonical JSON not found")
        return True

    with open(json_path, "r", encoding="utf-8") as f:
        valid_data = json.load(f)

    # Add an unknown field to the envelope
    invalid_data = {**valid_data, "unknown_field": "value"}

    try:
        validate_envelope_json(invalid_data)
        print("TC4 FAIL: Expected ValidationError for extra field but none raised")
        return False
    except jsonschema.ValidationError as e:
        error_msg = str(e).lower()
        # Check error mentions additionalProperties or the unknown field
        if "additionalproperties" in error_msg or "unknown_field" in error_msg:
            print(f"TC4 PASS: ValidationError raised for extra field")
            print(f"  Error: {e.message[:100]}...")
            return True
        else:
            print(f"TC4 FAIL: ValidationError raised but message doesn't mention additionalProperties")
            print(f"  Error: {e.message}")
            return False
    except Exception as e:
        print(f"TC4 FAIL: Unexpected error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    if not test_tc4():
        sys.exit(1)
