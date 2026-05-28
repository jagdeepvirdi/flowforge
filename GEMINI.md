# FlowForge — Project Instructions

## Overview
FlowForge is a database-driven pipeline orchestrator. It executes ordered steps (DB procedures, queries, reports, emails, Drive uploads) configured via a React frontend. All configuration lives in a PostgreSQL database. The project reached **v1.0.0** on 2026-05-25 and is now entering the **v2.0 Production Hardening** phase.

## Technical Stack
- **Backend**: Python 3.11+, Flask, SQLAlchemy, APScheduler, Celery (Redis/RabbitMQ).
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Zustand, React Query.
- **Database**: PostgreSQL (internal config), PostgreSQL/Oracle/MySQL (user data).
- **Communication**: REST API (JSON) + JWT Auth.
- **Quality**: SonarCloud (Quality Gate), OpenSSF Scorecard, Codecov (~80% target).

## Core Mandates
- **No-YAML Config**: Normal operation should not require editing YAML files. Use the UI/API. YAML is for import/export only.
- **Encryption**: Sensitive credentials MUST be encrypted using `flowforge.crypto` (AES-256-GCM).
- **Pluggable Architecture**: Follow abstract base class patterns for new steps/providers.
- **Async Execution**: Long-running pipelines MUST be executed asynchronously via the **Celery worker** queue when `FLOWFORGE_REDIS_URL` is set.
- **Scalability**: All shared state must live in **PostgreSQL or Redis**, allowing for horizontal scaling of API and Worker instances.
- **Frontend Style**: **NO inline styles.** Use Tailwind CSS or CSS variables. Follow the design tokens in `frontend/src/index.css`.
- **AI-First**: Leverage local Ollama for data profiling, SQL optimization, and failure diagnosis.
- **Security First**: All GitHub Actions pinned to SHA. Docker images pinned to SHA. No hardcoded secrets.

## Directory Structure
- `flowforge/`: Core Python package.
  - `api/`: Flask REST API routes, auth, and serializers.
  - `engine/`: Pipeline runner, launcher, context resolution, and scheduler.
  - `steps/`: Individual step type implementations (db_query, email, bulk_load, etc.).
  - `connections/`: Database connection classes (PostgreSQL, Oracle, MySQL).
  - `email_providers/`: Email provider classes (Gmail, M365, SMTP).
  - `reports/`: Report generators (Excel, PDF, CSV, JSON).
  - `storage/`: Google Drive and OneDrive integrations.
  - `db/`: SQLAlchemy models and Alembic migrations.
- `frontend/`: React frontend.
  - `src/pages/`: Main application views.
  - `src/components/`: Reusable UI components.
  - `src/lib/`: API clients, stores, and shared utilities.
- `tests/`: Pytest suite (Backend) and Vitest/Playwright (Frontend).
- `docs/`: Comprehensive documentation and task history.

## Development Workflows
- **Code Style**: Follow PEP 8 for Python. Use type hints for all new functions.
- **Testing**: Run `pytest` and `npm run test` before any change. Add tests for all new features or bug fixes.
- **Bug Fixes**: ALWAYS empirically reproduce the failure with a test case before applying the fix.
- **Documentation**: Update `docs/TASKS.md` for new tasks and move completed items to `docs/TASKS_ARCHIVE.md`.
- **Quality Gate**: New code should not increase cognitive complexity beyond 15 in critical paths. Check SonarCloud reports.

## Common Tasks
- **Adding a Step**: Inherit from `BaseStep` in `flowforge/steps/base.py`, implement `run()`, and register it.
- **Adding a Connection/Provider**: Inherit from the respective `Base` class, implement required methods, and update the factory.
- **Database Migrations**: Use Alembic for all schema changes (`alembic revision --autogenerate`).
- **Modifying UI**: Use Tailwind CSS. Reuse components from `frontend/src/components/shared/`.
