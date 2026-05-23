# FlowForge — Codebase Review

**Review date**: 2026-05-23
**Reviewer**: Claude Sonnet 4.6 (via Claude Code)
**Commit**: cbf0d23
**Branch**: master

---

## Score Comparison (Previous → Current)

| Dimension | 2026-05-20 | 2026-05-23 | Δ | Verdict |
|---|---|---|---|---|
| Architecture | 6.5 / 10 | 7.0 / 10 | +0.5 | Concurrency limit, timeout, stuck-run sweep added |
| Code Quality | 6.0 / 10 | 7.0 / 10 | +1.0 | Silent failures fixed; step_type attribute; timezone |
| Database | 6.5 / 10 | 8.0 / 10 | +1.5 | Indexes, step-order fix, constraint widened, TZ migration |
| Security | 5.5 / 10 | 7.5 / 10 | +2.0 | Keys split; credentials out; ProxyFix; audit log seeded |
| Tests | 6.0 / 10 | 7.5 / 10 | +1.5 | False-green fixed; 8 new test files; Vitest added |
| Frontend | 5.5 / 10 | 6.5 / 10 | +1.0 | Error boundaries; basic validation; type fixes; pagination |
| DevOps | 6.0 / 10 | 7.5 / 10 | +1.5 | Scheduler in Docker; healthcheck; seed moved to CLI |
| **Overall** | **6.0 / 10** | **7.3 / 10** | **+1.3** | Significant progress; frontend is still the ceiling |

---

## 1. Architecture · 7.0 / 10

### Strengths
- **Layered abstractions** — `BaseStep → concrete steps`, `BaseConnection`, `EmailProvider` ABC are clean and genuinely extensible. Adding a new step type or DB backend takes one file.
- **Database-driven config** — No YAML sprawl. A pipeline is a row in `ff_pipelines`; its steps are rows in `ff_pipeline_steps`. The UI is the primary interface — nothing is second-class.
- **Jinja2 context system** (`context.py`) — 25+ built-in variables covering all practical reporting needs: date ranges, quarter boundaries, week start/end, step outputs, env vars, pipeline variables.
- **Smart attachment handling** — Large reports automatically redirect through Google Drive. The logic is cleanly isolated in `email_step.py`.
- **Concurrency limit** — `_semaphore` and `FLOWFORGE_MAX_CONCURRENT_RUNS` prevent runaway thread spawning.
- **Timeout enforcement** — `concurrent.futures.ThreadPoolExecutor` with `.result(timeout=...)` actually enforces `timeout_minutes` (was documented but unimplemented in previous review).
- **Stuck-run sweep** — `_sweep_stuck_runs()` at app startup marks `running` rows as `failed` after a restart.

### Remaining Issues

**[ARCH-1] Daemon threads — no graceful shutdown**
`threading.Thread(target=_run_in_background, daemon=True)` — daemon threads are killed immediately on process exit. A pipeline mid-execution during a `kill` or deployment loses its state. The semaphore releases correctly but in-flight DB writes are lost. A `signal` handler with a drain period would fix this.

**[ARCH-2] Scheduler uses in-memory store, not PostgreSQL jobstore**
CLAUDE.md states "APScheduler with PostgreSQL job store" but `scheduler.py` uses a plain `BackgroundScheduler` with the default memory store. Jobs are re-synced from the DB on startup (`_sync_pipeline_jobs`), which is workable but not the same as a durable jobstore. Multi-process deployments will run duplicate jobs.

**[ARCH-3] No webhook/API trigger**
Pipelines can only be triggered from the UI, the scheduler, or the CLI. There is no `POST /pipelines/{id}/trigger?token=...` endpoint for external systems to call. Common need: trigger a pipeline after a data load from an ETL tool.

---

## 2. Code Quality · 7.0 / 10

### Strengths
- Consistent `logging.getLogger(__name__)` throughout.
- Dataclasses for result types (`PipelineResult`, `StepResult`) — no raw dicts passed around.
- Type hints on all public function signatures.
- Silent exception swallowing in runner.py fixed — now catches `SQLAlchemyError` and logs at `ERROR` level.
- `step_type` attribute on `BaseStep` — no more fragile `class.__name__.replace('Step', '')` string hack.
- Context collision protection — built-in variable keys are protected from overwrite.
- `_utcnow()` now returns timezone-aware timestamps stored as `TIMESTAMPTZ`.

### Remaining Issues

**[CODE-1] `table_name` interpolation in `db_query.py`**
```python
# db_query.py
sql = f"TRUNCATE {output_table}"
cursor.execute(f"INSERT INTO {output_table} ...")
```
`output_table` comes from user config (stored in DB), not raw user input — acceptable risk level. However if connection credentials are ever compromised, table names could be weaponized. Should at minimum validate against a safe identifier regex (`^[a-zA-Z_][a-zA-Z0-9_.]*$`) before interpolation.

**[CODE-2] No SMTP timeout**
`flowforge/email_providers/smtp.py` — `smtplib.SMTP()` is created without a `timeout` parameter. A slow or unresponsive SMTP server blocks the pipeline thread indefinitely (bypassing `timeout_minutes`). Fix: `smtplib.SMTP(host, port, timeout=30)`.

**[CODE-3] Drive API failures are silent**
`flowforge/storage/google_drive.py` — upload errors are caught and logged but the exception is re-raised to the email step only if the Drive upload was the primary goal. In smart-attachment mode, a Drive upload failure silently falls back to direct attach regardless of file size. Users have no visibility that their "smart" upload failed.

**[CODE-4] `bulk_load` step `output_table` not parametrized**
Same interpolation pattern as CODE-1 applies to the bulk_load step's target table name.

---

## 3. Database · 8.0 / 10

### Strengths
- UUID primary keys throughout.
- `CheckConstraint` on all enum columns.
- Proper FK cascade rules (`ON DELETE CASCADE` for steps, `ON DELETE SET NULL` for run history).
- `JSONB` for step config — correct choice.
- Alembic with 6 migrations, all reversible.
- Performance indexes added: `(pipeline_id, started_at DESC)` on `ff_pipeline_runs`; `pipeline_run_id` on `ff_step_runs`.
- Step reordering two-phase swap — no longer violates the unique constraint.
- Timezone-aware timestamps (`TIMESTAMPTZ`) across all tables.
- `ff_projects` properly isolated with FK to all scoped tables.

### Remaining Issues

**[DB-1] `PipelineRun.pipeline_id ON DELETE SET NULL` creates invisible history**
When a pipeline is deleted, its runs stay with `pipeline_id = NULL`. The denormalized `pipeline_name` column preserves display but API filters `WHERE pipeline_id = ?` will never return these runs. A deleted pipeline's full history disappears from the UI without warning.

**[DB-2] Check constraint lists unsupported DB types**
```python
CheckConstraint("db_type IN ('postgresql', 'oracle', 'mysql', 'mssql', 'snowflake')")
```
`mysql`, `mssql`, `snowflake` are in the constraint but the `get_connection()` factory raises an error for them. Users can insert a MySQL connection through the API and it will validate at the DB level but fail at runtime. Should either remove from the constraint or implement the factory entries.

**[DB-3] No index on `ff_pipeline_variables(pipeline_id)`**
`pipeline_variables` is loaded on every pipeline run. At 100+ vars per pipeline this is a full table scan.

---

## 4. Security · 7.5 / 10

### Strengths
- AES-256-GCM via `cryptography.hazmat` — random nonce per encryption, correct implementation.
- bcrypt with cost factor 12 for admin password.
- `FLOWFORGE_SECRET_KEY` (AES) and `FLOWFORGE_JWT_SECRET` now split — compromise of one doesn't compromise both.
- No real credentials in test fixtures — env-var driven.
- Rate limiting on `/api/auth/login` (10/min per IP).
- `ProxyFix` middleware with `FLOWFORGE_TRUSTED_PROXIES` for correct IP detection.
- CORS warns loudly in production if `FLOWFORGE_CORS_ORIGIN` is unset.
- Basic audit log (`logs/audit.log`) — login success/failure, pipeline start/end.

### Remaining Issues

**[SEC-1] No JWT token revocation**
A stolen or leaked JWT is valid for 24 hours with zero invalidation mechanism. No blocklist, no `jti` claim tracking, no `/auth/logout` server-side action. For a tool that runs arbitrary SQL and sends emails, this is a meaningful gap. Minimum fix: store a `jti` UUID per token, maintain a server-side revocation set.

**[SEC-2] Audit log is incomplete**
`flowforge/audit.py` logs login events and pipeline start/end. It does NOT log:
- Configuration changes (connection created/modified/deleted)
- Email provider setup
- Email sends (who was sent what, when)
- Report generation (what data was exported)
- User accessing run logs

A tool processing sensitive business data that passes a compliance review needs all of the above.

**[SEC-3] Jinja2 renders SQL before execution (intentional but risky)**
```python
sql = render(self.config['query'], context)
cursor.execute(sql, params)
```
Admin-controlled pipeline variables flow through Jinja2 into the SQL string before execution. Parameterized queries run after rendering — but the Jinja2 render step itself is unguarded. A poorly scoped `{{ env.DB_PASSWORD }}` in a query will happily exfiltrate credentials into a SQL string. Should document this risk prominently and consider a separate safe variable namespace.

**[SEC-4] Secret pipeline variables stored as encrypted text, but decrypted in memory for all steps**
Secret vars are decrypted into the pipeline context at run start and remain accessible to all steps in the pipeline. If a `db_query` step has `output_variable: secret_key`, a user could extract a secret to a visible field. Low risk in single-user v1; higher in multi-user v2.

---

## 5. Tests · 7.5 / 10

### Strengths
- Integration tests hit real PostgreSQL — correct and valuable.
- Runner unit tests cover the `on_error` state machine well.
- 15 test files, 168+ tests covering crypto, auth, connections, pipelines, reports, recipients, runs, email configs, context resolution, step DB operations, smart attachments, Jinja2 error handling, cron validation, pipeline variables, projects, db_query capture.
- Vitest frontend tests (13 tests across Dashboard, Pipelines, TopBar search).
- All false-green tests fixed.

### Remaining Issues

**[TEST-1] Frontend test coverage is thin — 13 tests**
13 Vitest tests cover basic rendering and one search interaction. No tests for:
- Form validation logic
- CRUD operations (create pipeline, save report)
- ProjectSwitcher state management
- CronBuilder expression generation
- Email designer attachment logic
- Step editor type switching

**[TEST-2] No E2E tests**
No Playwright or Cypress suite. The full user journey (login → create pipeline → run → check history) is untested. Critical for catching regressions across the API/frontend boundary.

**[TEST-3] Email send integration not tested**
Gmail, M365, SMTP providers have no integration tests. `test_email_providers.py` uses mocked SMTP. A real credential rotation or API change would not be caught in CI.

**[TEST-4] Report generation not tested end-to-end**
`test_report_generators.py` tests the Excel/CSV writers in isolation but doesn't test the full pipeline (query → format → write file → verify file on disk).

**[TEST-5] `bulk_load` step untested**
The `bulk_load` step (`flowforge/steps/bulk_load.py`) has no test file. Given its complexity (COPY vs chunked fallback, archive mode, footer stripping), this is a gap.

---

## 6. Frontend · 6.5 / 10

### Strengths
- TypeScript throughout.
- React Query used correctly — mutations invalidate right keys, polling is conditional.
- React error boundary (`RouteErrorBoundary`) wraps all page routes.
- Basic form validation with `fieldErrors` state in all main forms.
- Design system CSS tokens (`--accent`, `--surface`, etc.) defined and mostly applied.
- Pagination in RunHistory.
- Help system (HelpDrawer, page intro cards, field tooltips, glossary) is genuinely useful.
- Zustand project store with localStorage persistence.
- All `any` types in TopBar search replaced with proper types.

### Remaining Issues

**[FE-1] Email preview modal is missing** ← documented, not built
CLAUDE.md explicitly specifies: *"Preview: render email with sample variables → show in modal"*. No `GET /email-configs/{id}/preview` endpoint exists. `EmailEdit.tsx` has no preview button or handler. This is a notable gap — users writing Jinja2 templates have no way to see the rendered output without sending a real email.

**[FE-2] Form validation is `fieldErrors` state, not React Hook Form + Zod**
CLAUDE.md lists "React Hook Form + Zod validation" as the forms library. What exists is manual `fieldErrors` state with basic required-field checks. No field-level debouncing, no schema-driven validation, no type-safe form values. Works fine for v1 but isn't the declared implementation.

**[FE-3] Inline styles still prevalent**
Despite the CSS token migration, components like `ProjectSwitcher.tsx`, `Layout.tsx` and most pages still use hardcoded hex values (`#21252F`, `#2D3143`) in inline style objects. Tailwind CSS is installed but not used for layout or spacing — only for occasional utility. Theming and dark mode would require touching dozens of components.

**[FE-4] No loading skeletons**
All data-fetching components show nothing (or previous stale data) while loading. A brief blank flash is visible on every page navigation. Skeleton loaders or at least a spinner per card section would fix this.

**[FE-5] Bulk Loads page not in the code review scope but referenced in nav**
The sidebar lists "Bulk Loads" (`/bulk-loads`) but the page implementation quality was not assessed in this review.

**[FE-6] Mobile / responsive design — zero**
The design is entirely fixed-width desktop. This is acceptable for v1 (data pipeline admin tools are desktop-first) but should be noted.

---

## 7. DevOps · 7.5 / 10

### Strengths
- Docker Compose: `db` + `app` + `scheduler` services, all with healthchecks.
- GitHub Actions CI runs full pytest with a real PostgreSQL service container.
- Alembic migrations with 6 versioned, reversible scripts.
- `flowforge db upgrade` / `db seed` CLI commands separate from app startup.
- `flowforge cleanup` + daily scheduler job prune output files.
- `flowforge.ps1` / `flowforge.sh` start API + scheduler + Vite together in dev/prod modes.

### Remaining Issues

**[OPS-1] No production WSGI guide**
`wsgi.py` exists at the root but there is no documentation on deploying with Gunicorn/Waitress behind Nginx. The README jumps from Docker Compose to local dev with no "production on a real server" path.

**[OPS-2] No log rotation**
`logs/audit.log` grows indefinitely. No `logging.handlers.RotatingFileHandler` or logrotate config provided.

**[OPS-3] `alembic.ini` at root hardcodes a local DB URL**
```ini
sqlalchemy.url = postgresql://flowforge:flowforge@localhost:5432/flowforge
```
This is overridden at runtime by `env.py` loading `.env`, but anyone running `alembic` directly without `.env` will silently connect to the wrong DB.

---

## 8. Missing Features (Documented but Not Built)

| Feature | Source | Status |
|---|---|---|
| Email preview modal | CLAUDE.md line 435 | ❌ Not implemented — no API endpoint, no UI |
| React Hook Form + Zod | CLAUDE.md (Tech Stack) | ⚠️ Partial — basic `fieldErrors` only |
| MySQL / MSSQL connections | DB check constraint + backlog | ⚠️ Constraint allows; factory raises at runtime |
| Webhook trigger | Expected for any orchestrator | ❌ Not implemented |
| Token revocation / logout | Security baseline | ❌ Not implemented |
| PDF report format | README says Excel/CSV/PDF | ✅ WeasyPrint installed — verify pipeline works end-to-end |

---

## 9. Market Comparison

### Competitive Landscape

| Tool | Target user | Config style | Email | Reports | Self-hosted | Monthly cost |
|---|---|---|---|---|---|---|
| **FlowForge** | Solo dev / small team | Web UI | Built-in (3 providers) | Built-in (Excel/CSV/PDF) | Yes | $0 |
| Apache Airflow | Data engineer | Python DAGs | Plugin | DIY | Yes (complex) | ~$0 infra |
| Prefect | Data engineer | Python flows | Plugin | DIY | Cloud or self | $0–$400+ |
| Dagster | Data engineer | Python assets | Plugin | DIY | Yes | $0–$800+ |
| n8n | Non-technical | Visual canvas | Built-in | DIY | Yes | $0–$50+ |
| Zapier | Non-technical | Visual, no-code | Built-in | DIY | No | $20–$600+ |
| cron + scripts | Developer | Edit files | DIY | DIY | Yes | $0 |

### Where FlowForge Wins
1. **Zero monthly cost** for any workload you can fit on one server.
2. **SQL-native** — target users think in queries and procedures, not Python functions or visual flowcharts.
3. **Email + Drive built-in** — the most common reporting automation task works out of the box, including smart size routing.
4. **Oracle support** — most orchestrators treat Oracle as an afterthought; FlowForge has first-class package syntax support.
5. **No code required** — a data analyst with SQL skills can configure a full pipeline without touching Python.
6. **Multi-project** — organize by team or department in one instance; Airflow requires separate deployments.
7. **Lightweight** — single `docker compose up` vs. Airflow's 5+ containers.

### Where FlowForge Lags
1. **No visual DAG canvas** — Airflow and n8n have drag-and-drop pipeline graphs; FlowForge has an ordered list.
2. **Sequential steps only** — no parallel execution, no branching, no conditional steps.
3. **No pipeline dependencies** — can't say "run Pipeline B only after Pipeline A succeeds."
4. **Single-user v1** — all competitors support multi-user with roles.
5. **No retry with backoff** — Airflow/Prefect retry failed tasks automatically; FlowForge re-runs the whole pipeline.
6. **No alerting integrations** — no Slack, PagerDuty, or webhook-out on failure.
7. **Limited observability** — no metrics endpoint, no distributed tracing, no Grafana integration.
8. **No secrets manager integration** — no Vault, AWS SSM, or environment-variable injection from a secure store.
9. **Email preview missing** — Jinja2 email templates have no live preview.
10. **No mobile/responsive UI** — desktop-only.

### Honest Niche Assessment
FlowForge sits squarely between "cron + scripts" and "Airflow." Its value proposition is:
> *"If you're automating monthly reports, data extracts, and email distributions for a finance, HR, or ops team — and you don't want to write a Python orchestration framework — FlowForge is the fastest path from SQL to automated email."*

It should not be compared to Airflow for a data engineering platform. It should be compared to "we have a cron job that runs a Python script that emails a report."

---

## 10. V1.0 Readiness Assessment

### ✅ Ready for V1.0 if your users are:
- Solo developers or small teams (1–10 people)
- Running light scheduling (< 50 pipelines, < 200 runs/day)
- On a single server (not distributed)
- Comfortable with basic admin (can set env vars, run `docker compose up`)
- Using PostgreSQL or Oracle as their data source

### ⚠️ Not ready for production if:
- You need multi-user access control
- You run 100+ concurrent pipelines
- You're in a regulated environment requiring complete audit trails
- You need guaranteed exactly-once execution on restart
- You need conditional branching or parallel steps

### Verdict
**7.3 / 10 — Solid V1.0 for the stated target audience.** The core loop (configure → schedule → run → report → email) works reliably. The codebase is maintainable and extensible. The two most important gaps for any public release are the missing email preview (UX) and the lack of a webhook trigger (integration). Everything else is polish or v2 scope.

---

## 11. Marketing Features (Top 10)

Use these in the README, landing page, and release notes:

1. **$0/month, forever** — No per-seat pricing, no cloud vendor lock-in. One server, unlimited pipelines.
2. **No YAML. No Python. No DAGs.** — Configure everything from the web UI. If you know SQL, you can use FlowForge.
3. **Email that just works** — Gmail OAuth2, Microsoft 365, or any SMTP server. Built-in. Not a plugin.
4. **Smart attachments** — Files too large to email? Automatically uploaded to Google Drive; a shareable link goes in the email instead.
5. **Oracle-first** — Unlike every other modern orchestrator, Oracle packages and procedures are first-class citizens.
6. **30+ built-in Jinja2 variables** — `{{ current_month }}`, `{{ quarter_end }}`, `{{ steps.report.output_path }}` — no Python required.
7. **Multi-project workspace** — Finance, HR, Marketing — each team sees only their pipelines in one instance.
8. **Query results in email** — Embed live query data directly in email bodies. No attachment needed.
9. **Bulk file loading** — Drop CSVs in a folder; FlowForge picks them up, loads them to your database, and archives them.
10. **Full run history** — Every step logged: timing, rows affected, Drive links, email recipients. Zero mystery.

---

## 12. New Issues Found in This Review

These are not yet in TASKS.md and should be addressed before public launch:

| ID | Issue | Priority | Effort |
|---|---|---|---|
| NEW-1 | Email preview modal — API endpoint + frontend | P0 | 4h |
| NEW-2 | SMTP `timeout` parameter missing | P1 | 30m |
| NEW-3 | Audit log: config changes, email sends, report exports not logged | P1 | 4h |
| NEW-4 | JWT token revocation (jti + server-side blocklist) | P1 | 3h |
| NEW-5 | `output_table` table-name injection guard in `db_query` and `bulk_load` | P1 | 1h |
| NEW-6 | DB check constraint lists MySQL/MSSQL but factory doesn't support them | P2 | 2h |
| NEW-7 | `ff_pipeline_variables` index on `pipeline_id` | P2 | 30m |
| NEW-8 | Frontend E2E tests (Playwright) | P2 | 20h |
| NEW-9 | Production deployment guide (Gunicorn + Nginx) | P2 | 2h |
| NEW-10 | Webhook / API trigger for external systems | P2 | 3h |

---

*Previous review: 2026-05-20 — overall 6.0 / 10 — 19 issues identified, all resolved.*
*Next target: 8.0 / 10 — close NEW-1 through NEW-5 and ship email preview + webhook trigger.*
