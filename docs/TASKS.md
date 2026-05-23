# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 9.5 / 10 (updated 2026-05-23)
## Codebase Review Score: 7.3 / 10 (reviewed 2026-05-23 — see CODEBASE_REVIEW.md)

| Dimension | 2026-05-20 | 2026-05-23 |
|---|---|---|
| Architecture | 6.5 | 7.0 (+0.5) |
| Code Quality | 6.0 | 7.0 (+1.0) |
| Database | 6.5 | 8.0 (+1.5) |
| Security | 5.5 | 7.5 (+2.0) |
| Tests | 6.0 | 7.5 (+1.5) |
| Frontend | 5.5 | 6.5 (+1.0) |
| DevOps | 6.0 | 7.5 (+1.5) |
| **Overall** | **6.0** | **7.3 (+1.3)** |

---

## New Issues — Found in 2026-05-23 Review

*Identified in the latest codebase review. Address before public launch.*

- [ ] **[NEW-1] Email preview modal** — API endpoint `GET /email-configs/{id}/preview` + preview button in `EmailEdit.tsx`. Documented in CLAUDE.md; never built. P0.
- [ ] **[NEW-2] SMTP send timeout** — `smtplib.SMTP(host, port, timeout=30)` missing in `smtp.py`; slow servers block pipeline threads indefinitely. P1.
- [ ] **[NEW-3] Audit log completeness** — `flowforge/audit.py` logs login and pipeline events but NOT config changes (connections, providers), email sends, or report exports. P1.
- [ ] **[NEW-4] JWT token revocation** — stolen token valid 24h; add `jti` claim + server-side blocklist + `/auth/logout` endpoint. P1.
- [ ] **[NEW-5] Table-name injection guard** — `db_query.py` and `bulk_load.py` interpolate `output_table` into raw SQL; validate against safe identifier regex `^[a-zA-Z_][a-zA-Z0-9_.]*$`. P1.
- [ ] **[NEW-6] DB factory vs check constraint mismatch** — constraint allows `mysql`, `mssql`, `snowflake` but factory raises at runtime; either remove from constraint or implement. P2.
- [ ] **[NEW-7] Index on `ff_pipeline_variables(pipeline_id)`** — full table scan on every pipeline run. P2.
- [ ] **[NEW-8] Frontend E2E tests (Playwright)** — no coverage of the full login → create → run → history journey. P2.
- [ ] **[NEW-9] Production deployment guide** — `wsgi.py` exists but no Gunicorn + Nginx setup documented. P2.
- [ ] **[NEW-10] Webhook / API trigger** — `POST /pipelines/{id}/trigger?token=...` for external system integration. P2.

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
- [x] **Pipeline variables** — Variables card in Pipeline Builder; key/value/secret pairs; `{{ var_key }}` and `{{ vars.var_key }}` in all step configs; secrets encrypted at rest and masked in UI. *(Shipped 2026-05-23)*
- [x] **Bulk file loader step (`bulk_load`)** — Directory scanning, `file_prefix`/`file_prefix_exclude`, PostgreSQL `COPY FROM STDIN`, chunked Python fallback, footer row stripping, archive-after-load, `on_no_files` behaviour, Bulk Loads UI page. *(Shipped 2026-05-23)*

### Platform
- [ ] Multi-user auth with roles (v2)
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)
- [ ] AI analyze step — `flowforge/steps/ai_analyze.py`, Ollama/Claude routing, `{{ ai_summary }}` variable (v2)

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Resolved — migrated to `python-oracledb` (thin mode, pure Python, no Instant Client needed) |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
