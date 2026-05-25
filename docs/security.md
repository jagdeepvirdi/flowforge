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

## Access Control

### Roles

| Role | Capabilities |
|---|---|
| `admin` | Full access — pipelines, reports, email configs, connections, user management |
| `editor` | Create and edit pipelines, reports, email configs, recipient groups, connections; cannot manage users |
| `viewer` | Read-only — view pipelines, run history, reports; cannot create, edit, run, or delete anything |

### Enforcement

- **API layer**: the `@require_role(role)` decorator on every write route reads `g.current_user_role` (injected by `require_auth` JWT middleware) and returns `403 Forbidden` for insufficient roles.
- **Frontend layer**: write controls (Create, Edit, Delete, Run, Clone buttons) are hidden for `viewer` and non-`admin` roles via the `useCurrentUser()` hook.

Both layers are required — the API is the authoritative enforcement point; the frontend gating is UX convenience only.

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

---

## Reporting a Vulnerability

See [SECURITY.md](../SECURITY.md) at the repository root for supported versions and the disclosure process.
