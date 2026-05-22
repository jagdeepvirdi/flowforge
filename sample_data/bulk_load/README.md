# Bulk Load — Sample Data & Test Setup

## What's here

```
sample_data/bulk_load/
├── incoming/
│   ├── SUBS_20260522_001.csv   ← 10 subscribers (batch 1)
│   ├── SUBS_20260522_002.csv   ← 10 subscribers (batch 2)
│   └── ORDERS_20260522.csv     ← 3 orders (SKIPPED — wrong prefix)
├── archive/                    ← files move here after load
├── setup_table.sql             ← creates the target table
└── README.md
```

The two `SUBS_` files will be loaded. `ORDERS_20260522.csv` is intentionally
present to demonstrate prefix filtering — it will be skipped.

---

## Step 1 — Create the target table

Run this Python one-liner from the project root (after starting FlowForge):

```powershell
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['FLOWFORGE_DB_URL'])
cur = conn.cursor()
cur.execute(open('sample_data/bulk_load/setup_table.sql').read())
conn.commit(); conn.close()
print('Table created.')
"
```

Or paste the SQL from `setup_table.sql` into any SQL client (pgAdmin, DBeaver, etc.).

---

## Step 2 — Create the Bulk Load config in FlowForge

Open **Bulk Loads → New Bulk Load** and fill in:

| Field | Value |
|---|---|
| Name | `Subscriber Daily Load` |
| Description | `Test bulk load — loads SUBS_ CSV files` |
| Connection | `FlowForge DB` (your PostgreSQL connection) |
| Target table | `public.bulk_test_subscribers` |
| Load mode | `Replace` (truncate + reload each run) |
| Source directory | `D:\Project\flowforge\sample_data\bulk_load\incoming` |
| File type | `CSV` |
| File prefix | `SUBS_` |
| Exclude prefix | *(leave blank)* |
| Header rows | `1` |
| Footer rows | `0` |
| Delimiter | `,` |
| On no files | `Skip (succeed)` |
| Archive directory | `D:\Project\flowforge\sample_data\bulk_load\archive\{{ current_date }}` |

Save the config.

---

## Step 3 — Add a Bulk Load step to a pipeline

1. Open any pipeline (or create a new test pipeline)
2. Add a **Bulk Load** step
3. Pick `Subscriber Daily Load` from the dropdown
4. Save the pipeline

---

## Step 4 — Run it

Click **Run Now** on the pipeline. In Run History you should see:

- **files_found**: 2
- **files_loaded**: 2
- **records_loaded**: 20
- **records_failed**: 0

The two `SUBS_` files will be archived to
`sample_data\bulk_load\archive\<today's date>\`.

---

## Step 5 — Verify the data

```sql
SELECT plan, status, COUNT(*) AS subscribers, SUM(monthly_amount) AS mrr
FROM public.bulk_test_subscribers
GROUP BY plan, status
ORDER BY plan, status;
```

Expected result:

| plan | status | subscribers | mrr |
|---|---|---|---|
| basic | active | 7 | 209.93 |
| basic | cancelled | 1 | 29.99 |
| premium | active | 6 | 599.94 |
| premium | suspended | 1 | 99.99 |
| standard | active | 4 | 239.96 |
| standard | cancelled | 1 | 59.99 |

---

## Re-running the test

After the first run the CSVs are archived. To run again:

```powershell
# Restore files from archive to incoming
Copy-Item "D:\Project\flowforge\sample_data\bulk_load\archive\*\SUBS_*.csv" `
          "D:\Project\flowforge\sample_data\bulk_load\incoming\"
```

Or just copy the originals from git since they're committed.
