# FlowForge Roadmap

## Current Release: v1.0 (Stabilisation)

**Goal:** Public GitHub release — stable, tested, `docker compose up` works, badges and docs polished.

| Area | Status |
|---|---|
| Core pipeline engine (DB procedures, queries, reports, email, Drive) | ✅ Complete |
| Email providers: Gmail, Microsoft 365, SMTP, SendGrid, AWS SES, Mailgun | ✅ Complete |
| Notification steps: Slack, Teams, Telegram | ✅ Complete |
| Database connections: PostgreSQL, Oracle, MySQL, MSSQL, ODBC | ✅ Complete |
| SSH command + DB health check steps | ✅ Complete |
| MFA (TOTP), SSO (Google/Microsoft), IP allowlisting | ✅ Complete |
| GDPR data export and deletion | ✅ Complete |
| Audit log with retention policy | ✅ Complete |
| Report column formatting, parallel steps, pipeline dependencies | ✅ Complete |
| Environment promotion workflow | ✅ Complete |
| OpenSSF Scorecard ≥ 8.0 | 🔄 In progress |
| PyPI package publication | 🔄 In progress |

## v2.0 — Production Hardening

**Goal:** Production-ready for teams. Starts after v1.0 ships.

- Multi-user authentication with role-based access control
- Distributed Redis-backed concurrency lock (horizontal scale)
- Team-scoped project membership (`ff_project_members`)
- Gunicorn + Nginx deployment guide (docs)
- Prometheus metrics endpoint (`/api/metrics`)
- Celery Flower monitoring dashboard

## v3.0 — Ecosystem Expansion

**Goal:** Community-driven connectors and pipeline DAGs. No fixed date.

- Snowflake, BigQuery, Redshift connectors
- AWS S3 / Azure Blob upload step
- Visual pipeline canvas (drag-and-drop DAG editor)
- Plugin system for community step types
- SAML support (Okta, Azure AD, Ping)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to propose features or report bugs. Open a GitHub Issue before starting significant work.
