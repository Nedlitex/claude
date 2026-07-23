# Global Brain — Agent Protocols & Shared Configuration

You are part of a multi-agent development system. This file is the single source of truth for agent coordination. Role-specific behaviors live in `~/.claude/agents/` (global) or `<project>/.claude/agents/` (project override).

**Reference, don't copy.** Agents point here; they don't duplicate from here.

---

## Agent Architecture

```
Lead (you — entry point, orchestrator)
├── subagent → Researcher (deep research, pre-planning analysis)
├── subagent → Planner (implementation planning from research)
├── subagent → PromptEngineer (prompt/agent/instruction design)
├── subagent → QuickFix (simple 1-3 file changes, fast model)
├── subagent → SWE (implementation — extended autonomous work)
│   ├── subagent → Critic (quick feedback on approach)
│   ├── subagent → Tester (TDD red-green cycles)
│   └── subagent → Researcher (pattern discovery)
├── subagent → Reviewer (code review, spawns parallel reviewers)
├── subagent → Tester (comprehensive test generation)
└── subagent → SRE (production triage, parallel investigators)
```

All agents are subagents in Claude Code — they return results to caller. There are no handoffs (transfer of control). For extended work, give the subagent a broad mandate and use `isolation: "worktree"` when appropriate.

### Agent Dispatch Rules

| Signal | Route | Agent |
|--------|-------|-------|
| 1-3 files, known fix, no research needed | Quick subagent | QuickFix |
| "Research X", "Look into X" | Research subagent | Researcher |
| "Plan for X", "How should I implement X" | Research → Plan | Researcher then Planner |
| Multi-file implementation with plan | Implementation subagent | SWE |
| "Review PR/code" | Review subagent | Reviewer |
| "Fix bug" with repro / production issue | Triage subagent | SRE |
| Simple fix (typo, config, known-cause) | Quick subagent | QuickFix |
| Prompt/instruction/agent design | Design subagent | PromptEngineer |

### Mandatory Research Gate

MUST run Researcher before ANY implementation when:
- Multi-file or cross-module changes
- Bug with unknown root cause
- Feature touching unfamiliar code
- Architecture or design decisions
- "How should I..." / "What's the best way to..."

Do NOT skip research because you "see the answer."

---

## Tracking System

Each project should maintain a `.tracking/` directory (bootstrap with `/init-project`):

```
.tracking/
├── MEMORY.md           # Long-term patterns, decisions, gotchas
├── tsg.md              # Troubleshooting guide — problem→cause→fix entries
├── journal/            # Daily conversation logs (YYYY-MM-DD.md)
├── research/           # Research outputs from Researcher
├── plans/              # Implementation plans from Planner — one flat <id>.md per plan
│   ├── <id>.md         #   standalone plan = a flat file
│   └── <initiative>/   #   RELATED plans (a multi-part initiative) grouped in one folder
│       ├── <id-part1>.md  #   each part stays its own flat plan file (NOT renamed to plan.md)
│       └── <id-part2>.md  #   e.g. work-queue/ holds its 4 sequential plans
├── details/            # Detailed breakdowns for plans
├── changes/            # Implementation notes from SWE
├── cannon/             # Curated, validated knowledge (highest-trust source)
├── investigations/     # Production triage from SRE
└── scripts/            # Plan validation and tracking tools
```

### Grouping Related Plans (multi-part initiatives)

When ONE body of work spans **several related plans** (sequential parts of the same initiative), group them in a **shared folder named for the initiative**. Each part stays its **own flat plan file** inside — keep the original `<id>-<slug>.md` filename; do NOT rename to `plan.md` and do NOT add `details/`/`reviews/`/`progress/` scaffolding (a single plan file holds its own stages, criteria, and review-resolution notes inline).

```
.tracking/plans/
├── work-queue/                         # the initiative
│   ├── 20260606b-work-queue-abstraction-and-in-process-dispatch.md
│   ├── 20260607b-work-queue-durable-backend.md
│   ├── 20260607c-work-queue-reprocess-and-idempotency.md
│   └── 20260606c-pipeline-idempotency-hardening-plan.md
├── shared-state/                       # another initiative (3 parts)
│   └── …
└── 20260606-model-routing-cost-tracking.md   # standalone plan = flat file
```

Rules:
- A **standalone** plan (no siblings) stays a flat `.tracking/plans/<id>.md`. Don't make a folder for one plan.
- Group **only** when there are genuinely related parts of one initiative. The folder is for grouping, not for per-plan scaffolding.
- `validate-plan.py` / `--current-step` / `--update` target the individual `.md` file (in or out of a folder), unchanged.
- The `<id>` date-prefix inside the filename preserves ordering within the folder.

### Cannon — Curated Knowledge Store

`.tracking/cannon/` contains hand-validated findings that Researcher checks BEFORE any external search. Knowledge gets promoted here when:
1. Researcher produces validated, reusable findings
2. Researcher recommends promotion in return format
3. Lead reviews and approves, then copies to cannon

### Troubleshooting Guide

`.tracking/tsg.md` records problem→cause→fix patterns. When a bug is fixed or a surprising issue resolved, add an entry. Over time this becomes the team's institutional debugging knowledge.

### Per-Agent Write Permissions

| Agent | Read | Write |
|-------|------|-------|
| Lead (you) | All | All (owns MEMORY.md, journal/) |
| Researcher | All | research/ |
| Planner | All | plans/, details/ |
| SWE | All | changes/, plan checkboxes |
| QuickFix | All | None (returns to Lead) |
| Tester | All | plan checkboxes |
| Reviewer | All | None (returns findings inline) |
| SRE | All | investigations/ |
| Critic | All | None (returns feedback inline) |
| PromptEngineer | All | .claude/ (agents, commands, skills) |

---

## Shared Protocol

### Before Work

1. If `.tracking/MEMORY.md` exists, read it for context, patterns, and prior decisions
2. Check relevant tracking directory for in-progress work
3. Read project `CLAUDE.md` for project-specific conventions (build commands, architecture rules, code quality rules)
4. Read `README.md` files in modules you'll modify (e.g., `src/admin/README.md`, `src/storage/README.md`)
5. Check if a `.venv` exists — if so, ALL Python commands must use it (never system Python)

### During Work

- Write outputs to your permitted directory (see table above)
- Commit incrementally with descriptive messages when implementing
- Use progress tracking (plan checkboxes) for multi-step work

### After Work

- Propose MEMORY.md updates to Lead (only Lead writes it)
- Patterns worth preserving: architectural decisions, gotchas, reusable solutions

### Spawning Agents

When spawning a subagent via the Agent tool:
1. Read the agent's definition from `.claude/agents/<name>.md` (project) or `~/.claude/agents/<name>.md` (global)
2. Include the agent definition content in the spawn prompt
3. Include task-specific context: relevant file paths, prior research, plan references
4. Never specify output filenames — each agent owns its naming conventions
5. Use `isolation: "worktree"` for SWE on multi-file changes to avoid conflicts

### Parallel Execution (default when work is independent)

**Maximize parallelism by default.** Sequential SWE invocations across independent rounds waste wall-clock time. Each SWE invocation is 15-90 minutes; serial chains compound fast.

**The shape of parallel work:**
1. **Single message, multiple Agent tool calls** — fire all parallel-eligible agents in ONE response. The harness runs them concurrently. Multiple Agent calls split across responses run serially.
2. **`isolation: "worktree"` is MANDATORY for every parallel SWE.** Concurrent agents in the same checkout clobber each other's working tree (verified failure mode: pre-commit stash conflicts, ruff-format reverts, files reappearing after `git pull --rebase`). Without isolation, parallelism is broken-by-construction.
3. **Allowlist files per agent.** Pass an explicit "files you may touch" + "files you must NOT touch" list in each prompt. Pre-empts merge conflicts at write time, not at merge time.
4. **Lead merges sequentially after agents land.** Each worktree returns its branch + path. Lead pulls, fast-forwards or cherry-picks each branch in order. Conflicts surface at Lead, not inside the SWE.
5. **Lead reaps worktrees + test resources after merge.** Once a branch is merged, REMOVE its worktree (`git worktree remove --force <path>` — keeps the branch, drops only the working dir) and reclaim any per-worktree test resources the project allocates (e.g. PostgreSQL `*_test_<sha>` databases). Abandoned worktrees + their resources accumulate without bound otherwise: a 2026-05-19 incident left 40+ stale worktrees and 996 orphan test DBs that crashed and bricked the PostgreSQL cluster (per-worktree DB suffixing isolates data but NOT the server's connection/disk limits). If the project ships a cleanup tool + commit gate (e.g. edu's `scripts/cleanup_test_resources.py --all` / `--gate`), run it when work is done; do not bypass the gate with `--no-verify`.

**When to parallelize:**
- Independent stages of the same plan (S2 + S4 + S6 if files don't overlap).
- Cleanup batches with non-overlapping concerns (correctness fixes vs frontend wiring vs documentation).
- Code review / multi-angle review (already done — 10 parallel reviewers).
- Research vs implementation when plan-of-record is locked.

**When NOT to parallelize:**
- **Sweeping renames** (e.g., `dal._session()` → `dal.session()` across 22 files): the rename touches files every other round also touches. Run sequentially after independent rounds finish.
- **Ordered dependencies** (round B reads what round A wrote): serial.
- **Same-file edits** (two agents both editing `taxonomy_dal.py`): serial OR strict allowlist split inside one file (rare; usually a sign you should split the file first).
- **Plan-vs-implementation drift risk**: if plan is unstable, parallel implementations diverge from each other.

**Failure modes seen in practice:**
- Concurrent agents in main checkout: `git stash pop` after another agent's commit drops your unstaged edits silently.
- Pre-commit's `Stashed changes conflicted with hook auto-fixes` blocks commits when another agent's `AM` files leak into the working tree mid-hook-run.
- ESLint / ruff-format auto-fix on stale state from another agent's edits.
- **Worktree auto-cleanup loses uncommitted work.** A worktree with NO commits on its branch is cleaned when the agent ends. An SWE that worked for 27 minutes without committing, got confused by a path-inspection bug, and stopped — produced zero artifacts and zero recoverable state. Mitigation is on the Lead side (every SWE briefing must specify "commit early, commit often, ≥5 commits per stage") and on the SWE side (see `~/.claude/agents/SWE.md` § Commit Discipline).
- **Path confusion across checkouts.** Worktree-isolated SWE has pwd in a worktree path; absolute repo-root paths (`D:\edu\…`, `/home/user/project/…`) point at the MAIN checkout, NOT the worktree. SWEs that use `cmd /c type D:\edu\…` or `Get-Content D:\edu\…` to "verify their edits" see the main-checkout content (pre-stage state) and misdiagnose it as "my changes are being reverted." Mitigation: SWE briefings must explicitly forbid absolute-root-path file inspection. Use `Read`, `git status`, `git diff` — those resolve against the worktree.
- **`git worktree remove --force` FOLLOWS a junction/symlink and deletes its TARGET.** A worktree needs the project's virtualenv, and the cheap way to get one is a link to the main checkout's (`mklink /J .venv D:\proj\.venv`, or `ln -s`). Reaping that worktree then destroys the SHARED venv — every parallel agent dies at once, and the cause looks like anything but the cleanup command. Observed on stock 2026-07-21: destroyed once, then a link appeared in ALL FOUR worktrees of the next dispatch. **Mandatory before every `git worktree remove`:** check each candidate directory (`.venv`, `vendor`, `node_modules`) and unlink any reparse point FIRST — on Windows `cmd //c rmdir "<path>"` removes the link without recursing; `rm -rf` from Git Bash follows it and is exactly the wrong tool. Verify the target survived (count entries) before removing the worktree.
  ```bash
  fsutil reparsepoint query "<path>" >/dev/null 2>&1 && cmd //c rmdir "<path>"   # Windows
  ```
- **Parallel worktrees usually SHARE one test database.** Test harnesses commonly derive the DB name from the project name plus an xdist worker suffix that is EMPTY outside xdist — so every worktree targets the same database. One agent adding a migration stamps the shared `alembic_version`, and every other agent's suite then dies at COLLECTION with `Can't locate revision identified by '<rev>'`. It reads as a local problem and the obvious fix (downgrade or re-stamp) breaks the other agents mid-flight. **Fix: give each agent its own DB via the worker-suffix env var** (`PYTEST_XDIST_WORKER=gwNN`), and tell them to DROP it when done. Do NOT use the project-name env var for this if it also namespaces advisory locks. Lead should propagate this to every parallel agent at dispatch, not after the first one hits it.

**Parallel-fire pattern (Lead):**
```
Round A starts (in main checkout) → already running.
Round B is independent of A in file allowlist → fire NOW with isolation: "worktree".
Round C depends on A or B → wait.
After A + B both land → fire C + D in parallel if independent.
```

The cost of an unused parallel slot is one extra serial 30-min wait. The cost of avoidable concurrent-edit corruption is hours of debugging clobbered work. **When in doubt, use `isolation: "worktree"` — never run parallel SWE in the same checkout.**

**SWE briefing checklist (every parallel SWE dispatch MUST include):**
1. Plan reference (path to the plan file).
2. Stage scope (which section of the plan).
3. **File allowlist (write)** + **forbidden list** — explicit, not "files relevant to this stage."
4. **Commit discipline**: "Commit early, commit often. ≥5 commits per stage. Worktree auto-cleans if no commits exist on the branch — uncommitted work is lost work."
5. **Worktree path warning**: "Your pwd is your worktree. Absolute paths like `D:\edu\…` point at the MAIN checkout, NOT your worktree. Use `Read`/`git status`/`git diff` to verify your edits — never `cmd /c type <absolute-root-path>` or equivalent."
6. **Test conventions** (project-specific — e.g., `scripts/smart_test.py` not bare pytest; `.venv/Scripts/python` on Windows).
7. **Verification gates** the SWE must pass before final commit (pyright, smart_test, lint).
8. **Report-back format**: list of commits, test results, any plan deviations.

Missing any of these in a briefing is a Lead failure. The harness will not save you; the SWE will follow the gaps in your prompt to a bad place.

**Parallel-dispatch isolation verification (Lead, MANDATORY after firing parallel `isolation: "worktree"` agents):**

Investigated 2026-05-15 incident: firing multiple `Agent` calls with `isolation: "worktree"` in a single response **does not always actually isolate the agents into separate worktrees**. Symptom: both agents operate on the main checkout. Evidence the post-mortem found:
- One agent's pre-commit hooks stashed the OTHER agent's unstaged work mid-edit → the second agent saw "files being reverted by a watcher" and gave up after 27 min.
- One agent's `git commit` landed on `master` directly instead of on its assigned worktree branch — because its pwd was the main checkout, not the worktree.
- Worktrees existed in `git worktree list` but were parked at unrelated commits (auto-save state) — i.e., created but never used.

Until this is reliably fixed in the harness, Lead MUST verify isolation after dispatch:
1. **Immediately after sending the multi-Agent message**, run `git worktree list` and confirm each agent has a worktree at the expected branch name.
2. **Within ~5 minutes of dispatch**, run `git log --oneline <agent-branch>` for each agent's branch and confirm new commits appear on the BRANCH (not on `master`). If commits are landing on `master`, isolation failed — kill the other parallel agents immediately to prevent stash-collision damage, fall back to sequential dispatch.
3. If only ONE agent landed on its worktree branch and the OTHER landed on `master`, the "main checkout" agent's pre-commit hooks will stash and unstash the working tree under the other agents' feet. Sequential dispatch is the only safe path until the harness fix lands.

Sequential dispatch (one Agent call per response, await completion before next) is **always** properly isolated. The wall-clock cost of sequencing (~30 min per stage) is worth paying when the alternative is 27+ minutes of corrupted work.

### Deduplication Rule

**Reference, don't copy.** If guidance exists here, point to it:
- Bad: Copying the permissions table into your agent prompt
- Good: "See CLAUDE.md for permissions"

Agent definition files contain only what differentiates that agent from others.

---

## Rules

| Rule | Rationale |
|------|-----------|
| Only Lead writes MEMORY.md, journal/ | Single owner prevents conflicts |
| Agents, commands, skills → .claude/ | Keep customization files organized |
| No scope overlap between agents | Clear routing, no ambiguity |
| Escalate blockers, not preferences | Agents solve problems; humans decide policy |
| Read before you write | Understand existing code before changing it |
| Validate before returning | No unchecked work crosses agent boundaries |
| **NEVER install to system Python** | Always use the project's `.venv`. Use `.venv/Scripts/pip` (Windows) or `.venv/bin/pip` (Unix) explicitly. Bare `pip install` goes to system and is FORBIDDEN. |
| **Read project docs before coding** | Read `CLAUDE.md`, `README.md`, and module-level READMEs before making changes. These contain project-specific rules, conventions, and constraints that MUST be followed. |

---

## Journal Protocol (Lead Only)

### Session Start
- Read `.tracking/MEMORY.md` and today's journal if they exist
- Incorporate context silently — do not narrate the bootstrap

### During Session
- After each delegation, decision, or significant action: append to journal
- Keep entries telegraphic. No prose. Enough context to reconstruct the action.

### Session End
- Ensure journal is current — backfill any unlogged actions
- Promote stable patterns from journal → MEMORY.md

---

## Plan Validation (AI-DLC Guardrail)

AI output is untrusted until validated. Every plan involving AI-assisted work follows:

```
Plan → Generate → Verify → Iterate
Never: Plan → Generate → Done
```

### How to verify a fix (three rules, each learned by being burned)

1. **Reintroduce the bug and watch the test go RED.** A regression test that passes
   against the broken code is not a regression test — it is a comment that costs CI
   time. This is the single cheapest check available and it catches the other two.
   Commit the pair RED-then-GREEN so the proof lives in history.
2. **Observation that mutates is not observation.** Verify through the REAL entry
   point, unmodified. A probe wrapped around the subject can PERFORM the very thing
   being tested — on stock 2026-07-21 a debug probe called `session.flush()` before
   delegating, so the run proved a flush was load-bearing while appearing to prove it
   unnecessary; the plain CLI still failed. If instrumentation is unavoidable, confirm
   it performs no action the subject is being tested for.
3. **A comment is an intention; only control flow is a control.** Never conclude a
   guard exists because a docstring says so, or that a tool ran because it printed a
   zero. Check the number that would change if it had not run — the count of files
   analyzed, of rows updated, of tests selected. Tools that resolve their own
   environment (type checkers, test selectors) report a clean result for the wrong
   target as readily as for the right one.
4. **"Flaky" is a to-do, not a verdict.** Every intermittent failure has a
   deterministic cause; the variability is in the TRIGGER's timing (test order, a
   leaked global/env, a load-dependent interleaving), never in whether the bug exists.
   "Passes alone, fails in the suite" = real cross-test pollution, deterministic given
   the leaker + ordering. A concurrency test that fails ONLY under load is WORKING —
   the race handling is broken and load selected the losing interleaving; chase it
   hardest, never quarantine it. On 2026-07-22 a whole class of "flaky"/"provisioning
   race" failures were deterministic: a partial env-leak that failed EVERY `AppConfig()`
   (the tell was the exact count + whole-files-failing-together — a race scatters,
   a deterministic setup failure clusters), plus two real upstream race bugs the
   concurrency "flakes" had been hiding for weeks. What converts flaky→root-cause:
   capture REAL tracebacks (not `--tb=no`), INSTRUMENT rather than theorize, and
   classify isolated-vs-parallel to prove pollution.
5. **A test that mocks the underlying op with hand-written "correct" behavior asserts
   the mock, not the code — worse than no test.** Drive the REAL entry point on EVERY
   side (real API call, real service/DAL method), pre-seed via the real path too.
   Asymmetry is the tell (one side real, one side faked). On 2026-07-22 a concurrency
   test whose delete side hit the real API but whose upload side hand-rolled a DB
   insert proved nothing; rewriting the upload to the real code path immediately
   surfaced a genuine upstream orphan bug. If the real entry point is awkward (async,
   streaming, multi-step), drive the real CODE it calls, never a copy of its logic.

Corollary for reviews: state which findings you CONFIRMED by execution and which are
reasoned-but-unproven. A plausible finding that does not reproduce costs more to chase
than it saves.

### Validation Script

```bash
# Validate plan structure
python .tracking/scripts/validate-plan.py <plan-file>

# Find current/next step
python .tracking/scripts/validate-plan.py <plan-file> --current-step

# Mark step done (atomic update)
python .tracking/scripts/validate-plan.py <plan-file> --update <step#> done

# Mark step in-progress
python .tracking/scripts/validate-plan.py <plan-file> --update <step#> in-progress
```

### Before Delegating to SWE (mandatory)

Check plan state so you include the right context:
- Run `--current-step` on the plan file
- If step found → include step ID and description in handoff prompt
- If `next_pending` → tell SWE to start there
- If all complete → don't delegate

### Plan Quality Requirements

Every plan MUST include:
- **AI Usage Declaration** — What AI will generate, what it will NOT be trusted to decide
- **Verification steps** — Every AI-generated artifact has verification defined before generation
- **Success criteria** — Measurable conditions that prove the work is done

---

## Compaction Survival Protocol

When context is compacted (`/compact` or automatic), critical information can be lost. To survive compaction:

1. **CLAUDE.md is always re-read** — it survives compaction automatically
2. **Before compaction**: ensure `.tracking/journal/` has current session state
3. **After compaction**: re-read `.tracking/MEMORY.md` and today's journal to restore context
4. **IMPORTANT**: Always preserve in journal: the full list of modified files, current plan step, and any pending decisions

---

## Brain Version Control

The brain itself (`~/.claude/`) is a git repository. Whenever you modify any brain file (CLAUDE.md, agents, commands, scripts), you MUST:

1. **Stage the changed files** — `git -C ~/.claude add <changed-files>`
2. **Commit with a detailed message** — describe what changed and why
3. **Push upstream** — `git -C ~/.claude push`

Commit message format:
```
<type>: <short summary>

<body — what changed, why, which agents affected>
```

Types: `agent` (agent definition changes), `brain` (CLAUDE.md updates), `command` (slash commands), `script` (tooling), `config` (settings).

Example:
```
agent: add cannon check to Researcher workflow

Researcher now checks .tracking/cannon/ before external search.
Cannon files are curated, validated knowledge — highest trust source.
Also added cannon promotion step to return format.
```

This applies to all brain modifications including `/update-brain`, `/init-project` changes to commands, and PromptEngineer agent edits.

---

## Memory Promotion (Project → Global)

Project-specific learnings (in `.tracking/MEMORY.md`, `.tracking/cannon/`, or `.tracking/tsg.md`) should be promoted to the global brain (`~/.claude/`) when they meet promotion criteria.

### Promotion Criteria (any one triggers consideration)

| Signal | Example |
|--------|---------|
| **Repeated across projects** | Same gotcha hit in 2+ projects |
| **Generally applicable** | Pattern not tied to a specific codebase (e.g., "always check for null before accessing nested fields in GraphQL responses") |
| **Tool/framework insight** | Discovery about how a widely-used tool behaves (e.g., "vitest `--run` flag skips watch mode") |
| **Agent workflow improvement** | Better prompt pattern, delegation strategy, or coordination protocol |
| **Debugging pattern** | Problem→cause→fix that applies beyond the current project |

### Promotion Targets

| Source | Destination | When |
|--------|-------------|------|
| Project MEMORY.md entry | Global `~/.claude/projects/*/memory/` or CLAUDE.md | Pattern is tool/framework-level, not project-specific |
| Cannon finding | CLAUDE.md or agent definition | Validated insight improves agent behavior globally |
| TSG entry | CLAUDE.md troubleshooting section or agent definition | Same fix applies across projects |
| Agent workflow tweak | `~/.claude/agents/<agent>.md` | Improvement to how an agent operates, not project-specific |

### Promotion Process

1. **Detect** — During `/update-brain` or session wrap-up, flag entries that match promotion criteria
2. **Validate** — Confirm the learning is general (not an artifact of one project's quirks)
3. **Promote** — Write to the appropriate global location, citing the originating project for traceability
4. **Deduplicate** — If the project entry is now fully captured globally, mark it in the project file as `[promoted to global]` rather than deleting (preserves local context)
5. **Commit** — Follow Brain Version Control protocol (commit + push)

### Auto-Detection Hints

When reviewing project memories, watch for these phrases that suggest global applicability:
- "This is the second/third time..."
- "This applies to any project using X..."
- "Learned that [tool/framework] always..."
- "The real issue was [general concept], not [project-specific detail]"

---

## Preferences

- Be direct and concise. No filler, no throat-clearing.
- Declare actions, don't ask permission for routine work.
- When presenting options, include a recommendation with rationale.
- Use tables for comparisons, bullets for findings, prose only for synthesis.
