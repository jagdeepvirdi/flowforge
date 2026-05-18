#!/usr/bin/env bash
# FlowForge - run_tests.sh
# Usage:
#   ./tests/run_tests.sh           # full suite
#   ./tests/run_tests.sh --unit    # crypto only (no DB)
#   ./tests/run_tests.sh --manual  # manual API smoke test

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

MODE='full'
API_URL='http://localhost:5000'
API_USER='admin'
API_PASS='harpal123'

for arg in "$@"; do
    case $arg in
        --unit)   MODE='unit'   ;;
        --manual) MODE='manual' ;;
        --url=*)  API_URL="${arg#*=}" ;;
        --user=*) API_USER="${arg#*=}" ;;
        --pass=*) API_PASS="${arg#*=}" ;;
    esac
done

PYTHON="$ROOT/.venv/bin/python"
[ -f "$PYTHON" ] || PYTHON="python3"

if [ "$MODE" = "manual" ]; then
    echo ""
    echo "Running manual API smoke test..."
    exec "$PYTHON" "$ROOT/tests/manual/check_api.py" --url "$API_URL" --user "$API_USER" --pass "$API_PASS"
fi

if [ "$MODE" = "unit" ]; then
    echo ""
    echo "Running unit tests (no DB required)..."
    exec "$PYTHON" -m pytest "$ROOT/tests/test_crypto.py" -v
fi

echo ""
echo "Running full test suite..."
echo "  Test DB: postgresql://flowforge:***@localhost:5434/flowforge_test"
echo ""
"$PYTHON" -m pytest "$ROOT/tests" -v --tb=short --ignore="$ROOT/tests/manual"
