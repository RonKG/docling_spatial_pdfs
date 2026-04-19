# Agent 1: Spec Creator

**Purpose:** Read a feature from PROGRESS.md and create a build-ready specification with embedded implementation prompt.

**Trigger:** Human provides: `FEATURE_ID` (e.g., "F11")

**Input Files to Read:**
1. `PROGRESS.md` — feature row for ID, name, explanation, core files
2. `docs/library-contract-v1.md` — relevant model/API sections
3. `docs/library-roadmap-v1.md` — milestone context
4. `gazette_docling_pipeline_spatial.ipynb` — existing code at "Core files" location
5. Sample outputs in `output/` — for test case sources

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
