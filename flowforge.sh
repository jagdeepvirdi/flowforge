#!/usr/bin/env bash
# FlowForge - flowforge.sh
# Usage:
#   ./flowforge.sh dev start            # dev mode (Flask debug + Vite HMR + scheduler)
#   ./flowforge.sh prod start           # prod mode (build frontend + Flask/gunicorn + scheduler)
#   ./flowforge.sh prod start --gunicorn
#   ./flowforge.sh dev stop             # stop Flask API, Vite dev server, scheduler, and worker
#   ./flowforge.sh dev restart          # stop then start
#   ./flowforge.sh prod status          # show what's currently running
#
# Celery worker (optional):
#   If FLOWFORGE_REDIS_URL is set in .env, a Celery worker is started automatically
#   alongside the API in both dev and prod modes.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MODE="${1:-}"
ACTION="${2:-}"

usage() {
    echo "Usage: $0 {dev|prod} {start|stop|restart|status} [--gunicorn]" >&2
    exit 1
}

case "$MODE" in
    dev|prod) ;;
    *) usage ;;
esac

case "$ACTION" in
    start|stop|restart|status) ;;
    *) usage ;;
esac

USE_GUNICORN=false
for arg in "${@:3}"; do
    case $arg in
        --gunicorn) USE_GUNICORN=true ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

load_env() {
    if [ -f "$ROOT/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source "$ROOT/.env"
        set +a
        return 0
    fi
    return 1
}

check_db_connection() {
    if [ -z "${FLOWFORGE_DB_URL:-}" ]; then
        echo "[db] FLOWFORGE_DB_URL is not set - skipping database check." >&2
        return 0
    fi

    echo "[db] Checking database connection..."
    if ! python - <<'PYEOF'
import os, sys
from sqlalchemy import create_engine, text

url = os.environ.get("FLOWFORGE_DB_URL")
connect_args = {"connect_timeout": 5} if url.startswith("postgresql") else {}
try:
    engine = create_engine(url, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as e:
    print(f"[db] {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    then
        echo ""
        echo "[db] Could not connect to the database (see FLOWFORGE_DB_URL in .env)." >&2
        echo "     Check that PostgreSQL is running and reachable, and the credentials are correct." >&2
        echo ""
        return 1
    fi

    echo "[db] Database connection OK"
    return 0
}

stop_port() {
    local port="$1"
    local label="$2"
    local pid
    pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill -TERM "$pid" 2>/dev/null || true
        echo "  Stopped $label (PID $pid, port $port)"
    else
        echo "  $label not running on port $port"
    fi
}

stop_pattern() {
    local pattern="$1"
    local label="$2"
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        echo "  Stopped $label (PID(s) $pids)"
    else
        echo "  $label not running"
    fi
}

status_port() {
    local port="$1"
    local label="$2"
    local pid
    pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        printf "  %-14s RUNNING (PID %s, port %s)\n" "$label" "$pid" "$port"
    else
        printf "  %-14s stopped\n" "$label"
    fi
}

status_pattern() {
    local pattern="$1"
    local label="$2"
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        printf "  %-14s RUNNING (PID(s) %s)\n" "$label" "$(echo "$pids" | tr '\n' ' ')"
    else
        printf "  %-14s stopped\n" "$label"
    fi
}

do_stop() {
    load_env || true
    local port="${FLOWFORGE_PORT:-5000}"
    echo ""
    echo "Stopping FlowForge..."
    stop_port    "$port" "Flask API"
    stop_port    "5173"  "Vite UI"
    stop_pattern "flowforge.cli schedule" "Scheduler"
    stop_pattern "flowforge.cli worker"   "Celery worker"
    echo ""
    echo "Done."
    echo ""
}

do_status() {
    load_env || true
    local port="${FLOWFORGE_PORT:-5000}"
    echo ""
    echo "FlowForge status:"
    status_port    "$port" "Flask API"
    status_port    "5173"  "Vite UI"
    status_pattern "flowforge.cli schedule" "Scheduler"
    status_pattern "flowforge.cli worker"   "Celery worker"
    echo ""
}

do_start() {
    local mode="$1"

    if load_env; then
        echo "[env] Loaded .env"
    else
        echo "Warning: .env not found - copy .env.example to .env and fill in values." >&2
    fi

    if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$ROOT/.venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$ROOT/.venv/bin/activate"
        echo "[venv] Activated .venv"
    fi

    if ! check_db_connection; then
        exit 1
    fi

    local port="${FLOWFORGE_PORT:-5000}"

    # ── DEV MODE ─────────────────────────────────────────────────────────────
    if [ "$mode" = "dev" ]; then
        echo ""
        echo "Starting FlowForge in DEV mode..."
        echo "  API       -> http://localhost:$port"
        echo "  UI        -> http://localhost:5173"
        echo "  Scheduler -> running alongside API"
        [ -n "${FLOWFORGE_REDIS_URL:-}" ] && echo "  Worker    -> Celery worker (Redis detected)"
        echo ""
        echo "Press Ctrl+C to stop all processes."
        echo ""

        WORKER_PID=""
        cleanup() {
            echo ""
            echo "Stopping servers..."
            kill "$API_PID" "$SCHED_PID" "$UI_PID" ${WORKER_PID:+"$WORKER_PID"} 2>/dev/null || true
            wait "$API_PID" "$SCHED_PID" "$UI_PID" ${WORKER_PID:+"$WORKER_PID"} 2>/dev/null || true
            echo "Stopped."
        }
        trap cleanup INT TERM

        FLASK_ENV=development \
        python -m flask --app flowforge.api.app:create_app run \
            --host 0.0.0.0 --port "$port" --debug \
            2>&1 | sed 's/^/[api]   /' &
        API_PID=$!

        python -m flowforge.cli schedule \
            2>&1 | sed 's/^/[sched] /' &
        SCHED_PID=$!

        if [ -n "${FLOWFORGE_REDIS_URL:-}" ]; then
            python -m flowforge.cli worker \
                2>&1 | sed 's/^/[work]  /' &
            WORKER_PID=$!
            echo "[work]  Celery worker started (PID $WORKER_PID)"
        fi

        cd "$ROOT/frontend"
        npm run dev 2>&1 | sed 's/^/[ui]    /' &
        UI_PID=$!
        cd "$ROOT"

        wait -n "$API_PID" "$SCHED_PID" "$UI_PID" ${WORKER_PID:+"$WORKER_PID"} 2>/dev/null || \
            wait "$API_PID" "$SCHED_PID" "$UI_PID" ${WORKER_PID:+"$WORKER_PID"}
    fi

    # ── PROD MODE ────────────────────────────────────────────────────────────
    if [ "$mode" = "prod" ]; then
        echo ""
        echo "Starting FlowForge in PROD mode..."

        echo "Building frontend..."
        cd "$ROOT/frontend"
        npm run build
        cd "$ROOT"
        echo "[ok] Frontend built -> frontend/dist/"

        # Start scheduler in background
        python -m flowforge.cli schedule \
            2>&1 | sed 's/^/[sched] /' &
        SCHED_PID=$!
        echo "[sched] Scheduler started (PID $SCHED_PID)"

        WORKER_PID=""
        if [ -n "${FLOWFORGE_REDIS_URL:-}" ]; then
            python -m flowforge.cli worker \
                2>&1 | sed 's/^/[work]  /' &
            WORKER_PID=$!
            echo "[work]  Celery worker started (PID $WORKER_PID)"
        fi

        cleanup() {
            echo ""
            echo "Stopping background processes..."
            kill "$SCHED_PID" ${WORKER_PID:+"$WORKER_PID"} 2>/dev/null || true
            wait "$SCHED_PID" ${WORKER_PID:+"$WORKER_PID"} 2>/dev/null || true
            echo "Stopped."
        }
        trap cleanup EXIT INT TERM

        echo ""
        echo "Listening on http://0.0.0.0:$port"
        echo ""

        if [ "$USE_GUNICORN" = true ]; then
            echo "[server] Using gunicorn (production WSGI)"
            exec gunicorn \
                --bind "0.0.0.0:$port" \
                --workers "${GUNICORN_WORKERS:-4}" \
                --worker-class sync \
                --timeout 120 \
                --access-logfile - \
                --error-logfile - \
                "flowforge.api.app:create_app()"
        else
            echo "[server] Flask built-in server -- use --gunicorn for production traffic."
            export FLASK_ENV=production
            exec python -m flask --app flowforge.api.app:create_app run \
                --host 0.0.0.0 --port "$port"
        fi
    fi
}

case "$ACTION" in
    status)
        do_status
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_stop
        sleep 1
        do_start "$MODE"
        ;;
    start)
        do_start "$MODE"
        ;;
esac
