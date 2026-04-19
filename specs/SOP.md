# Feature Build SOP — Kenya Gazette Library

**Purpose:** This document defines the standard workflow for building any feature in the Kenya Gazette library. Follow it sequentially. Do not skip steps.

**When to use this:** Before starting any feature from `PROGRESS.md`.

---

## Phase 1: Discovery (Do This First)

### Step 1.1: Read PROGRESS.md
Locate your feature row. Extract:
- Feature ID (e.g., F11)
- Name (e.g., "Masthead parser")
- Simple Explanation (what it does)
- Core files (where it lives)
- Status (should be "⬜ Next" or "⬜ Not started")

**Rule:** Do not start if status is not "⬜ Next". Finish the current "Next" feature first.

### Step 1.2: Read canonical docs
Read these in order. Take notes on constraints that affect your feature.

| Doc | What to look for | Typical relevance |
|-----|------------------|-----------------|
| `docs/library-contract-v1.md` | Model definitions, API patterns, identity rules, error handling rules | Most features touch this |
| `docs/library-roadmap-v1.md` | Milestone context, comparability rules, out-of-scope items | Large features, anything touching public API |
| `docs/data-quality-confidence-scoring.md` | Scoring algorithms, calibration rules | F5-F10, F14-F16 |

### Step 1.3: Read existing implementation
Open the notebook/module from "Core files" in PROGRESS.md. Read the relevant cells/functions. Note:
- What already exists (do not rebuild)
- Where your feature plugs in
- What data structures flow in and out

---

## Phase 2: Generate the Spec (with LLM)

### Step 2.1: Prompt LLM to write the spec
Use this exact prompt format:

> **Build [FEATURE-ID] specs for review to implement [kebab-case-name].md**
>
> Follow `specs/SOP.md` Phase 1 (Discovery) and Phase 2 (Spec Template). Create `specs/[FEATURE-ID]-[kebab-case-name].md` with all 8 sections filled.
>
> Read these files first:
> - `PROGRESS.md` — locate [FEATURE-ID] row
> - `docs/library-contract-v1.md` — relevant sections
> - `docs/library-roadmap-v1.md` — milestone context
> - `gazette_docling_pipeline_spatial.ipynb` — relevant cells from "Core files"
>
> Include 5 test cases with actual PDF sources from `output/`.

### Step 2.2: Human review
Review the generated spec. Check:
- [ ] All 8 template sections present
- [ ] Test cases reference actual files in `output/`
- [ ] Output shapes match contract requirements
- [ ] Pass/fail criteria are objectively measurable
- [ ] Could an implementer code this without asking questions?

**If issues found:** Prompt LLM to revise: "Revise F11 spec: [specific changes needed]"

**If approved:** Proceed to Phase 3.

---

## Phase 3: Implement from Spec

### Step 3.1: Prompt LLM to implement
Use this exact prompt format:

> **Implement spec for [FEATURE-ID] [kebab-case-name].md in the specs folder**
>
> Read and implement the approved spec at `specs/[FEATURE-ID]-[kebab-case-name].md`.
>
> Follow the Definition of Done checklist. Update PROGRESS.md status when complete.

### Step 3.2: Review the build
Before accepting the implementation:
- Run all 5 test cases from the spec
- Verify integration (right fields populated)
- Run `check_regression()` if applicable
- Check PROGRESS.md was updated

---

## Phase 4: Close the Loop

### Step 4.1: Update PROGRESS.md
Change status from "⬜" to "✅ Complete" and add commit hash.

### Step 4.2: Commit
```bash
git add specs/[FEATURE-ID]-[name].md [implementation files] PROGRESS.md
git commit -m "[FEATURE-ID] Implement [feature name]"
git push origin main
```

### Step 4.3: Verify next feature
Read PROGRESS.md. The next "⬜ Next" row is your next task. Return to Phase 1.

---

## Appendix A: Spec Template (for LLM generation)

When generating a spec in Phase 2, the LLM must use this exact template:

```markdown
# [FEATURE-ID] Spec: [Feature Name]

## 1. Goal (one sentence)
What this feature does and why it exists.

## 2. Input/Output Contract

| Aspect | Specification |
|--------|---------------|
| Function name | `function_name_here` |
| Signature | `(param: Type) -> ReturnType` |
| Input source | Where the input comes from |
| Output shape | Exact fields, types, nullability |
| Error handling | "Never raise" / "Return None" / "Log warning" |

## 3. Links to Canonical Docs

| Doc | Section | Why it matters |
|-----|---------|----------------|
| `library-contract-v1.md` | Section X | Relevant model/API |
| `library-roadmap-v1.md` | Milestone Y | Sequencing rules |
| `PROGRESS.md` | [FEATURE-ID] row | Original definition |

## 4. Test Case Matrix

Minimum 5 test cases:

| ID | Scenario | Source | Input | Expected | Why |
|----|----------|--------|-------|----------|-----|
| TC1 | Happy path | `output/XXX.txt` | clean input | full result | Baseline |
| TC2 | Degraded/OCR | `output/YYY.txt` | garbled | partial/None | Graceful |
| TC3 | Edge variant | `output/ZZZ.txt` | unusual | handles it | Robustness |
| TC4 | Weird case | `output/WWW.txt` | odd layout | parses or Nones | Edge |
| TC5 | Boring baseline | `output/BBB.txt` | typical | standard | Regress |

## 5. Integration Point

- **Called by:** Function/class that calls this
- **Calls:** Dependencies this needs
- **Side effects:** Disk, cache, warnings
- **Model wiring:** Envelope/Notice fields populated

## 6. Pass/Fail Criteria

| Check | How to verify |
|-------|---------------|
| Returns correct type | `isinstance(result, ExpectedType)` |
| Handles bad input | TC2-TC4 pass without raising |
| Required fields | Assert no missing keys |
| Idempotency | Same input → same output |
| No regressions | `check_regression()` passes |

## 7. Definition of Done

- [ ] Function implemented at specified location
- [ ] All 5 test cases pass
- [ ] Integration verified (right fields populated)
- [ ] No regressions on canonical PDFs
- [ ] PROGRESS.md updated to "✅ Complete"

## 8. Open Questions / Risks

List any ambiguities needing resolution before build.
```

---

## Appendix B: Quick Reference

### Feature ID patterns
- F1-F10: Phase 0 (complete)
- F11-F14: Phase 1 (identity + boundaries)
- F15-F16: Phase 2 (calibration + regression)
- F17-F19: Phase 3 (package skeleton)
- F20-F22: Phase 4 (API + config)
- F23-F25: Phase 5 (schema + packaging)

### Common doc references
| Feature type | Primary doc | Section |
|--------------|-------------|---------|
| Identity fields | `library-contract-v1.md` | Section 2 |
| Model shapes | `library-contract-v1.md` | Section 3 |
| Public API | `library-contract-v1.md` | Section 5 |
| Scoring | `data-quality-confidence-scoring.md` | All |
| Milestone context | `library-roadmap-v1.md` | Relevant M* block |

### File naming conventions
- Spec: `specs/[FEATURE-ID]-[kebab-case].md`
- Implementation: Wherever "Core files" in PROGRESS.md says
- Tests: Inline in notebook for Phase 0-1, `tests/` for Phase 3+

---

**Last updated:** 2026-04-19
