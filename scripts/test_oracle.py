"""
Oracle connection + DataLoader smoke test.

Usage:
    pip install oracledb
    python scripts/test_oracle.py

Expects Oracle running via docker-compose (docker compose up oracle).
Default connection: flowforge/harpal123@localhost:1521/FREEPDB1
"""

import sys
import time

HOST = "localhost"
PORT = 1521
SERVICE = "FREEPDB1"
USER = "oracle"
PASSWORD = "harpal123"

TEST_TABLE = "ff_dataloader_test"


def wait_for_oracle(pool, retries: int = 12, delay: int = 5) -> None:
    """Poll until Oracle accepts connections (it takes ~2 min on first boot)."""
    print(f"Waiting for Oracle at {HOST}:{PORT}/{SERVICE} ...", end="", flush=True)
    for attempt in range(1, retries + 1):
        try:
            with pool.acquire() as conn:
                conn.cursor().execute("SELECT 1 FROM DUAL")
            print(" ready.")
            return
        except Exception:
            print(".", end="", flush=True)
            time.sleep(delay)
    print()
    sys.exit(f"Oracle did not become available after {retries * delay}s. "
             "Is the container healthy? (docker compose ps oracle)")


def test_connection(pool) -> None:
    print("\n[1] Basic connection test")
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT BANNER FROM V$VERSION WHERE ROWNUM = 1")
            banner = cur.fetchone()[0]
    print(f"    OK — {banner}")


def test_dataloader(pool) -> None:
    """Simulate a DataLoader bulk insert → query cycle."""
    print("\n[2] DataLoader simulation")

    # --- setup ---
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE {TEST_TABLE}'; "
                        f"EXCEPTION WHEN OTHERS THEN NULL; END;")
        conn.commit()

    # --- create table ---
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE {TEST_TABLE} (
                    id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name     VARCHAR2(100)  NOT NULL,
                    amount   NUMBER(12,2),
                    ts       TIMESTAMP DEFAULT SYSTIMESTAMP
                )
            """)
        conn.commit()
    print(f"    Created table {TEST_TABLE}")

    # --- bulk insert (executemany) ---
    rows = [
        ("Alice",   1500.00),
        ("Bob",     2300.75),
        ("Charlie", 875.50),
        ("Diana",   4200.00),
        ("Eve",     320.10),
    ]
    sql = f"INSERT INTO {TEST_TABLE} (name, amount) VALUES (:1, :2)"
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
            inserted = cur.rowcount
        conn.commit()
    print(f"    Bulk inserted {inserted} rows")

    # --- query back ---
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, name, amount FROM {TEST_TABLE} ORDER BY id"
            )
            fetched = cur.fetchall()

    print(f"    Queried {len(fetched)} rows:")
    for row in fetched:
        print(f"      id={row[0]}  name={row[1]:<10}  amount={row[2]}")

    # --- aggregate ---
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT SUM(amount) FROM {TEST_TABLE}")
            total = cur.fetchone()[0]
    print(f"    SUM(amount) = {total}")

    # --- teardown ---
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE {TEST_TABLE}")
        conn.commit()
    print(f"    Dropped table {TEST_TABLE}")
    print("    DataLoader test PASSED")


def main():
    try:
        import oracledb
    except ImportError:
        sys.exit("oracledb not installed. Run: pip install oracledb")

    pool = oracledb.create_pool(
        user=USER,
        password=PASSWORD,
        dsn=f"{HOST}:{PORT}/{SERVICE}",
        min=1,
        max=3,
        increment=1,
    )

    wait_for_oracle(pool)
    test_connection(pool)
    test_dataloader(pool)

    print("\nAll tests passed.")
    pool.close()


if __name__ == "__main__":
    main()
