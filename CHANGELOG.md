# Changelog

All notable changes to FlowForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-17

### Added
- **Pipeline engine** — ordered step execution with `on_error: stop | continue` per step; step outputs threaded into downstream context via `{{ steps.name.* }}`
- **Step types**: `db_procedure`, `db_query`, `report`, `email`, `drive_upload`
- **Database connections**: PostgreSQL (psycopg2 ThreadedConnectionPool) and Oracle (cx_Oracle SessionPool) behind a shared `BaseConnection` interface
- **Report generation**: Excel (openpyxl, optional template support), CSV (stdlib, UTF-8 BOM), PDF (WeasyPrint, optional install)
- **Email providers**: SMTP (smtplib, TLS/SSL), Gmail (OAuth2 + Gmail API), Microsoft 365 (MSAL + Graph API)
- **Smart attachment handling**: files over configured size threshold are automatically uploaded to Google Drive; shareable link replaces direct attachment in email body
- **Google Drive integration**: upload, download, folder create; service account or OAuth2 authentication
- **Jinja2 variable system**: `{{ current_date }}`, `{{ current_month }}`, `{{ current_year }}`, `{{ yesterday }}`, `{{ run_id }}`, `{{ pipeline_name }}`, `{{ env.VAR }}`, `{{ steps.name.output_path }}`, `{{ steps.name.drive_url }}`
- **CLI stub**: `flowforge` entry point via Click
- MIT License

[0.1.0]: https://github.com/your-org/flowforge/releases/tag/v0.1.0
