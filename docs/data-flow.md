# FlowForge — Data Flow & Compliance Reference

This document describes what personal and sensitive data FlowForge handles,
where it is stored, and where it is transmitted. It is intended to support
SOC 2, GDPR, HIPAA, and other regulated-environment assessments.

---

## What Data FlowForge Touches

| Data Type | Source | Purpose | Where Stored | Transmitted To |
|---|---|---|---|---|
| **Database credentials** | Admin (UI/env) | Connect to user data sources | `ff_db_connections.config` (AES-256 encrypted) | Target DB only |
| **Email credentials** | Admin (UI/env) | Send emails | `ff_email_providers.config` (AES-256 encrypted) | Gmail / M365 / SMTP |
| **SSH credentials** | Admin (UI) | Remote command execution | `ff_ssh_connections.config` (AES-256 encrypted) | Target SSH host only |
| **Report query results** | User databases | Generate Excel/CSV/PDF reports | `FLOWFORGE_OUTPUT_DIR` (disk) | Email recipients / Google Drive |
| **Email addresses** | Admin (UI) | Email delivery | `ff_recipient_groups.addresses` (plain text) | Email provider |
| **Pipeline run history** | System | Observability | `ff_pipeline_runs` + `ff_step_runs` | None |
| **Audit log** | System | Security / compliance | `ff_audit_log` + `logs/audit.log` | None (optional: stdout) |
| **User accounts** | Admin (UI) | Authentication | `ff_users` (password bcrypt-hashed) | None |
| **JWT tokens** | Login flow | Session auth | Browser localStorage | Bearer header on each API call |
| **TOTP secret** | User (MFA setup) | MFA second factor | `ff_users.mfa_secret` (AES-256 encrypted) | Never |
| **SSO email** | Google / Microsoft / SAML IdP | Account linking | `ff_users.sso_email` | SSO provider during login |

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FlowForge Runtime                               │
│                                                                              │
│  Browser ──JWT──► Flask API ──SQLAlchemy──► PostgreSQL (ff_* tables)        │
│                       │                                                       │
│                       ├── Runner ──► User DB (Oracle / PG / MySQL)          │
│                       │                  │ query results                     │
│                       │                  ▼                                   │
│                       ├── Report Step ──► output/ (disk, optionally .enc)   │
│                       │                  │                                   │
│                       ├── Email Step ──► Gmail API / MS Graph / SMTP        │
│                       │                  │ (with report attachment or link)  │
│                       ├── Drive Step ──► Google Drive API                   │
│                       │                                                       │
│                       └── SSH Step ──► Remote Host (stdout → output/)       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Encryption

| What | How | Key |
|---|---|---|
| DB connection credentials | AES-256-GCM | `FLOWFORGE_SECRET_KEY` (env) |
| Email provider credentials | AES-256-GCM | `FLOWFORGE_SECRET_KEY` (env) |
| SSH connection credentials | AES-256-GCM | `FLOWFORGE_SECRET_KEY` (env) |
| TOTP secret | AES-256-GCM | `FLOWFORGE_SECRET_KEY` (env) |
| MFA backup codes | AES-256-GCM | `FLOWFORGE_SECRET_KEY` (env) |
| Report output files | AES-256-GCM (optional) | `FLOWFORGE_SECRET_KEY` (env) |
| User passwords | bcrypt (one-way) | N/A — no decryption needed |

**Encryption key management:**
- `FLOWFORGE_SECRET_KEY` must be a 32-byte (64 hex character) random key.
- Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- Store in a secrets manager (AWS Secrets Manager, HashiCorp Vault, Kubernetes Secret).
- Never commit the key to source control.
- JWT tokens use a **separate** key (`FLOWFORGE_JWT_SECRET`) per SEC-2.

---

## Data Retention

| Data | Retention | Config |
|---|---|---|
| Pipeline runs + step logs | 90 days (configurable) | `FLOWFORGE_RUN_RETENTION_DAYS` |
| Audit log entries | 90 days (configurable) | `FLOWFORGE_AUDIT_RETENTION_DAYS` |
| Report output files | 7 days (configurable) | `FLOWFORGE_OUTPUT_TTL_DAYS` |
| Audit log file (disk) | Rotated at 10 MB, 5 backups | `FLOWFORGE_LOG_DIR` |

---

## Data Residency

FlowForge is self-hosted. All data remains in the operator's infrastructure
unless explicitly configured to transmit to:

- **Gmail API** / **Microsoft Graph** — for email delivery
- **Google Drive API** — for large attachment storage
- **AWS S3** / **Azure Blob Storage** — if a pipeline uses an `s3_upload` or `azure_blob_upload` step
- **Snowflake / BigQuery / Amazon Redshift** — if a pipeline's `db_procedure`/`db_query` steps reference a connection of that type (query result rows leave FlowForge's infrastructure for the cloud data warehouse's, same as any other configured DB connection)
- **Google / Microsoft OAuth2** — for SSO login (redirects only; no data sent to FlowForge from the IdP beyond email + name)
- **SAML 2.0 IdP** (Okta / Azure AD / PingFederate) — for enterprise SSO login (browser redirect + POST of a signed assertion; no data sent to FlowForge beyond the NameID/email in the assertion)
- **Ollama** — local AI; data stays on your machine
- **Claude API (Anthropic)** — only if `USE_CLAUDE=true` and `ANTHROPIC_API_KEY` is set; query result rows are sent to Anthropic for analysis

---

## GDPR Compliance

### Right to Access (Article 15)
`GET /api/admin/users/{id}/export`
Returns all personal data: user profile, audit log entries, pipeline run history.
Admin-only endpoint; requires `admin` role JWT.

### Right to Erasure (Article 17)
`DELETE /api/admin/users/{id}?purge=true`
Deletes the user record and anonymises all linked audit log entries (username replaced
with `[deleted:{uuid-prefix}]`, IP address removed, user_id set to NULL).
Pipeline run history records are not deleted — they are statistical, not personal.

### Right to Portability
Export is returned as structured JSON (see Right to Access above).

---

## Authentication Security

| Feature | Detail |
|---|---|
| Password hashing | bcrypt (12 rounds) |
| JWT algorithm | HS256 (configurable) |
| JWT expiry | 24 hours (configurable via `JWT_EXPIRY_HOURS`) |
| Token revocation | `ff_token_blocklist` table (on logout) |
| MFA | TOTP (RFC 6238) — `pyotp` — 30-second window |
| MFA backup codes | 10 one-time codes (XXXX-XXXX format), stored encrypted |
| SSO | Google OAuth2 / Microsoft MSAL / SAML 2.0 (enterprise IdP) — email-based account linking |
| Rate limiting | 10 login attempts / minute (`flask-limiter`) |
| IP allowlisting | `FLOWFORGE_ALLOWED_IPS` (CIDR ranges) |
| CORS | Restricted to `FLOWFORGE_CORS_ORIGIN` in production |
| Proxy trust | `FLOWFORGE_TRUSTED_PROXIES` (ProxyFix hops) |
| Secrets scanning | TruffleHog in CI on every push and PR |

---

## Audit Log

Every security-relevant action is written to both `ff_audit_log` (DB) and
`logs/audit.log` (file, 10 MB rotating). Captured events include:

`LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`,
`PIPELINE_CFG_CREATED`, `PIPELINE_CFG_UPDATED`, `PIPELINE_CFG_DELETED`,
`PIPELINE_SUCCESS`, `PIPELINE_FAILED`,
`CONNECTION_CREATED`, `CONNECTION_UPDATED`, `CONNECTION_DELETED`,
`EMAIL_SENT`, `REPORT_EXPORTED`,
`USER_CREATED`, `USER_UPDATED`, `USER_DELETED`,
`MFA_ENABLED`, `MFA_DISABLED`, `MFA_BACKUP_CODE_USED`,
`SSO_USER_CREATED`, `WEBHOOK_TRIGGER`

Audit log UI: `/settings/audit` (admin only) — filterable, exportable as CSV.

---

## Network Ports (default)

| Service | Port | Protocol |
|---|---|---|
| FlowForge web + API | 5000 | HTTP (use TLS termination at nginx/ALB) |
| PostgreSQL (FlowForge config) | 5432 | TCP |
| Redis (Celery queue, optional) | 6379 | TCP |
| Flower monitoring (optional) | 5555 | HTTP |

**TLS:** FlowForge does not terminate TLS itself. Deploy behind nginx or an
AWS ALB with a valid certificate. See `RUNBOOK.md §4a` for nginx config.
