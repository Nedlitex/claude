Run a health check on the agent team brain configuration.

## Checks to perform:

1. **Global brain**: Verify `~/.claude/CLAUDE.md` exists and is readable
2. **Settings**: Verify `~/.claude/settings.json` has agent teams enabled
3. **Agent definitions**: List all agents in `~/.claude/agents/` and any project-level overrides in `.claude/agents/`
4. **Tracking directory**: Check if `.tracking/` exists with required subdirectories
5. **MEMORY.md**: Check if `.tracking/MEMORY.md` exists and has content
6. **Journal**: Check for today's journal entry in `.tracking/journal/`
7. **Stale plans**: Check `.tracking/plans/` for any plans with uncompleted tasks

## Report format:

```
## Brain Health Report

Global Brain: [OK/MISSING]
Settings: [OK/MISSING agent teams]
Agents: [count] global, [count] project overrides
Tracking: [OK/MISSING/INCOMPLETE]
Memory: [OK/EMPTY/MISSING]
Journal: [today's entry exists/missing]
Plans: [count] active, [count] stale

Issues found: [count]
1. [issue description]
2. ...
```

If issues are found, offer to fix them.
