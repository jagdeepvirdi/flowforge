"""
Pre-test environment check: standalone script.

Validates:
  1. FLOWFORGE_DB_URL is set
  2. The database name contains 'test' (safety guard against wiping prod)
  3. The database is actually reachable

Exit 0 = all good.
Exit 1 = problem — diagnostic message printed to stdout.
"""
import os
import sys


def main() -> int:
    db_url = os.environ.get("FLOWFORGE_DB_URL", "")

    if not db_url:
        print("FLOWFORGE_DB_URL is not set.")
        print("")
        print("Set it before running tests, e.g.:")
        print("  $env:FLOWFORGE_DB_URL = 'postgresql://flowforge:<password>@localhost:5434/flowforge_test'")
        return 1

    db_name = db_url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]

    if "test" not in db_name.lower():
        print(f"FLOWFORGE_DB_URL points to '{db_name}' — not a test database.")
        print("")
        print("The database name must contain 'test' to prevent accidental data loss.")
        print("Update FLOWFORGE_DB_URL to point to your test database (e.g. flowforge_test).")
        return 1

    try:
        import psycopg2  # noqa: PLC0415
    except ImportError:
        print("psycopg2 is not installed in the current environment.")
        print("Run: .venv\\Scripts\\pip.exe install psycopg2-binary")
        return 1

    try:
        conn = psycopg2.connect(db_url, connect_timeout=5)
        conn.close()
        print(f"Test DB OK — connected to '{db_name}'")
        return 0
    except Exception as exc:
        print(f"Cannot connect to test database '{db_name}'.")
        print(f"  Error: {exc}")
        print("")
        print("Check that:")
        print("  1. Docker is running  →  docker compose ps")
        print("  2. FLOWFORGE_DB_URL host/port/credentials are correct")
        print(f"  Current FLOWFORGE_DB_URL: {db_url}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
