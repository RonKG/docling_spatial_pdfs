"""JSON Schema export for kenya_gazette_parser.

Provides runtime schema generation from Pydantic models and validation helpers.
Gate 4 requires Envelope to validate against its own schema on all canonical PDFs.

This subpackage also contains the checked-in JSON Schema files:
- envelope.schema.json: JSON Schema for Envelope (generated from Pydantic models)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ENVELOPE_SCHEMA_CACHE: dict | None = None


def get_envelope_schema(*, use_cache: bool = True) -> dict[str, Any]:
    """Return the JSON Schema for the Envelope model.

    Parameters
    ----------
    use_cache
        If True (default), returns a cached schema dict after first call.
        If False, regenerates from the Pydantic model each time.

    Returns
    -------
    dict
        A JSON-serializable dict conforming to JSON Schema Draft 2020-12.
        Contains `$defs` for all nested models (GazetteIssue, Notice, etc.).
    """
    global _ENVELOPE_SCHEMA_CACHE
    if use_cache and _ENVELOPE_SCHEMA_CACHE is not None:
        return _ENVELOPE_SCHEMA_CACHE

    from kenya_gazette_parser.models import Envelope

    schema = Envelope.model_json_schema(mode="serialization")
    schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
    schema.setdefault("$id", "https://kenya-gazette-parser/schema/envelope.schema.json")
    schema.setdefault("title", "Kenya Gazette Envelope")

    if use_cache:
        _ENVELOPE_SCHEMA_CACHE = schema
    return schema


def get_config_schema() -> dict[str, Any]:
    """Return the JSON Schema for the GazetteConfig model.

    Separate from Envelope because config is input to parse_file, not output.
    """
    from kenya_gazette_parser.models import GazetteConfig

    schema = GazetteConfig.model_json_schema(mode="serialization")
    schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
    schema.setdefault("$id", "https://kenya-gazette-parser/schema/config.schema.json")
    schema.setdefault("title", "Kenya Gazette Config")
    return schema


def validate_envelope_json(data: dict[str, Any]) -> bool:
    """Validate a raw dict against the Envelope JSON Schema.

    Parameters
    ----------
    data
        A dict loaded from a `_gazette_spatial.json` file or produced by
        `Envelope.model_dump(mode="json")`.

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    jsonschema.ValidationError
        If the data does not conform to the Envelope schema.
    jsonschema.SchemaError
        If the schema itself is invalid (should not happen with Pydantic output).
    """
    import jsonschema

    schema = get_envelope_schema()
    jsonschema.validate(instance=data, schema=schema)
    return True


def write_schema_file(
    out_path: Path | str | None = None,
    *,
    model: str = "envelope",
) -> Path:
    """Write the JSON Schema to a file.

    Parameters
    ----------
    out_path
        Output file path. If None, uses the default location:
        `kenya_gazette_parser/schema/{model}.schema.json`.
    model
        Which schema to write: "envelope" (default) or "config".

    Returns
    -------
    Path
        The path to the written file.
    """
    if model == "envelope":
        schema = get_envelope_schema(use_cache=False)
        default_name = "envelope.schema.json"
    elif model == "config":
        schema = get_config_schema()
        default_name = "config.schema.json"
    else:
        raise ValueError(f"Unknown model: {model!r}. Use 'envelope' or 'config'.")

    if out_path is None:
        out_path = Path(__file__).parent / default_name
    else:
        out_path = Path(out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
