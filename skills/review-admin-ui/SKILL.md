---
name: review-admin-ui
description: Run the full admin-portal QA checklist (docs/qa/admin-ui-checklist/) in a REAL Chromium browser via the Playwright MCP server, against an ISOLATED stack — a free port pair (never the default 3000/8000) and a DEDICATED review database `edu_ui_review` (EDU_TEST_MODE=1, so nothing leaks into the dev `edu`, the pytest `edu_test`, or prod DB) — recreated pristine BEFORE the run and dropped AFTER, so it never collides with a running test suite. SEEDS the DB (scripts/seed_admin_ui_review.py) so pagination/filter/detail tests are executable, runs super-admin steps FIRST so the run self-creates its admin user + .pem prerequisite, then walks every tab's function blocks across EN/中文 and phone/desktop, and writes a Claude-feedable findings report to .tracking/ui-reviews/. Use when the user asks to "run the admin UI review", "execute the QA checklist in a browser", "audit the admin UI quality", or "review-admin-ui".
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
2. **Dedicated, disposable DB.** The backend runs with `EDU_TEST_MODE=1` →
   `EDU_TEST_DB=edu_ui_review`, a database used by NOTHING else, so the review can
   create/delete freely with zero chance of colliding with the pytest suite (which
   owns `edu_test`). `review_db.py` recreates it pristine before the run and drops
   it after. (`src/config/settings.py::_enforce_test_mode` enforces the redirect and
   refuses to target the dev `edu` DB; `review_db.py` additionally refuses to touch
   `edu`/`edu_test`/`edu_test_e2e`/`edu_test_prod`.)
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

Other prereqs: the project `.venv`, and a reachable local PostgreSQL cluster with
the `vector`/`pg_trgm` extensions available (the `postgres` superuser can create
them). The review DB itself is auto-created — you do NOT pre-create it. Screenshots land in
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

### 2b. Recreate the dedicated review DB (pristine, BEFORE the backend)
Drop + create `edu_ui_review` with the `vector`/`pg_trgm` extensions, so the run
starts from a clean, isolated database. Set the PG creds in the same command:
```
$env:DATABASE__PG_HOST="localhost"; $env:DATABASE__PG_PORT="5432"
$env:DATABASE__PG_USERNAME="postgres"; $env:DATABASE__PG_PASSWORD="postgres"
& ".venv\Scripts\python.exe" "<repo>\.claude\skills\review-admin-ui\review_db.py" recreate
```
(Use `create` instead of `recreate` to keep an existing review DB across runs.)
This never touches `edu`/`edu_test`/`edu_test_e2e`/`edu_test_prod` — it refuses by
name.

### 3. Start the backend on `edu_ui_review` (background, run_in_background: true)
Set the test-mode env **in the same command** so uvicorn inherits it (shell state
does not persist between PowerShell tool calls):
```
$env:EDU_TEST_MODE = "1"
$env:EDU_TEST_DB   = "edu_ui_review"
$env:DATABASE__AUTO_MIGRATE_LOCAL_ON_BOOT = "true"   # apply alembic head to the fresh review DB on boot
& "<repo>\scripts\start_backend_local.ps1" -Port <BPORT>
```
LOCAL_MODE is set by the script (super-admin surface ON). A non-fatal prod-sentinel
`SchemaParityError` at boot is fine. The freshly-recreated `edu_ui_review` is empty;
the auto-migrate boot path builds the schema to head.

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

### 5b. Seed the sentinel + confirm clean slate (AFTER the backend migrates)
Once the backend is healthy the schema exists but there is no `users.id=1`
super-admin sentinel (it is not migration-seeded). Run `seed` to wipe any rows and
insert the sentinel, so local super-admin + row attribution work:
```
$env:EDU_TEST_DB = "edu_ui_review"
& ".venv\Scripts\python.exe" "<repo>\.claude\skills\review-admin-ui\review_db.py" seed
```
`seed` empties every table in reverse FK order and re-inserts only the sentinel; on
the freshly-recreated DB the wipe is a no-op and it just seeds. (`review_db.py check`
reports row counts without mutating.)

### 5c. Seed the review DATA (so the checklist tests are executable)
An empty portal can't exercise pagination/filter/detail tests. Populate the DB with
the state every checklist needs (≥1 page of users/tasks/logs/files/exams/etc., every
filter value, rich detail entities) — the spec is `docs/qa/admin-ui-checklist/SEED-SPEC.md`:
```
$env:EDU_TEST_DB = "edu_ui_review"
& ".venv\Scripts\python.exe" "<repo>\scripts\seed_admin_ui_review.py"
```
It prints the per-entity counts it inserted (~400 rows). It refuses any DB but the
review/test DB. Re-runnable only on a fresh DB (recreate first); it is not idempotent.
A few surfaces are filled by the BACKEND on boot, not this seed — config rows, the
prompt catalog, the 6 agents + qgen pipeline, and the active automations — so those
tabs already have data. (Config-revision history, an active prompt revision, and a
draft automation are the only "empty by default" extras; create them through the UI
during the review if you want to exercise rollback / active-revision / Enable.)

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
   **Dry run** on migrate — do NOT Apply unless deliberately
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

### 8. Teardown (drop the dedicated DB — nothing left behind)
1. `browser_close()`.
2. Stop the isolated stack: `kill-ports.ps1 -Ports <FPORT>,<BPORT>` (releases the
   backend's connections to the review DB).
3. **Drop the whole review DB** — it is dedicated, so removing it leaves zero
   residue:
   ```
   $env:EDU_TEST_DB = "edu_ui_review"
   & ".venv\Scripts\python.exe" "<repo>\.claude\skills\review-admin-ui\review_db.py" drop
   ```
4. Delete the issued credential: remove `<repo>\.claude\skills\review-admin-ui\pem\`.

Leave the stack running only if the user wants to keep poking — but still `drop` the
review DB when they're done. (`drop` uses `WITH (FORCE)`, so it works even if a
stray connection lingers; run it after step 2 to be clean.)

## Notes
- **Why super-admin first:** Admin Management is the only surface that mints an
  admin + PEM. Running it first turns the review's own actions into the fixtures the
  admin-tier tabs need — no separate seeding script, and it tests the issue/login
  path for real.
- **Fully isolated DB — no test-suite collision.** The run uses its own
  `edu_ui_review` database (recreated before, dropped after), so a pytest suite on
  `edu_test` can run concurrently without interference. To keep the review DB around
  for post-run inspection, use `review_db.py create` (not `recreate`) in step 2b and
  skip the `drop` in teardown. To point at a different name, set `$env:EDU_TEST_DB`
  before steps 2b/3/5b/8 — but never to `edu`/`edu_test*` (the script refuses those).
- **The matrix is the spec.** Read each `docs/qa/admin-ui-checklist/NN-*.md` file as
  you reach that tab — the function blocks, expected/break steps, and 🚩 watch-points
  are the exact things to check. If you find a function in the UI the checklist
  doesn't cover, note it in the report (and it should be added to the matrix —
  CLAUDE.md Admin Portal Rules + `tests/architecture/test_admin_ui_checklist_coverage.py`).
- **If a tab is empty when it shouldn't be**, the seed is missing that state — note it
  in the report and extend `scripts/seed_admin_ui_review.py` + `SEED-SPEC.md` (the
  seed arch test keeps it honest). The seed deliberately skips what the backend
  boot-seeds (config, prompt catalog, agents/pipelines, active automations).
- **Headful/headless, viewport, output-dir** are pinned in `.mcp.json` (shared with
  `verify-admin`); change them there, not per-call. If Chromium is missing:
  `cd src/frontend/admin && pnpm exec playwright install chromium`.
- Console/network diagnostics: `browser_console_messages()` /
  `browser_network_requests()` — include the relevant lines under any FAIL.
