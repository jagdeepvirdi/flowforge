# FlowForge — Project Instructions

## Overview
FlowForge is a database-driven pipeline orchestrator. It executes ordered steps (DB procedures, queries, reports, emails, Drive uploads) configured via a React frontend. All configuration lives in a PostgreSQL database.

## Technical Stack
- **Backend**: Python 3.11+, Flask, SQLAlchemy, APScheduler.
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Zustand, React Query.
- **Database**: PostgreSQL (internal config), PostgreSQL/Oracle (user data).
- **Communication**: REST API (JSON) + JWT Auth.

## Core Mandates
- **No-YAML Config**: Normal operation should not require editing YAML files. Use the UI/API.
- **Encryption**: Sensitive credentials MUST be encrypted using `flowforge.crypto`.
- **Pluggable Architecture**: Follow abstract base class patterns for new steps/providers.
- **Async Execution**: Long-running pipelines MUST be executed asynchronously via the **Celery worker** queue. Never run heavy logic in the API request thread.
- **Scalability**: All shared state must live in **PostgreSQL or Redis**, allowing for multiple API and Worker instances.
- **Frontend Style**: **STOP using inline styles.** Use Tailwind CSS or CSS variables for all new components. Refactor existing inline styles when touching files.
- **AI-First**: Leverage local Ollama for data profiling and query optimization where possible.

## Directory Structure
- `flowforge/`: Core Python package.
  - `api/`: Flask REST API routes and app factory.
  - `engine/`: Pipeline runner, context resolution, and scheduler.
  - `steps/`: Individual step type implementations.
  - `connections/`: Database connection classes (PostgreSQL, Oracle).
  - `email_providers/`: Email provider classes (Gmail, M365, SMTP).
  - `reports/`: Report generators (Excel, PDF, CSV).
  - `storage/`: Google Drive integration.
  - `db/`: SQLAlchemy models and schema.
- `frontend/`: React frontend.
  - `src/pages/`: Main application views.
  - `src/components/`: Reusable UI components.
  - `src/lib/`: API clients and shared utilities.
- `tests/`: Pytest suite.

## Development Workflows
- **Code Style**: Follow PEP 8 for Python. Use type hints for all new functions.
- **Testing**: Run `pytest` before any major change. Add new tests for new features/bug fixes in the `tests/` directory.
- **Database Changes**: Update `flowforge/db/models.py` and `flowforge/db/schema.sql` (migrations pending).
- **Environment**: Always use `.env` for local configuration. Never hardcode secrets.

## Common Tasks
- **Adding a Step**: Inherit from `BaseStep` in `flowforge/steps/base.py`, implement `run()`, and register it in the engine/frontend.
- **Adding a Connection/Provider**: Inherit from the respective `Base` class, implement required methods, and update the factory.
- **Modifying UI**: Use Tailwind CSS for styling. Follow the design tokens defined in `frontend/src/index.css`.
