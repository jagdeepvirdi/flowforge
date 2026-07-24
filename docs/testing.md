# FlowForge — Test Runbook

Complete steps to run every layer of the test suite.
Copy-paste ready for a human or an AI agent (Gemini, Claude, etc.).

---

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| PostgreSQL | running on port 5434 | `psql -p 5434 -U flowforge -c "\l"` |
| `.venv` | created | `.venv\Scripts\python.exe --version` |
| `.env.test` | exists at repo root | present at `D:\Project\flowforge\.env.test` |

### `.env.test` contents (already configured)
```
FLOWFORGE_DB_URL=postgresql://flowforge:harpal123@localhost:5434/flowforge_test
FLOWFORGE_SECRET_KEY=4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0
FLOWFORGE_JWT_SECRET=4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0
E2E_USERNAME=admin
E2E_PASSWORD=H@rpal123
```

> The test DB (`flowforge_test`) is separate from the app DB (`flowforge`).
> `conftest.py` drops and recreates all tables on every pytest run — never point it at the live DB.

---

## Layer 1 — Backend Unit Tests (no DB required)

Tests only `test_crypto.py` — pure in-memory, no database connection needed.

### PowerShell
```powershell
cd D:\Project\flowforge
.\tests\run_tests.ps1 -Unit
```

### Direct command
```powershell
.venv\Scripts\python.exe -m pytest tests\test_crypto.py -v
```

Expected: all crypto encrypt/decrypt tests pass in seconds.

---

## Layer 2 — Backend Integration Tests (requires test DB)

Runs the full pytest suite against `flowforge_test`. `conftest.py` wipes and remigrates the DB at startup.

### PowerShell (recommended)
```powershell
cd D:\Project\flowforge
$env:FLOWFORGE_DB_URL  = "postgresql://flowforge:harpal123@localhost:5434/flowforge_test"
$env:FLOWFORGE_SECRET_KEY = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
$env:FLOWFORGE_JWT_SECRET  = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
.\tests\run_tests.ps1
```

### Or using the run_tests.ps1 script (sets env automatically via .env.test)
```powershell
cd D:\Project\flowforge
Get-Content .env.test | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
.\tests\run_tests.ps1
```

### Bash / WSL / Linux / macOS
```bash
cd /path/to/flowforge
source .env.test
./tests/run_tests.sh
```

### Run with coverage report
```powershell
$env:FLOWFORGE_DB_URL = "postgresql://flowforge:harpal123@localhost:5434/flowforge_test"
$env:FLOWFORGE_SECRET_KEY = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
$env:FLOWFORGE_JWT_SECRET  = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
.venv\Scripts\python.exe -m pytest tests\ -v --tb=short --ignore=tests\manual --cov=flowforge --cov-report=term-missing
```

### Run a single test file
```powershell
$env:FLOWFORGE_DB_URL = "postgresql://flowforge:harpal123@localhost:5434/flowforge_test"
$env:FLOWFORGE_SECRET_KEY = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
$env:FLOWFORGE_JWT_SECRET  = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
.venv\Scripts\python.exe -m pytest tests\test_pipelines.py -v
```

What the test runner does:
1. Drops all `ff_*` tables in `flowforge_test`
2. Runs Alembic migrations up to `head`
3. Seeds a `testadmin` user
4. Runs all test files in `tests\` (skipping `tests\manual\`)

Notable suites worth knowing by name (not exhaustive — see `tests\` for the full list):
- `test_dag_engine.py`, `test_dag_integration.py`, `test_runner_dag_gate.py` — the step-level DAG
  matrix (Phase 14 Option B): topological execution, cycle rejection, branch-scoped `on_error: stop`,
  ancestors-only `{{ steps.* }}` context, and the wave-engine/DAG-engine gate itself.

---

## Layer 3 — Frontend Unit Tests (Vitest)

No backend or DB needed. Runs React component tests in jsdom.

```powershell
cd D:\Project\flowforge\frontend
npm run test
```

Watch mode (re-runs on file change):
```powershell
npm run test:watch
```

Test files: `frontend\src\__tests__\*.test.{ts,tsx}`
- `Login.test.tsx`
- `Dashboard.test.tsx`
- `Pipelines.test.tsx`
- `Connections.test.tsx`
- `TopBarSearch.test.tsx`
- `AuditLog.test.tsx`
- `BulkLoadEdit.test.tsx`
- `BulkLoads.test.tsx`
- `HelpDrawer.test.tsx`
- `MailFieldsSmtp.test.tsx`
- `Reports.test.tsx`
- `RunHistory.test.tsx`
- `Settings.test.tsx`
- `StepEditor.test.tsx`
- `StepTrendsPanel.test.tsx`
- `TriggersCard.test.tsx`
- `Users.test.tsx`
- `api.test.ts`
- `PipelineCanvas.test.tsx` — canvas rendering, edge display
- `canvasLayout.test.ts`, `pipelineWaves.test.ts`, `pipelineReorder.test.ts`, `resolveDrop.test.ts` — canvas layout/drag logic
- `stepDeps.test.ts` — step-dependency edge helpers (DAG feature, see Phase 14 Option B)

---

## Layer 4 — Frontend E2E Tests (Playwright)

Requires the **full stack** running before Playwright is launched.

### Step 1 — Start backend (Terminal 1)
```powershell
cd D:\Project\flowforge
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
}
.venv\Scripts\python.exe -m flask --app flowforge.api.app:create_app run -p 5000
```

### Step 2 — Start frontend dev server (Terminal 2)
```powershell
cd D:\Project\flowforge\frontend
npm run dev
```
Wait until Vite reports: `Local: http://localhost:5173/`

### Step 3 — Run Playwright tests (Terminal 3)
```powershell
cd D:\Project\flowforge\frontend
npm run test:e2e
```

Playwright reads `../.env.test` automatically for `E2E_USERNAME` and `E2E_PASSWORD`.

### Open the Playwright UI (interactive mode)
```powershell
cd D:\Project\flowforge\frontend
npm run test:e2e:ui
```

### View the HTML report after a run
```powershell
cd D:\Project\flowforge\frontend
npm run test:e2e:report
```

E2E test files in `frontend\e2e\`:
- `global.setup.ts` — logs in, saves auth state to `.auth.json`
- `dashboard.spec.ts` — dashboard page
- `pipelines.spec.ts` — pipeline list
- `pipeline-journey.spec.ts` — full create → run → verify journey
- `pipeline-canvas.spec.ts` — canvas view, drag-to-reorder, step-dependency edges
- `connections.spec.ts` — connections page
- `auth.spec.ts` — login / logout
- `login.spec.ts` — login form validation
- `run-history.spec.ts` — run history page
- `global.teardown.ts` — deletes all `E2E *` pipelines created during tests

---

## Layer 5 — Manual API Smoke Test

Runs a quick sanity check against a live server (GET pipelines, auth, etc.).

```powershell
cd D:\Project\flowforge
.\tests\run_tests.ps1 -Manual -ApiUrl http://localhost:5000 -ApiUser admin -ApiPass "H@rpal123"
```

Or directly:
```powershell
.venv\Scripts\python.exe tests\manual\check_api.py --url http://localhost:5000 --user admin --pass "H@rpal123"
```

---

## All Layers — Full Run (no E2E)

Run Layers 1–3 in one go (no server required):

```powershell
cd D:\Project\flowforge

# Set test env vars
$env:FLOWFORGE_DB_URL  = "postgresql://flowforge:harpal123@localhost:5434/flowforge_test"
$env:FLOWFORGE_SECRET_KEY = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"
$env:FLOWFORGE_JWT_SECRET  = "4d688ef00edded2d39f4109d9e6497d54fff5165555a8a41e8aaedb9c7f62fd0"

# Backend tests
.venv\Scripts\python.exe -m pytest tests\ -v --tb=short --ignore=tests\manual

# Frontend unit tests
cd frontend
npm run test
cd ..
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `FLOWFORGE_DB_URL is not set` | Set the env var (see Layer 2 commands above) |
| `SAFETY ABORT: FLOWFORGE_DB_URL points to "flowforge"` | You're pointing at the live DB — change it to `flowforge_test` |
| `connection refused port 5434` | PostgreSQL Docker container is not running — `docker-compose up -d db` |
| `ModuleNotFoundError: flowforge` | Run `pip install -e .` inside the venv |
| `Address already in use :5000` | Another Flask instance is running — kill it |
| `Address already in use :5173` | Another Vite instance is running — kill it or change port |
| Playwright can't log in | Confirm backend is running and `.env.test` has correct `E2E_PASSWORD=H@rpal123` |
| `npm: command not found` | Node.js not installed or not on PATH |

---

## Test Database Details

| Field    | Value                                               |
|----------|-----------------------------------------------------|
| Host     | localhost                                           |
| Port     | 5434                                                |
| Database | `flowforge_test`                                    |
| User     | `flowforge`                                         |
| Password | `harpal123`                                         |
| Note     | Wiped and remigrated on every `pytest` run          |
