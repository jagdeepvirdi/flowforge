# docs/ — Index

All documentation files in this directory and what they contain.

---

## User-Facing Guides

| File | Purpose |
|---|---|
| [getting-started.md](getting-started.md) | Full setup walkthrough: prerequisites, install, `.env` config, first pipeline, CLI reference, Gmail/Drive OAuth2 setup, Docker Compose, scheduler diagnostics |
| [step-types.md](step-types.md) | Complete config reference for every step type: `db_procedure`, `db_query`, `report`, `email`, `drive_upload`, `data_load`, `bulk_load` — with JSONB examples, field tables, and output variable docs |
| [email-providers.md](email-providers.md) | Setup guides for all three email providers: SMTP (with presets for Outlook, Yahoo, SendGrid), Microsoft 365 (Azure AD app registration + admin consent + token refresh), Gmail (OAuth2 via `flowforge setup gmail`) |
| [gmail-oauth2-setup.md](gmail-oauth2-setup.md) | Step-by-step Gmail OAuth2 credential setup in Google Cloud Console — screenshots and common errors |
| [running-the-server.md](running-the-server.md) | How to run FlowForge in dev and prod modes, manage the scheduler process, use `flowforge.ps1` / `flowforge.sh`, troubleshoot common startup errors |

---

## Operations & Development

| File | Purpose |
|---|---|
| [RUNBOOK.md](RUNBOOK.md) | Operational reference: Alembic migration workflow, DB stamp scenario (legacy DB with no migration history), startup sequence, test DB setup, production checklist |
| [manual-testing-guide.md](manual-testing-guide.md) | Step-by-step manual test checklist for verifying end-to-end flows before a release: DB connection, report preview, pipeline run, email send, scheduler trigger |

---

## Project Management

| File | Purpose |
|---|---|
| [TASKS.md](TASKS.md) | Active work and backlog. Current codebase review score (7.3/10), new issues found in 2026-05-23 review, and post-v1 feature backlog with known risks |
| [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) | Completed tasks, ordered newest-first. Full history of every feature, bug fix, and refactor with file-level detail. Sessions from initial scrub through v1.0.0 |

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
| `feature-requests/` | Extended notes and design decisions for specific features (e.g., `manual-testing-reviews.md`) |
| `screenshots/` | UI screenshots used in README and docs |

---

*Last updated: 2026-05-23*
