# FlowForge Roadmap

> **Source of truth:** [`docs/TASKS.md`](docs/TASKS.md) is the authoritative, continuously-updated
> tracker of what's actually shipped (verified against the code, with dates). This file is a
> high-level summary derived from it for newcomers — if the two ever disagree, trust TASKS.md
> and treat this file as stale until updated. Last reconciled: 2026-07-09.

## Shipped

Delivered and verified in the codebase (dates below are when each landed; see TASKS.md
for exact commits/detail).

| Area | Status |
|---|---|
| Core pipeline engine (DB procedures, queries, reports, email, Drive) | ✅ |
| Email providers: Gmail, Microsoft 365, SMTP, SendGrid, AWS SES, Mailgun | ✅ |
| Notification steps: Slack, Teams, Telegram | ✅ *(2026-05-30)* |
| Database connections: PostgreSQL, Oracle, MySQL, MSSQL, ODBC, Snowflake, BigQuery, Redshift | ✅ *(2026-05-30 / 2026-07-01)* |
| AWS S3 / Azure Blob / OneDrive upload steps | ✅ *(2026-07-01)* |
| SSH command + DB health check steps | ✅ |
| Multi-user auth with role-based access control | ✅ |
| Team-scoped project membership (`ff_project_members`) | ✅ *(2026-07-01)* |
| Distributed Redis-backed concurrency lock (horizontal scale) | ✅ *(2026-07-01)* |
| Plugin system for community step types | ✅ *(2026-07-01)* |
| MFA (TOTP), SSO (Google/Microsoft), SAML, IP allowlisting | ✅ |
| GDPR data export and deletion | ✅ |
| Audit log with retention policy | ✅ |
| Report column formatting, parallel steps, pipeline dependencies | ✅ |
| Environment promotion workflow | ✅ |
| Gunicorn + Nginx deployment guide (docs) | ✅ |
| Prometheus metrics endpoint (`/api/metrics`) | ✅ |
| Celery Flower monitoring dashboard | ✅ |
| Visual pipeline canvas (list/graph toggle, drag-to-reorder & group, execution-order-accurate layout) | ✅ *(2026-07-09)* |

This is well past what the original "v1.0 / v2.0 / v3.0" gating implied — v2.0 and v3.0
backlog items shipped ahead of the v1.0 GTM checklist being finished. Version-numbered
milestones below are kept as loose, informal buckets, not release gates.

## In progress

- OpenSSF Scorecard ≥ 8.0 — currently 6.5/10; see TASKS.md Phase 10 for the specific
  checks still open (several are structurally hard for a solo maintainer — e.g. Code-Review
  requires a second approver, which GitHub blocks for self-authored PRs)
- PyPI package publication — `publish.yml` workflow exists; publication status itself isn't
  tracked anywhere else, so treat as unverified until confirmed
- Go-to-market checklist (demo assets, ProductHunt, Reddit, awesome-lists, LinkedIn) — see
  TASKS.md Phase 10

## Not yet built

- **Arbitrary step-to-step DAG editing** — the canvas view shipped 2026-07-09 (TASKS.md Phase
  14, Option A) covers visualizing/editing the existing sequential + parallel-group model, but
  true Airflow-style freeform dependency edges and branching (Option B) would require rewriting
  the runner's execution model; scoped as a separate, larger initiative in TASKS.md Phase 14.2.
- Fuzzing registered with OSS-Fuzz (Hypothesis tests exist but aren't recognized by Scorecard)
- Cosign-signed releases

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to propose features or report bugs. Open a GitHub Issue before starting significant work.
