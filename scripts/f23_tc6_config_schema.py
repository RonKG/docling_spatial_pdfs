"""TC6: Config schema generation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import get_config_schema


def test_tc6():
    schema = get_config_schema()

    # Check required top-level keys
    assert "$schema" in schema, "Missing $schema"
    assert "$id" in schema, "Missing $id"
    assert "title" in schema, "Missing title"
    assert "type" in schema, "Missing type"
    assert "properties" in schema, "Missing properties"

    # Check type
    assert schema["type"] == "object", f"Expected type='object', got {schema['type']}"

    # Check for expected properties (llm, runtime, bundles)
    expected_properties = ["llm", "runtime", "bundles"]
    for prop in expected_properties:
        assert prop in schema["properties"], f"Missing property: {prop}"

    # Check $defs has the expected config models
    defs = schema.get("$defs", {})
    expected_defs = ["LLMPolicy", "RuntimeOptions", "Bundles"]
    for model in expected_defs:
        assert model in defs, f"Missing $defs entry for {model}"

    print(f"TC6 PASS: Config schema valid")
    print(f"  - Properties: {list(schema['properties'].keys())}")
    print(f"  - $defs: {list(defs.keys())}")
    return True


if __name__ == "__main__":
    try:
        test_tc6()
    except AssertionError as e:
        print(f"TC6 FAIL: {e}")
        sys.exit(1)
