"""TC3: Validation failure - invalid envelope raises ValidationError."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import validate_envelope_json
import jsonschema


def test_tc3():
    # Invalid envelope: missing required fields, wrong sha length
    invalid_data = {"pdf_sha256": "short"}

    try:
        validate_envelope_json(invalid_data)
        print("TC3 FAIL: Expected ValidationError but none raised")
        return False
    except jsonschema.ValidationError as e:
        # Check error message mentions missing required fields
        error_msg = str(e)
        required_fields = ["library_version", "schema_version", "output_format_version",
                          "extracted_at", "pdf_sha256", "issue", "notices", "corrigenda",
                          "document_confidence", "layout_info", "warnings"]
        found_mention = any(field in error_msg for field in required_fields) or "required" in error_msg.lower()

        if found_mention:
            print(f"TC3 PASS: ValidationError raised correctly")
            print(f"  Error mentions: {e.message[:100]}...")
            return True
        else:
            print(f"TC3 FAIL: ValidationError raised but message doesn't mention required fields")
            print(f"  Error: {e.message}")
            return False
    except Exception as e:
        print(f"TC3 FAIL: Unexpected error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    if not test_tc3():
        sys.exit(1)
