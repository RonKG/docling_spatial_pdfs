"""TC5: Checked-in schema file matches runtime schema."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import get_envelope_schema


def deep_equal(a, b, path=""):
    """Deep compare two dicts/lists, ignoring key order."""
    if type(a) != type(b):
        return False, f"Type mismatch at {path}: {type(a).__name__} vs {type(b).__name__}"

    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            missing = set(a.keys()) - set(b.keys())
            extra = set(b.keys()) - set(a.keys())
            return False, f"Key mismatch at {path}: missing={missing}, extra={extra}"
        for key in a:
            eq, msg = deep_equal(a[key], b[key], f"{path}.{key}")
            if not eq:
                return False, msg
        return True, ""
    elif isinstance(a, list):
        if len(a) != len(b):
            return False, f"List length mismatch at {path}: {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            eq, msg = deep_equal(x, y, f"{path}[{i}]")
            if not eq:
                return False, msg
        return True, ""
    else:
        if a != b:
            return False, f"Value mismatch at {path}: {a!r} vs {b!r}"
        return True, ""


def test_tc5():
    schema_path = Path(__file__).parent.parent / "kenya_gazette_parser" / "schema" / "envelope.schema.json"

    if not schema_path.exists():
        print(f"TC5 FAIL: Schema file not found at {schema_path}")
        return False

    # Load checked-in schema
    with open(schema_path, "r", encoding="utf-8") as f:
        checked_in = json.load(f)

    # Generate runtime schema (bypass cache)
    runtime = get_envelope_schema(use_cache=False)

    # Compare
    equal, msg = deep_equal(checked_in, runtime)

    if equal:
        print("TC5 PASS: Checked-in schema matches runtime schema")
        return True
    else:
        print(f"TC5 FAIL: Schema mismatch - {msg}")
        print("  Run 'python scripts/f23_regenerate_schema.py' to update the checked-in file")
        return False


if __name__ == "__main__":
    if not test_tc5():
        sys.exit(1)
