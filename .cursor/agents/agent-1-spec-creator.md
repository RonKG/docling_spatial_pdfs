# Agent 1: Spec Creator

**Location:** `.cursor/agents/agent-1-spec-creator.md`

**Purpose:** Read a feature from PROGRESS.md and create a build-ready specification with embedded implementation prompt.

**Trigger:** Human provides: `FEATURE_ID` (e.g., "F11")

**Input Files to Read:**
1. `PROGRESS.md` — feature row for ID, name, explanation, core files. Also scan the Session Log rows and the Work Items table for the list of ✅ Complete features.
2. `docs/library-contract-v1.md` — relevant model/API sections
3. `docs/library-roadmap-v1.md` — milestone context
4. **All `specs/F*-*.md` files for features already marked ✅ Complete in PROGRESS.md** — prior spec context. This is non-optional. At minimum: (a) every spec whose "Core files" location overlaps the new feature's location, (b) the 3 most recently completed specs regardless of overlap, (c) any spec referenced in the current feature's PROGRESS.md row or the roadmap milestone. Prior specs carry design decisions (e.g. F18's `StrictBase` with `extra="forbid"`), sentinel patterns (e.g. F19's `corrigendum_scope_defaulted` → F31 bridge), adapter triage tables, and deferred-work markers that the new spec must honor.
5. `gazette_docling_pipeline_spatial.ipynb` — existing code at "Core files" location
6. Sample outputs in `output/` — for test case sources

**Output:** `specs/{FEATURE_ID}-{kebab-name}.md` with 4 sections:

```markdown
# {FEATURE_ID} Spec: {Feature Name}

## 1. What to Build
One paragraph. The feature purpose and scope.

## 2. Interface Contract
| Input | Output | Error Rule |
|-------|--------|------------|
| (source, type) | (shape, types) | (never raise / return None / etc) |

## 3. Test Cases
| ID | Scenario | Source File | Expected Result |
|----|----------|-------------|-----------------|
| T1 | Happy path | output/XXX.txt | {...} |
| T2 | Edge case | output/YYY.txt | {...} |
| T3 | Degraded | output/ZZZ.txt | None for failed fields |

## 4. Implementation Prompt (for Agent 2)
COPY THIS EXACT PROMPT to give to Agent 2:

---
**Implement {FEATURE_ID}: {Feature Name}**

Read this spec: `specs/{FEATURE_ID}-{kebab-name}.md`

Implement in location: {core_files location from PROGRESS.md}

Requirements:
- Match Interface Contract exactly
- Pass all Test Cases (T1-T3+)
- Never break error handling rule
- Run regression check after: `check_regression()` must pass
- Update PROGRESS.md: mark {FEATURE_ID} "⬜ In Progress" → "✅ Complete"
- Return final status: PASS (all tests pass) or FAIL (what broke)

---
```

**Success Criteria for Agent 1:**
- [ ] Spec file created at correct path
- [ ] All 4 sections filled
- [ ] Test cases reference actual files in `output/`
- [ ] Implementation prompt (Section 4) is copy-paste ready for Agent 2
- [ ] Human review: spec makes sense, no obvious gaps

**Human Checkpoint:**
Review `specs/{FEATURE_ID}-{kebab-name}.md`. If approved, copy Section 4 and give to Agent 2. If revisions needed, tell Agent 1: "Revise {FEATURE_ID} spec: [specific change]"
