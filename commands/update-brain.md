Capture learnings from the current conversation and update the project brain.

## Workflow

1. **Scan recent conversation** — Review the last ~20 messages for:
   - Corrections the user made ("no, we do it like X", "that's wrong")
   - Patterns discovered during implementation
   - Architectural decisions made
   - Gotchas or surprises encountered
   - New conventions established
   - Tool/build/test commands learned

2. **Categorize findings** — Group into:
   - **MEMORY.md updates** — Architectural decisions, conventions, gotchas
   - **Cannon candidates** — Validated, reusable knowledge (ask before promoting)
   - **Agent updates** — If behavior corrections apply to a specific agent role
   - **CLAUDE.md updates** — If project-level rules need updating
   - **TSG entries** — Troubleshooting patterns (problem → cause → fix)

3. **Present proposed changes** — Show the user what you plan to update:
   ```
   ## Proposed Brain Updates

   ### MEMORY.md
   - [+ addition or ~ change]: description

   ### TSG (.tracking/tsg.md)
   - [+ new entry]: problem → fix

   ### Cannon (.tracking/cannon/)
   - [+ new file]: topic — why it's worth curating

   ### Agent updates
   - [agent-name]: what to change and why

   ### CLAUDE.md
   - [+ addition or ~ change]: description
   ```

4. **Wait for approval** — Do not write anything until the user confirms.

5. **Apply changes** — Update the approved files. For MEMORY.md, append to the appropriate section. For cannon, create a new markdown file with clear structure. For TSG, append a new entry.

6. **Confirm** — Report what was updated with file paths.

## Rules

- NEVER auto-update without showing the user first
- MEMORY.md updates go in the appropriate section (Architecture Decisions, Patterns & Conventions, Gotchas)
- Cannon files must be validated knowledge — not hypotheses
- If nothing worth capturing, say so: "No brain updates needed from this session."

$ARGUMENTS
