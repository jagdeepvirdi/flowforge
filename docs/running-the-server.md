# Running FlowForge with flowforge.ps1 / flowforge.sh

These scripts start and stop the FlowForge API and frontend dev server together. Use them instead of running Flask and Vite manually.

- **Windows**: `flowforge.ps1` (PowerShell)
- **macOS / Linux**: `flowforge.sh` (Bash)

---

## Pre-checks

Before running either script, confirm the following are in place.

### 1. Python virtual environment

```bash
# Create (once)
python -m venv .venv

# Install dependencies
# Windows
.venv\Scripts\pip install -e .
# macOS/Linux
.venv/bin/pip install -e .
```

The scripts auto-activate `.venv` if it exists and `VIRTUAL_ENV` is not already set.

### 2. Node.js and frontend dependencies

Node 18+ is required. Install frontend packages once:

```bash
cd frontend
npm install
cd ..
```

### 3. .env file

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
FLOWFORGE_DB_URL=postgresql://flowforge:changeme@localhost:5432/flowforge
FLOWFORGE_SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
```

The scripts load `.env` automatically at startup. If the file is missing, a warning is printed but the script continues (it will fail later when Flask tries to connect to the database).

### 4. Database migrated

```bash
flowforge db upgrade
flowforge db seed   # creates the admin user on first run
```

### 5. Ports available

| Service | Default port |
|---|---|
| Flask API | `5000` (override with `FLOWFORGE_PORT` in `.env`) |
| Vite dev UI | `5173` (fixed) |

### 6. (Prod mode only) WSGI server installed

```bash
# Windows — waitress
pip install waitress

# macOS/Linux — gunicorn
pip install gunicorn
```

---

## Usage

### Windows — flowforge.ps1

```powershell
# Execution policy (one-time, if scripts are blocked)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Dev mode (Flask debug + Vite HMR)
.\flowforge.ps1 start

# Dev mode on a custom port
.\flowforge.ps1 start -Port 8080

# Prod mode — builds frontend, serves with Flask built-in server
.\flowforge.ps1 start -Mode prod

# Prod mode with waitress (recommended for real traffic)
.\flowforge.ps1 start -Mode prod -UseWaitress

# Stop both servers
.\flowforge.ps1 stop
```

### macOS / Linux — flowforge.sh

```bash
# Make executable (one-time)
chmod +x flowforge.sh

# Dev mode (Flask debug + Vite HMR)
./flowforge.sh start

# Prod mode — builds frontend, serves with Flask built-in server
./flowforge.sh start prod

# Prod mode with gunicorn (recommended for real traffic)
./flowforge.sh start prod --gunicorn

# Stop both servers
./flowforge.sh stop
```

---

## What each mode does

### Dev mode (default)

- Starts Flask with `--debug` (auto-reload on Python file changes)
- Starts Vite dev server with Hot Module Replacement on port 5173
- API logs prefixed `[api]`, UI logs prefixed `[ui]`
- Press **Ctrl+C** to stop both processes

### Prod mode

- Runs `npm run build` — outputs static files to `frontend/dist/`
- Flask serves the built frontend from `frontend/dist/`
- Without a WSGI flag: uses Flask's built-in server with `FLASK_ENV=production` (single-threaded, not suitable for concurrent users)
- With `-UseWaitress` / `--gunicorn`: uses a production-grade WSGI server (multi-threaded / multi-worker)

---

## Stopping the servers

**Ctrl+C** in the terminal where the script is running stops both processes.

To stop from a separate terminal:

```powershell
# Windows
.\flowforge.ps1 stop
```

```bash
# macOS/Linux
./flowforge.sh stop
```

The stop command reads `FLOWFORGE_PORT` from `.env` and kills the process listening on that port, then kills the process on port 5173.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cannot be loaded because running scripts is disabled` (Windows) | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `.env not found` warning | Copy `.env.example` to `.env` and fill in values |
| `ModuleNotFoundError: No module named 'flowforge'` | Activate the venv: `.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (macOS/Linux), then `pip install -e .` |
| `npm: command not found` | Install Node 18+ from https://nodejs.org |
| `ENOENT node_modules` on the UI job | Run `npm install` inside the `frontend/` directory |
| Port 5000 already in use | Set `FLOWFORGE_PORT=5001` (or any free port) in `.env` |
| `waitress` / `gunicorn` not found | Install with `pip install waitress` (Windows) or `pip install gunicorn` (Linux/macOS) |
| API job immediately fails in dev mode | Check that `FLOWFORGE_DB_URL` is set correctly and PostgreSQL is running |

---

## Related

- [Getting Started](getting-started.md) — installation, first pipeline, CLI reference
- [RUNBOOK.md](../RUNBOOK.md) — database migration workflow, stamp scenario, production checklist
