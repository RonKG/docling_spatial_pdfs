"""TC8: Import smoke - no circular imports."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_tc8():
    try:
        from kenya_gazette_parser import get_envelope_schema, validate_envelope_json, write_schema_file
        print("TC8 PASS: Import from package root works")
        print(f"  - get_envelope_schema: {get_envelope_schema.__module__}")
        print(f"  - validate_envelope_json: {validate_envelope_json.__module__}")
        print(f"  - write_schema_file: {write_schema_file.__module__}")
        return True
    except ImportError as e:
        print(f"TC8 FAIL: ImportError - {e}")
        return False
    except Exception as e:
        print(f"TC8 FAIL: Unexpected error - {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    if not test_tc8():
        sys.exit(1)
