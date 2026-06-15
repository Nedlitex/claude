---
name: verify-admin
description: Start the local admin backend + Next.js frontend (killing whatever is on ports 8000/3000 first) and drive a REAL Chromium browser via the Playwright MCP server to verify the admin portal works — capturing screenshots at each step and sending them to the user as proof. Use after changing admin-portal pages/components, or whenever the user asks to "verify the admin UI in a browser", "smoke-test the portal", or "check it actually works". Honors the project rule that admin changes must be verified in a running browser, not just by tsc/vitest.
---

# verify-admin

Brings up the local admin stack and drives a **real Chromium browser through the
Playwright MCP server** (`mcp__playwright__browser_*` tools), so the agent itself
clicks through the portal, takes screenshots, and **sends those screenshots to the
user as proof**. This replaces the old opaque `node tests/manual/*.mjs` flow — the
agent now performs each browser action directly and shows the result.

Backend = `scripts/start_backend_local.ps1` (uvicorn, port 8000, LOCAL_MODE so
super-admin works). Frontend = `scripts/start_admin_frontend.bat` (Next dev,
port 3000, proxy → backend).

**Always kill the ports first** — a stale uvicorn/next on 8000/3000 serves OLD
code, so the browser would verify the wrong build.

## Prerequisite: Playwright MCP server must be loaded

This skill needs the `mcp__playwright__*` tools. They come from a `playwright`
MCP server registered either user-scope (`~/.claude.json`) or in the repo's
`.mcp.json`. **MCP tools only load at session startup** — if
`ToolSearch` for `browser_navigate` returns nothing, the server was added/changed
in this session and is NOT yet usable.

- Verify it is registered + connected: `claude mcp list` (look for
  `playwright: ... ✔ Connected`).
- Confirm the tools are live: `ToolSearch` with `select:mcp__playwright__browser_navigate,mcp__playwright__browser_take_screenshot,mcp__playwright__browser_click,mcp__playwright__browser_snapshot`.
- If the server is connected but the tools don't resolve, **tell the user to
  restart Claude Code** (or `/exit` and reopen) so the MCP tools register, then
  re-run `/verify-admin`. Do not fall back to the old `.mjs` script silently —
  the whole point is real, screenshotted automation.

Screenshots are written by the MCP server to its configured `--output-dir`. The
**global (user-scope)** Playwright MCP writes to `~/.claude/screenshots/`
(`C:\Users\<you>\.claude\screenshots\` on Windows). If a project pins its own
`.mcp.json` playwright entry with a repo-relative `--output-dir` (e.g.
`<repo>/src/frontend/admin/tests/manual/screenshots/mcp/`), that project-scope
override wins inside that repo. `browser_take_screenshot` returns/saves a file
under whichever dir is active; pass that returned path to `SendUserFile` — never
hardcode the dir, read it back from the tool result.

## Steps

Use the **PowerShell tool** (already runs in pwsh) for steps 1–3. Invoke scripts
with the call operator `&` and an ABSOLUTE path — `pwsh -File <relative>` fails to
resolve from the tool's working dir. **Do NOT hardcode any repo path** — this skill
runs in whatever repo is checked out. Resolve the roots first:

0. **Resolve the repo root and this skill's dir** (PowerShell tool):
   ```powershell
   $repo  = (git rev-parse --show-toplevel).Trim()       # the checked-out repo (e.g. D:\edu, D:\edu2, a worktree)
   $skill = "$HOME\.claude\skills\verify-admin"            # this skill's bundled assets (kill-ports.ps1)
   "repo=$repo skill=$skill"
   ```
   Use `$repo\scripts\…` for the app launchers and `$skill\…` for the bundled
   helper. (If the project ships its own `.claude/skills/verify-admin/`, prefer
   `$repo\.claude\skills\verify-admin` for the helper.)

1. **Kill existing ports (mandatory clean slate).**
   ```powershell
   & "$skill\kill-ports.ps1"
   ```
   (Add `-Ports 3001,8001` to target a non-default pair.)

2. **Start the backend** (background — it runs uvicorn in the foreground, so it
   must stay attached as a long-running task). PowerShell tool, `run_in_background: true`:
   ```powershell
   & "$repo\scripts\start_backend_local.ps1"
   ```
   A non-fatal `Prod DB sentinel probe failed … SchemaParityError` at boot is
   fine — it only means the (unused) prod-target DB is behind; local serves
   normally and `Application startup complete` still prints.

3. **Start the frontend** (the .bat self-detaches into its own window and returns
   immediately — run it foreground; it does NOT block):
   ```powershell
   cmd /c "$repo\scripts\start_admin_frontend.bat"
   ```

4. **Wait until BOTH are healthy** (bounded poll — these are external
   long-running servers, so polling their health is the right call; do NOT just
   sleep a fixed time). Backend cold boot on Windows ~10–30s; Next dev first
   compile ~10–40s. Re-check until both are 200 (PowerShell tool):
   ```
   $b = try { (Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "DOWN" }
   $f = try { (Invoke-WebRequest "http://127.0.0.1:3000/zh/login" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "DOWN" }
   "backend=$b frontend=$f"
   ```
   If the backend never comes up, read its background output — common causes: a
   poison-message loop (self-heals — stale job drops on first delivery), a PG
   connection failure, or a storage-config error.

5. **Drive the browser via Playwright MCP.** Work the portal with the
   `mcp__playwright__browser_*` tools. Core loop for every interaction:
   `browser_snapshot` (get the accessibility tree + element `ref`s) → act
   (`browser_click` / `browser_type` / `browser_select_option`) → `browser_wait_for`
   the expected text → `browser_take_screenshot`. Use the snapshot's `ref`s to
   target elements; do NOT guess coordinates.

   Recommended tools (load schemas with `ToolSearch select:...` if not present):
   - `browser_navigate(url)` — go to a page.
   - `browser_snapshot()` — accessibility tree with `ref`s (preferred over screenshots for *deciding* what to click).
   - `browser_click(element, ref)` / `browser_type(element, ref, text)` — interact.
   - `browser_wait_for(text=...)` — wait for content (never fixed sleeps).
   - `browser_take_screenshot(filename=..., fullPage=true)` — capture PROOF.
   - `browser_console_messages()` / `browser_network_requests()` — diagnose failures.
   - `browser_close()` — teardown the browser at the end.

   **Login (local super admin):**
   1. `browser_navigate("http://127.0.0.1:3000/zh/login")`.
   2. `browser_snapshot()`, find the super-admin login button (the local-mode
      one-click button), `browser_click` it.
   3. `browser_wait_for` the dashboard/landing text; `browser_take_screenshot`
      `01-login.png`.

   **Then exercise whatever changed.** Default smoke checks (adapt to the actual
   change under review):
   - **R1** — Automations list shows working Disable/Enable controls. Navigate to
     the automations page, snapshot, screenshot `02-automations-list.png`.
   - **R2** — a clickable automation target opens a read-only pipeline popup.
     Click a target, wait for the dialog, screenshot `03-pipeline-popup.png`.
   - **R3** — a clickable pipeline-step agent name opens a read-only agent popup.
     Click it, wait for the dialog, screenshot `04-agent-popup.png`.

   For each check, decide PASS/FAIL from the snapshot/visible text (assert the
   expected element/text is present), and note it. After every navigation, call
   `browser_console_messages()` once — a portal that renders but throws console
   errors is a FAIL, not a pass.

6. **Report with proof.** Output a PASS/FAIL line per check, then **`SendUserFile`
   every screenshot** using the path each `browser_take_screenshot` returned (the
   active `--output-dir` — user-scope `~/.claude/screenshots/` or a repo-relative
   project override; do not hardcode it) (`status: "proactive"` if the user is
   away). The screenshots ARE the deliverable — never claim a check passed without
   sending its screenshot. On any FAIL, also surface the relevant
   `browser_console_messages` / `browser_network_requests` lines.

7. **Teardown (ask first).** Call `browser_close()` to drop the browser. Leave the
   servers running so the user can keep poking the portal; only stop them when the
   user asks — re-run `kill-ports.ps1` to tear down.

## Notes

- Backend reads the repo `.env` (storage backend, DB) and binds loopback. It uses
  the repo's configured local dev DB — this verifies real behavior, not a test DB.
- The frontend proxy needs `ADMIN_SECRET` (in `<repo>/src/frontend/admin/.env.local`)
  to match the backend `ADMIN__SECRET` (in `<repo>/.env`). A `403 privilege
  escalation` on every request means they differ.
- The MCP server downloads its own Chromium on first run (`npx -y @playwright/mcp`).
  If launch fails for a missing browser, run
  `cd <repo>/src/frontend/admin && pnpm exec playwright install chromium`.
- Headful/headless: the MCP server defaults to headed Chromium. To run headless,
  add `--headless` to the server `args` in `.mcp.json`.
- `--output-dir`, `--viewport-size`, and `--browser` are pinned in `.mcp.json`;
  change viewport/output there, not per-call.
- Legacy fallback: the old `node tests/manual/verify-admin-changes.mjs` script
  still exists and self-discovers data, but prefer the MCP path so the agent
  produces step-by-step screenshots it can show the user.
