#!/usr/bin/env bash
# FlowForge - flowforge.sh
# Usage:
#   ./flowforge.sh start               # dev mode (Flask debug + Vite HMR + scheduler)
#   ./flowforge.sh start prod          # prod mode (build frontend + Flask/gunicorn + scheduler)
#   ./flowforge.sh start prod --gunicorn
#   ./flowforge.sh stop                # stop Flask API, Vite dev server, scheduler, and worker
#
# Celery worker (optional):
#   If FLOWFORGE_REDIS_URL is set in .env, a Celery worker is started automatically
#   alongside the API in both dev and prod modes.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACTION="${1:-}"
if [ -z "$ACTION" ]; then
    echo "Usage: $0 {start|stop} [dev|prod] [--gunicorn]" >&2
    exit 1
fi

# ── STOP ────────────────────────────────────────────────────────────────────
if [ "$ACTION" = "stop" ]; then
    if [ -f "$ROOT/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source "$ROOT/.env"
        set +a
    fi

    PORT="${FLOWFORGE_PORT:-5000}"

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

    echo ""
    echo "Stopping FlowForge..."
    stop_port    "$PORT" "Flask API"
    stop_port    "5173"  "Vite UI"
    stop_pattern "flowforge.cli schedule" "Scheduler"
    stop_pattern "flowforge.cli worker"   "Celery worker"
    echo ""
    echo "Done."
    echo ""
    exit 0
fi

# ── START ────────────────────────────────────────────────────────────────────
if [ "$ACTION" != "start" ]; then
    echo "Unknown action: $ACTION. Use 'start' or 'stop'." >&2
    exit 1
fi

MODE="${2:-dev}"
USE_GUNICORN=false
for arg in "${@:3}"; do
    case $arg in
        --gunicorn) USE_GUNICORN=true ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

# Load .env
if [ -f "$ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env"
    set +a
    echo "[env] Loaded .env"
else
    echo "Warning: .env not found - copy .env.example to .env and fill in values." >&2
fi

# Activate venv
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$ROOT/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT/.venv/bin/activate"
    echo "[venv] Activated .venv"
fi

PORT="${FLOWFORGE_PORT:-5000}"

# ── DEV MODE ─────────────────────────────────────────────────────────────────
if [ "$MODE" = "dev" ]; then
    echo ""
    echo "Starting FlowForge in DEV mode..."
    echo "  API       -> http://localhost:$PORT"
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
        --host 0.0.0.0 --port "$PORT" --debug \
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

# ── PROD MODE ─────────────────────────────────────────────────────────────────
if [ "$MODE" = "prod" ]; then
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
    echo "Listening on http://0.0.0.0:$PORT"
    echo ""

    if [ "$USE_GUNICORN" = true ]; then
        echo "[server] Using gunicorn (production WSGI)"
        exec gunicorn \
            --bind "0.0.0.0:$PORT" \
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
            --host 0.0.0.0 --port "$PORT"
    fi
fi
