"""TC1: Schema generation - get_envelope_schema() returns valid JSON Schema."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from kenya_gazette_parser.schema import get_envelope_schema


def test_tc1():
    schema = get_envelope_schema()

    # Check required top-level keys
    assert "$schema" in schema, "Missing $schema"
    assert "$id" in schema, "Missing $id"
    assert "title" in schema, "Missing title"
    assert "type" in schema, "Missing type"
    assert "properties" in schema, "Missing properties"
    assert "$defs" in schema, "Missing $defs"

    # Check type
    assert schema["type"] == "object", f"Expected type='object', got {schema['type']}"

    # Check $defs has at least 10 entries for nested models
    defs = schema["$defs"]
    assert len(defs) >= 10, f"Expected at least 10 $defs entries, got {len(defs)}"

    # Check for expected nested models
    expected_models = [
        "GazetteIssue", "Notice", "Corrigendum", "ConfidenceScores",
        "DocumentConfidence", "Provenance", "LayoutInfo", "BodySegment",
        "DerivedTable", "Warning", "Cost"
    ]
    for model in expected_models:
        assert model in defs, f"Missing $defs entry for {model}"

    # Check Envelope properties
    expected_properties = [
        "library_version", "schema_version", "output_format_version",
        "extracted_at", "pdf_sha256", "issue", "notices", "corrigenda",
        "document_confidence", "layout_info", "warnings", "cost"
    ]
    for prop in expected_properties:
        assert prop in schema["properties"], f"Missing property: {prop}"

    # Check DerivedTable has additionalProperties: true (extra="allow")
    derived_table = defs["DerivedTable"]
    assert derived_table.get("additionalProperties") is True, \
        "DerivedTable should have additionalProperties: true"

    # Check other models have additionalProperties: false (extra="forbid")
    for model in ["Notice", "Corrigendum", "BodySegment", "Provenance"]:
        assert defs[model].get("additionalProperties") is False, \
            f"{model} should have additionalProperties: false"

    print(f"TC1 PASS: Schema structure valid")
    print(f"  - $defs count: {len(defs)}")
    print(f"  - Top-level properties: {len(schema['properties'])}")
    print(f"  - Models with additionalProperties: false: {sum(1 for m in defs.values() if m.get('additionalProperties') is False)}")
    print(f"  - Models with additionalProperties: true (DerivedTable): {sum(1 for m in defs.values() if m.get('additionalProperties') is True)}")
    return True


if __name__ == "__main__":
    try:
        test_tc1()
    except AssertionError as e:
        print(f"TC1 FAIL: {e}")
        sys.exit(1)
