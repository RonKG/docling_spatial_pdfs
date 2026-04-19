# Kenya Gazette PDF library — LLM ideation prompt

Use this document as a **copy-paste prompt** (or briefing) for another model session to design a maintainable Python library: **PDF in → structured, DB-ready JSON out**, with **version-to-version comparability** and explicit **configuration** (LLM on/off, which artifacts to emit, feeds and grain).

Related notes in this repo: `analysis/analysis-01/schema design analysis 01.md` (identity keys, issue vs notice, versioning).

---

## Prompt (paste below this line)

**Role:** You are a senior Python library designer and document-IR engineer. Help me design a **maintainable, extensible** Python package that ingests **Kenya Gazette PDFs** and emits **structured, database-ready JSON** (or equivalent typed objects), with a clear path to **improve accuracy over time** and let **client applications compare outputs across library versions** on the same PDF.

### Product goal

- **Primary flow:** `PDF in → validated structured gazette data out` (plus metadata needed for ops and quality).
- **Distribution:** Installable like any normal Python package (`pip install …`), importable API, usable from other apps and services.
- **Non-goal (for now):** Building the host app’s database schema or UI—focus on the **library contract**, **schemas**, **versioning**, and **quality signals**.

### Hard requirements

1. **Structured output** that maps cleanly to persistence (rows/documents) without lossy “mystery blobs.”
2. **Extensibility:** new gazette layouts, notice types, or extraction strategies without rewriting consumers.
3. **Accuracy can improve over time:** pipeline stages should be swappable (rules → ML → LLM assist, etc.).
4. **Version comparison:** a client should be able to run **v1.0 vs v2.0** on the **same PDF** and decide whether to **migrate stored data** based on **quality deltas** (not just diff noise).
5. **Observability:** enough diagnostics to debug bad pages, bad tables, and low-confidence fields—without leaking secrets in logs.

### Questions to answer (be opinionated)

**A. Public API shape**

- Single entry point vs facades (`parse`, `parse_file`, `parse_bytes`)?
- Return **Pydantic/dataclasses** vs raw **dict/JSON** vs both?
- How to expose **optional** stages (OCR, table recovery, LLM repair) without complicating the default path?

**B. Configuration and inputs beyond the PDF**

Propose a coherent model for:

- **API keys** (which features need them; how to pass: env vs explicit params vs config file; redaction in logs).
- **Field selection / projection** (“only return legal metadata + notices, skip full text” etc.).
- **Locale, date formats, gazette series/volume assumptions** (Kenya-specific).
- **Output verbosity:** minimal vs audit mode (bounding boxes, provenance, token usage).
- **Determinism:** seeds, caching, “frozen pipeline” runs for regression tests.

**C. LLM controls**

- A clear **`llm` policy**: `disabled` | `optional` | `required` (or equivalent), plus **per-stage** overrides if useful (for example: `llm: { enabled: false }` vs `llm: { enabled: true, stages: { classify_notices: true, repair_tables: false } }`).
- Behavior when LLM is off: deterministic fallbacks, degraded accuracy, and how **quality/confidence** reflects that.
- **Cost and privacy:** how API keys are supplied, whether prompts/responses are **never logged** by default, and optional **usage** fields in the output envelope.

**D. Document / artifact selection (“what to output”)**

Treat the parse result as an **envelope** with optional **bundles**. The user should be able to configure:

- **`include` / `exclude` lists** or a **`bundles`** map with booleans (pick one pattern and justify it).
- Examples of bundles to consider naming: `document_index`, `pages`, `blocks`, `tables`, `notices`, `attachments_metadata`, `full_text`, `spatial_markdown`, `debug_trace`, `provenance`, `images` (thumbnails/crops), etc.
- Rules for **defaults** (safe/minimal vs “everything”) and for **stable JSON** when optional bundles are omitted (no accidental schema drift).

**E. Feeds and grain**

Define **feeds** as named **output modes** with a documented **grain** (aggregation level) and **payload shape**.

Propose a small **taxonomy**, for example (illustrative—replace with better names):

| Feed id (example) | Grain | Typical contents | Typical consumer |
|-------------------|--------|------------------|------------------|
| `gazette_summary` | whole PDF | Issue metadata, section list, counts | Catalog / search index |
| `notice_stream` | notice | One record per legal notice with fields + confidence | DB rows |
| `page_stream` | page | Per-page text/layout/table summary | QA / OCR review |
| `block_stream` | block | Fine blocks with bboxes | Highlighting / tooling |
| `table_feed` | table | Extracted tables with headers + cells | Analytics |

Requirements:

- Each feed must declare: **grain**, **required fields**, **optional fields**, **ordering key**, and **stable ID strategy** (for comparing library v1 vs v2).
- Explain how **multiple feeds** can be requested in one run **without duplicating heavy work** (shared pipeline, selective serialization).
- Explain how **projection** works: user selects feeds **and** field subsets within a feed (if you recommend field masks, say how they interact with schema versioning).

**F. Validation**

- If the user asks for a feed/grain combination that is inconsistent (for example, `notice_stream` without running notice detection), how does the library **fail fast** vs **degrade** with warnings?

**G. Schema and compatibility**

- **JSON Schema** or **OpenAPI-style** descriptions for outputs?
- **Semantic versioning** rules: what changes are MAJOR vs MINOR vs PATCH for consumers?
- **Migration helpers:** deprecations, adapters, `output_format_version` field?

**H. Quality and confidence (first-class)**

- How should the library encode **per-field confidence**, **evidence** (page, bbox, snippet), and **overall document quality**?
- How should a client **compare** v1 vs v2: stable IDs for notices, alignment keys, diff strategies?

Align with a layered model if helpful (see repo `docs/data-quality-confidence-scoring.md` for scoring concepts).

**I. Testing and golden files**

- How to structure **fixtures** (redacted PDFs, page images, expected JSON)?
- **Regression suite** design: snapshot tests vs property tests vs LLM-eval (when appropriate)?

**J. Packaging and docs**

- Module layout, plugin points, and **minimal** public surface area.
- What belongs in README vs separate deep docs?

### Constraints and assumptions (adjust if wrong)

- PDFs may be **native text** or require **OCR** for some pages.
- Some gazette content is **tabular**; tables must not be flattened carelessly.
- Downstream systems care about **legal notice identity** and **citations** more than decorative layout.
- **Offline-first:** core parsing works without network; LLM steps are optional.
- Optional: a **CLI** later (`kenya-gazette parse …`); design the core so CLI is a thin wrapper.

### Deliverables from the session

1. **2–3 architecture options** with tradeoffs (complexity, accuracy ceiling, operational cost).
2. A recommended **default architecture** and **MVP scope** (what ships in 1.0).
3. A concrete **Python API sketch** (function signatures + config object).
4. A **JSON envelope** proposal including: `library_version`, `schema_version`, `document`, `quality`, `warnings`, `provenance`, and optional `cost`/`usage` if LLM is used.
5. **YAML or Python config examples** showing: LLM off + minimal feeds; LLM on + full audit feeds; a middle option for production DB ingestion.
6. A **roadmap**: milestones for rules-only baseline → hybrid → smarter extraction, and how each milestone preserves **comparability** across versions.

**Start:** Ask **at most 5 clarifying questions** only if absolutely necessary; otherwise proceed with best-effort assumptions and mark them explicitly.

---

## Local constraints (optional paste-in for Kenya-specific sessions)

- Notices are cited by **issue + notice number**; notice numbers repeat across issues; uniqueness is **within an issue**. See `analysis/schema design analysis 01.md`.
- Prefer a canonical **`gazette_issue`** id and stable **notice alignment keys** for v1 vs v2 diffs.
