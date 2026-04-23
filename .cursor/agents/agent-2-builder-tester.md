# Agent 2: Builder & Tester

**Location:** `.cursor/agents/agent-2-builder-tester.md`

**Purpose:** Implement feature from spec, run tests, update PROGRESS.md, report status.

**If invoked via autoflow:** read `.cursor/agents/agent-0-orchestrator.md` first (especially section 4). The orchestrator will have already resolved any open questions in the spec's section 8; treat those answers as binding. Do not commit — that is Agent 3's job. Everything else in this role doc still applies.

**Trigger:** Human provides: Copy of Section 4 (Implementation Prompt) from Agent 1's spec file; or, in autoflow, the orchestrator dispatches this agent with the spec path and feature ID.

**Input Files to Read:**
1. The spec file referenced in the prompt (e.g., `specs/F11-masthead-parser.md`)
2. `PROGRESS.md` — to find the feature row and update status
3. Files referenced in "Test Cases" section
4. `gazette_docling_pipeline_spatial.ipynb` — to add implementation cells

**Output Actions:**
1. Write implementation code at location specified in spec
2. Run test cases from spec Section 3
3. Run `check_regression()` if applicable
4. Update `PROGRESS.md`: change status from "⬜ Next" → "⬜ In Progress" → "✅ Complete"
5. Generate build report

**Output Report Format:**

```markdown
# Build Report: {FEATURE_ID}

## Implementation
- Location: {file/cell reference}
- Lines changed: {count}

## Test Results
| Test | Status | Notes |
|------|--------|-------|
| T1 | PASS / FAIL | {notes} |
| T2 | PASS / FAIL | {notes} |
| T3 | PASS / FAIL | {notes} |

## Regression Check
Status: PASS / FAIL / SKIP

## Risks / Callouts
- {Any issues found}
- {Workarounds applied}

## PROGRESS.md Updated
- Status: {new status}
- Commit pending: YES (Agent 3 will commit)

## Final Status: {PASS / FAIL}
```

**Success Criteria for Agent 2:**
- [ ] Code implemented at specified location
- [ ] All test cases from spec pass
- [ ] No regressions (or regression failure documented)
- [ ] PROGRESS.md updated with status and any risk notes
- [ ] Build report generated

**Human Checkpoint:**
Review build report. If final status is PASS, proceed to Agent 3 for commit. If FAIL or concerns exist, ask Agent 2 to fix: "Fix {FEATURE_ID}: [specific issue]" or escalate to Agent 3 with concerns noted.
