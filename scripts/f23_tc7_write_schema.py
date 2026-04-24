"""TC7: write_schema_file() creates file."""
from pathlib import Path
import json
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import write_schema_file


def test_tc7():
    with tempfile.TemporaryDirectory(prefix="f23_tc7_") as tmp_dir:
        out_path = Path(tmp_dir) / "test.schema.json"

        # Write schema to temp file
        result_path = write_schema_file(out_path=out_path)

        # Check file exists
        assert result_path.exists(), f"Schema file not created at {result_path}"

        # Check contents are valid JSON
        with open(result_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Check contains $schema key
        assert "$schema" in schema, "Schema missing $schema key"

        print(f"TC7 PASS: write_schema_file() creates valid schema file")
        print(f"  - Path: {result_path}")
        print(f"  - Size: {result_path.stat().st_size} bytes")
        return True


if __name__ == "__main__":
    try:
        test_tc7()
    except AssertionError as e:
        print(f"TC7 FAIL: {e}")
        sys.exit(1)
