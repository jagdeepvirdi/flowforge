# Contributing to FlowForge

Thanks for your interest in contributing. This guide covers how to get the development environment running, how the project is structured, and how to submit a pull request.

---

## Quick Dev Setup

Get a working dev environment in under 5 minutes:

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge

# Python backend
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -e ".[dev]"

# Database — needs a running PostgreSQL instance
cp .env.example .env               # set FLOWFORGE_DB_URL + FLOWFORGE_SECRET_KEY
flowforge db upgrade
flowforge db seed                  # creates the admin user

# Frontend
cd frontend && npm install && npm run dev &
cd ..

# Backend
flowforge web
```

Open `http://localhost:5173`. Default login: `admin` / the password you set in `.env`.

## Running Tests

```bash
# Backend (needs FLOWFORGE_DB_URL pointing to a test DB)
pytest tests/

# Frontend unit tests
cd frontend && npx vitest run
```

---

## Development Setup

### Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Git

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.\.venv\Scripts\Activate.ps1     # Windows (PowerShell)
```

### 2. Install Python dependencies

```bash
# Core + dev tools
pip install -e ".[dev]"

# Optional extras (only install what you're testing)
pip install -e ".[gmail]"        # Gmail OAuth2
pip install -e ".[drive]"        # Google Drive
pip install -e ".[microsoft365]" # Microsoft 365 / MSAL
pip install -e ".[oracle]"       # Oracle cx_Oracle
```

### 3. Set up the database

```bash
# Create the FlowForge database and user
psql -U postgres -c "CREATE USER flowforge WITH PASSWORD 'flowforge';"
psql -U postgres -c "CREATE DATABASE flowforge OWNER flowforge;"

# Run migrations
alembic upgrade head
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — minimum required:
#   FLOWFORGE_DB_URL=postgresql://flowforge:flowforge@localhost:5432/flowforge
#   FLOWFORGE_SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
#   FLOWFORGE_USERNAME=admin
#   FLOWFORGE_PASSWORD=<bcrypt hash>
```

To generate a bcrypt hash for the admin password:

```python
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('yourpassword'))"
```

### 5. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 6. Start the dev servers

```bash
# Backend (Flask, port 5000)
flowforge web

# Frontend (Vite, port 5173) — in a separate terminal
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running Tests

**Policy:** All new functionality must include tests. Bug fixes must include a regression test. PRs without tests will not be merged.

Tests use `pytest` and hit a real PostgreSQL database. They do **not** use mocked DB connections — this was a deliberate choice after mock/real divergence caused issues in the past.

### Test database setup

Set `FLOWFORGE_DB_URL` in your environment to a test database (separate from dev):

```bash
# PowerShell
$env:FLOWFORGE_DB_URL = "postgresql://flowforge:flowforge@localhost:5432/flowforge_test"

# bash / zsh
export FLOWFORGE_DB_URL=postgresql://flowforge:flowforge@localhost:5432/flowforge_test
```

The test database is created and seeded automatically by `tests/conftest.py`.

### Running the full suite

```bash
pytest
```

### Running a specific file or test

```bash
pytest tests/test_pipelines.py
pytest tests/test_context.py::test_quarter_variables
```

### Test coverage

```bash
pytest --cov=flowforge --cov-report=term-missing
```

### Manual test scripts

```bash
python tests/manual/check_api.py        # API smoke test
python tests/manual/check_email.py      # Send a test email
python tests/manual/check_runner.py     # Run a pipeline end-to-end
python tests/manual/check_scheduler.py  # Scheduler smoke test
```

---

## Project Structure

```
flowforge/
├── flowforge/               # Python package
│   ├── api/                 # Flask REST API
│   │   ├── app.py           # App factory
│   │   ├── auth.py          # JWT middleware
│   │   └── routes/          # One blueprint per resource
│   ├── connections/         # DB connection classes (postgres, oracle)
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   └── migrations/      # Alembic migration scripts
│   ├── email_providers/     # SMTP, Gmail, Microsoft 365
│   ├── engine/
│   │   ├── context.py       # Jinja2 variable resolution
│   │   ├── loader.py        # Load pipeline + steps from DB
│   │   ├── runner.py        # Pipeline executor
│   │   └── scheduler.py     # APScheduler daemon
│   ├── reports/             # Excel, PDF, CSV generators
│   ├── steps/               # Step type implementations
│   ├── storage/             # Google Drive
│   └── crypto.py            # AES-256-GCM encrypt/decrypt
├── frontend/                # React + Vite + TypeScript
│   └── src/
│       ├── components/      # Shared + page-specific components
│       ├── lib/             # API client, types, helpContent
│       └── pages/           # One file per page
├── tests/                   # pytest test suite
│   └── manual/              # Manual smoke test scripts
└── docs/                    # Reference documentation
```

---

## Adding a New Step Type

1. Create `flowforge/steps/your_step.py` — subclass `BaseStep`, implement `execute(context)`
2. Return a `StepResult` with appropriate fields set (`output_path`, `drive_url`, `rows_affected`, `output_variables`, etc.)
3. Register the step type in `flowforge/engine/loader.py` — add a branch in the step factory
4. Add the config form in `frontend/src/components/pipeline/StepEditor.tsx`
5. Add help text in `frontend/src/lib/helpContent.ts`
6. Document it in `docs/step-types.md`
7. Write tests in `tests/test_steps_<name>.py`

---

## Pull Request Guidelines

1. **One PR per feature or fix.** Keep changes focused so reviewers can evaluate them cleanly.
2. **Tests required.** New behaviour needs at least one test. Bug fixes should add a regression test.
3. **No new dependencies without discussion.** Open an issue first if a new package is needed.
4. **Don't break existing tests.** Run the full suite before opening a PR.
5. **Commit style**: use conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).

### PR checklist

- [ ] Tests pass locally: `pytest`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] New env vars documented in `.env.example`
- [ ] New step type documented in `docs/step-types.md`
- [ ] CHANGELOG.md updated under `[Unreleased]`

---

## Reporting Issues

Use GitHub Issues — there are templates for bugs and feature requests. Please include:
- FlowForge version (`pip show flowforge`)
- Python version and OS
- Steps to reproduce (for bugs)
- Relevant log output from `ff_step_runs.logs`
