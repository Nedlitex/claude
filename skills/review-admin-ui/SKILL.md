---
name: review-admin-ui
description: Run the full admin-portal QA checklist (docs/qa/admin-ui-checklist/) in a REAL Chromium browser via the Playwright MCP server, against an ISOLATED stack — a free port pair (never the default 3000/8000) and the edu_test database (EDU_TEST_MODE=1, so nothing leaks into the dev `edu` or prod DB), wiping edu_test clean BEFORE and AFTER so the shared test DB never accumulates review data. Runs super-admin steps FIRST so the run self-creates its admin user + .pem prerequisite, then walks every tab's function blocks across EN/中文 and phone/desktop, and writes a Claude-feedable findings report to .tracking/ui-reviews/. Use when the user asks to "run the admin UI review", "execute the QA checklist in a browser", "audit the admin UI quality", or "review-admin-ui".
---

# review-admin-ui

Drives a **real Chromium browser through the Playwright MCP server**
(`mcp__playwright__browser_*`) over the hand-to-tester QA matrix in
`docs/qa/admin-ui-checklist/`, and produces a report you can hand straight back to
Claude to code the fixes.

It differs from the lighter `verify-admin` skill in four ways the user asked for:

1. **Isolated ports.** It picks a FREE `(frontend, backend)` pair from a high band
   (3090+/8090+) via `pick-ports.ps1` — it never touches a dev portal on 3000/8000.
   Both `scripts/start_admin_frontend.bat` and `scripts/start_backend_local.ps1`
   already take a port argument.
2. **Isolated DB.** The backend runs with `EDU_TEST_MODE=1` → `EDU_TEST_DB=edu_test`,
   so every read/write hits `edu_test`, never the production-shaped dev `edu` DB or
   prod. (`src/config/settings.py::_enforce_test_mode` enforces the redirect and
   refuses to target `edu`.)
3. **Self-seeding order.** It runs the **super-admin** surface FIRST (local
   one-click super-admin → Admin Management) so the run *creates its own admin user
   and downloads its .pem*, then signs in as that admin via PEM login for the rest.
   No manual fixture setup.
4. **Actionable report.** It writes `.tracking/ui-reviews/<date>-admin-ui-review.md`
   from `report-template.md` — a priority-ordered fix backlog where each finding
   names the failing gate, the likely component file, and a concrete fix.

## Prerequisite: Playwright MCP server must be loaded

Same as `verify-admin`. This skill needs `mcp__playwright__*` tools (from the
`playwright` MCP server in `.mcp.json`). **MCP tools only load at session
startup.** If `ToolSearch select:mcp__playwright__browser_navigate` returns
nothing: confirm `claude mcp list` shows `playwright … ✔ Connected`; if connected
but unresolved, tell the user to restart Claude Code, then re-run. Do not fall back
to a non-browser path — real screenshots are the point.

Other prereqs: the project `.venv`, PostgreSQL up with the `edu_test` database +
`vector`/`pg_trgm` extensions (see CLAUDE.md "Build & Test"). Screenshots land in
the MCP `--output-dir` (`src/frontend/admin/tests/manual/screenshots/mcp/`); write
review shots under a `review/` filename prefix.

## Steps

Use the **PowerShell tool** for steps 1–5 (invoke scripts with `&` + an ABSOLUTE
path). Use **absolute repo paths** under `D:\edu2\…` (or wherever this clone lives —
resolve with `git rev-parse --show-toplevel`).

### 1. Pick a free port pair
```
& "<repo>\.claude\skills\review-admin-ui\pick-ports.ps1"
```
Parse `FPORT=` / `BPORT=` from stdout. Use them everywhere below. (Pass
`-FrontStart/-BackStart` if the band is busy.)

### 2. Clean slate on the chosen pair
```
& "<repo>\.claude\skills\review-admin-ui\kill-ports.ps1" -Ports <FPORT>,<BPORT>
```

### 3. Start the backend on `edu_test` (background, run_in_background: true)
Set the test-mode env **in the same command** so uvicorn inherits it (shell state
does not persist between PowerShell tool calls):
```
$env:EDU_TEST_MODE = "1"
$env:EDU_TEST_DB   = "edu_test"
$env:DATABASE__AUTO_MIGRATE_LOCAL_ON_BOOT = "true"   # apply alembic head to edu_test on boot
& "<repo>\scripts\start_backend_local.ps1" -Port <BPORT>
```
LOCAL_MODE is set by the script (super-admin surface ON). A non-fatal prod-sentinel
`SchemaParityError` at boot is fine. If `edu_test` is missing/behind, the auto-migrate
boot path brings it to head; if the DB does not exist, create it first
(`createdb edu_test` + the `vector`/`pg_trgm` extensions per CLAUDE.md).

### 4. Start the frontend pointed at that backend (foreground — the .bat self-detaches)
```
cmd /c "<repo>\scripts\start_admin_frontend.bat <FPORT> <BPORT>"
```

### 5. Wait until BOTH are healthy (bounded poll — never a fixed sleep)
```
$b = try { (Invoke-WebRequest "http://127.0.0.1:<BPORT>/health" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "DOWN" }
$f = try { (Invoke-WebRequest "http://127.0.0.1:<FPORT>/zh/login" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "DOWN" }
"backend=$b frontend=$f"
```
Backend cold boot ~10–30s; Next first compile ~10–40s. Re-poll until both 200. If
the backend never comes up, read its background output (PG connection? storage
config?).

### 5b. Wipe `edu_test` to a clean slate (BEFORE the review)
The review writes into `edu_test` (shared with pytest), so start clean and leave
clean. Run the row-wipe AFTER the backend is healthy (schema present), with the
same PG creds:
```
$env:EDU_TEST_DB = "edu_test"   # or edu_playwright_test if pytest is running
$env:DATABASE__PG_HOST="localhost"; $env:DATABASE__PG_PORT="5432"
$env:DATABASE__PG_USERNAME="postgres"; $env:DATABASE__PG_PASSWORD="postgres"
& ".venv\Scripts\python.exe" "<repo>\.claude\skills\review-admin-ui\reset_edu_test.py"
```
It `DELETE`s every row in reverse FK order (keeping only the `users.id=1`
super-admin sentinel) and refuses to touch the dev `edu` DB. Use `--check` first
if you want to see current row counts without deleting.

### 6. Drive the review IN THIS ORDER (self-seeding)

Core browser loop for every interaction: `browser_snapshot` (get refs) → act
(`browser_click`/`browser_type`/`browser_select_option`) → `browser_wait_for`
(expected text, never a sleep) → `browser_take_screenshot`. After each navigation
call `browser_console_messages()` once — a page that renders but throws console
errors is a FAIL.

**Two viewports, two languages.** For each function judge all 9 gates. Drive the
happy path + the break-it path once, then cover the matrix efficiently:
`browser_resize` to phone (~390×844) and desktop (~1440×900), and toggle locale via
the EN/中文 switch (or the `/en/…` vs `/zh/…` URL prefix). Q6/Q9 are judged on phone;
Q4 by switching locale. Don't re-do every click four times — re-snapshot per
lang/viewport and confirm the gate-relevant thing (layout intact, strings
translated).

**Phase 0 — Super-admin first (creates the prerequisites):**
1. `browser_navigate("http://127.0.0.1:<FPORT>/zh/login")`, snapshot, click the
   **local super-admin** one-click button → land on dashboard. Screenshot
   `review/00-super-login.png`. (Covers file `00` F2 + the super-admin nav.)
2. Walk **`17-admin-management.md`**: in **Create admin**, fill username
   `qa.reviewer`, a label, a valid expiry (≤1y), submit → the browser downloads a
   **`.pem`**. Capture it: the MCP server saves downloads — locate the
   `qa.reviewer_*.pem` it wrote and copy it to
   `<repo>\.claude\skills\review-admin-ui\pem\qa-admin.pem` (create the `pem\` dir;
   it is gitignored). If the download path is hard to capture, re-trigger with
   **Download again** and read it from the browser download dir. **Verify the file
   exists and is non-empty before Phase 1** — it is the prerequisite for PEM login.
   Continue F-blocks: admins list, Manage capabilities (grant the new admin enough
   caps to exercise the admin tabs — e.g. manage_users, manage_content,
   manage_taxonomy, run_ingest, manage_config, view_audit_log).
3. Walk **`18-migrate.md`** and **`19-db-status.md`** (still super-admin). Use
   **Dry run** on migrate — do NOT Apply against edu_test unless deliberately
   seeding. Walk file `00` F6 (DB-target toggle) but **do not switch to PROD**.

**Phase 1 — Admin, via the PEM you just issued:**
4. Sign out (file `00` F3). On the login screen, use the PEM picker to sign in with
   `pem\qa-admin.pem` (file `00` F1 — the real PEM login path). Screenshot
   `review/00-pem-login.png`.
5. Walk the admin tabs **in dependency order**, creating data THROUGH the UI so
   later tabs have something to show (creating the fixture also tests the create
   flow):
   - `12-taxonomy`, `07-textbook`, `06-knowledge-base` — establish vocabulary/content.
   - `05-files` — upload a small file (tests upload + gives Files/preview data).
   - `08-exams`, `09-question-gen` — ingest/generate (also populates `03-tasks`).
   - then the read-heavy tabs `01-dashboard`, `02-users`, `03-tasks`, `04-logs`,
     `10-audit-log`, `11-config`, `13-prompts`, `14-crawl`, `15-agent-pipelines`,
     `16-automations`.
   When a function needs data you cannot create in-session, mark its checks
   **⚪ not-observed** (per the README rule) — never fake a pass.

**For every function block:** do the **✅ Expected use** step and assert the
concrete success; do the **⚠️ Break it** step and assert the graceful failure;
read the **🚩 watch-points** and check exactly those against the snapshot. Record
PASS / FAIL / NOT-OBSERVED per gate (Q1–Q9), with the lang/viewport where it failed.
Destructive actions: confirm BOTH that the typed-confirm is required AND that Cancel
changes nothing.

### 7. Write the report (the deliverable)
Copy `report-template.md` to `.tracking/ui-reviews/<YYYY-MM-DD>-admin-ui-review.md`
(get the date from `Get-Date -Format yyyy-MM-dd`; create the dir). Fill it:
- the **Summary** table (per-file pass/fail/not-observed counts),
- the **Fix backlog** — every FAIL as a P1/P2/P3 item with observed/expected, the
  **likely component file** (take it from the checklist's 🚩 watch-point, which
  already cites the source, or from the page route), and a **concrete fix**,
- the **Full per-function results** for traceability,
- attach each failing screenshot path.
Then tell the user the report path and **`SendUserFile`** the key failing
screenshots as proof.

### 8. Teardown (always leave `edu_test` clean)
1. `browser_close()`.
2. **Wipe `edu_test` again** so the review leaves nothing behind (same command as
   step 5b — run it BEFORE killing the backend, while the DB is reachable, or after;
   it connects directly to PG so either order works):
   ```
   & ".venv\Scripts\python.exe" "<repo>\.claude\skills\review-admin-ui\reset_edu_test.py"
   ```
3. Stop the isolated stack: `kill-ports.ps1 -Ports <FPORT>,<BPORT>`.
4. Delete the issued credential: remove `<repo>\.claude\skills\review-admin-ui\pem\`.

Leave the stack running only if the user wants to keep poking — but still run the
post-run wipe when they're done so the shared test DB doesn't accumulate review data.

## Notes
- **Why super-admin first:** Admin Management is the only surface that mints an
  admin + PEM. Running it first turns the review's own actions into the fixtures the
  admin-tier tabs need — no separate seeding script, and it tests the issue/login
  path for real.
- **edu_test is shared with pytest.** This run writes data into `edu_test`. That is
  intended (isolation from dev/prod), but if a pytest run is happening concurrently,
  pass `-FrontStart/-BackStart` is irrelevant — instead set `$env:EDU_TEST_DB =
  "edu_playwright_test"` in step 3 to use the dedicated Playwright DB and avoid
  cross-talk. Default stays `edu_test` per the project instruction.
- **The matrix is the spec.** Read each `docs/qa/admin-ui-checklist/NN-*.md` file as
  you reach that tab — the function blocks, expected/break steps, and 🚩 watch-points
  are the exact things to check. If you find a function in the UI the checklist
  doesn't cover, note it in the report (and it should be added to the matrix —
  CLAUDE.md Admin Portal Rules + `tests/architecture/test_admin_ui_checklist_coverage.py`).
- **Headful/headless, viewport, output-dir** are pinned in `.mcp.json` (shared with
  `verify-admin`); change them there, not per-call. If Chromium is missing:
  `cd src/frontend/admin && pnpm exec playwright install chromium`.
- Console/network diagnostics: `browser_console_messages()` /
  `browser_network_requests()` — include the relevant lines under any FAIL.
