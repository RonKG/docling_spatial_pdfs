# Agent 0: Feature Build Orchestrator (Autoflow)

**Location:** `.cursor/agents/agent-0-orchestrator.md`

**Purpose:** Drive the full 3-agent feature build pipeline (Spec -> Build -> Review) from a single human trigger phrase, with exactly one human pause point between spec generation and build.

**Trigger phrases (case-insensitive, whitespace-tolerant):**
- `kick off FXX`
- `build FXX`

Where `FXX` is any feature ID that appears as a row in `PROGRESS.md` (e.g. `F21`, `F22`, `F30`).

**Not triggered by** phrases like "run agent 2 for FXX", "review FXX", "spec FXX" — those remain manual single-stage invocations using the existing `.cursor/agents/agent-1-*.md`, `agent-2-*.md`, `agent-3-*.md` docs.

---

## 1. Flow overview

```mermaid
flowchart LR
    H[Human: "kick off FXX"] --> A1[Stage A: Agent 1 Spec Creator]
    A1 --> P[HUMAN PAUSE: approve / revise / reject]
    P -->|approve| A2[Stage B: Agent 2 Builder & Tester]
    P -->|revise| A1
    P -->|reject| STOP1[Stop, report]
    A2 -->|PASS| A3[Stage C: Agent 3 Senior Reviewer]
    A2 -->|FAIL| STOP2[Stop, report to human]
    A3 -->|PASS / PASS WITH NOTES| DONE[Commit + update PROGRESS.md + report to human]
    A3 -->|FAIL| STOP3[Stop, do not commit, report to human]
```

One human pause. Three possible early stops (A2 FAIL, A3 FAIL, rejected spec). Otherwise the orchestrator walks all the way to commit.

---

## 2. Stage A — Spec Creation (Agent 1)

The parent agent (the one reading this file) performs Stage A directly or by dispatching a subagent. Subagent preferred if the spec is large; direct otherwise.

### 2.1 Inputs to prepare
Before invoking Agent 1, the orchestrator reads:
- `PROGRESS.md` — extract the `FXX` row (name, simple explanation, core files, status)
- `specs/SOP.md` — Stage 1 discovery list

### 2.2 Dispatch prompt for Agent 1
Give Agent 1 this exact prompt (substituting `FXX` and kebab-name from the `PROGRESS.md` row):

> **Create spec for FXX: `<Feature Name>`**
>
> Follow `.cursor/agents/agent-1-spec-creator.md` end-to-end. Read `PROGRESS.md`, the canonical docs, and every prior `specs/F*-*.md` file for completed features (full list in the Agent 1 role doc). Produce `specs/FXX-<kebab-name>.md` with all 8 sections from `specs/SOP.md` Appendix A filled.
>
> When done, return:
> 1. A one-paragraph summary of the spec (what will be built, where, integration point).
> 2. The exact "Open Questions / Risks" (section 8) list, each with your recommended answer.
> 3. The path to the spec file.

### 2.3 Handoff to the pause
After Agent 1 returns, the orchestrator **does not invoke Agent 2**. Instead it formats the human pause message (see section 3).

---

## 3. The human pause (single approval gate)

Present to the human, in chat, exactly three blocks:

```
## Spec ready for review: FXX

### (a) One-paragraph summary
<copied verbatim from Agent 1's return: what + where + how it plugs in>

### (b) Open questions with recommended answers
Q1: <question> — recommend: <answer>
Q2: <question> — recommend: <answer>
...
(If Agent 1 reported zero open questions, write "None — spec is unambiguous.")

### (c) Decision
Reply with one of:
- `approve`              -> proceed to build with the recommended answers
- `approve: Qn=<value>`  -> proceed with overrides for specific questions
- `revise: <instruction>`-> send spec back to Agent 1 with this change
- `reject`               -> stop, close out FXX
```

### 3.1 Interpreting the reply

| Human reply | Orchestrator action |
|-------------|---------------------|
| `approve` (no overrides) | Proceed to Stage B using recommended answers. If Q1-Qn exist, note answers in the build prompt. |
| `approve: Qn=<value>` (one or more) | First, edit `specs/FXX-<kebab-name>.md` section 8 to record the final answers (replace "recommend: X" with "answer: Y" inline). Then proceed to Stage B. |
| `revise: <instruction>` | Dispatch Agent 1 again with the instruction. When it returns, re-run section 3 (the pause) with the refreshed spec. No Stage B until the human re-approves. |
| `reject` | Stop. Leave the spec file on disk as-is (useful record). Do not edit PROGRESS.md. Report to the human: "FXX build cancelled at spec review." |

### 3.2 What the orchestrator must NOT do at the pause
- Do not auto-approve after a timeout or silence.
- Do not start Agent 2 in parallel "just to save time."
- Do not skip the pause even if Agent 1 reports zero open questions — the human still needs the summary + explicit `approve`.

---

## 4. Stage B — Build & Test (Agent 2)

Invoked only after explicit `approve` (with or without overrides).

### 4.1 Record spec answers (if overrides given)
Before dispatching Agent 2, use `StrReplace` on `specs/FXX-<kebab-name>.md` section 8 to turn each "recommend: …" into "**answer: …**" reflecting the human's final decisions. This makes the spec self-contained for Agent 3 later.

### 4.2 Dispatch Agent 2
Launch via the `Task` tool.

- `subagent_type`: `generalPurpose` (Agent 2's role is not exposed as a direct subagent type yet; the generalPurpose agent is instructed to load the role doc first)
- `run_in_background`: `false` (orchestrator needs the build report to proceed)
- `description`: `Build FXX` (short, user-visible)

Prompt (substitute `FXX` and kebab-name):

> **You are Agent 2: Builder & Tester.** Read `.cursor/agents/agent-2-builder-tester.md` in full, then follow it exactly for this task.
>
> **Implement FXX: `<Feature Name>`**
>
> Spec: `specs/FXX-<kebab-name>.md`
> Location: `<core files from PROGRESS.md>`
>
> Requirements (from the spec's Definition of Done):
> - Match the Interface Contract exactly.
> - Pass every Test Case in section 4 (TC1-TCn).
> - Run `check_regression()` if the feature touches the pipeline; document result.
> - Update `PROGRESS.md`: move FXX status to `✅ Complete`; refresh the `Today` block (Previous=FXX, Current=next `⬜ Next` row); append one row to the Session Log with the date, feature, and a one-paragraph factual summary of what changed.
> - Do **not** commit. Agent 3 commits.
>
> Return the full Build Report in the format from section "Output Report Format" of the Agent 2 role doc, including Final Status (PASS or FAIL).

### 4.3 Branch on Agent 2's final status

| Final Status | Orchestrator action |
|--------------|---------------------|
| `PASS` | Proceed to Stage C. |
| `FAIL` | Stop. Do not invoke Agent 3. Surface Agent 2's full report to the human, highlight the failing test(s) / regression, and ask: "Fix, revise spec, or abandon?" Wait for human reply. |

---

## 5. Stage C — Review & Commit (Agent 3)

Invoked only after Agent 2 returned `PASS`.

### 5.1 Dispatch Agent 3
Launch via the `Task` tool.

- `subagent_type`: `generalPurpose`
- `run_in_background`: `false`
- `description`: `Review FXX`

Prompt:

> **You are Agent 3: Senior Reviewer.** Read `.cursor/agents/agent-3-reviewer.md` in full, then follow it exactly for this task.
>
> **Review FXX: `<Feature Name>`**
>
> - Spec: `specs/FXX-<kebab-name>.md`
> - Build report: (paste Agent 2's report here verbatim)
> - Implementation touched: `<file list from Agent 2's report>`
>
> Run the full review checklist. Verify tests independently (re-run regression if the feature touches the pipeline). If verdict is `PASS` or `PASS WITH NOTES`, stage the changed files, commit with message `FXX: <Feature Name>` (use a heredoc for the message), update the FXX row in `PROGRESS.md` with the commit SHA, and amend or add a second chore commit if the SHA update requires it.
>
> Return the full Review Report in the role doc's format, including Verdict and (if committed) the commit hash(es).

### 5.2 Branch on Agent 3's verdict

| Verdict | Orchestrator action |
|---------|---------------------|
| `PASS` | Report success to human: verdict, commit SHA, any non-blocking recommendations. Done. |
| `PASS WITH NOTES` | Same as PASS, plus surface the notes prominently so the human can decide whether to log follow-up debt in `PROGRESS.md`. |
| `FAIL` | Stop. Do not retry Agent 2 automatically. Surface Agent 3's blocker list and its recommendation ("back to Agent 1" or "back to Agent 2"). Ask the human which path to take. **Default behaviour: stop and report. No auto-loop.** |

---

## 6. Failure and recovery rules (summary)

| Where it fails | What the orchestrator does |
|----------------|---------------------------|
| Agent 1 produces malformed spec (missing sections) | Dispatch Agent 1 again with a specific fix prompt; do not pause human until spec is well-formed. |
| Human rejects spec at pause | Stop. No further action. |
| Human says `revise: ...` | Loop back to Stage A with the instruction. Re-pause when Agent 1 returns. |
| Agent 2 returns FAIL | Stop. Report. Ask human. No auto-retry. |
| Agent 3 returns FAIL | Stop. Report. Ask human. **No auto-retry and no auto-commit.** |
| Tool / subagent error mid-stage | Stop. Report the raw error to the human with the stage name; do not silently continue. |

The guiding rule: **one human pause after spec, plus one human pause on any downstream failure.** Never more, never fewer.

---

## 7. What the orchestrator must preserve

- **PROGRESS.md invariants** (Today block, Work Items table, Session Log order) — exactly as documented in `specs/SOP.md`. Session Log rows stay chronological.
- **Commit hygiene** — commit message format `FXX: <Feature Name>`, body written via heredoc (per the project's established commit style), never `--no-verify`, never force-push.
- **Spec permanence** — once written, `specs/FXX-<kebab-name>.md` is edited only to record final answers to open questions (section 8) or to apply spec typo fixes flagged by Agent 2/3. Structural rewrites require a `revise` round-trip.

---

## 8. Quick reference — prompts to copy

| Stage | Prompt skeleton |
|-------|----------------|
| A (Spec) | See section 2.2 |
| Pause   | See section 3 (three-block format) |
| B (Build) | See section 4.2 |
| C (Review) | See section 5.1 |
