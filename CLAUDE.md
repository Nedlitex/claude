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
├── plans/              # Implementation plans from Planner
├── details/            # Detailed breakdowns for plans
├── changes/            # Implementation notes from SWE
├── cannon/             # Curated, validated knowledge (highest-trust source)
├── investigations/     # Production triage from SRE
└── scripts/            # Plan validation and tracking tools
```

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
3. Read project CLAUDE.md for project-specific conventions

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

## Preferences

- Be direct and concise. No filler, no throat-clearing.
- Declare actions, don't ask permission for routine work.
- When presenting options, include a recommendation with rationale.
- Use tables for comparisons, bullets for findings, prose only for synthesis.
