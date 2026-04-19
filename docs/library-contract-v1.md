# Kenya Gazette library contract — v1

Design contract a contributor (or LLM session) can follow to refactor
[`gazette_docling_pipeline_spatial.ipynb`](../gazette_docling_pipeline_spatial.ipynb)
into a `kenya_gazette` package without re-litigating output shape or public
API decisions. Treat the code blocks as illustrative model sketches, not
runnable code yet.

---

## 1. Scope and non-goals

This contract locks the **library output envelope** (top-level JSON shape,
identity rules, confidence shape) and the **public Python API** (entry points,
config object, projection mechanism). It deliberately does **not** specify the
host application's database schema, a CLI, or internal module layout — those
are downstream of a stable envelope and can change without breaking
consumers. See sections E and J of
[ideation prompt](../analysis/kenya-gazette-library-ideation-prompt.md) for
context, and
[schema design analysis 01](../analysis/schema%20design%20analysis%2001.md)
for the identity reasoning this contract operationalizes.

---

## 2. Identity model

Three identifiers, in order of stability, plus a degraded-mode rule.

- **`gazette_issue_id` — canonical issue key.** Format:
  `KE-GAZ-{volume}-{issue_no}-{publication_date}[-S{n}]`. Examples:
  `KE-GAZ-CXXIV-282-2022-12-30`, `KE-GAZ-CXXIV-15-2022-01-28-S2` (second
  supplement). `volume` keeps the masthead Roman numeral verbatim;
  `issue_no` is decimal; `publication_date` is ISO `YYYY-MM-DD` parsed from
  the masthead. The parser rejects any field it cannot normalize and falls
  back per the rule below — it never silently invents one.
- **`notice_id` — composite, derived.** `f"{gazette_issue_id}:{notice_no}"`.
  Stable across re-runs of the same PDF; the alignment key for v1-vs-v2 diffs
  required by the ideation prompt section H.
- **`pdf_sha256` — bytes-level idempotency.** SHA-256 of the input PDF file
  contents. Lets a loader upsert by source even before the masthead is
  parsed, and lets us tell "same PDF re-extracted" from "same logical issue,
  different scan."
- **Degraded-mode rule.** If masthead parsing fails (any required field
  missing or unparseable), `gazette_issue_id` falls back to
  `KE-GAZ-UNKNOWN-{pdf_sha256[:12]}`, `GazetteIssue.parse_confidence` drops
  below `0.5`, and a warning of kind `masthead.parse_failed` is appended to
  `Envelope.warnings`. Notices still get `notice_id`s using the fallback issue
  id, so downstream stays addressable.

Source pointers in [schema design analysis 01](../analysis/schema%20design%20analysis%2001.md):

- "Identity and keys" — composite vs surrogate decision (covered in section 4
  below).
- "Gazette (issue) vs notice (fact)" — why `GazetteIssue` is its own object.
- "What to avoid" — single global `notice_no`, display titles as keys.

---

## 3. Envelope and Notice Pydantic models

Pydantic v2 sketches. Field types are illustrative; see open questions for v1
vs v2 and date-vs-string trade-offs.

```python
class Envelope(BaseModel):
    library_version: str            # e.g. "0.3.1" — package __version__
    schema_version: str             # e.g. "1.0.0" — see section 7
    output_format_version: int      # bumps only on breaking JSON shape change
    extracted_at: datetime          # UTC, ISO 8601
    pdf_sha256: str                 # idempotency key
    issue: GazetteIssue
    notices: list[Notice]
    corrigenda: list[Corrigendum]
    document_confidence: DocumentConfidence
    layout_info: LayoutInfo
    warnings: list[Warning]         # never raised exceptions; structured notes
    cost: Cost | None = None        # populated only when LLM stages ran
```

```python
class GazetteIssue(BaseModel):
    gazette_issue_id: str           # canonical key from section 2
    volume: str | None              # Roman numeral as printed
    issue_no: int | None
    publication_date: date | None
    supplement_no: int | None = None
    masthead_text: str              # raw lines, kept for audit
    parse_confidence: float         # 0.0-1.0; <0.5 means fallback id in use
```

```python
class Notice(BaseModel):
    notice_id: str                  # f"{gazette_issue_id}:{notice_no}"
    gazette_issue_id: str           # FK back to Envelope.issue
    gazette_notice_no: str | None   # may be None for unrecoverable blocks
    gazette_notice_header: str | None
    title_lines: list[str]
    gazette_notice_full_text: str
    body_segments: list[BodySegment]
    derived_table: DerivedTable | None = None
    other_attributes: dict[str, Any]    # char_span_start_line, etc.
    provenance: Provenance
    confidence_scores: ConfidenceScores
    confidence_reasons: list[str]
    content_sha256: str             # SHA-256 of normalized full_text;
                                    # the v1-vs-v2 alignment payload key
```

`Notice` is the typed wrapper around the dict shape that `split_gazette_notices`
already builds (around lines 413-505 in the notebook). The new fields are
`notice_id`, `gazette_issue_id`, and `content_sha256`; everything else is
exactly the keys the function emits today.

**Note on `body_segments` extensibility.** The 1.0 schema only defines
`"text"` and `"blank"` segment types. Richer detection (tables, signatures,
citations, addresses) lands in 2.x (see roadmap M5). Adding new segment types
is a **MINOR** schema bump — old consumers see the same shape, just with more
variety in the `type` field. The `derived_table` field and `table` confidence
score already exist in 1.0 as optional/nullable to accommodate this future work.

```python
class Corrigendum(BaseModel):
    scope: Literal[                 # required by schema design analysis 01
        "issue_level",              # an issue-wide CORRIGENDA section
        "notice_is_corrigendum",    # this notice corrects another
        "notice_references_other",  # mentions a corrigendum elsewhere
    ]
    target_notice_no: str | None    # cited "Gazette Notice No. X of YYYY"
    target_year: int | None
    amendment: str | None           # extracted "to read" replacement text
    raw_text: str
    provenance: Provenance
```

```python
class ConfidenceScores(BaseModel):
    notice_number: float            # 0.0-1.0, all components
    structure: float
    spatial: float
    boundary: float
    table: float | None = None      # present only if derived_table exists
    composite: float                # weighted aggregate, see notebook
                                    # composite_confidence around line 910
```

```python
class Provenance(BaseModel):
    header_match: Literal["strict", "recovered", "inferred", "none"]
    line_span: tuple[int, int]      # [start, end) in spatial plain text
    raw_header_line: str | None = None
    stitched_from: list[str] = []   # previous notice ids merged in
    ocr_quality: float | None = None  # set when OCR caps confidence
```

```python
class DocumentConfidence(BaseModel):
    layout: float                   # from reorder_by_spatial_position_*
    ocr_quality: float              # from _estimate_ocr_quality
    notice_split: float             # 1 - low_band_share
    composite: float                # weighted: 0.6*notice + 0.2*layout + 0.2*ocr
    counts: dict[Literal["high", "medium", "low"], int]
    mean_composite: float
    min_composite: float
    n_notices: int
    ocr_reasons: list[str] = []
```

```python
class LayoutInfo(BaseModel):
    layout_confidence: float        # whole-document
    pages: list[PageLayout]         # per-page band breakdown
    # PageLayout shape mirrors compute_page_layout_confidence output;
    # kept as dict[str, Any] in v1 if we don't want to lock it yet.
```

`Warning` and `Cost` are deliberately lightweight:

```python
class Warning(BaseModel):
    kind: str                       # dotted, e.g. "masthead.parse_failed"
    message: str
    where: dict[str, Any] | None = None   # page, line_span, notice_id, ...

class Cost(BaseModel):
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    usd_estimate: float | None = None
```

---

## 4. Key strategy — Option A vs Option B

Both options keep `(gazette_issue_id, notice_no)` as the **business** key from
[schema design analysis 01](../analysis/schema%20design%20analysis%2001.md). They differ in
what the **Notice model** carries as its primary identifier.

**Option A — composite natural key only.**

```python
class Notice(BaseModel):
    gazette_issue_id: str
    gazette_notice_no: str          # required, never None for keyed notices
    # ... rest of fields from section 3 ...
```

- Pros: no extra field; the key is exactly the citation a lawyer would write;
  any consumer can reconstruct it from two columns.
- Cons: the `notice_no` is a string (because of forms like "31A"); composite
  FKs are awkward in most ORMs; rows with `notice_no = None` (orphan blocks
  from broken extractions) cannot be keyed at all and must be excluded or
  given a sentinel.

**Option B — surrogate `notice_id` plus unique constraint (recommended).**

```python
class Notice(BaseModel):
    notice_id: str                  # f"{gazette_issue_id}:{notice_no}"
                                    # or f"{gazette_issue_id}:_orphan_{i}"
    gazette_issue_id: str
    gazette_notice_no: str | None
    # ... rest ...
```

- Pros: single string FK; unrecoverable blocks still get a stable id (so
  warnings can point at them); same id format works for in-memory dicts and
  database rows; the unique constraint on `(gazette_issue_id, notice_no)`
  still enforces the domain rule for non-null cases.
- Cons: one extra field whose value is mechanically derivable; care needed so
  that `_orphan_{i}` ids stay stable across re-runs (use the line span index,
  not the list position).

**Recommendation: Option B.** Keeps the FK story simple, supports orphan
blocks, and matches the `notice_id` field in the section 3 sketches. If
implementer chooses Option A instead, drop `notice_id` from `Notice` and
have consumers build the composite key themselves; the rest of this contract
is unaffected.

---

## 5. Public API sketch

Pure parsing is separated from disk I/O. `parse_*` returns an `Envelope` and
touches nothing on disk; `write_envelope` is the only function that does.

```python
def parse_file(path: Path | str, config: GazetteConfig | None = None) -> Envelope: ...

def parse_bytes(
    data: bytes,
    *,
    filename: str | None = None,    # used only for warnings/provenance
    config: GazetteConfig | None = None,
) -> Envelope: ...

def write_envelope(
    env: Envelope,
    out_dir: Path,
    bundles: Bundles,               # which artifacts to materialize
) -> dict[str, Path]:               # returns {bundle_name: written_path}
    ...
```

```python
class LLMPolicy(BaseModel):
    mode: Literal["disabled", "optional", "required"] = "disabled"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    stages: dict[str, bool] = {}    # per-stage overrides, e.g.
                                    # {"validate_notices": True,
                                    #  "repair_tables": False}
    cache_dir: Path | None = None   # mirrors notebook .llm_cache behavior

class RuntimeOptions(BaseModel):
    deterministic: bool = False     # frozen seeds, no wallclock fields
    timeout_seconds: float | None = None
    include_full_docling_dict: bool = False

class Bundles(BaseModel):
    notices: bool = True            # parsed Notice list; cheapest, default on
    corrigenda: bool = True         # Corrigendum list
    document_index: bool = False    # one-row-per-PDF summary for catalog use
    spatial_markdown: bool = False  # the highlighted spatial .md export
    full_text: bool = False         # spatial plain text .txt
    tables: bool = False            # derived_table entries split out
    debug_trace: bool = False       # confidence reasons + per-band layout
    images: bool = False            # page thumbnails / notice crops

class GazetteConfig(BaseModel):
    llm: LLMPolicy = LLMPolicy()
    runtime: RuntimeOptions = RuntimeOptions()
    bundles: Bundles = Bundles()    # only consumed by write_envelope;
                                    # parse_* always populates the full Envelope
```

Bundle write semantics (one line each):

- `notices` — `{stem}_notices.json`, list of `Notice`s as plain JSON.
- `corrigenda` — `{stem}_corrigenda.json`.
- `document_index` — `{stem}_index.json`, flat record with issue id,
  pdf_sha256, counts, document_confidence; ready for catalog ingest.
- `spatial_markdown` — `{stem}_spatial_markdown.md`, current notebook output.
- `full_text` — `{stem}_spatial.txt`, current notebook output.
- `tables` — `{stem}_tables.json`, all `derived_table`s with notice ids.
- `debug_trace` — `{stem}_trace.json`, confidence reasons, layout bands,
  warnings — everything needed to debug a low-confidence run.
- `images` — `{stem}_images/` with page thumbnails and notice bbox crops.

Note: parsing always builds the full `Envelope` once; `Bundles` only controls
which **files** `write_envelope` materializes. This is the projection
mechanism for ideation prompt section D — selective serialization, no
duplicated heavy work.

---

## 6. Three worked config examples

**Minimal offline.** Library use, no disk writes, no network.

```python
config = GazetteConfig(
    llm=LLMPolicy(mode="disabled"),
    bundles=Bundles(notices=True, corrigenda=True),  # other bundles ignored
)
env = parse_file("issue.pdf", config)
# caller consumes env.notices in-process; never calls write_envelope
```

**Production DB ingest.** LLM available but optional, three persisted
artifacts.

```python
config = GazetteConfig(
    llm=LLMPolicy(mode="optional", stages={"validate_notices": True}),
    bundles=Bundles(notices=True, corrigenda=True, document_index=True),
)
env = parse_file(pdf_path, config)
write_envelope(env, out_dir=Path("ingest/"), bundles=config.bundles)
```

**Full audit.** LLM required, every bundle on, deterministic for regression.

```python
config = GazetteConfig(
    llm=LLMPolicy(mode="required", stages={}),  # all stages may use LLM
    runtime=RuntimeOptions(deterministic=True, include_full_docling_dict=True),
    bundles=Bundles(
        notices=True, corrigenda=True, document_index=True,
        spatial_markdown=True, full_text=True, tables=True,
        debug_trace=True, images=True,
    ),
)
env = parse_file(pdf_path, config)
write_envelope(env, out_dir=Path("audit/"), bundles=config.bundles)
```

---

## 7. Versioning rules

`schema_version` follows semver against the `Envelope` JSON shape:

- **MAJOR** — a consumer that ignores unknown fields would still break:
  field removed, type changed, semantic of an existing field changed (e.g.
  `composite` rescaled), enum value removed.
- **MINOR** — additive only: new optional field, new bundle, new enum value
  on a field documented as open. Old consumers keep working.
- **PATCH** — no JSON shape change. Bug fix in scoring, regex tweak,
  performance work. Confidence numbers may move; field set does not.

`output_format_version` is an integer that bumps with every MAJOR. Consumers
that pin a major can `assert env.output_format_version == 1` as a cheap guard.

---

## 8. Open questions

Deliberately left to the implementer:

- **Pydantic v1 vs v2.** Sketches above use v2 syntax; v1 still works for the
  same fields with `Config` classes. Pick one at implementation time based on
  the host project's existing dependency.
- **`parse_bytes` and hashing.** When `filename` is `None`, `pdf_sha256` is
  still computed from `data`, but warnings/provenance lose their filename;
  decide whether to require `filename` or accept anonymous bytes.
- **`Cost` granularity.** Aggregate per-envelope (current sketch) or
  per-stage (`dict[str, Cost]`)? Per-stage is more useful for tuning but adds
  shape; defer until we have more than one LLM stage.
- **`LayoutInfo.pages`.** Locked-down `PageLayout` model now, or
  `list[dict[str, Any]]` until layout-confidence shape stabilizes? Lean
  toward `dict` until at least two consumers depend on the fields.
- **Date parsing.** `publication_date: date` is clean but rejects any
  malformed masthead; alternative is `str` plus a parsed
  `publication_date_iso: date | None`. Trade strictness for partial recovery.
- **Warning taxonomy.** Should `Warning.kind` be a `Literal[...]` enum or a
  free dotted string? Literal catches typos but every new warning means a
  MINOR bump.
