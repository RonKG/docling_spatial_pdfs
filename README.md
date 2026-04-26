# kenya-gazette-parser

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-≥3.10-blue.svg)](https://www.python.org/downloads/)

Parse Kenya Gazette PDFs into structured, validated JSON envelopes.

Built on [Docling](https://github.com/DS4SD/docling) for PDF extraction.

## Installation

### Install from GitHub

```bash
pip install git+https://github.com/RonKG/docling_spatial_pdfs.git
```

### Install for development

```bash
git clone https://github.com/RonKG/docling_spatial_pdfs.git
cd docling_spatial_pdfs
pip install -e ".[dev]"
```

## Quickstart

```python
from kenya_gazette_parser import parse_file, write_envelope

# Parse a PDF into a validated Envelope
env = parse_file("path/to/gazette.pdf")

# Inspect the results
print(f"Issue: {env.issue.gazette_issue_id}")
print(f"Notices: {len(env.notices)}")
print(f"Document confidence: {env.document_confidence.mean_composite:.3f}")

# Access individual notices
for notice in env.notices[:3]:
    print(f"  - {notice.notice_id}: {notice.gazette_notice_header or '(no header)'}")
```

## Envelope structure

`parse_file` and `parse_bytes` return a validated **`Envelope`**: a single in-memory object that matches the v1 contract and the generated JSON schema.

**Top level**

| Field | Role |
| --- | --- |
| `library_version` | Package version string. |
| `schema_version` | Envelope shape version (e.g. `"1.0"`). |
| `output_format_version` | Integer; bumps only on breaking JSON shape changes. |
| `extracted_at` | When parsing ran (UTC). Changes every run; exclude it from idempotency or diff checks. |
| `pdf_sha256` | SHA-256 of the input PDF bytes (idempotency for the file). |
| `issue` | `GazetteIssue` — masthead and issue metadata. |
| `notices` | `list[Notice]` — one entry per extracted notice. |
| `corrigenda` | `list[Corrigendum]` — correction notices and cross-refs. |
| `document_confidence` | Whole-document quality scores and band counts. |
| `layout_info` | Layout confidence and per-page spatial layout detail. |
| `warnings` | Structured messages (e.g. masthead fallback, table coerced to text, corrigendum defaults). |
| `cost` | `None` in 1.0; reserved for LLM token usage when that path is active. |

**`issue` (`GazetteIssue`)** — `gazette_issue_id` (stable issue key when masthead parses), `volume`, `issue_no`, `publication_date`, `supplement_no`, `masthead_text`, `parse_confidence`.

**Each `notice` (`Notice`)** — `notice_id` and `gazette_issue_id` (stable keys), optional `gazette_notice_no` / `gazette_notice_header`, `title_lines`, `gazette_notice_full_text`, `body_segments` (each segment is `text` or `blank` in 1.0), `derived_table` when tabular data was recovered, `provenance`, `confidence_scores` and `confidence_reasons`, and `content_sha256` of the notice text (payload key for diffs). Optional `other_attributes` holds parser-specific keys.

**Serialization** — `env.model_dump(mode="json")` (or Pydantic v2’s JSON helpers) is suitable for storage or APIs.

Full field lists, identity rules, and API details: [docs/library-contract-v1.md](docs/library-contract-v1.md) (sections 2 and 3).

## Writing Output Files

```python
from kenya_gazette_parser import write_envelope

# Write all default bundles to disk
written = write_envelope(env, out_dir="output/", pdf_path="path/to/gazette.pdf")
for name, path in written.items():
    print(f"{name}: {path}")
```

Pass `bundles={...}` to select specific outputs. See the `Bundles` model for options.

## Configuration

Pass a `GazetteConfig` to customize parsing. LLM validation stages are declared but inactive in 1.0.

**1.0 note:** Some `GazetteConfig` fields (for example `llm` and most of `runtime`) are reserved for post-1.0 behavior. They are accepted for forward compatibility but do not change `parse_file` or `parse_bytes` output yet.

```python
from kenya_gazette_parser import parse_file, GazetteConfig, Bundles

config = GazetteConfig(bundles=Bundles(notices=True, document_index=True))
env = parse_file("gazette.pdf", config=config)
```

See [docs/library-contract-v1.md](docs/library-contract-v1.md) section 5 for full API.

## JSON Schema

The output envelope conforms to a JSON Schema. Use it to validate outputs from other tools or languages.

```python
from kenya_gazette_parser import get_envelope_schema, validate_envelope_json
import json

# Get the schema
schema = get_envelope_schema()

# Validate a JSON file
with open("gazette_spatial.json") as f:
    data = json.load(f)
validate_envelope_json(data)  # Raises if invalid
```

Schema file: `kenya_gazette_parser/schema/envelope.schema.json`

## Status

**Version:** 0.1.0 (alpha)  
**Schema version:** 1.0 (locked)

API is stable for 1.0. See [PROGRESS.md](PROGRESS.md) for roadmap.

## License

Apache License 2.0. See [LICENSE](LICENSE).
