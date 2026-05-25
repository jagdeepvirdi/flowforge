# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 1.x (latest) | ✅ Active — security fixes released as patch versions |
| 0.x | ❌ No longer supported — upgrade to 1.x |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

### Option 1 — GitHub Private Security Advisory (preferred)

1. Go to the [Security tab](https://github.com/jagdeepvirdi/flowforge/security/advisories) of this repository.
2. Click **"Report a vulnerability"**.
3. Fill in the details — affected component, reproduction steps, impact assessment.

GitHub keeps the report private between you and the maintainer until a fix is published.

### Option 2 — Email

Send details to: **jagdeep.singh.virdi@gmail.com**

Include:
- A description of the vulnerability and affected component
- Steps to reproduce (or a proof-of-concept)
- Potential impact
- Your GitHub username (optional, for credit in the advisory)

## Response SLA

| Step | Target |
|---|---|
| Acknowledgement | Within 72 hours |
| Triage and severity assessment | Within 7 days |
| Fix or workaround | Within 30 days for high/critical; 90 days for low/medium |
| Public disclosure | Coordinated with reporter after fix is released |

## Security Documentation

For the full security model — credential encryption, JWT, RBAC, audit logging, template sandboxing, and key rotation — see [docs/security.md](docs/security.md).
