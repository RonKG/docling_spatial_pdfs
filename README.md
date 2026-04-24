# kenya-gazette-parser

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-≥3.10-blue.svg)](https://www.python.org/downloads/)

Parse Kenya Gazette PDFs into structured, validated JSON envelopes.

Built on [Docling](https://github.com/DS4SD/docling) for PDF extraction.

## Installation

### Install from GitHub

```bash
pip install git+https://github.com/rwahome/docling_spatial_pdfs.git
```

### Install for development

```bash
git clone https://github.com/rwahome/docling_spatial_pdfs.git
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
