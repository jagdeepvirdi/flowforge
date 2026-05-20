# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*

---

## GitHub Release Score: 8.2 / 10 (updated 2026-05-18)

| Dimension | Score |
|---|---|
| Code quality | 7/10 — Clean architecture, good separation of concerns |
| Feature completeness | 7/10 — Async, Docker, CI done; M365 token refresh + YAML import still missing |
| Security | 8/10 — Encryption + rate limiting done; Alembic migrations still missing |
| Documentation | 5/10 — Missing pages, no screenshots |
| Deployment UX | 7/10 — Docker Compose + CI added |
| GitHub readiness | 8/10 — Legacy removed, stubs fixed, deps corrected |

---

## Remaining Work

---

## Phase 1 — Core Stability 🔴
*Must be done before any public release. Backend fixes.*

- [ ] **Bug: Report columns show as col0/col1/col2** — `execute_query()` in `connections/postgres.py:35` discards `cursor.description` and returns only rows. `ReportStep` at `steps/report.py:31` falls back to `[f'col{i}' for i in range(...)]` whenever `report_cfg['columns']` is null (always true for `report_config_id`-based configs). Fix: add `execute_query_with_columns() -> tuple[list[tuple], list[str]]` to `BaseConnection` and both concrete implementations; update `ReportStep.run()` to use it. Same fix needed in `oracle.py`.

---

## Phase 2 — Tests & Verification 🧪
*Automated test coverage + manual pre-launch smoke tests.*

### Features Before Launch

- [x] **Built-in smart date-range variables** — Add `{{ week_start }}`, `{{ week_end }}`, `{{ month_start }}`, `{{ month_end }}`, `{{ quarter_start }}`, `{{ quarter_end }}` to `flowforge/engine/context.py` alongside the existing date vars. Values always calculated relative to today at runtime (ISO week: Mon–Sun; month: 1st–last day; quarter: Q1=Jan–Mar etc.). Update the `{{ variable }}` field tooltip in `helpContent.ts` to list the new vars with examples.
- [x] **db_query scalar output variable** — Add optional `output_variable` field to `db_query` step config. When set, captures the value from the first column of the first row and makes it available as `{{ <output_variable> }}` in subsequent step configs and the email body template (e.g., `output_variable: subscription_count` → `{{ subscription_count }}` in email). Update `StepEditor.tsx` to show the field for `db_query` steps.

### Manual Verification Checklist (do before launch)

#### End-to-End Pipeline Test
- [ ] Create DB connection → Test → verify "Connected"
- [ ] Create report config with simple `SELECT` → Preview → verify rows appear
- [ ] Create pipeline with one `report` step → Run Now → check Run History
- [ ] Add `email` step after report → run → verify email received
- [ ] Verify `{{ current_date }}` resolves in output filename and email subject
- [ ] Verify `StepResult.output_path` flows from report step → email attachments
- [ ] Verify `duration_ms` and `rows_affected` written to `ff_step_runs`

#### Scheduler Smoke Test
- [ ] Create pipeline with `* * * * *` schedule → start scheduler → verify auto-run in history
- [ ] Disable pipeline → verify no more runs triggered

---

## Phase 4 — Polish & Release Prep 🔵
*Docs, GitHub presence, and final UX touches.*

- [ ] **Visual cron builder** — Replace the raw cron text input in `PipelineEdit.tsx` with a frequency picker: Every N minutes / Hourly / Daily / Weekly / Monthly / Custom (raw). Picker generates the cron string; raw mode still available for power users. Show "Next 5 run times" preview below the field. Also fix `FieldTooltip` popping upward and clipping behind the fixed TopBar — switch to downward pop when near the top of the viewport.
- [ ] **TopBar refresh button** — Add a `RefreshCw` icon button to `TopBar.tsx` (left of the help button) that calls `queryClient.invalidateQueries()` scoped to the current page's query keys. No-op on pages with no server data (e.g. Settings OAuth tab).
- [ ] **Run history: log resolved variable values** — After context rendering in the pipeline runner, append a "Variables resolved:" block to `ff_step_runs.logs` listing each built-in and pipeline variable with its computed value (mask `is_secret` vars). Lets you validate in Run History exactly what date range was passed to a report query.
- [ ] **Help discovery indicator** — Add a subtle pulse/dot to the TopBar `?` button for first-time users (cleared via `localStorage` flag `ff_help_seen`) so they know the help drawer exists. The drawer is fully built (Phase 3 done) but users may not discover it.
- [ ] **README screenshots** — Dashboard, Pipeline Builder, Run Detail. Highest-impact item for GitHub stars.
- [ ] **Write `docs/step-types.md`** — Full config spec for each step type with YAML examples.
- [ ] **Write `docs/email-providers.md`** — SMTP + M365 setup sections (Gmail already done).
- [ ] **Add `CONTRIBUTING.md`** — Running tests, project structure, PR process.
- [ ] **Add GitHub issue templates** — Bug report + feature request.
- [ ] **Validate cron expressions** — Check field ranges, not just 5-part split.
- [ ] **Update CHANGELOG.md** — Document what's actually in v0.1.0.

---

## Backlog (Post v1)

### More Email Providers
- [ ] SendGrid API
- [ ] AWS SES
- [ ] Mailgun

### More Storage
- [ ] SFTP upload step
- [ ] AWS S3 upload step
- [ ] Azure Blob upload step
- [ ] **OneDrive / SharePoint upload step** — Graph API + MSAL (already installed via `[microsoft365]`). New `onedrive_upload` step type, extend smart attachment with `storage_provider` field (`google_drive` | `onedrive`). Deferred to post-core-stability. *User confirmed active need.*

### More DB Support
- [ ] MySQL / MariaDB
- [ ] MSSQL / SQL Server
- [ ] Generic ODBC

### Pipeline Features
- [ ] Pipeline dependencies (run B after A)
- [ ] Parallel step execution
- [ ] Step retry with exponential backoff
- [ ] Pipeline YAML import/export from UI
- [ ] **Pipeline run parameter UI** — A "Parameters" section on the pipeline edit page where you define named params and their computation rules (e.g., `week_start = start of current ISO week`, `week_end = end of current ISO week`). More flexible than built-in date vars; allows per-pipeline customization. Params become available as `{{ params.week_start }}` in all step configs. Pairs with the built-in smart date vars (ship those first).
- [ ] **Bulk file loader step (`bulk_load`)** — Replaces the Oracle SQL\*Loader shell script at `github.com/jagdeepvirdi/DayToDayOfficeOperations`. Full spec below.

  **Step config (stored in `pipeline_steps.config` JSONB):**
  ```json
  {
    "connection_id": "uuid",
    "source_directory": "/data/incoming/",
    "file_prefix": "SUBS_",
    "file_prefix_exclude": null,
    "file_type": "csv",
    "delimiter": ",",
    "header_rows": 1,
    "footer_rows": 0,
    "target_table": "STAGING.SUBSCRIPTIONS",
    "load_mode": "append",
    "column_mapping": [],
    "use_sqlloader": true,
    "archive_directory": "/data/archive/{{ current_date }}/",
    "on_no_files": "skip"
  }
  ```

  **Execution — three internal paths:**
  1. **Oracle + `use_sqlloader: true`** — FlowForge generates a `.ctl` control file dynamically from the step config (delimiter, column mapping, date formats). Calls `sqlldr user/pass@dsn control=<tmp>.ctl log=<tmp>.log bad=<tmp>.bad` as a subprocess. Parses the `.log` file for "rows loaded" / "rows not loaded" counts. Surfaces `.bad` file content (rejected rows) in `step_runs.logs`. Fastest path — Oracle direct-path load, bypasses redo logging.
  2. **PostgreSQL** — Uses psycopg2 `cursor.copy_expert("COPY table FROM STDIN CSV HEADER", file)`. Equivalent speed to SQL\*Loader for Postgres. Parse `copy_expert` counts for loaded/rejected rows.
  3. **Python fallback** (any DB, or `use_sqlloader: false`)— Reads file in chunks of 10,000 rows, strips `header_rows` + `footer_rows`, inserts via `executemany()`. Slower but requires no external tooling.

  **Control file auto-generation (Oracle path):**
  FlowForge writes the `.ctl` to a temp directory — the user never touches it. Derives from: delimiter, `column_mapping`, any date-format hints on columns. After load: archive source files to `archive_directory`, delete temp `.ctl`/`.log`/`.bad`.

  **Step output variables (available in subsequent steps via `{{ steps.<name>.x }}`):**
  | Variable | Example |
  |---|---|
  | `files_found` | 3 |
  | `files_loaded` | 3 |
  | `files_failed` | 0 |
  | `records_loaded` | 147,832 |
  | `records_failed` | 14 |
  | `duration_sec` | 8.3 |

  Use these directly in an `email` step body to send a load confirmation — no new feature needed, standard pipeline step.

  **Run History tracking:**
  - `step_runs.rows_affected` = `records_loaded`
  - `step_runs.logs` = full load summary + first 50 rejected rows from `.bad` file

  **Code changes required:**
  - `flowforge/steps/bulk_load.py` — new step class
  - `flowforge/steps/base.py` — add `files_found`, `files_loaded`, `files_failed`, `records_loaded`, `records_failed`, `duration_sec` fields to `StepResult`
  - `flowforge/engine/context.py` — propagate new `StepResult` fields into pipeline context (same pattern as `output_path` and `drive_url`)
  - `frontend/src/components/pipeline/StepEditor.tsx` — add `bulk_load` step config panel
  - `frontend/src/lib/helpContent.ts` — add `bulk_load` to step hints
  - Alembic migration — add `bulk_load` to step type enum if constrained

  **Implementation order:** Python fallback first (works immediately, no Oracle client needed for dev/test) → PostgreSQL COPY → Oracle SQL\*Loader.

### Platform
- [ ] Multi-user auth with roles (v2)
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)
- [ ] AI analyze step — `flowforge/steps/ai_analyze.py`, Ollama/Claude routing, `{{ ai_summary }}` variable (v2)

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| cx_Oracle requires Oracle Instant Client | Document clearly; make Oracle optional: `pip install flowforge[oracle]` |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
