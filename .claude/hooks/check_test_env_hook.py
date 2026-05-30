"""
Claude Code PreToolUse hook.

Intercepts PowerShell/Bash tool calls that contain 'pytest' or 'run_tests'
and runs tests/check_test_env.py first.  If the DB pre-check fails the tool
call is blocked and a clear diagnostic message is shown.

Input:  JSON payload on stdin (Claude Code hook protocol)
Output: JSON on stdout only when blocking  {"continue": false, "stopReason": "..."}
Exit:   0 = allow the tool call through
        1 = block the tool call (JSON written to stdout)
"""
import json
import os
import subprocess
import sys


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return 0  # not valid JSON — don't block

    cmd = (payload.get("tool_input") or {}).get("command", "")
    if not cmd or ("pytest" not in cmd and "run_tests" not in cmd):
        return 0  # not a test command — skip check

    # Locate project root (this file lives at <root>/.claude/hooks/)
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Prefer the project venv; fall back to whatever python is on PATH
    venv_python = os.path.join(root, ".venv", "Scripts", "python.exe")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    check_script = os.path.join(root, "tests", "check_test_env.py")
    result = subprocess.run(
        [python, check_script],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        msg = (result.stdout + result.stderr).strip()
        output = {
            "continue": False,
            "stopReason": (
                "Test DB pre-check failed:\n\n"
                + msg
                + "\n\nFix FLOWFORGE_DB_URL and ensure the test database is running, then retry."
            ),
        }
        print(json.dumps(output))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
