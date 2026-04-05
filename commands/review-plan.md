---
name: review-plan
description: "Run 6 parallel reviewers (robustness, cleanness, understandability, testability, efficiency, + angry senior engineer) against a plan file, then aggregate findings."
---

# /review-plan — 6-Angle Architecture Review

Run 6 parallel Reviewer agents against a plan or architecture document, each focused on a different quality angle. Includes an "angry senior engineer" who aggressively rejects anything with security, efficiency, or readability issues. Aggregate findings into a prioritized list of fixes.

## Usage

```
/review-plan <path-to-plan-file>
```

If no path is provided, look for the active plan file in the current plan mode context.

## Execution

### Step 1: Launch 5 reviewers in parallel (single message, multiple Agent tool calls)

Each reviewer is a `subagent_type: Reviewer` with `run_in_background: true`.

**Reviewer 1 — Robustness:**
> Review the plan at `{path}` from the angle of **robustness**. Focus on: failure modes not covered, recovery gaps, state machine holes, thread safety, timeout/deadline propagation, edge cases in lifecycle operations, network partition handling, DB consistency during multi-step operations, graceful degradation when external services are down. For each issue: specific section, problem, concrete fix.

**Reviewer 2 — Cleanness:**
> Review the plan at `{path}` from the angle of **code cleanness and design quality**. Focus on: naming consistency, separation of concerns, abstraction levels, single responsibility, interface cleanliness, redundancy between concepts, cohesion, dependency direction, consistency across similar patterns. For each issue: specific section, problem, concrete fix.

**Reviewer 3 — Understandability:**
> Review the plan at `{path}` from the angle of **ease of understanding** for a new developer. Focus on: learning curve, complexity of abstractions, magic/implicit behavior, naming clarity, pattern overload, debugging experience, onboarding friction, convention burden. For each issue: specific section, problem, concrete simplification. Be honest about over-engineering.

**Reviewer 4 — Testability:**
> Review the plan at `{path}` from the angle of **testability**. Focus on: can each component be tested in isolation, is DI sufficient for test isolation, are there hidden global states, can lifecycle/state machines be tested without real threads, can AI calls be tested without real APIs, can retry logic be tested deterministically, is test infrastructure sufficient, are there missing test categories. For each issue: specific section, problem, concrete fix.

**Reviewer 5 — Efficiency:**
> Review the plan at `{path}` from the angle of **performance and efficiency**. Focus on: DB call frequency, serialization overhead, thread/event loop overhead, memory accumulation, lock contention, progress propagation cost, template rendering, polling vs push, JSON serialization, startup time. For each issue: specific section, problem, estimated impact (low/medium/high), concrete optimization.

**Reviewer 6 — Angry Senior Engineer (The Gatekeeper):**
> You are a brutally honest senior engineer with 20 years of experience who has seen too many "clever" architectures collapse in production. You have ZERO tolerance for:
>
> **Security**: Any pattern that could lead to injection, data leaks, credential exposure, privilege escalation, or unvalidated input reaching sensitive operations. If you see raw string interpolation near SQL, user input reaching file paths, secrets in config objects that could be logged, or missing auth checks — you REJECT immediately.
>
> **Efficiency**: Any design that wastes resources unnecessarily. Gratuitous DB round-trips, O(n^2) algorithms hiding behind clean abstractions, unbounded memory growth, creating threads/connections that could be pooled, serializing data that will be immediately deserialized. If the "clean" design is 10x slower than the obvious approach, the clean design is WRONG.
>
> **Code Readability**: Any pattern where understanding what happens requires reading 4+ files, tracing through 3+ layers of indirection, or knowing implicit conventions not enforced by the type system. If a junior developer cannot understand what a function does by reading it and its immediate dependencies, it is TOO CLEVER.
>
> Review the plan at `{path}`. For every issue you find, rate it: REJECT (blocks everything), HATE (strongly object), or DISLIKE (grudgingly accept). You must find at least 5 issues or explain why the plan is unusually clean. Do NOT be nice. Do NOT soften feedback. If something is bad, say it is bad and say exactly why. End with a GO/NO-GO verdict.

### Step 2: Wait for all 6 reviewers to complete

### Step 3: Aggregate findings

Read all 6 reviewer outputs. Create a unified summary. The Angry Senior Engineer's REJECTs are automatically Critical-priority:

1. **Deduplicate** — same issue found by multiple reviewers gets merged, noting which angles flagged it
2. **Prioritize** — Critical > Major > Minor > Nitpick. Issues found by 2+ reviewers get bumped up one level
3. **Categorize** into:
   - **Must fix** — blocks implementation
   - **Should fix** — address in plan before starting
   - **Can fix during implementation** — track as known items
   - **Deferred** — acknowledged but not blocking

4. Present the aggregated table to the user

### Step 4: Ask user which fixes to apply

Use AskUserQuestion to confirm which categories to apply, then update the plan file with resolutions.

## Notes

- Each reviewer runs in ~2-3 minutes
- All 6 run in parallel so total wall time is ~3 minutes
- Reviewers are read-only — they never edit the plan
- The Angry Senior Engineer's REJECTs are treated as blockers — plan cannot proceed until resolved
- This command can be re-run after applying fixes to verify resolutions
- On re-runs, include a note in each prompt: "This is a re-review after fixes were applied. Focus on whether the previous issues were properly resolved, and look for any new issues introduced by the fixes."
