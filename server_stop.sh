#!/usr/bin/env bash
# FlowForge - server_stop.sh
# Stops the Flask API and Vite dev server.
# Usage: ./server_stop.sh

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env to get FLOWFORGE_PORT if set
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
