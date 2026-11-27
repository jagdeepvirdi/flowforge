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

MFA enrollment, disable and backup-code events (`MFA_ENABLED`, `MFA_DISABLED`, `MFA_BACKUP_CODE_USED`) and password-reset events (`PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`) are written to the audit log under exactly these names.

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

### Token lookup table (`ff_token_map`)

Subscriber identifiers are pseudonymised with keyed HMAC tokens (`flowforge/tokenization.py`). The reverse lookup is **opt-in**: with `token_store: true` on a `reconcile` step, the *sampled* identifiers (at most `sample_size` per category per run) are saved so an admin can turn a finding back into a subscriber. Treat that table as personal data:

- **Encrypted at rest.** Only the AES-GCM ciphertext (under `FLOWFORGE_SECRET_KEY`) holds the identifier; the token and kind are plain. Someone with database access *and* the secret key can read it.
- **Reveal is admin-only and audited.** `POST /api/tokens/reveal` (1–100 tokens) requires the `admin` role, is not cacheable, and writes a `TOKEN_REVEALED` audit entry with the counts and the tokens, never the values.
- **Temporary.** Mappings are deleted `FLOWFORGE_TOKEN_MAP_RETENTION_DAYS` (default 30; `0` = keep forever) after they were last seen, by the daily maintenance job; `flowforge tokens purge --older-than-days N | --all` deletes on demand. Include the table in any data-subject erasure process.
- **Key rotation.** Changing `FLOWFORGE_SECRET_KEY` makes stored ciphertext unreadable (reveal reports `undecryptable`); there is no re-encryption tool yet. Changing the tokenization key changes all future tokens, so old rows stop matching and age out.
- **Not a control against an insider with the key.** Pseudonymisation reduces exposure in emails, run history and exports; it does not make the data anonymous.

### Integrity — what is and is not guaranteed

**What you may say:** the audit log is append-only in the application, protected by a database trigger against accidental or application-level edits, and *tamper-evident*: every row is sealed into a keyed hash chain that `flowforge audit verify` checks. **What you may not say:** "immutable" or "tamper-proof". Someone with the table owner's credentials can still change it; the design makes that *detectable*, not impossible.

**Layer 1 — a write-blocking trigger.** A trigger on `ff_audit_log` refuses `UPDATE`, `DELETE` and `TRUNCATE` unless the transaction has set `flowforge.audit_maintenance = 'on'`. Only two code paths set it, both in `flowforge/audit_chain.py` and pinned by `tests/test_audit_log_mutation_sites.py`: the retention prune, and the GDPR purge (`DELETE /users/<id>?purge=true`, `flowforge user delete --purge`). This stops bugs, SQL-injection-style exploits in the app, and anyone running ad-hoc SQL as a role that does not know about the gate. **It does not stop the table owner**, who can set the flag or drop the trigger. (The application connects as the owner today, because `FLOWFORGE_DB_URL` is used for both migrations and runtime; separating the roles is not built, see below.)

**Layer 2 — a keyed hash chain.** Each row written since migration `0035_audit_chain` carries `seq`, `prev_hash`, a `content_digest` of its fields, and `row_hash = HMAC-SHA256(key, seq | prev_hash | content_digest)`. The key is `FLOWFORGE_AUDIT_CHAIN_KEY` (64+ hex chars), or derived from `FLOWFORGE_SECRET_KEY`. An owner who edits a row, deletes one from the middle, or reorders rows breaks the chain, and cannot repair it without the key. Run it:

```bash
flowforge audit verify                 # exit 0 = intact, 1 = problems, 2 = bad usage
flowforge audit verify --anchor 4812:ab12...   # also prove nothing newer was cut off
flowforge audit anchor                 # print the current "seq:hash" to store elsewhere
# or GET /api/audit-logs/verify[?anchor=seq:hash]   (admin)
```

**Operating it.** Schedule `flowforge audit verify` (it streams, so memory stays flat; time is linear in the number of rows) and alert on a non-zero exit. Every audit write also logs a `CHAIN seq=... hash=...` line to `logs/audit.log` and the stdout stream: ship those to storage the database owner cannot edit, and pass the latest one as `--anchor`.

**What verification detects:** an edited row (any field), a deleted row in the middle, reordered rows, a forged row (no key), rows inserted without a chain after it started, a deleted head with no retention record, and (with an anchor) a rewritten row or a chain cut back past the anchor.

**What it does not detect — be honest about these:**

- **Removal of the newest rows** (tail truncation) is invisible without an anchor: a shorter chain is still a valid chain. The anchor is what closes this, and only if it is stored somewhere the attacker cannot reach.
- **An attacker who has the key** (host access to the app, or the environment) can rewrite the whole chain consistently. Protect `FLOWFORGE_SECRET_KEY` / `FLOWFORGE_AUDIT_CHAIN_KEY` like any other secret, and prefer an external anchor.
- **Rows written before the chain existed ("legacy", `seq` NULL)** can never be verified and age out with retention. A forged row with an old timestamp and no `seq` looks exactly like one.
- **GDPR-purged rows** (`anonymized = true`) keep their place in the chain, but their content is no longer checked. Each purge writes a chained `AUDIT_ANONYMIZED` event with a row count, and verification fails if the number of anonymised rows does not match those records, so flagging extra rows to hide an edit is caught; but a purged row's contents are, by definition, no longer evidence.
- **Key rotation.** Changing `FLOWFORGE_SECRET_KEY` makes every existing row fail verification (reported as "wrong key"). Set `FLOWFORGE_AUDIT_CHAIN_KEY` to a fixed value *before* the first rotation to decouple them; there is no re-sealing tool yet.
- **Writes are best-effort.** A failed insert is swallowed so auditing never crashes a request; the event is then missing. If no key is available the event is still written, but *unchained*, and `verify` reports it. The file and stdout copies are separate, but the file rotates and is an ordinary editable file.

**Retention.** The prune removes the oldest rows (default 90 days) and first appends a chained `AUDIT_PRUNED` row recording the hash of the last row it removed, so the new head still links to something the chain vouches for. Deleting the head *without* that record is reported. With no key available the prune deletes nothing (it could not record the checkpoint).

**Editors can reach the table through a connection to FlowForge's own database.** `editor`-role users can run arbitrary SQL through `db_query`/`db_procedure` (see `threat-model.md`). FlowForge therefore **refuses connections that point at its own PostgreSQL database** (same host, port and database name as `FLOWFORGE_DB_URL`; checked when a connection is created, updated or tested, and again whenever one is opened, including the `DB_HOST`/`DB_NAME` fallback in steps). The trigger now also blocks such SQL from editing audit rows even if a connection to the metadata database slipped through, but an owner-level connection could still open the gate, so the guard stays. Both are defence in depth: neither can see through a proxy or pooler on another port, or a second database that mirrors the metadata. The real control is a least-privilege database role for every connection. To monitor FlowForge's own database deliberately (for example with `db_health_check`), set `FLOWFORGE_ALLOW_INTERNAL_DB_CONNECTIONS=true` and accept this caveat.

**Not built: separate database roles.** The strongest prevention would run migrations as an owner role and the app as a role with `INSERT`/`SELECT` only on `ff_audit_log`, with retention and the GDPR purge exposed as `SECURITY DEFINER` functions. That changes how deployments are set up and is not done; until it is, the table owner can open the trigger gate, and the chain plus an external anchor is the control that covers that case.

---

## Template Sandbox

Pipeline step configs use Jinja2 templates for variable substitution. FlowForge uses **`SandboxedEnvironment`** — arbitrary Python execution (`__import__`, attribute access to internals) is blocked.

**Env var access** in templates is controlled by `FLOWFORGE_TEMPLATE_ENV_VARS`:
- If set (e.g. `FLOWFORGE_TEMPLATE_ENV_VARS=REPORT_DIR,DB_SCHEMA`), only the listed variables are accessible via `{{ env.VAR_NAME }}`. If a listed name looks credential-shaped (matches the same keyword check used by blocklist mode), a warning is logged — the var is still exposed, since allowlist mode is explicit and opt-in.
- If unset (**deprecated**), all env vars are accessible except a hardcoded blocklist (`FLOWFORGE_SECRET_KEY`, `FLOWFORGE_JWT_SECRET`, `*_CLIENT_SECRET`, `*_PASSWORD`, etc.) — logged once per process as a deprecation warning, since a blocklist can never be exhaustive against the next credential-shaped env var a future integration adds. Migrate to allowlist mode.

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
