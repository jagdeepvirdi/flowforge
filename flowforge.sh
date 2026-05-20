#!/usr/bin/env bash
# FlowForge - server.sh
# Usage:
#   ./server.sh start               # dev mode (Flask debug + Vite HMR)
#   ./server.sh start prod          # prod mode (build frontend + Flask/gunicorn)
#   ./server.sh start prod --gunicorn
#   ./server.sh stop                # stop Flask API and Vite dev server

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

    echo ""
    echo "Stopping FlowForge servers..."
    stop_port "$PORT" "Flask API"
    stop_port "5173"  "Vite UI"
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
    echo "  API  -> http://localhost:$PORT"
    echo "  UI   -> http://localhost:5173"
    echo ""
    echo "Run ./server.sh stop in another terminal to stop."
    echo ""

    cleanup() {
        echo ""
        echo "Stopping servers..."
        kill "$API_PID" "$UI_PID" 2>/dev/null || true
        wait "$API_PID" "$UI_PID" 2>/dev/null || true
        echo "Stopped."
    }
    trap cleanup INT TERM

    FLASK_ENV=development \
    python -m flask --app flowforge.api.app:create_app run \
        --host 0.0.0.0 --port "$PORT" --debug \
        2>&1 | sed 's/^/[api] /' &
    API_PID=$!

    cd "$ROOT/frontend"
    npm run dev 2>&1 | sed 's/^/[ui]  /' &
    UI_PID=$!
    cd "$ROOT"

    wait -n "$API_PID" "$UI_PID" 2>/dev/null || wait "$API_PID" "$UI_PID"
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
        echo "[server] Flask built-in server — use --gunicorn for real production traffic."
        export FLASK_ENV=production
        exec python -m flask --app flowforge.api.app:create_app run \
            --host 0.0.0.0 --port "$PORT"
    fi
fi
