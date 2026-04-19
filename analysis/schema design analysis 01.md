Schema ideation

### **Identity and keys**

- Treat `(gazette_issue, notice_no)` as the **natural business key**: notice numbers repeat across issues; they are only unique **within** an issue.
- Define `gazette_issue` as a **canonical, stable identifier** (normalized string or structured volume + issue number + optional supplement), not raw filenames or OCR strings that drift.
- Decide explicitly: **composite primary key** vs **surrogate** `id` + **unique constraint** on `(gazette_issue_id, notice_no)`. Surrogate keys simplify FKs and migrations; the unique constraint still enforces domain rules.

### **Gazette (issue) vs notice (fact)**

- **Issue-level fields** (publication date from masthead/first page, corrigenda-at-issue-level, source PDF hash/path) belong on a `gazettes` (or `gazette_issues`) entity; **notices** reference that entity by FK to avoid contradictory dates across rows for the same PDF.
- If you start with one flat table, still add a `gazette_issue_id` (or equivalent) so you can normalize later without changing the logical key.

### **Payload and versioning**

- Store the structured extract as **JSON/JSONB** and/or **blob + URI**; always pair with `schema_version` or `pipeline_version` (and optionally `extracted_at`) so old rows stay interpretable after parser changes.
- Preserve **lineage inside the JSON or in columns**: `line_span`, `source_file`, `page` range if available—whatever you need to audit “this row came from this place in this file.”

### **Corrigenda**

- Specify **scope**: issue contains corrigenda vs **this notice is** a corrigendum vs **references** another notice. Do not imply notice-level precision unless extraction actually supports it; default to **issue-level flag** plus optional structured links later.

### **Quality and operations**

- Carry **confidence** (or tiered flags) at notice level if the pipeline emits it, so you can filter or down-rank without deleting rows.
- Include **idempotency** for loads: same PDF re-run should **upsert** the same logical notices, not duplicate rows (natural key or hash-based dedup policy).

### **What to avoid**

- A single global `notice_no` primary key.
- **Display titles** as the only gazette key without normalization.
- Duplicating **issue date** on every notice without a rule for **which** date wins when OCR disagrees (prefer single issue record as source of truth).

---

You can prepend: *“Constraints: Kenya Gazette notices are cited by issue + notice number; our extractor emits per-notice JSON with provenance and confidence.”*