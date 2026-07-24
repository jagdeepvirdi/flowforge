# FlowForge Security Model

This document describes how FlowForge protects credentials, controls access, and handles incidents.

---

## Credential Encryption

All sensitive configuration — database passwords, OAuth2 tokens, SMTP credentials — is stored **encrypted at rest** in the `config` JSONB column of `ff_db_connections` and `ff_email_providers`.

**Algorithm**: AES-256-GCM via the Python `cryptography` library.

**Key**: Derived from the `FLOWFORGE_SECRET_KEY` environment variable (must be 64 hex characters — 32 bytes). The key is **never stored in the database**.

```python
# Encrypt before storing
encrypted = encrypt_config({"password": "secret"})   # → {"ct": "...", "iv": "...", "tag": "..."}

# Decrypt before use
config = decrypt_config(row.config)
```

Each encryption call generates a fresh random IV (nonce), so two encryptions of the same plaintext produce different ciphertexts.

### Key Rotation

To rotate `FLOWFORGE_SECRET_KEY` without data loss:

1. Export all connections and providers via `GET /api/connections` and `GET /api/providers` (credentials are **not** included in API responses — they are masked).
2. Use the `flowforge` CLI or the admin UI to re-enter credentials under the new key after the key change.
3. Update `FLOWFORGE_SECRET_KEY` in your environment / secrets manager.
4. Restart the API and scheduler processes.

> There is currently no automated re-encryption migration. All stored secrets must be re-entered when rotating the key.

---

## Authentication — JWT

FlowForge uses **JSON Web Tokens** (JWT) for session authentication.

| Property | Value |
|---|---|
| Signing algorithm | HS256 |
| Signing secret | `FLOWFORGE_JWT_SECRET` env var (separate from `FLOWFORGE_SECRET_KEY`) |
| Token lifetime | 24 hours |
| Revocation | Server-side blocklist (`ff_token_blocklist`) — `POST /api/auth/logout` |

### Token Revocation

Each token carries a `jti` (JWT ID) claim — a UUID generated at login. On logout, the `jti` is written to `ff_token_blocklist` with its expiry timestamp. Subsequent requests carrying the same token are rejected with `401`.

Expired blocklist entries are pruned daily by the scheduler cleanup job.

### Login Rate Limiting

`POST /api/auth/login` is rate-limited to **10 requests per minute per IP** via `flask-limiter`. Manual pipeline triggers are limited to **10 per minute**.

---

## Multi-Factor Authentication (MFA)

FlowForge supports TOTP-based MFA (RFC 6238, via `pyotp`), opt-in per user (`flowforge/api/routes/mfa.py`).

| Property | Value |
|---|---|
| Enrollment | `POST /api/auth/mfa/enroll` generates a secret + provisioning URI; `POST /api/auth/mfa/confirm` activates it only after a valid TOTP code is entered |
| Login flow | An MFA-enabled user's `POST /api/auth/login` returns a short-lived MFA **challenge token**, not a session JWT. `POST /api/auth/mfa/verify` (TOTP code) or `POST /api/auth/mfa/verify-backup` (backup code) exchanges the challenge token for a full JWT |
| Backup codes | 10 single-use codes generated at enrollment (`XXXX-XXXX` format), returned once, stored AES-256-GCM encrypted; each is consumed on use |
| Secret storage | `ff_users.mfa_secret` — AES-256-GCM encrypted, same key as connection/provider credentials |
| Disabling MFA | `POST /api/auth/mfa/disable` requires re-entering the account password — an active session alone is not sufficient |

MFA enrollment and disable events are written to the audit log (`MFA_ENABLED`, `MFA_DISABLED`, `MFA_BACKUP_CODE_USED`).

---

## Single Sign-On (SSO)

FlowForge supports three SSO paths, all via email-based account linking (`flowforge/api/routes/sso.py`):

| Provider | Flow | Config |
|---|---|---|
| Google | OAuth2 authorization code | `GOOGLE_SSO_CLIENT_ID`, `GOOGLE_SSO_CLIENT_SECRET` |
| Microsoft | OAuth2 via MSAL | `MICROSOFT_SSO_TENANT_ID`, `MICROSOFT_SSO_CLIENT_ID`, `MICROSOFT_SSO_CLIENT_SECRET` |
| SAML 2.0 (enterprise IdP — Okta, Azure AD, PingFederate) | SP-initiated redirect + signed assertion POST to an ACS endpoint | `SAML_SP_ENTITY_ID`, `SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`, `SAML_IDP_X509_CERT` |

Each provider is disabled (`501`) unless its env vars are set. A CSRF `state` token is generated per login attempt and consumed exactly once on callback. New users can be auto-provisioned on first SSO login (`_auto_create()`) or must already exist, depending on configuration — no password is ever set for an SSO-only account.

---

## Access Control

### Roles

| Role | Capabilities |
|---|---|
| `admin` | Full access — pipelines, reports, email configs, connections, user management; bypasses project scoping |
| `editor` | Create and edit pipelines, reports, email configs, recipient groups, connections; cannot manage users |
| `viewer` | Read-only — view pipelines, run history, reports; cannot create, edit, run, or delete anything |

### Project Scoping

Beyond role, non-admin users are scoped to the **projects** they're a member of (`ff_project_members`). An `editor` or `viewer` can only see and act on pipelines, reports, email configs, and recipient groups that belong to a project they've been added to — not every resource in the deployment. New users and project creators are auto-added to the relevant project. Admins see and act on every project regardless of membership. This is workspace-level segmentation within one shared deployment/database, not hard multi-tenancy — see [`threat-model.md`](threat-model.md#out-of-scope) for the distinction.

### Enforcement

- **API layer**: the `@require_role(role)` decorator on every write route reads `g.current_user_role` (injected by `require_auth` JWT middleware) and returns `403 Forbidden` for insufficient roles. Project-scoped routes additionally check `ff_project_members` before returning or mutating a resource.
- **Frontend layer**: write controls (Create, Edit, Delete, Run, Clone buttons) are hidden for `viewer` and non-`admin` roles via the `useCurrentUser()` hook.

Both layers are required — the API is the authoritative enforcement point; the frontend gating is UX convenience only.

---

## Webhook / API Trigger Tokens

Pipelines can be triggered via HTTP using scoped tokens generated in the Pipeline Builder. Each token is:

- **Scoped** — tied to a single pipeline; cannot trigger any other resource
- **Revocable** — individual tokens can be revoked without affecting other tokens or the pipeline itself
- **Audited** — every webhook trigger is recorded in the audit log with timestamp and pipeline name
- **Never expiring by default** — revoke explicitly when a token is no longer needed

Token values are stored as bcrypt hashes in the database — the plaintext token is shown only once at creation and is not recoverable. Treat tokens like passwords: store them in your CI/CD secrets manager, not in code.

---

## Audit Log

Every significant action is written to `logs/audit.log` (rotating `RotatingFileHandler`, 10 MB × 5 backups).

**Events logged**: login success / failure (with IP), pipeline STARTED / SUCCESS / FAILED, config changes (connection create/update/delete, provider create/update/delete), webhook trigger, user create/delete.

Each entry includes: ISO-8601 timestamp, event type, resource name, user (`by=<username>`), and user ID.

### Structured JSON Output

Set `FLOWFORGE_AUDIT_STDOUT=true` to emit audit events as JSON lines to stdout — suitable for ingestion by Datadog, Loki, or any log aggregation system.

### Retention

The file handler retains 5 rotated backups (~50 MB total). For long-term retention, consume the structured stdout stream and forward to your log platform.

---

## Template Sandbox

Pipeline step configs use Jinja2 templates for variable substitution. FlowForge uses **`SandboxedEnvironment`** — arbitrary Python execution (`__import__`, attribute access to internals) is blocked.

**Env var access** in templates is controlled by `FLOWFORGE_TEMPLATE_ENV_VARS`:
- If set (e.g. `FLOWFORGE_TEMPLATE_ENV_VARS=REPORT_DIR,DB_SCHEMA`), only the listed variables are accessible via `{{ env.VAR_NAME }}`.
- If unset, all env vars are accessible except a hardcoded blocklist (`FLOWFORGE_SECRET_KEY`, `FLOWFORGE_JWT_SECRET`, `*_CLIENT_SECRET`, `*_PASSWORD`, etc.).

---

## Input Validation

- **Procedure / table names**: validated against `^[a-zA-Z_][a-zA-Z0-9_.]*$` before SQL construction — blocks identifier injection.
- **CSV delimiter**: must be exactly one printable non-quote, non-backslash character.
- **File download paths**: resolved with `Path.resolve()` and checked to be within `FLOWFORGE_OUTPUT_DIR` — blocks directory traversal.
- **Excel template paths**: resolved and checked to be within `FLOWFORGE_TEMPLATE_DIR`.
- **Request body size**: capped at 16 MB (`MAX_CONTENT_LENGTH`).
- **Field lengths**: enforced by `flowforge/api/validators.py` on all create/update endpoints.

---

## Transport Security

FlowForge does not terminate TLS itself. Deploy behind Nginx or a load balancer with HTTPS. The Docker Compose setup exposes port 80 via Nginx — add a TLS terminator (e.g. Certbot + Nginx, Cloudflare Tunnel) in front for production.

Set `FLOWFORGE_CORS_ORIGIN` to your frontend origin in production. Leaving it unset on a production deployment logs a startup warning.

**Reverse proxy trust (`FLOWFORGE_TRUSTED_PROXIES`):** When Nginx or an ALB sits in front, set `FLOWFORGE_TRUSTED_PROXIES=1` in `.env`. This tells Flask to trust the `X-Forwarded-For` header so rate limiting and audit log entries record the real client IP rather than the proxy's `127.0.0.1`. Without this, all login attempts appear to originate from the same IP, making per-IP rate limiting ineffective. Do **not** set this flag when the app is exposed directly to the internet without a proxy.

---

## Reporting a Vulnerability

See [SECURITY.md](../SECURITY.md) at the repository root for supported versions and the disclosure process.
