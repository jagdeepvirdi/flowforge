# FlowForge — Threat Model and Assurance Case

## Scope

This document describes the trust boundaries, assets, assumed threats, and mitigations for a self-hosted FlowForge deployment. It satisfies the OpenSSF Best Practices Silver `assurance_case` criterion.

---

## Assets

| Asset | Sensitivity | Location |
|---|---|---|
| Database credentials (user DBs) | Critical | `db_connections.config` (AES-256 encrypted) |
| Email provider OAuth tokens | Critical | `email_providers.config` (AES-256 encrypted) |
| AES-256 encryption key | Critical | `FLOWFORGE_SECRET_KEY` env var only — never stored in DB |
| JWT signing secret | Critical | `FLOWFORGE_JWT_SECRET` env var only |
| Pipeline output files (reports) | Sensitive | `output/` directory (optionally AES-256 encrypted at rest) |
| Audit log | Sensitive | `ff_audit_log` DB table |
| Pipeline definitions and run history | Internal | `pipelines`, `pipeline_runs` DB tables |
| User credentials | Sensitive | `ff_users` table — bcrypt hashed, never plaintext |

---

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│ Browser (untrusted)                                             │
│   └─ HTTPS → FlowForge API (Flask/Gunicorn)                    │
│                └─ JWT validated on every request               │
│                └─ IP allowlist enforced before routing         │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ FlowForge Process (trusted)                                     │
│   ├─ Jinja2 SandboxedEnvironment (untrusted template strings)  │
│   ├─ AES-256-GCM for all credential storage                    │
│   ├─ Pipeline runner (executes user-configured steps)          │
│   └─ Scheduler (APScheduler with PostgreSQL job store)         │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ External Services (semi-trusted, authenticated)                 │
│   ├─ FlowForge config DB (PostgreSQL)                          │
│   ├─ User data DBs (PostgreSQL / Oracle / MySQL / MSSQL)       │
│   ├─ Email providers (Gmail API, Graph API, SMTP+TLS)          │
│   ├─ Google Drive API                                          │
│   └─ SSH targets (paramiko, key/password auth)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Threats and Mitigations

### T1 — Template injection via Jinja2

**Scenario:** A user or pipeline variable contains `{{ ... }}` syntax that accesses internal objects or environment variables.

**Mitigations:**
- All templates rendered in `jinja2.sandbox.SandboxedEnvironment` — Python builtins and dunder attributes are blocked
- `_SafeEnv` class blocks a hardcoded list of credential env vars (`FLOWFORGE_SECRET_KEY`, `GMAIL_CLIENT_SECRET`, etc.) from being accessed via `{{ env.VAR }}`
- Optional `FLOWFORGE_TEMPLATE_ENV_VARS` allowlist mode — when set, only explicitly listed env vars are accessible
- `render_sql()` logs a warning when secret pipeline variables appear in SQL templates and recommends bind parameters

### T2 — Credential exposure from database

**Scenario:** The FlowForge config database is accessed by an unauthorised party.

**Mitigations:**
- All `db_connections.config` and `email_providers.config` JSONB columns are AES-256-GCM encrypted at application level before storage
- The decryption key (`FLOWFORGE_SECRET_KEY`) is never stored in the database — it must be provided via environment variable
- Losing `FLOWFORGE_SECRET_KEY` makes all stored credentials unrecoverable (by design)

### T3 — Unauthenticated API access

**Scenario:** API endpoints are called without valid credentials.

**Mitigations:**
- All API routes (except `/auth/login`, `/auth/password-reset/*`, `/auth/sso/*`) require a valid JWT Bearer token
- JWTs are short-lived and signed with `FLOWFORGE_JWT_SECRET`
- Failed login attempts are rate-limited (`flask-limiter`)
- Optional IP allowlist (`FLOWFORGE_ALLOWED_IPS`) rejects requests from non-listed CIDR ranges before any routing

### T4 — Privilege escalation via RBAC bypass

**Scenario:** A non-admin user accesses admin-only functionality.

**Mitigations:**
- Role check decorator applied to all admin routes (`@require_role('admin')`)
- RBAC enforcement is in `auth.py` middleware, not individual route handlers
- Role stored in JWT payload — cannot be changed without re-authentication
- Non-admin users are further scoped by `ff_project_members` project membership — a non-admin
  cannot see or edit a pipeline, report, email config, or recipient group in a project they don't
  belong to, even with a valid editor/viewer JWT; admins bypass project scoping everywhere

### T5 — Supply chain compromise

**Scenario:** A malicious package is installed as a dependency.

**Mitigations:**
- All Python dependencies pinned to exact versions with SHA-256 hashes in `requirements.txt`
- `pip install --require-hashes -r requirements.txt` in Docker builds — pip refuses to install if any hash mismatches
- `pip-audit` runs on every CI push and PR — fails the build on any known CVE
- `npm audit --audit-level=high` runs on every frontend CI push
- TruffleHog secrets scan on every push (`.github/workflows/secrets-scan.yml`)
- Dependabot configured for automated dependency updates

### T6 — SQL injection via pipeline queries

**Scenario:** A maliciously crafted SQL query in a `db_query` or `report` step exfiltrates or modifies data.

**Mitigations:**
- FlowForge does not construct SQL from user inputs at runtime — queries are authored by administrators and stored in `report_configs`
- Jinja2 variable interpolation in SQL templates is logged as a warning when secret variables are used (`render_sql()`)
- The principle of least privilege applies: DB connection credentials should be scoped to read-only where possible (documented in `docs/connections.md`)

### T7 — Report file access

**Scenario:** Generated report files are accessed by unauthorised parties.

**Mitigations:**
- Report files are stored in the `output/` directory, which should not be web-accessible
- Optional AES-256-GCM encryption at rest via `FLOWFORGE_ENCRYPT_OUTPUT=true`
- Download endpoints (`/api/runs/{id}/download/{filename}`) require authentication and validate that the file belongs to a run the user can access

### T8 — MFA bypass / account takeover

**Scenario:** An attacker who has obtained a user's password attempts to bypass the second authentication factor, or to strip MFA from the account entirely.

**Mitigations:**
- MFA (TOTP, RFC 6238, via `pyotp`) is opt-in per user; enrollment requires confirming a valid TOTP code before it activates (`flowforge/api/routes/mfa.py`)
- Login for an MFA-enabled user returns a short-lived MFA challenge token, not a full session JWT — a full JWT is only issued after `/auth/mfa/verify` confirms a valid TOTP code or a single-use backup code
- 10 one-time backup codes are generated at enrollment and stored AES-256-GCM encrypted; each is consumed on use
- Disabling MFA requires re-entering the account password, not just an active session
- SSO (Google OAuth2 / Microsoft MSAL / SAML 2.0) is a separate, email-based account-linking path with its own mitigations — see [`security.md`](security.md)

### T9 — Remote command injection via `ssh_command`

**Scenario:** The `ssh_command` step executes an operator-authored command string on a remote SSH host with no sandboxing of what that command can do.

**Mitigations:**
- `ssh_command` is a deliberately powerful step type; only users with pipeline-edit access (editor/admin role, and project membership where project scoping applies) can add or modify one
- The command string is authored by an administrator/editor at config time, not derived from untrusted runtime input; `{{ variable }}` interpolation into the command goes through the same sandboxed Jinja2 environment as T1
- SSH connection credentials (`ff_ssh_connections.config`) are AES-256-GCM encrypted, same as DB and email credentials (see Assets table)
- As with DB credentials (T6), the SSH user configured for a connection should be scoped to only what the pipeline's commands need — FlowForge does not restrict or sandbox what the remote command executes once the connection is authenticated

---

## Security Invariants

The following properties must hold in all code paths:

1. `FLOWFORGE_SECRET_KEY` is never written to the database or log files
2. Jinja2 templates are always rendered in `SandboxedEnvironment`
3. Credential env vars in `_ENV_BLOCKLIST` always return `''` in template context
4. User passwords are always stored as bcrypt hashes — plaintext is never persisted
5. All external HTTPS connections verify TLS certificates (no `verify=False`)
6. JWT tokens are validated on every protected request, not just login

---

## Out of Scope

- Physical security of the host server
- Security of the end-user's browser or OS
- Security of third-party external services (Gmail, Google Drive, etc.) — FlowForge trusts their APIs
- True multi-tenant isolation (separate deployments/DBs per customer). Project-level access
  (`ff_project_members`) scopes non-admin users to the pipelines/reports/emails/recipient groups in
  projects they belong to, but this is team-workspace segmentation within one shared deployment and
  database, not hard multi-tenant isolation — admins bypass project scoping everywhere, and there is
  no per-project encryption key, network isolation, or resource quota
