Initialize the agent team tracking structure for this project.

## Steps

1. Create the `.tracking/` directory structure:
   ```
   .tracking/
   ├── MEMORY.md
   ├── tsg.md
   ├── journal/
   ├── research/
   ├── plans/
   ├── details/
   ├── changes/
   ├── cannon/
   ├── investigations/
   └── scripts/
   ```

2. Create `.tracking/MEMORY.md` with this starter content:
   ```markdown
   # Project Memory

   Long-term patterns, decisions, and gotchas. Maintained by Lead only.

   ---

   ## Architecture Decisions

   _(none yet)_

   ## Patterns & Conventions

   _(none yet)_

   ## Gotchas & Lessons Learned

   _(none yet)_
   ```

3. Create `.tracking/tsg.md` (Troubleshooting Guide):
   ```markdown
   # Troubleshooting Guide

   Problems encountered and their solutions. Grows over time as the team works.

   ---

   <!-- Entry format:
   ### [Short problem title]
   **Symptom:** What you observed
   **Cause:** Root cause
   **Fix:** What resolved it
   **Date:** YYYY-MM-DD
   -->
   ```

4. Create `.tracking/cannon/README.md`:
   ```markdown
   # Cannon — Curated Knowledge Store

   Hand-validated, high-confidence findings. Researcher checks here before any external search.

   ## How knowledge gets here
   1. Researcher produces validated findings
   2. Researcher recommends promotion to cannon in return format
   3. Lead reviews and approves
   4. Lead copies validated content here

   ## Rules
   - Only validated, reusable knowledge belongs here
   - Each file should be self-contained on one topic
   - Include sources/evidence for every claim
   - Remove or update entries that become stale
   ```

5. Copy the plan validation script:
   - Read `~/.claude/scripts/validate-plan.py`
   - Write it to `.tracking/scripts/validate-plan.py`

6. If no project `CLAUDE.md` exists, create one from the template below. If one exists, ask the user if they want to add the agent team section.

7. Report what was created.

## Project CLAUDE.md Template

```markdown
# Project Instructions

## Overview
<!-- Brief description of this project -->

## Tech Stack
<!-- Languages, frameworks, key dependencies -->

## Build & Test
<!-- Commands to build, test, lint -->

## Conventions
<!-- Project-specific coding standards, naming, etc. -->

## Agent Team
This project uses the global agent team from `~/.claude/agents/`.
Tracking directory: `.tracking/`

### Plan Validation
```bash
# Validate plan structure
python .tracking/scripts/validate-plan.py <plan-file>
# Find current/next step
python .tracking/scripts/validate-plan.py <plan-file> --current-step
# Mark step done
python .tracking/scripts/validate-plan.py <plan-file> --update <step#> done
```

### Cannon
Curated knowledge in `.tracking/cannon/`. Researcher checks here first.

To override an agent for this project, create `.claude/agents/<name>.md` in this repo.
```

$ARGUMENTS
