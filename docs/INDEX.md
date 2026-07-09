# docs/ — Index

All documentation files in this directory and what they contain.

---

## User-Facing Guides

| File | Purpose |
|---|---|
| [getting-started.md](getting-started.md) | Full setup walkthrough: prerequisites, install, `.env` config, first pipeline, CLI reference, Gmail/Drive OAuth2 setup, OneDrive setup, AI features (Ollama/Claude/Gemini), scheduler diagnostics |
| [deployment.md](deployment.md) | Production deployment guide: Docker Compose (recommended) and bare-metal Gunicorn + Nginx + systemd on Ubuntu/Debian, TLS with Let's Encrypt, upgrade procedure |
| [step-types.md](step-types.md) | Complete config reference for every step type: `db_procedure`, `db_query`, `report`, `email`, `data_load`, `bulk_load`, `drive_upload`, `onedrive_upload`, `s3_upload`, `azure_blob_upload`, `ai_analyze`, `ssh_command`, `db_health_check`, `ssh_health_check`, `data_report`, `sftp_transfer`, `notification` — with JSONB examples, field tables, output variable docs, and full Jinja2 variable reference |
| [email-providers.md](email-providers.md) | Setup guides for all three email providers: SMTP (with presets for Outlook, Yahoo, SendGrid), Microsoft 365 (Azure AD app registration + admin consent + token refresh), Gmail (OAuth2 via `flowforge setup gmail`) |
| [gmail-oauth2-setup.md](gmail-oauth2-setup.md) | Step-by-step Gmail OAuth2 credential setup in Google Cloud Console — screenshots and common errors |
| [running-the-server.md](running-the-server.md) | How to run FlowForge in dev and prod modes, manage the scheduler process, use `flowforge.ps1` / `flowforge.sh`, troubleshoot common startup errors |
| [FAQ.md](FAQ.md) | Answers to specific "what is X" / "how does Y behave" questions not spelled out elsewhere — pipeline canvas, webhook triggers, upstream dependencies and cycle detection, etc. |

---

## Operations & Development

| File | Purpose |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Operational reference: Alembic migration workflow, DB stamp scenario (legacy DB with no migration history), startup sequence, full CLI reference, production checklist |
| [testing.md](testing.md) | Complete test runbook: Layer 1 unit tests, Layer 2 integration tests (test DB setup, env vars), Layer 3 frontend Vitest, Layer 4 Playwright E2E, Layer 5 API smoke test — copy-paste ready commands for all five layers |
| [security.md](security.md) | Security model: AES-256 credential encryption, JWT auth with token blocklist, multi-user roles (admin/editor/viewer), webhook token security, audit log, Jinja2 sandbox, input validation, CORS, proxy trust |
| [manual-testing-guide.md](manual-testing-guide.md) | Step-by-step manual test checklist for verifying end-to-end flows before a release: connections, bulk load, DB query, report generation, email (Gmail + M365), Drive/OneDrive, SFTP, AI features, scheduling |
| [plugins.md](plugins.md) | How to write a community plugin step type — drop a `BaseStep` subclass into `FLOWFORGE_PLUGIN_DIR` without forking FlowForge |
| [threat-model.md](threat-model.md) | Trust boundaries, assets, threats, and mitigations for a self-hosted deployment — satisfies OpenSSF Best Practices Silver `assurance_case` |
| [data-flow.md](data-flow.md) | Data inventory, encryption, retention, and GDPR rights reference — supports SOC 2 / GDPR / HIPAA assessments |
| [SONAR_ISSUES.md](SONAR_ISSUES.md) | Point-in-time snapshot of open SonarCloud/Scorecard findings and their resolution status — see `docs/TASKS.md` Phase 10 for current state |

---

## Project Management

| File | Purpose |
|---|---|
| [TASKS.md](TASKS.md) | Active work and backlog — consolidated pending items (Phase 10), codebase review score history, and Scorecard/SonarCloud remediation status. Source of truth for what's actually shipped |
| [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) | Completed tasks, ordered newest-first. Full history of every feature, bug fix, and refactor with file-level detail. Sessions from initial scrub through v1.0.0 |

---

## Strategy & Product

| File | Purpose |
|---|---|
| [USE_CASE.md](USE_CASE.md) | Who FlowForge is for, real-world use cases by industry (Finance, HR, Ops, IT, SaaS), comparison vs Airflow/Prefect/n8n/Zapier, the Oracle advantage, honest limitations, and sizing guide |

---

## Code Review & Analysis

| File | Purpose |
|---|---|
| [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md) | Brutally honest scored review of the entire codebase. Covers architecture, code quality, database, security, tests, frontend, DevOps. Includes score history, market comparison, V1.0 readiness verdict, top marketing features, and new issues to fix |
| [GEMINI_REVIEW.md](GEMINI_REVIEW.md) | Independent codebase review by Gemini — alternative perspective on the same codebase |

---

## Local / Private

| File | Purpose |
|---|---|
| [credentials.local.md](credentials.local.md) | Local dev credentials (PostgreSQL URLs, test passwords). **Gitignored — never committed.** |

---

## Sub-directories

| Path | Purpose |
|---|---|
| `scenarios/` | End-to-end pipeline setup guides for real-world use cases |
| `scenarios/health-monitoring.md` | Daily infrastructure health monitoring — SSH metrics + DB health + Excel report + conditional alerts |
| `scenarios/log-extraction.md` | Remote script & log processing — SSH run script + DB report + email with log + Excel attached |
| `feature-requests/` | Extended notes and design decisions for specific features (e.g., `manual-testing-reviews.md`) |
| `screenshots/` | UI screenshots used in README and docs |

---

*Last updated: 2026-07-09*
