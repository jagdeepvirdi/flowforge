"""
Oracle connection + DataLoader smoke test.

Usage:
    pip install oracledb
    python scripts/test_oracle.py

Expects Oracle running via docker-compose (docker compose up oracle).
Default connection: oracle/<ORACLE_PASSWORD>@localhost:1521/FREEPDB1
Set ORACLE_PASSWORD and optionally ORACLE_USER, ORACLE_HOST, ORACLE_PORT,
ORACLE_SERVICE in the environment (or source .env first).
"""

import os
import sys
import time

HOST    = os.environ.get("ORACLE_HOST",    "localhost")
PORT    = int(os.environ.get("ORACLE_PORT", "1521"))
SERVICE = os.environ.get("ORACLE_SERVICE", "FREEPDB1")
USER    = os.environ.get("ORACLE_USER",    "oracle")
PASSWORD = os.environ.get("ORACLE_PASSWORD") or sys.exit(
    "ERROR: ORACLE_PASSWORD env var is not set. Source .env or set it manually."
)

SOURCE_TABLE = "ff_source_data"
TARGET_TABLE = "ff_loaded_data"


def wait_for_oracle(pool, retries: int = 12, delay: int = 5) -> None:
    print(f"Waiting for Oracle at {HOST}:{PORT}/{SERVICE} ...", end="", flush=True)
    for _ in range(retries):
        try:
            with pool.acquire() as conn:
                conn.cursor().execute("SELECT 1 FROM DUAL")
            print(" ready.")
            return
        except Exception:
            print(".", end="", flush=True)
            time.sleep(delay)
    print()
    sys.exit(f"Oracle did not become available after {retries * delay}s.")


def test_connection(pool) -> None:
    print("\n[1] Basic connection test")
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
            banner = cur.fetchone()[0]
    print(f"    OK — {banner}")


def test_dataloader(pool) -> None:
    """
    Simulates the DataLoadStep end-to-end using OracleConnection directly:
      - Creates a source table and seeds it with rows
      - Uses execute_many + make_placeholders (the DataLoader bulk path)
      - Reads rows back to verify
    """
    print("\n[2] DataLoader simulation")

    import oracledb
    from flowforge.connections.oracle import OracleConnection

    conn = OracleConnection(
        host=HOST, port=PORT, service_name=SERVICE,
        user=USER, password=PASSWORD,
    )

    # ── setup: drop tables if they exist ─────────────────────────────────────
    for table in (SOURCE_TABLE, TARGET_TABLE):
        with pool.acquire() as c:
            with c.cursor() as cur:
                cur.execute(
                    f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE {table}'; "
                    f"EXCEPTION WHEN OTHERS THEN NULL; END;"
                )
            c.commit()

    # ── create target table ───────────────────────────────────────────────────
    conn.execute_write(f"""
        CREATE TABLE {TARGET_TABLE} (
            id     NUMBER,
            name   VARCHAR2(100),
            amount NUMBER(12,2)
        )
    """)
    print(f"    Created table {TARGET_TABLE}")

    # ── bulk insert via DataLoader path ───────────────────────────────────────
    columns = ["id", "name", "amount"]
    rows = [
        (1, "Alice",   1500.00),
        (2, "Bob",     2300.75),
        (3, "Charlie",  875.50),
        (4, "Diana",   4200.00),
        (5, "Eve",      320.10),
    ]

    placeholders = conn.make_placeholders(len(columns))
    col_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {TARGET_TABLE} ({col_list}) VALUES ({placeholders})"
    print(f"    INSERT SQL: {insert_sql}")

    total = conn.execute_many(insert_sql, rows)
    print(f"    Bulk inserted {total} rows")

    # ── verify ────────────────────────────────────────────────────────────────
    fetched, cols = conn.execute_query_with_columns(
        f"SELECT id, name, amount FROM {TARGET_TABLE} ORDER BY id"
    )
    print(f"    Queried {len(fetched)} rows ({cols}):")
    for row in fetched:
        print(f"      id={row[0]}  name={row[1]:<10}  amount={row[2]}")

    total_amount = conn.execute_query(f"SELECT SUM(amount) FROM {TARGET_TABLE}")[0][0]
    print(f"    SUM(amount) = {total_amount}")
    assert len(fetched) == 5, "Expected 5 rows"

    # ── replace mode: truncate + reload ──────────────────────────────────────
    print("    Testing replace mode (truncate + reload)...")
    conn.execute_write(f"TRUNCATE TABLE {TARGET_TABLE}")
    new_rows = [(10, "Zara", 9999.99)]
    conn.execute_many(insert_sql, new_rows)
    count = conn.execute_query(f"SELECT COUNT(*) FROM {TARGET_TABLE}")[0][0]
    assert count == 1, f"Expected 1 row after replace, got {count}"
    print("    Replace mode OK — 1 row after truncate+reload")

    # ── teardown ──────────────────────────────────────────────────────────────
    conn.execute_write(f"DROP TABLE {TARGET_TABLE}")
    conn.close()
    print(f"    Dropped table {TARGET_TABLE}")
    print("    DataLoader test PASSED")


def main():
    try:
        import oracledb
    except ImportError:
        sys.exit("oracledb not installed. Run: pip install oracledb")

    # Also ensure flowforge package is importable
    try:
        from flowforge.connections.oracle import OracleConnection  # noqa: F401
    except ImportError:
        sys.exit("flowforge package not found. Run from project root: pip install -e .")

    pool = oracledb.create_pool(
        user=USER, password=PASSWORD,
        dsn=f"{HOST}:{PORT}/{SERVICE}",
        min=1, max=3, increment=1,
    )

    wait_for_oracle(pool)
    test_connection(pool)
    test_dataloader(pool)

    print("\nAll tests passed.")
    pool.close()


if __name__ == "__main__":
    main()
