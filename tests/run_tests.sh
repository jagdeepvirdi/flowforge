#!/usr/bin/env bash
# FlowForge — run_tests.sh
# One-command test runner: starts Docker, sets env, checks DB, runs pytest.
#
# Usage (run from the project root or tests/):
#   ./tests/run_tests.sh              # full suite (default)
#   ./tests/run_tests.sh --unit       # crypto only — no DB, no Docker needed
#   ./tests/run_tests.sh --quick      # skip slow integration tests
#   ./tests/run_tests.sh --manual     # manual API smoke test against running app
#   ./tests/run_tests.sh -- -x -k auth  # pass extra flags straight to pytest
#
# Environment:
#   Reads from .env.test if present (gitignored), otherwise uses the dev defaults
#   defined below. Override any value by exporting it before running.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Resolve python ───────────────────────────────────────────────────────────
if   [[ -f "$ROOT/.venv/Scripts/python.exe" ]]; then PYTHON="$ROOT/.venv/Scripts/python.exe"  # Windows/Git Bash
elif [[ -f "$ROOT/.venv/bin/python"         ]]; then PYTHON="$ROOT/.venv/bin/python"
else PYTHON="python3"
fi

# ── Parse args ───────────────────────────────────────────────────────────────
MODE='full'
API_URL='http://localhost:5000'
API_USER='admin'
API_PASS="${FLOWFORGE_PASSWORD:-}"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)   MODE='unit'   ;;
        --quick)  MODE='quick'  ;;
        --manual) MODE='manual' ;;
        --url=*)  API_URL="${1#*=}" ;;
        --user=*) API_USER="${1#*=}" ;;
        --pass=*) API_PASS="${1#*=}" ;;
        --)       shift; EXTRA_ARGS+=("$@"); break ;;
        *)        EXTRA_ARGS+=("$1") ;;
    esac
    shift
done

# ── Env vars ─────────────────────────────────────────────────────────────────
# Load .env.test if present (gitignored); skip keys already in the environment.
ENV_FILE="$ROOT/.env.test"
if [[ -f "$ENV_FILE" ]]; then
    while IFS='=' read -r key val; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue   # skip comments
        [[ -z "$key" ]]               && continue   # skip blank lines
        key="${key// /}"
        if [[ -z "${!key:-}" ]]; then
            export "$key"="$val"
        fi
    done < "$ENV_FILE"
fi

# Test-run secrets. Nothing is baked into this script: the DB URL must come from .env.test
# (see .env.test.example) or the environment, and the encryption/JWT keys are random per run
# unless you set them. The test database is recreated on every run, so a fresh key is fine.
: "${FLOWFORGE_DB_URL:?FLOWFORGE_DB_URL is not set - copy .env.test.example to .env.test and fill it in}"
new_hex_key() { python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || openssl rand -hex 32; }
export FLOWFORGE_SECRET_KEY="${FLOWFORGE_SECRET_KEY:-$(new_hex_key)}"
export FLOWFORGE_JWT_SECRET="${FLOWFORGE_JWT_SECRET:-$(new_hex_key)}"
export FLOWFORGE_DB_URL

# ── Manual smoke test ────────────────────────────────────────────────────────
if [[ "$MODE" == "manual" ]]; then
    echo ""
    echo "Running manual API smoke test..."
    exec "$PYTHON" "$ROOT/tests/manual/check_api.py" --url "$API_URL" --user "$API_USER" --pass "$API_PASS"
fi

# ── Unit-only mode ───────────────────────────────────────────────────────────
if [[ "$MODE" == "unit" ]]; then
    echo ""
    echo "Running unit tests (no DB required)..."
    exec "$PYTHON" -m pytest "$ROOT/tests/test_crypto.py" -v "${EXTRA_ARGS[@]}"
fi

# ── Docker: ensure DB container is up ────────────────────────────────────────
echo ""
echo "Checking Docker containers..."

running_services=$(docker compose -f "$ROOT/docker-compose.yml" ps --status running --services 2>/dev/null || true)
if ! echo "$running_services" | grep -q '^db$'; then
    echo "  Starting containers (docker compose up -d)..."
    docker compose -f "$ROOT/docker-compose.yml" up -d >/dev/null
fi

# Wait for DB healthy (up to 30 s)
echo "  Waiting for DB to be healthy..."
healthy=false
for _ in $(seq 1 15); do
    status=$(docker inspect flowforge-db-1 --format '{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    if [[ "$status" == "healthy" ]]; then healthy=true; break; fi
    sleep 2
done
if [[ "$healthy" != "true" ]]; then
    echo "  DB did not become healthy in 30 s. Check: docker compose ps" >&2
    exit 1
fi
echo "  DB is healthy."

# ── DB pre-check ─────────────────────────────────────────────────────────────
echo ""
echo "Running DB pre-check..."
"$PYTHON" "$ROOT/tests/check_test_env.py"

# ── Pytest ────────────────────────────────────────────────────────────────────
echo ""
if [[ "$MODE" == "quick" ]]; then
    echo "Running quick test suite (skipping slow integration tests)..."
    "$PYTHON" -m pytest "$ROOT/tests" -v --tb=short --ignore="$ROOT/tests/manual" -m 'not slow' "${EXTRA_ARGS[@]}"
else
    echo "Running full test suite..."
    "$PYTHON" -m pytest "$ROOT/tests" -v --tb=short --ignore="$ROOT/tests/manual" "${EXTRA_ARGS[@]}"
fi

exit_code=$?
echo ""
if [[ $exit_code -eq 0 ]]; then
    echo "All tests passed."
else
    echo "Tests failed (exit $exit_code)."
fi
exit $exit_code
