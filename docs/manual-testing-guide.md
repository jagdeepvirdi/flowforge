# FlowForge — Manual Testing Guide

Use this document to verify each major feature end-to-end before shipping or
after a significant change. Work through each section in order — earlier
sections create the connections and configs that later sections depend on.

Mark each checkbox as you complete it. `<repo>` below means the folder you cloned
FlowForge into.

**Already covered by automated tests** (no need to repeat by hand): the backend
suite (`pytest`) and the Playwright E2E suite (`frontend/e2e`). The E2E suite
includes the "Brain not attached" checks (no AI UI anywhere, `/api/ai/*` returns
`503`). This guide is for what
automation cannot judge: real email and cloud delivery, files on disk, and
anything that needs an external account.

---

## Prerequisites

- FlowForge server running: `flowforge web` (or `.\flowforge.ps1 start` / `./flowforge.sh start`)
- PostgreSQL running on `localhost:5434`
- Browser open at `http://localhost:5000`
- An admin account to log in with. On a fresh install run `flowforge db seed`: it prints a
  one-time password (change it at first login). To add a throwaway tester later:
  `flowforge user create tester --role admin --generate-password`. The password is printed
  once; no password is ever stored in a file or typed on a command line.

---

## 1. Connections Setup

These are required by almost every test below. Set them up first.

### 1a. PostgreSQL connection

1. Go to **Connections → Add connection**
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `FlowForge DB` |
   | Type | `PostgreSQL` |
   | Host | `localhost` |
   | Port | `5434` |
   | Database | `flowforge` |
   | Username | `flowforge` |
   | Password | *(your local DB password from `.env`)* |

3. Click **Test connection** — expect green / latency shown
4. Save

- [ ] Connection saved and test passes

### 1b. Gmail provider

1. Go to **Connections → Email providers → Add provider**
2. Select **Gmail**
3. Run OAuth2 setup if not already done: `flowforge setup gmail`
4. Fill in Client ID, Client Secret, Refresh Token, Sender email
5. Save and test

- [ ] Gmail provider saved

### 1c. Microsoft 365 provider

1. Go to **Connections → Email providers → Add provider**
2. Select **Microsoft 365**
3. Fill in Tenant ID, Client ID, Client Secret, Sender email
   (requires an Azure AD app registration with `Mail.Send` permission)
4. Run: `flowforge setup microsoft365` to complete device-code auth
5. Save and test

- [ ] M365 provider saved
- [ ] Test send succeeds (check the inbox of the sender address)

### 1d. SMTP provider (optional — covers Outlook, Yahoo, custom)

1. Go to **Connections → Email providers → Add provider**
2. Select **SMTP**
3. Fill in host, port, credentials
4. Save and test

- [ ] SMTP provider saved

---

## 2. Bulk Load

Sample data is committed at `<repo>\sample_data\bulk_load\`.

### 2a. Create the target table

Run once in any SQL client (pgAdmin, DBeaver, or the one-liner below):

```powershell
python -c "
import os, psycopg2
conn = psycopg2.connect(os.environ['FLOWFORGE_DB_URL'])
cur = conn.cursor()
cur.execute(open('sample_data/bulk_load/setup_table.sql').read())
conn.commit(); conn.close()
print('Done.')
"
```

- [ ] `public.bulk_test_subscribers` table created

### 2b. Create the Bulk Load config

Go to **Bulk Loads → New Bulk Load** and fill in:

| Field | Value |
|---|---|
| Name | `Subscriber Daily Load` |
| Connection | `FlowForge DB` |
| Target table | `public.bulk_test_subscribers` |
| Load mode | `Replace` |
| Source directory | `<repo>\sample_data\bulk_load\incoming` |
| File type | `CSV` |
| File prefix | `SUBS_` |
| Header rows | `1` |
| Footer rows | `0` |
| Delimiter | `,` |
| On no files | `Skip (succeed)` |
| Archive directory | `<repo>\sample_data\bulk_load\archive\{{ current_date }}` |

Save the config.

- [ ] Bulk Load config saved

### 2c. Add to a pipeline and run

1. Create a new pipeline: **Pipelines → New Pipeline** → name `Bulk Load Test`
2. Add a **Bulk Load** step → pick `Subscriber Daily Load`
3. Save and click **Run Now**
4. Check Run History — expand the step log

Expected results:

| Metric | Expected |
|---|---|
| files_found | 2 |
| files_loaded | 2 |
| records_loaded | 20 |
| records_failed | 0 |

- [ ] Run succeeds
- [ ] Step log shows 2 files, 20 records
- [ ] CSV files moved to `sample_data\bulk_load\archive\<today>\`
- [ ] `ORDERS_20260522.csv` was NOT loaded (prefix filtered)

### 2d. Verify data in DB

```sql
SELECT plan, status, COUNT(*) AS subscribers, SUM(monthly_amount) AS mrr
FROM public.bulk_test_subscribers
GROUP BY plan, status
ORDER BY plan, status;
```

Expected:

| plan | status | subscribers | mrr |
|---|---|---|---|
| basic | active | 6 | 179.94 |
| basic | cancelled | 1 | 29.99 |
| premium | active | 6 | 599.94 |
| premium | suspended | 1 | 99.99 |
| standard | active | 5 | 299.95 |
| standard | cancelled | 1 | 59.99 |

- [ ] Data matches expected

### 2e. Re-run test (restore files first)

```powershell
Copy-Item "<repo>\sample_data\bulk_load\archive\*\SUBS_*.csv" `
          "<repo>\sample_data\bulk_load\incoming\"
```

Run the pipeline again. Because load mode is **Replace**, the table should
still have exactly 20 rows after the second run (not 40).

- [ ] Second run succeeds with 20 rows, not 40

---

## 3. DB Query Step

### 3a. Simple query — write to output table

Unlike Bulk Load's `create_if_missing`, `db_query`'s `output_table` requires
the target table to already exist — `Replace`/`Truncate + Insert` only
`TRUNCATE` it, and `Append` only `INSERT`s, so create it first:

```sql
DROP TABLE IF EXISTS public.subscriber_summary;

CREATE TABLE public.subscriber_summary (
    plan    VARCHAR(50),
    status  VARCHAR(20),
    cnt     INTEGER,
    mrr     NUMERIC(10, 2)
);
```

- [ ] `public.subscriber_summary` table created

1. Create a pipeline: `DB Query Test`
2. Add a **DB Query** step named `plan_summary`:

   | Field | Value |
   |---|---|
   | Step name | `plan_summary` |
   | Connection | `FlowForge DB` |
   | Query | `SELECT plan, status, COUNT(*) AS cnt, SUM(monthly_amount) AS mrr FROM public.bulk_test_subscribers GROUP BY plan, status ORDER BY plan, status` |
   | Output table | `public.subscriber_summary` |
   | Mode | `Replace` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] `public.subscriber_summary` populated (6 rows)

### 3b. Query with Jinja2 variable + downstream email

Reuses the `plan_summary` step from 3a. The query stays aggregated so it
still fits `subscriber_summary`'s 4 columns (avoids the column-count
mismatch a `SELECT *` against `bulk_test_subscribers` would hit), but is
now filtered by a pipeline variable. A downstream email step makes the
filtered result actually visible instead of only inferable from "no error" —
`db_query` has no results preview of its own, and Run History only shows
the row count.

1. Add a pipeline variable: `target_plan = premium`
2. Edit the `plan_summary` step's query:
   ```sql
   SELECT plan, status, COUNT(*) AS cnt, SUM(monthly_amount) AS mrr
   FROM public.bulk_test_subscribers
   WHERE plan = '{{ target_plan }}'
   GROUP BY plan, status
   ORDER BY plan, status
   ```
   Leave **Output table** (`public.subscriber_summary`) and **Mode**
   (`Replace`) as-is.
3. Tick **Capture rows for email**, set **Row limit** to `10`.
4. Add an **Email** step after `plan_summary` (using your Gmail config).
5. In the email body, add:
   ```html
   <p>Filtered summary for {{ target_plan }}:</p>
   {{ steps.plan_summary.table_html }}
   ```
6. Run the pipeline.

Expected rows (premium only):

| plan | status | cnt | mrr |
|---|---|---|---|
| premium | active | 6 | 599.94 |
| premium | suspended | 1 | 99.99 |

- [ ] Variable resolved correctly — query filtered to premium only
- [ ] `public.subscriber_summary` now holds 2 rows, not 6 — `Replace` mode
      overwrote 3a's result
- [ ] Email received with a table showing exactly those 2 rows

### 3c. Query → email with results (capture_rows)

Tests that query rows are captured, rendered as HTML, and appear correctly
in a sent email — without the user writing any raw Jinja2.

**Setup — create the pipeline**

1. Create a pipeline: `Capture Rows Test`
2. Add a **DB Query** step named `load_summary`:

   | Field | Value |
   |---|---|
   | Connection | `FlowForge DB` |
   | Query | `SELECT plan, status, COUNT(*) AS subscribers, SUM(monthly_amount) AS mrr FROM public.bulk_test_subscribers GROUP BY plan, status ORDER BY plan, status` |
   | Output table | *(leave blank)* |
   | Capture rows for email | **Ticked** |
   | Row limit | `10` |

3. Add an **Email** step (using your Gmail config):
   - In the Pipeline Builder, look at the **Query data** section under the email step — it should list `load_summary` with three snippet options.

- [ ] "Query data — available in email body" section appears in the email step, listing `load_summary`
- [ ] Three snippet lines visible: `table_html`, `kv_html`, custom loop

**Setup — configure the email body**

4. Open the email config in **Email Templates**
5. Set the body to:

   ```html
   <p>Hi,</p>
   <p>Here is the subscriber breakdown for {{ current_month }}:</p>

   {{ steps.load_summary.table_html }}

   <p>Top-line summary:</p>

   {{ steps.load_summary.kv_html }}

   <p>Custom loop:</p>
   <ul>
   {% for row in steps.load_summary.rows %}
   <li>{{ row.plan }} / {{ row.status }}: {{ row.subscribers }} subscribers, ${{ row.mrr }}</li>
   {% endfor %}
   </ul>
   ```

6. Check the **Available variables** card on the right — confirm `{{ steps.step_name.table_html }}`, `{{ steps.step_name.kv_html }}`, and the `{% for row %}` loop are listed.

- [ ] New capture variables present in Available Variables card

**Run and verify**

7. Save the email config and return to the pipeline. Run it via **Run Now**.

- [ ] Pipeline succeeds — both steps green in Run History
- [ ] Email received. It goes to the To address of the email config you picked (a direct address or its
      recipient group), so check the inbox that config is actually wired to
- [ ] Email body contains an HTML `<table>` with columns `plan`, `status`, `subscribers`, `mrr`
- [ ] Table has 6 data rows (one per plan/status combination)
- [ ] `kv_html` block shows the first row as a key-value list (`plan`, `status`, `subscribers`, `mrr` as label:value)
- [ ] Custom loop `<ul>` contains 6 `<li>` items with plan/status/count/mrr values

**Row limit test**

8. Edit the `load_summary` step — set **Row limit** to `2`
9. Re-run the pipeline

- [ ] Email table now has exactly 2 data rows (not 6)
- [ ] `rows_affected` in the step run log still shows `6` (full query count, not capped)

**Capture disabled test**

10. Untick **Capture rows for email** on the `load_summary` step
11. Re-run the pipeline

- [ ] Email sent without error (body renders with empty strings where `table_html`/`kv_html` were)
- [ ] "Query data" section disappears from the email step in Pipeline Builder

---

## 4. DB Procedure Step

*(Requires a stored procedure to exist in the target DB.)*

### 4a. PostgreSQL procedure

Create a test procedure first. The db_procedure step issues a plain SQL `CALL`,
which PostgreSQL only allows on objects created with `CREATE PROCEDURE` — a
`CREATE FUNCTION` (even one `RETURNS void`) will fail with "is not a
procedure ... HINT: To call a function, use SELECT.":

```sql
CREATE OR REPLACE PROCEDURE public.ff_test_proc(p_plan TEXT)
LANGUAGE plpgsql AS $$
BEGIN
  RAISE NOTICE 'ff_test_proc called with plan=%', p_plan;
END;
$$;
```

Then in a pipeline, add a **DB Procedure** step:

| Field | Value |
|---|---|
| Connection | `FlowForge DB` |
| Procedure | `public.ff_test_proc` |
| Parameters | `{ "p_plan": "premium" }` |

Run the pipeline.

- [ ] Step succeeds with no error
- [ ] Logs visible in step run detail

### 4b. Oracle package (if Oracle connection configured)

Create a test package first. The db_procedure step runs `BEGIN name(:param1, ...); END;`,
so `name` must resolve to a callable procedure — a package-qualified procedure
(`PKG_NAME.PROC_NAME`) works, same as a standalone one. Connect as the app user
of your Oracle test database and run:

```sql
CREATE OR REPLACE PACKAGE pkg_ff_test AS
  PROCEDURE test_proc(p_plan IN VARCHAR2);
END pkg_ff_test;
/

CREATE OR REPLACE PACKAGE BODY pkg_ff_test AS
  PROCEDURE test_proc(p_plan IN VARCHAR2) IS
  BEGIN
    DBMS_OUTPUT.PUT_LINE('pkg_ff_test.test_proc called with plan=' || p_plan);
  END test_proc;
END pkg_ff_test;
/
```

Then in a pipeline, add a **DB Procedure** step:

| Field | Value |
|---|---|
| Connection | Your Oracle connection |
| Procedure | `pkg_ff_test.test_proc` |
| Parameters | `{ "p_plan": "premium" }` |

Run the pipeline.

- [ ] Step succeeds with no error
- [ ] Logs visible in step run detail

---

## 5. Report Generation

### 5a. CSV report

1. Go to **Reports → New Report**
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `Subscriber Summary CSV` |
   | Connection | `FlowForge DB` |
   | Query | `SELECT * FROM public.bulk_test_subscribers ORDER BY plan, status` |
   | Format | `CSV` |
   | Output filename | `subscribers_{{ current_date }}.csv` |

3. Click **Preview** — confirm rows appear
4. Add to a pipeline as a **Report** step and run

- [ ] Preview shows data
- [ ] Pipeline run generates the CSV file
- [ ] Output path visible in step run log

### 5b. Excel report

Repeat 5a with format `Excel`, add a sheet name `Subscribers`.

- [ ] Excel file generated and downloadable

### 5c. PDF report (requires WeasyPrint)

Repeat 5a with format `PDF`.

- [ ] PDF generated (or clear error if WeasyPrint not installed)

---

## 6. Email — Gmail

### 6a. Basic email send

1. Go to **Email Templates → New Email**
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `Test Email — Gmail` |
   | Provider | Gmail provider |
   | To | an address you can read |
   | Subject | `FlowForge test email {{ current_date }}` |
   | Body | `<p>This is a test email sent at {{ current_date }}.</p>` |

3. Add to a pipeline as an **Email** step and run

- [ ] Email received in inbox
- [ ] Subject has date resolved (not literal `{{ current_date }}`)

### 6b. Email with report attachment

1. Create a pipeline: **Report → Email**
   - Step 1: Report step (generates CSV)
   - Step 2: Email step → Attachments: `{{ steps.step1_name.output_path }}`
2. Run the pipeline

- [ ] Email received with CSV attached

### 6c. Smart attachment (large file → Drive link)

1. Set the email config's **Max attachment size** to `0.001` MB (1 KB) to
   force Drive upload even for small files
2. Run the Report → Email pipeline again

- [ ] Email received with a Drive link in the body instead of an attachment
- [ ] Drive link opens the file

- [ ] Reset max attachment size back to `10` MB after testing

---

## 7. Email — Microsoft 365

Repeat tests 6a and 6b using the M365 provider instead of Gmail.

- [ ] Email received via M365
- [ ] Attachment delivered correctly

---

## 8. Google Drive Upload

### 8a. Standalone Drive upload step

1. Create a pipeline: **Report → Drive Upload**
   - Step 1: Report step (CSV)
   - Step 2: Drive Upload step:

     | Field | Value |
     |---|---|
     | File path | `{{ steps.step1_name.output_path }}` |
     | Folder ID | Your Google Drive folder ID |
     | Rename to | `report_{{ current_date }}.csv` |

2. Run the pipeline

- [ ] File appears in Google Drive folder with correct name
- [ ] `drive_url` visible in step run log

---

## 9. Data Load Step (data_load)

### 9a. File → DB (append mode)

1. Create a pipeline with a **Data Load** step:

   | Field | Value |
   |---|---|
   | Source type | `File` |
   | File path | `<repo>\sample_data\bulk_load\incoming\SUBS_20260522_001.csv` |
   | Target connection | `FlowForge DB` |
   | Target table | `public.bulk_test_subscribers` |
   | Mode | `Append` |

2. Run the pipeline

- [ ] 10 rows appended

### 9b. File → DB with create_if_missing

1. Use a table name that does NOT exist yet, e.g. `public.dl_test_new`
2. Tick **Create table if it doesn't exist**
3. Run the pipeline

- [ ] Table created automatically with correct inferred column types
- [ ] Rows loaded
- [ ] Check column types in pgAdmin: `subscriber_id` → TEXT, `monthly_amount` → NUMERIC, `start_date` → DATE

- [ ] Re-run pipeline — table already exists, data appended, no error

### 9c. Query → DB (cross-connection load)

1. Add a **Data Load** step with source type **SQL Query**:

   | Field | Value |
   |---|---|
   | Source connection | `FlowForge DB` |
   | Query | `SELECT subscriber_id, plan, monthly_amount FROM public.bulk_test_subscribers WHERE status = 'active'` |
   | Target connection | `FlowForge DB` |
   | Target table | `public.active_subscribers` |
   | Mode | `Replace` |
   | Create if missing | Ticked |

2. Run the pipeline

- [ ] `public.active_subscribers` created and populated with active subscribers only

---

## 10. Pipeline Variables

Pipeline variables let you define constants once at the pipeline level and reference them in
every step via `{{ var_key }}` or `{{ vars.var_key }}`.

### 10a. Constant value (currency / region filter)

1. Open any pipeline (e.g. `Query Test`) → **Variables** card → **Add variable**
2. Set:

   | Key | Value | Secret |
   |---|---|---|
   | `currency` | `USD` | No |

3. Edit the DB Query step to use it:
   ```sql
   SELECT * FROM public.bulk_test_subscribers
   WHERE plan = '{{ currency }}'
   ```
   *(or substitute a real column for your data)*
4. Save and run

- [ ] Variable resolved — query does not contain the literal `{{ currency }}`
- [ ] Step log shows results filtered to the variable value

### 10b. Date-range constants (timestamp boundaries)

1. Add two variables to the pipeline:

   | Key | Value | Secret |
   |---|---|---|
   | `from_ts` | `{{ month_start_ts }}` | No |
   | `to_ts` | `{{ month_end_ts }}` | No |

   *(These reference built-in timestamp variables — `YYYYMMDDHHmmSS` format)*
2. In the query step use:
   ```sql
   SELECT * FROM public.bulk_test_subscribers
   WHERE CAST(created_at AS TEXT) BETWEEN '{{ from_ts }}' AND '{{ to_ts }}'
   ```
3. Run and check step log for the resolved values

Available timestamp built-ins (all 14-digit `YYYYMMDDHHmmSS`):

| Variable | Meaning |
|---|---|
| `{{ day_start_ts }}` | Today 00:00:00 |
| `{{ day_end_ts }}` | Today 23:59:59 |
| `{{ yesterday_start_ts }}` | Yesterday 00:00:00 |
| `{{ yesterday_end_ts }}` | Yesterday 23:59:59 |
| `{{ month_start_ts }}` | First of month 00:00:00 |
| `{{ month_end_ts }}` | Last of month 23:59:59 |
| `{{ prev_month_start_ts }}` | First of previous month 00:00:00 |
| `{{ prev_month_end_ts }}` | Last of previous month 23:59:59 |

- [ ] `{{ month_start_ts }}` resolves to a 14-digit timestamp (e.g. `20260501000000`)
- [ ] `{{ prev_month_end_ts }}` resolves to last day of previous month at 23:59:59

### 10c. Delta extraction (last_success_at)

`{{ last_success_at }}` is injected automatically by the runner: it holds the
`finished_at` timestamp of the most recent successful run for this pipeline
(or empty string on the first run).

1. Use this query in a DB Query step:
   ```sql
   {% if last_success_at %}
   SELECT * FROM public.bulk_test_subscribers
   WHERE updated_at >= '{{ last_success_at }}'
   {% else %}
   SELECT * FROM public.bulk_test_subscribers
   {% endif %}
   ```
2. Run the pipeline twice:
   - First run: `last_success_at` is empty → full extract
   - Second run: `last_success_at` = first run's finish time → delta extract

- [ ] First run: full extract (no date filter in logs)
- [ ] Second run: delta filter applied (`last_success_at` value appears in logs)

Also available: `{{ last_success_date }}` — same run, YYYY-MM-DD format.

### 10d. Secret variable (credential)

1. Add a variable:

   | Key | Value | Secret |
   |---|---|---|
   | `api_key` | `my-secret-value` | Yes (ticked) |

2. Save the pipeline
3. GET the pipeline via API or reload the page

- [ ] Secret var shows `***` in the UI — plaintext never returned
- [ ] Variable is still usable in step configs (resolved at runtime)

---

## 11. Data Load — create_if_missing

### 11a. Auto-create with type inference

1. Create a pipeline: `Data Load Auto-Create Test`
2. Add a **Data Load** step:

   | Field | Value |
   |---|---|
   | Source type | `File` |
   | File path | `<repo>\sample_data\bulk_load\incoming\SUBS_20260522_001.csv` |
   | Target connection | `FlowForge DB` |
   | Target table | `public.dl_auto_{{ current_date }}` |
   | Mode | `Append` |
   | Create table if missing | Ticked |

3. Run the pipeline
4. Open pgAdmin or a SQL client and inspect:

   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_schema = 'public'
     AND table_name LIKE 'dl_auto_%'
   ORDER BY ordinal_position;
   ```

Expected column types (based on SUBS CSV):

| Column | Expected type |
|---|---|
| `subscriber_id` | text |
| `plan` | text |
| `status` | text |
| `monthly_amount` | numeric |
| `start_date` | date |

- [ ] Run succeeds — step log shows "(table auto-created)"
- [ ] Table exists in DB with the correct columns
- [ ] Numeric column is `numeric`, not `text`
- [ ] Date column is `date`, not `text`

### 11b. Re-run — table already exists

Run the same pipeline again (without dropping the table).

- [ ] Run succeeds — no "table auto-created" note in step log
- [ ] Rows appended correctly (no error about existing table)

### 11c. Replace mode with auto-create

Edit the step to use mode `Replace` instead of `Append`, then run on a table
that doesn't exist yet (rename `target_table` to `public.dl_replace_test`).

- [ ] Table auto-created AND truncated on first run
- [ ] Second run: table truncated, same row count (not doubled)

---

## 12. Scheduling

1. Open a pipeline → set a schedule (e.g. every 5 minutes: `*/5 * * * *`)
2. Enable the schedule and wait
3. Check Run History — pipeline should appear as triggered by `scheduler`
4. Disable the schedule

- [ ] Scheduled run appears in history with `triggered_by = scheduler`
- [ ] Schedule disabled without deleting the pipeline

---

## 13. OneDrive Upload

*(Requires Azure AD app registration with `Files.ReadWrite.All` permission.
Same credentials as M365 email — set `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`,
`MICROSOFT_CLIENT_SECRET`, `MICROSOFT_SENDER_EMAIL` in `.env`.)*

### 13a. Standalone OneDrive upload step

1. Create a pipeline: **Report → OneDrive Upload**
   - Step 1: Report step (CSV or Excel)
   - Step 2: OneDrive Upload step:

     | Field | Value |
     |---|---|
     | File path | `{{ steps.step1_name.output_path }}` |
     | Folder ID | Your OneDrive folder ID (from the folder URL) |
     | Rename to | `report_{{ current_date }}.csv` |
     | Make shareable | Ticked |

2. Run the pipeline

- [ ] File appears in OneDrive folder with the correct name
- [ ] `drive_url` (anonymous view link) visible in step run log
- [ ] Link opens the file in a browser without login

### 13b. OneDrive link in email body

1. Extend the pipeline from 13a — add an **Email** step after the upload:
   - In the email body: `<p>Your report: <a href="{{ steps.upload_step.drive_url }}">Click here</a></p>`
2. Run the pipeline

- [ ] Email received with a working OneDrive link
- [ ] Link resolves to the correct file

### 13c. OneDrive as smart attachment fallback

1. In an Email config, set `onedrive_folder_id` and set **Max attachment size** to `0.001` MB
2. Attach a report file that exceeds this threshold
3. Run the pipeline

- [ ] Email received with OneDrive link in body instead of direct attachment
- [ ] Log shows "smart attachment → OneDrive"

---

## 14. SFTP Transfer Step (sftp_transfer)

*(Requires an accessible SFTP server. For local testing:
`docker run -p 2222:22 -e SSH_USERS="testuser:1001" atmoz/sftp` or
use any accessible SFTP endpoint you have credentials for.)*

### 14a. Download single file

1. Create a pipeline: `SFTP Test`
2. Add an **SFTP Transfer** step:

   | Field | Value |
   |---|---|
   | Host | `localhost` (or your SFTP host) |
   | Port | `2222` (or `22`) |
   | Username | `testuser` |
   | Password | *(your SFTP password)* |
   | Operation | `download` |
   | Remote path | `/upload/test_file.csv` (a file that exists on the server) |
   | Local path | `<repo>\sample_data\sftp_test\` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] File downloaded to `sample_data\sftp_test\test_file.csv`
- [ ] `output_path` visible in step run log
- [ ] `files_loaded = 1` in log

### 14b. Download directory with glob pattern

1. Edit the step:
   - Remote path: `/upload/` (a directory)
   - Pattern: `*.csv`
   - Local path: `<repo>\sample_data\sftp_test\`

- [ ] Only `.csv` files downloaded (any `.txt` or other files skipped)
- [ ] `files_found` and `files_loaded` counts visible in log

### 14c. overwrite=false skips existing

1. Run the download step again with `overwrite: false`

- [ ] Step succeeds
- [ ] `files_loaded = 0` — already-downloaded files are skipped, not overwritten
- [ ] No error

### 14d. Upload file

1. Generate a small file locally (or use a report output)
2. Add an SFTP Transfer step:

   | Field | Value |
   |---|---|
   | Operation | `upload` |
   | Local path | `{{ steps.report_step.output_path }}` (or a hard-coded path) |
   | Remote path | `/upload/reports/{{ current_date }}/` |
   | Create remote dirs | Ticked |

3. Run the pipeline

- [ ] File uploaded to the correct remote path
- [ ] Remote directory created automatically (if it didn't exist)
- [ ] `files_loaded = 1` in log

### 14e. Private key authentication

1. Configure the step with `key_path` (path to a local private key) instead of `password`
2. Run the pipeline

- [ ] Step connects successfully using the private key
- [ ] No error about missing password

### 14f. Invalid host / credentials

1. Set the host to a non-existent server and run

- [ ] Step fails with a clear "SFTP error" message
- [ ] Pipeline error recorded in Run History with the step name

---

## 15. Multi-User Roles & Access Control

*(Create the test accounts below in Settings → Users, or from a terminal with
`flowforge user create editor_test --role editor --generate-password`.)*

### 15a. Create users with different roles

1. Log in as `admin`
2. Go to **Settings → Users → Add User**
3. Create three accounts:

   | Username | Role |
   |---|---|
   | `editor_test` | `editor` |
   | `viewer_test` | `viewer` |
   | `admin_test` | `admin` |

- [ ] All three users created and visible in the user list

### 15b. Viewer restrictions

1. Log out and log in as `viewer_test`
2. Open the Dashboard — pipelines are visible

- [ ] **Run Now** button is absent or disabled on pipeline cards
- [ ] No **New Pipeline** button visible
- [ ] Connections page: no **Add** or **Delete** buttons
- [ ] Settings → Users page: not accessible (redirected or 403)

### 15c. Editor permissions

1. Log in as `editor_test`
2. Create a new pipeline, add a step, and save

- [ ] Pipeline created successfully
- [ ] **Run Now** works — pipeline runs
- [ ] Settings → Users page: not accessible

### 15d. Admin full access

1. Log in as `admin_test`

- [ ] Can access Settings → Users
- [ ] Can create/edit/delete users
- [ ] Can run pipelines and edit all configs

### 15e. Self-service password change

1. Log in as `editor_test`
2. Go to **Settings → Change Password**
3. Enter current password and a new one, confirm

- [ ] Password changed successfully
- [ ] Can log in with the new password
- [ ] Old password rejected

### 15f. JWT token revocation (logout)

1. Log in as any user — capture the JWT token from browser DevTools (Application → Local Storage → `flowforge-auth` → the `token` value inside `state`)
2. Click **Sign out** at the bottom of the sidebar
3. In Postman or curl, call any protected endpoint with the old token:
   ```
   GET /api/pipelines
   Authorization: Bearer <old-token>
   ```

- [ ] Server returns `401 Unauthorized` — token is revoked immediately on logout
- [ ] Logging back in issues a new token that works

---

## 16. Pipeline Clone & YAML Import/Export

### 16a. Clone a pipeline

1. Go to **Pipelines**
2. Open any pipeline with at least two steps
3. Click the **Clone** button (three-dot menu or toolbar)
4. Confirm — a copy is created named `<original> (Copy)` (a second clone becomes `<original> (Copy) 2`)

- [ ] Clone appears in the pipeline list
- [ ] All steps, schedules, and variables are copied
- [ ] Editing the clone does not affect the original

### 16b. Export pipeline as YAML

1. On the **Pipelines** page, click **Export YAML** for a pipeline
2. Download the `.yaml` file

- [ ] File downloads successfully
- [ ] YAML contains `name`, `steps`, `schedule`, `variables` keys
- [ ] Step configs are intact (connection IDs, queries, etc.)

Also available via CLI:
```powershell
flowforge export "Pipeline Name"
```

- [ ] CLI produces same YAML content as the UI export

### 16c. Import pipeline from YAML

1. Modify the exported YAML — change the `name` to `Imported Pipeline`
2. On the **Pipelines** page, click the **Import** (upload) button
3. Upload the modified file

- [ ] Pipeline imported and visible in the list with the new name
- [ ] All steps and configs intact

CLI equivalent:
```powershell
flowforge import pipeline.yaml
flowforge import pipeline.yaml --overwrite   # replace if name exists
```

- [ ] CLI import succeeds
- [ ] `--overwrite` replaces an existing pipeline without error

---

## 17. Step Retry & Failure Webhook

### 17a. Step retry on transient failure

1. Open a pipeline → edit a step → expand **Advanced**
2. Set:

   | Field | Value |
   |---|---|
   | Retry count | `3` |
   | Retry delay (seconds) | `5` |

3. Point the step at a temporarily unavailable resource (e.g. a wrong DB host) and run

- [ ] Run History shows the step retried 3 times before failing
- [ ] The server log shows `failed (attempt 1/4), retrying in 5s`, then attempt 2/4, and so on
      (retry attempts go to the server log, not the step's run-history log)
- [ ] Total run duration reflects the delays (≥ 15 s)

### 17b. Retry succeeds on later attempt

1. Configure a step that will fail once then succeed (e.g. restore the correct DB host mid-run, or use `on_error: continue` on a preceding step)
2. Set retry count to `2`

- [ ] Step log shows it succeeded on attempt 2 (not attempt 1)
- [ ] Pipeline overall status is `success`

### 17c. Failure webhook

1. Open a pipeline → **Advanced** → set **On-failure webhook URL** to a public test endpoint (e.g. `https://webhook.site/<your-id>`)
2. Add a step that will intentionally fail (bad SQL)
3. Run the pipeline

- [ ] Pipeline fails
- [ ] Webhook receives a `POST` with JSON payload containing `pipeline_name`, `run_id`, `error_step`, `error_message`
- [ ] Webhook fires once per pipeline failure (not per step)

4. Fix the pipeline — run again successfully

- [ ] Webhook does **not** fire on success

---

## 18. API / Webhook Trigger

### 18a. Get the pipeline trigger token

1. Open a pipeline → the **Triggers** card → the API/webhook trigger section
2. Copy the trigger URL and token, e.g.:
   ```
   POST /api/pipelines/<id>/trigger?token=flwf_...
   ```

- [ ] Token is shown (masked, with a reveal button)
- [ ] Token starts with `flwf_`

### 18b. Trigger via curl / Postman

```powershell
Invoke-WebRequest -Method POST `
  -Uri "http://localhost:5000/api/pipelines/<id>/trigger?token=flwf_..." `
  -UseBasicParsing
```

- [ ] Response `202` with `{ "run_id": "...", "status": "running", "pipeline_name": "..." }`
- [ ] Run appears in Run History with `triggered_by = api`

### 18c. Invalid token is rejected

```powershell
Invoke-WebRequest -Method POST `
  -Uri "http://localhost:5000/api/pipelines/<id>/trigger?token=invalid" `
  -UseBasicParsing
```

- [ ] Response: `401 Unauthorized`
- [ ] No run created

### 18d. Audit trail

1. Go to **Settings → Audit Log**
2. Filter by action `WEBHOOK_TRIGGER`

- [ ] Trigger event logged with the pipeline name and `triggered_by = api`

---

## 19. Audit Log

1. Go to **Settings → Audit Log** (admin only)

### 19a. Events are recorded

Perform these actions and confirm each appears in the log:
- [ ] Login → action `LOGIN_SUCCESS`
- [ ] Failed login (wrong password) → action `LOGIN_FAILED`
- [ ] Create a pipeline → action `PIPELINE_CFG_CREATED`
- [ ] Run a pipeline → `PIPELINE_STARTED`, then `PIPELINE_SUCCESS` (or `PIPELINE_FAILED`)
- [ ] Delete a connection → action `CONNECTION_DELETED`
- [ ] Create, edit and delete a user → `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`

### 19b. Filters

1. Filter by **Action** = `PIPELINE_RUN`
- [ ] Only run events shown

2. Filter by **Username** = `admin`
- [ ] Only admin events shown

### 19c. Pagination

1. Generate more than 50 audit events (run several pipelines, login/logout multiple times)
2. Open the Audit Log page

- [ ] Paginated — 50 rows per page
- [ ] Next/Previous page controls work

### 19d. CSV export

1. Click **Export CSV**

- [ ] CSV downloads with all visible (filtered) log entries
- [ ] Columns: `ID`, `Timestamp`, `Action`, `Username`, `User ID`, `IP Address`, `Details`

### 19e. Viewer/editor cannot access audit log

1. Log in as `viewer_test` or `editor_test`
2. Navigate to `/settings/audit`

- [ ] Redirected or `403 Forbidden`

---

## 20. Notification Step (Slack / Teams / Telegram)

### 20a. Slack

1. Set up a Slack incoming webhook in your Slack workspace (Apps → Incoming Webhooks)
2. Create a pipeline with a **Notification** step:

   | Field | Value |
   |---|---|
   | Platform | `slack` |
   | Webhook URL | Your Slack webhook URL |
   | Message | `Pipeline {{ pipeline_name }} completed on {{ current_date }}` |

3. Run the pipeline

- [ ] Slack message received with variables resolved
- [ ] Message not empty or literal `{{ pipeline_name }}`

### 20b. Microsoft Teams

1. Set up an Incoming Webhook connector in a Teams channel
2. Add a **Notification** step:

   | Field | Value |
   |---|---|
   | Platform | `teams` |
   | Webhook URL | Your Teams webhook URL |
   | Title | `FlowForge Alert` |
   | Message | `{{ pipeline_name }} finished at {{ current_date }}` |

- [ ] Teams message received with bold title and resolved variables

### 20c. Telegram

1. Create a Telegram bot via @BotFather; note the bot token
2. Get your chat ID (send `/start` to the bot then call `https://api.telegram.org/bot<token>/getUpdates`)
3. Add a **Notification** step:

   | Field | Value |
   |---|---|
   | Platform | `telegram` |
   | Bot token | Your bot token |
   | Chat ID | Your chat ID |
   | Parse mode | `HTML` |
   | Message | `<b>{{ pipeline_name }}</b> completed successfully.` |

- [ ] Telegram message received with bold formatting applied

### 20d. Notification on pipeline failure

1. Add a **Notification** step at the end of a pipeline that also has a step set to `on_error: continue`
2. Force the first step to fail
3. Run the pipeline

- [ ] Notification step still runs after the failed step
- [ ] Message body includes `{{ failed_step }}` (if used in the template)

### 20e. Invalid webhook URL

1. Set an obviously wrong webhook URL and run

- [ ] Step fails with a clear error message
- [ ] Pipeline run status reflects the failure

---

## 21. Additional Email Providers

### 21a. SMTP (generic)

1. Go to **Connections → Email Providers → Add Provider → SMTP**
2. Fill in:

   | Field | Value |
   |---|---|
   | Host | `smtp.gmail.com` (or your SMTP server) |
   | Port | `587` |
   | Username | Your email address |
   | Password | App password |
   | Use TLS | Ticked |

3. Click **Test**

- [ ] Test email received
- [ ] SMTP provider saved and selectable in Email configs

### 21b. SendGrid

*(Requires a SendGrid account and API key with `Mail Send` permission.)*

1. Go to **Connections → Email Providers → Add Provider → SendGrid**
2. Fill in:

   | Field | Value |
   |---|---|
   | API Key | Your SendGrid API key (`SG.xxx`) |
   | From email | A verified sender address |
   | From name | `FlowForge` |

3. Click **Test**

- [ ] Test email received via SendGrid
- [ ] Provider saved

### 21c. AWS SES

*(Requires an AWS account, SES verified sender, and an IAM key with `ses:SendRawEmail`.)*

1. Go to **Connections → Email Providers → Add Provider → AWS SES**
2. Fill in:

   | Field | Value |
   |---|---|
   | AWS Access Key ID | Your access key |
   | AWS Secret Access Key | Your secret key |
   | AWS Region | `us-east-1` (or your SES region) |
   | From email | A SES-verified sender address |

3. Click **Test**

- [ ] Email delivered via SES
- [ ] Provider saved

### 21d. Mailgun

*(Requires a Mailgun account. Free tier allows 5,000 emails/month.)*

1. Go to **Connections → Email Providers → Add Provider → Mailgun**
2. Fill in:

   | Field | Value |
   |---|---|
   | API Key | Your Mailgun API key |
   | Domain | Your Mailgun sending domain |
   | Region | `US` or `EU` |
   | From email | `noreply@yourdomain.com` |

3. Click **Test**

- [ ] Email delivered via Mailgun
- [ ] Provider saved

---

## 22. Additional Database Connections

### 22a. MySQL / MariaDB

*(Requires MySQL or MariaDB running. Docker: `docker run -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=testdb mysql:8`.)*

1. Go to **Connections → Add Connection → MySQL**
2. Fill in host, port (`3306`), database, username, password
3. Click **Test Connection**

- [ ] Test passes (latency shown)
- [ ] Add a DB Query step pointing at this connection — query executes

### 22b. MSSQL / SQL Server

*(Requires SQL Server or Azure SQL. Docker: `mcr.microsoft.com/mssql/server:2022-latest`.)*

1. Go to **Connections → Add Connection → MSSQL**
2. Fill in:

   | Field | Value |
   |---|---|
   | Host | `localhost` |
   | Port | `1433` |
   | Database | `master` (or your DB) |
   | Username | `sa` |
   | Password | Your SA password |

3. Test connection

- [ ] Test passes
- [ ] DB Query step runs a simple `SELECT 1` successfully

### 22c. ODBC (generic)

1. Go to **Connections → Add Connection → ODBC**
2. Provide a DSN or connection string (e.g. `DSN=MyDSN` or a full ODBC connection string)
3. Test connection

- [ ] Connection tested (result depends on your ODBC driver/DSN)

---

## 23. Report — JSON Format

1. Go to **Reports → New Report**
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `Subscriber Summary JSON` |
   | Connection | `FlowForge DB` |
   | Query | `SELECT * FROM public.bulk_test_subscribers ORDER BY plan` |
   | Format | `JSON` |
   | Output filename | `subscribers_{{ current_date }}.json` |

3. Add to a pipeline as a **Report** step and run

- [ ] JSON file generated at the output path
- [ ] File is valid JSON (array of objects, one per row)
- [ ] Column names match query result columns
- [ ] Output path visible in step run log

---

## 24. Celery / Redis Task Queue (optional)

*(Requires Redis running. Docker: `docker run -p 6379:6379 redis:7`. Set `FLOWFORGE_REDIS_URL=redis://localhost:6379/0` in `.env` and restart.)*

### 24a. Worker starts and picks up tasks

In a separate terminal, start a Celery worker:
```powershell
flowforge worker --concurrency 4
```

- [ ] Worker starts and logs `[celery.worker.consumer] Connected to redis://localhost:6379/0`

### 24b. Pipeline run dispatched as Celery task

1. Trigger a pipeline via **Run Now**
2. Watch the Celery worker terminal

- [ ] Worker terminal shows `Received task: flowforge.tasks.run_pipeline`
- [ ] Run History shows `triggered_by = web_ui`
- [ ] Run completes and status updates in the UI

### 24c. Fallback when Redis is unavailable

1. Stop Redis
2. Restart the FlowForge server (without `FLOWFORGE_REDIS_URL` set, or with Redis stopped)
3. Trigger a pipeline

- [ ] Pipeline runs via background thread (no Celery error)
- [ ] Run History shows the run completed normally

---

## 25. Snowflake / BigQuery / Redshift Connections

### 25a. Snowflake

*(Requires a Snowflake account and `pip install flowforge[snowflake]`.)*

1. Go to **Connections → Add Connection → Snowflake**
2. Fill in:

   | Field | Value |
   |---|---|
   | Account Identifier | `xy12345.us-east-1` (your account locator) |
   | Username | Your Snowflake username |
   | Password | Your Snowflake password |
   | Warehouse | `COMPUTE_WH` (or your warehouse) |
   | Database | `MY_DB` |
   | Schema | `PUBLIC` |
   | Role (optional) | `SYSADMIN` |

3. Click **Test connection**

- [ ] Test passes (latency shown)
- [ ] Add a DB Query step pointing at this connection — query executes and returns rows

### 25b. BigQuery

*(Requires a GCP project and `pip install flowforge[bigquery]`.)*

1. Go to **Connections → Add Connection → BigQuery**
2. Fill in:

   | Field | Value |
   |---|---|
   | Project ID | `my-gcp-project` |
   | Dataset (optional) | `my_dataset` |
   | Service Account Key (JSON) | Paste a service account key, or leave blank to use Application Default Credentials |

3. Click **Test connection**

- [ ] Test passes with a pasted service account key
- [ ] Test passes leaving the key blank (if `gcloud auth application-default login` has been run on the host)
- [ ] A DB Query step using a named `@param` (not positional `%s`) resolves correctly — BigQuery has no positional placeholder support

### 25c. Redshift

*(Uses the same connection form as PostgreSQL/MySQL/Oracle — Redshift is wire-compatible with Postgres, no dedicated form.)*

1. Go to **Connections → Add Connection → Amazon Redshift**
2. Fill in Host, Port (defaults to `5439`), Database, Username, Password
3. Click **Test connection**

- [ ] Test passes
- [ ] DB Query step runs a simple `SELECT 1` successfully

---

## 26. S3 / Azure Blob Upload Steps

### 26a. S3 upload

*(Requires `pip install flowforge[s3]` and either `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION` set, or a working boto3 default credential chain — e.g. an IAM instance role.)*

1. Create a pipeline: **Report → S3 Upload**
   - Step 1: Report step (CSV or Excel)
   - Step 2: S3 Upload step:

     | Field | Value |
     |---|---|
     | File path | `{{ steps.step1_name.output_path }}` |
     | Bucket | Your S3 bucket name |
     | Key (optional) | `reports/report_{{ current_month }}.xlsx` |
     | Rename to (optional) | leave blank if Key is set |
     | Return presigned URL | Ticked (default) |

2. Run the pipeline

- [ ] File appears in the S3 bucket at the given key
- [ ] Step run log shows a presigned HTTPS URL (not a bare `s3://` URI) when "Return presigned URL" is ticked
- [ ] Untick "Return presigned URL" and re-run — log shows a plain `s3://bucket/key` URI instead
- [ ] Presigned URL opens the file directly in a browser without AWS credentials, and expires after ~1 hour

### 26b. Azure Blob upload

*(Requires `pip install flowforge[azure_blob]` and `AZURE_STORAGE_CONNECTION_STRING`, or `AZURE_STORAGE_ACCOUNT_URL` + optionally `AZURE_STORAGE_ACCOUNT_KEY`.)*

1. Create a pipeline: **Report → Azure Blob Upload**
   - Step 1: Report step
   - Step 2: Azure Blob Upload step:

     | Field | Value |
     |---|---|
     | File path | `{{ steps.step1_name.output_path }}` |
     | Container | Your Azure container name |
     | Blob name (optional) | `report_{{ current_month }}.xlsx` |
     | Return shareable (SAS) URL | Ticked (default) |

2. Run the pipeline

- [ ] File appears in the Azure container
- [ ] With `AZURE_STORAGE_ACCOUNT_KEY` set: step log shows a SAS URL (24h expiry) that opens the file without further auth
- [ ] With only `AZURE_STORAGE_CONNECTION_STRING`/`AZURE_STORAGE_ACCOUNT_URL` and no account key: log shows a plain blob URL instead (SAS generation requires the account key) — not an error

---

## 27. MFA (TOTP)

*(Requires `pip install pyotp`.)*

### 27a. Enroll

1. Log in as any user → **Settings**
2. Find the **Two-Factor Authentication (MFA)** card (status badge shows "Disabled")
3. Click **Enable MFA**
4. Scan the displayed QR code with an authenticator app (Google Authenticator, Authy, etc.), or use "Copy" on the manual entry secret
5. Enter the 6-digit code from the app into **Verification code**
6. Click **Activate MFA**

- [ ] QR code renders and scans successfully in an authenticator app
- [ ] Wrong code is rejected with a clear error
- [ ] Correct code activates MFA — a "backup codes" banner appears with 10 one-time codes
- [ ] Click **Done — I've saved my backup codes** — MFA card now shows "Active"

### 27b. Login with MFA enabled

1. Log out
2. Log in with username/password as usual

- [ ] Login does not complete immediately — an **Authenticator code** prompt appears instead
3. Enter a valid TOTP code from the authenticator app

- [ ] Login succeeds and issues a normal session token

### 27c. Login with a backup code

1. Log out, log in with username/password again
2. At the authenticator-code prompt, use the backup-code fallback link
3. Enter one of the 10 saved backup codes

- [ ] Login succeeds via backup code
- [ ] The same backup code is rejected if used a second time (one-time use)
- [ ] Response after backup-code login shows how many backup codes remain

### 27d. Disable MFA

1. Settings → MFA card → **Disable MFA**
2. Confirm current password

- [ ] MFA disabled — card returns to "Disabled" state
- [ ] Next login does not prompt for a TOTP/backup code

---

## 28. SSO (Google / Microsoft) and SAML

### 28a. Google SSO

*(Requires `GOOGLE_SSO_CLIENT_ID`/`GOOGLE_SSO_CLIENT_SECRET` set, `pip install google-auth-oauthlib`, and a matching OAuth redirect URI `{FLOWFORGE_APP_URL}/api/auth/sso/google/callback` registered in Google Cloud Console.)*

1. On the Login page, confirm a **"Sign in with Google"** button appears (only shown when configured)
2. Click it → complete Google's consent screen

- [ ] Redirects back to FlowForge and logs in successfully
- [ ] With `FLOWFORGE_SSO_AUTO_CREATE=false` (default) and no matching existing username: login is rejected with "Account not found. Contact your administrator."
- [ ] With `FLOWFORGE_SSO_AUTO_CREATE=true`: a new user is auto-created on first SSO login

### 28b. Microsoft SSO

*(Requires `MICROSOFT_SSO_TENANT_ID`/`MICROSOFT_SSO_CLIENT_ID`/`MICROSOFT_SSO_CLIENT_SECRET`, `pip install msal`, and a matching Azure AD app registration.)*

1. Confirm the Microsoft SSO button appears on Login when configured
2. Complete the Microsoft consent flow

- [ ] Redirects back and logs in successfully
- [ ] Auto-create behavior matches the Google case (`FLOWFORGE_SSO_AUTO_CREATE`)

### 28c. SAML

*(Requires `SAML_SP_ENTITY_ID`, `SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`, `SAML_IDP_X509_CERT`, and `pip install python3-saml`.)*

1. Fetch `GET /api/auth/sso/saml/metadata` and register it (or the individual fields) with your IdP (Okta, Azure AD, PingFederate)
2. Confirm a **"Sign in with SSO"** button appears on Login
3. Click it → complete the IdP login

- [ ] Redirects to the IdP, then back to FlowForge via the ACS endpoint, and logs in successfully
- [ ] `GET /api/auth/sso/providers` correctly reflects which of `google`/`microsoft`/`saml` are configured (used to decide which buttons render)

---

## 29. GDPR Export / Deletion

*(Admin only — Settings → Users.)*

### 29a. Data export

1. Go to **Settings → Users**
2. Click the download icon next to a non-current-user account ("GDPR export — download all personal data as JSON")

- [ ] JSON file downloads as `flowforge-gdpr-export-<username>.json`
- [ ] File contains `user`, `audit_log` (up to 1000 entries), and `pipeline_runs` (up to 500 entries)
- [ ] Data matches what's visible elsewhere in the UI for that user

### 29b. GDPR purge

1. Click the **GDPR** button next to a non-current-user account
2. Confirm the dialog: "GDPR purge: delete '<user>' and anonymise all their audit log entries?"

- [ ] User is deleted from the Users list
- [ ] Audit Log entries previously attributed to that user now show `username = [deleted:<uid8>]` with `ip_address` cleared, instead of disappearing entirely
- [ ] Attempting to purge your own currently-logged-in account: the delete/GDPR buttons are not shown at all

### 29c. Plain delete (no purge)

1. Click the trash icon next to a user (not the GDPR button)
2. Confirm "Delete user '<user>'? This cannot be undone."

- [ ] User is deleted, but their audit log entries retain the original username (no anonymisation) — confirms plain delete and GDPR purge are genuinely different operations

---

## 30. Plugin System

*(Reference: `docs/plugins.md`, example at `examples/plugins/http_webhook_step.py`.)*

### 30a. Load a plugin step type

1. Set `FLOWFORGE_PLUGIN_DIR=./plugins` in `.env` (this is also the default if unset)
2. Copy `examples/plugins/http_webhook_step.py` into that directory
3. Restart FlowForge (`flowforge web`)

- [ ] `GET /api/step-types` now includes an entry with `"plugin": true` for the new type, alongside the built-ins (`"plugin": false`)
- [ ] In Pipeline Builder, the new step type appears in the **Steps** add-button row, labelled `(plugin)`

### 30b. Configure and run a plugin step

1. Add the plugin step to a pipeline

- [ ] Since there's no dedicated form, the step falls back to a raw JSON config textarea — confirm it's editable and saves correctly
2. Fill in valid JSON config for the plugin and run the pipeline

- [ ] Step executes using the same retry / `on_error` / `parallel_group` machinery as built-in steps
- [ ] Step failure (e.g. malformed config) is reported in Run History like any other step failure

### 30c. Conflicting or broken plugin

1. Add a second plugin file whose `step_type` string duplicates an existing built-in (e.g. `email`)
2. Restart FlowForge

- [ ] Server starts normally (no crash) — a warning is logged and the conflicting plugin is skipped; the built-in `email` type is unaffected
3. Add a plugin file with a Python syntax error, restart

- [ ] Server still starts — the broken plugin is skipped with a logged error, other plugins/built-ins still load

### 30d. Plugin connection / email provider

1. Add a plugin file defining a `BaseConnection` subclass with a unique `db_type` and a `from_config(cls, cfg)` classmethod (see `docs/plugins.md` § Connection plugins), restart FlowForge

- [ ] `GET /api/registry/connections` includes an entry for the new `db_type` with `"plugin": true`
- [ ] Connections page → Add Connection → Type dropdown lists the new type, labelled `(plugin)`
- [ ] Selecting it shows a raw JSON config textarea instead of the usual host/port/user fields
2. Save a connection of that type with valid JSON config, then click **Test**

- [ ] Test succeeds using the plugin's own `test()` implementation
3. Repeat steps 1-2 for a plugin `EmailProvider` subclass (`provider_type` + `from_config`) — same checks against `GET /api/registry/email_providers` and the Email Providers tab

---

## 31. Team-Scoped Project Members

### 31a. Add and remove members

1. Log in as `admin` → **Projects**
2. Click the members icon ("Manage members") on a project card

- [ ] **Members — <project name>** modal opens, listing current members with role badges
3. Select a non-admin user from the **"Select a user…"** dropdown, click **Add**

- [ ] User appears in the member list immediately
- [ ] Adding the same user again is not offered (already filtered out of the dropdown)
4. Click the remove icon next to a member

- [ ] Member is removed from the list

### 31b. Non-member access is blocked

1. Create `member_test` (editor role), add them to Project A only (not Project B)
2. Log in as `member_test`

- [ ] Pipelines/Reports/Emails/Recipients belonging to Project B are not visible or editable
- [ ] Attempting to access a Project B resource directly (e.g. via its URL/API) returns `403 Access denied to this project`
- [ ] Project A resources remain fully visible and editable per the user's role (editor)

### 31c. Admin bypass

1. Log in as `admin` (not added to Project B as a member)

- [ ] Admin can see and edit Project B's resources anyway — admins bypass project membership entirely

---

## 32. Pipeline Dependencies (Fan-Out) and Parallel Step Execution

### 32a. Upstream dependency triggers downstream automatically

1. Create Pipeline A (`Upstream Test`) and Pipeline B (`Downstream Test`), both enabled
2. Open Pipeline B → **Triggers** card → **Dependencies** tab → **"+ Add upstream dependency…"** → select Pipeline A
3. Save Pipeline B
4. Run Pipeline A manually via **Run Now**

- [ ] Once Pipeline A finishes with status `success`, Pipeline B automatically starts
- [ ] Pipeline B's Run History shows the triggered run with `triggered_by = dependency`
- [ ] If Pipeline A fails instead, Pipeline B does **not** auto-trigger

### 32b. Parallel step execution

1. In a pipeline, add two independent steps (e.g. two DB Query steps against different tables)
2. On both steps, set the **"∥ Group"** field to the same value, e.g. `group1`

- [ ] Both step cards show a purple left border and a `∥ group1` badge
3. Run the pipeline

- [ ] Both steps' start times overlap in Run History (visible via step timestamps/durations) rather than running strictly sequentially
- [ ] If one step in the group fails and has `on_error: stop`, the pipeline halts only after the whole wave completes (not mid-wave)

---

## 33. Pipeline Run Diff View

1. Run a pipeline successfully at least twice, changing the underlying data slightly between runs (e.g. insert a few more rows)
2. Go to **Run History** → open the most recent run's **Run Detail**
3. Find the **"Diff vs previous run"** panel

- [ ] Panel shows, per step: row count vs previous run (with the delta), duration vs previous run (% change), and file size vs previous run (for steps producing an output file that still exists on disk)
- [ ] A step that's new in this run (didn't exist in the previous run) is marked as new, not shown with a misleading delta
- [ ] On the very first successful run of a pipeline (no prior run to diff against), the panel explains there's nothing to compare instead of erroring

---

## 34. Report Column Formatting

1. Go to **Reports** → open or create a report with at least one numeric and one date column
2. Find the **Column Formatting** card → click **Add rule**
3. Set:

   | Field | Value |
   |---|---|
   | Column name | exact name of a numeric column, e.g. `mrr` |
   | Number format | `Currency $` preset |
   | Width | `15` |

4. Click **Add condition** under that rule:

   | Field | Value |
   |---|---|
   | if value | `>` `500` |
   | bg | pick a highlight color |
   | text | pick a contrasting color |

5. Add to a pipeline as a Report step (Excel format) and run

- [ ] Generated Excel file: the target column is formatted as currency (`$#,##0.00`)
- [ ] Column width matches the configured width (not auto-fit)
- [ ] Rows where the value exceeds 500 have the configured background/text color; rows at or below do not
- [ ] Header row renders with the default grey fill + bold font regardless of custom rules
- [ ] Add a second, conflicting condition on the same column — confirm the **first** matching condition wins (not the last)
- [ ] A custom raw number-format string (not one of the presets) is also accepted and applied correctly

---

## 35. Environment Promotion Workflow

*(Requires at least two Projects to exist.)*

1. Go to **Pipelines** → find a pipeline with at least one secret pipeline variable and one step referencing a connection/report/email config (e.g. a DB Query or Email step)
2. Click **"Promote to another project"**
3. In the **Promote Pipeline** modal, select a different target project → click **Promote**

- [ ] If secret variables or cross-project resource references exist, a warnings list is shown instead of silently succeeding — e.g. `"Secret variable 'X' was not copied — set it manually in the target project."` and `"Step 'Y': connection_id references an ID from the source project — update it..."`
- [ ] The new pipeline appears in the target project, named `"<original> (<target project>)"` (or with your custom suffix)
- [ ] The promoted copy is **disabled** by default, even if the source pipeline was enabled
- [ ] Non-secret pipeline variables and all steps (including `parallel_group`) are copied correctly
- [ ] Editing the promoted copy does not affect the original pipeline
- [ ] Attempting to promote to the *same* project the pipeline is already in is rejected with a clear error

---

## 36. Prometheus Metrics + Flower Dashboard

### 36a. Metrics endpoint

1. Log in via the API to obtain a JWT (`POST /api/auth/login`)
2. Call `GET /api/metrics` with `Authorization: Bearer <token>`

- [ ] Response is `text/plain` Prometheus exposition format (not JSON)
- [ ] Contains `flowforge_runs_total{status="success"}` / `{status="failed"}` / `{status="cancelled"}` counters
- [ ] Contains `flowforge_runs_active` gauge — trigger a long-running pipeline and confirm this increments while it's running, then drops back down after it finishes
- [ ] Contains `flowforge_queue_depth` — with `FLOWFORGE_REDIS_URL` unset, this reads `0` rather than erroring
- [ ] Calling `/api/metrics` with no `Authorization` header (or an invalid token) returns `401`, same as any other `/api` endpoint

### 36b. Flower dashboard

*(Requires Celery/Redis configured — see §24.)*

1. Start the stack with the monitoring profile: `docker compose --profile monitoring up`
2. Browse to `http://localhost:5555` (or your configured `FLOWER_PORT`)

- [ ] Basic-auth prompt appears; the credentials you set in `FLOWER_BASIC_AUTH` work (`docker compose` refuses to start without it)
- [ ] No default or well-known credentials are accepted
- [ ] Dashboard shows active Celery workers and task history
- [ ] Trigger a pipeline run — the corresponding `flowforge.run_pipeline_task` appears in Flower's task list
- [ ] Without `--profile monitoring`, `docker compose up` does **not** start the Flower container (opt-in only)

---

## 37. IP Allowlisting

*(Off by default — only active when `FLOWFORGE_ALLOWED_IPS` is set. If testing locally, note that requests from `127.0.0.1`/`::1` may not match a CIDR you'd expect; adjust the allowlist to include your actual test client IP.)*

### 37a. Allowed IP passes through

1. Set `FLOWFORGE_ALLOWED_IPS=127.0.0.1/32` (or your actual client IP) and restart
2. Use the app normally from that IP

- [ ] All `/api/*` requests succeed as before
- [ ] Non-API routes (frontend static assets, the SPA shell) are unaffected regardless of IP — the filter only applies to `/api/*`

### 37b. Disallowed IP is blocked

1. Set `FLOWFORGE_ALLOWED_IPS` to a CIDR that does **not** include your test client (e.g. `10.99.99.0/24`) and restart
2. Attempt any `/api/*` call

- [ ] Response is `403 {"error": "Access denied: your IP is not allowed"}`

### 37c. Invalid CIDR handling

1. Set `FLOWFORGE_ALLOWED_IPS=not-a-real-cidr,10.0.0.0/8` and restart

- [ ] Server starts normally (doesn't crash on the malformed entry) — a warning is logged, and the valid CIDR (`10.0.0.0/8`) still takes effect
2. Set `FLOWFORGE_ALLOWED_IPS=` (empty) or unset it entirely, restart

- [ ] No IP filtering applied — behavior identical to before this feature existed

---

## 38. Visual Pipeline Canvas & Step-Level DAG Dependencies

### 38a. Canvas layout (Option A)

1. Open a pipeline with at least 3 steps, two of them sharing the same `parallel_group`
2. Toggle the grid icon above the step list

- [ ] Steps render as nodes left-to-right in actual execution-wave order; the two `parallel_group` steps appear stacked in the same column
- [ ] Dragging a node reorders it, or moves it into/out of the group column; toggling back to the list view reflects the change
- [ ] Clicking a node opens its config in a side panel; add/duplicate/delete work from the node's hover actions

### 38b. Drawing a real step dependency (DAG mode)

1. In the canvas view, drag from one step node's handle to another step node's handle
2. Reload the page (no Save click needed first)

- [ ] The new edge renders in the accent color, visually distinct from the neutral synthetic layout edges
- [ ] The edge still shows after reload (persisted via `POST /api/pipelines/{id}/step-dependencies`, not just client-side state)
- [ ] Once any real edge exists for the pipeline, only real edges render — the synthetic wave-layout edges disappear for that pipeline

### 38c. Cycle / self-connect rejection

1. With an existing A → B edge, try to draw B → A

- [ ] Rejected with an inline error banner (not a silent failure); no edge is created
2. Try connecting a step to itself

- [ ] Rejected client-side before any API call is made

### 38d. Branch-scoped failure in DAG mode

1. Build a small DAG: A → B, with A's `on_error` set to `stop`; add an independent step C with no edges to A or B
2. Make step A fail (e.g. point a `db_query` step at a nonexistent table) and run the pipeline
3. Open Run Detail

- [ ] Step A shows `failed`, step B shows `skipped`, step C shows `success` — C is not held up by A's failure
- [ ] This differs from a plain sequential/parallel-group pipeline, where a `stop` failure halts every later step regardless of relation to the failed one

---

## 39. SSH Command Step (ssh_command)

*(Requires an accessible SSH server — same setup as §14's Docker SFTP container works, or any host you have credentials for. Create an **SSH Connection** first: Connections → Add Connection → SSH.)*

### 39a. Basic command execution

1. Create a pipeline: `SSH Command Test`
2. Add an **SSH Command** step:

   | Field | Value |
   |---|---|
   | SSH connection | Your SSH connection |
   | Command | `echo hello from {{ pipeline_name }}` |
   | Capture output | Ticked |

3. Run the pipeline

- [ ] Step succeeds
- [ ] Step log shows `STDOUT: hello from SSH Command Test` (variable resolved, not literal `{{ pipeline_name }}`)
- [ ] Log includes `Exit status: 0`

### 39b. Capture stdout into a pipeline variable

1. Edit the step: set **Output variable** to `script_result`, command to `echo captured-value`
2. Add a downstream **Email** step with body `<p>{{ script_result }}</p>`
3. Run the pipeline

- [ ] Email received containing `captured-value` (not the literal `{{ script_result }}`)

### 39c. Save output to file and attach to email

1. Tick **Save output**, set **Output filename** to `ssh_output_{{ current_date }}.log`
2. Add a downstream **Email** step with attachment `{{ steps.<step_name>.output_path }}`
3. Run the pipeline

- [ ] Email received with the `.log` file attached
- [ ] File contents match the command's stdout

### 39d. Non-zero exit fails the step

1. Set command to `exit 1`
2. Run the pipeline

- [ ] Step fails with `Command failed with exit status 1`
- [ ] `output_path` is still set if **Save output** was ticked (log file available even on failure)

### 39e. Unknown host key rejected by default

1. Point the SSH connection at a host not in the FlowForge server's `known_hosts`
2. Run the step (with `FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS` unset or `false`)

- [ ] Step fails with a host-key/SSH error, not a silent connect
- [ ] Setting `FLOWFORGE_SSH_ALLOW_UNKNOWN_HOSTS=true` and restarting allows the connection through

---

## 40. Database Health Check Step (db_health_check)

*(Run against each DB type you have available — PostgreSQL is required for the rest of this guide, so at minimum test that one.)*

### 40a. PostgreSQL health check

1. Create a pipeline: `DB Health Check Test`
2. Add a **Database Health Check** step:

   | Field | Value |
   |---|---|
   | Connection | `FlowForge DB` |
   | Format | `Excel` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] Step log shows `PostgreSQL Health Check`, `Active Sessions: N`, and a Cache Hit Ratio line
- [ ] Generated Excel file has one sheet per section (Sessions, Cache Performance, and Replication Lag if replicas exist)

### 40b. CSV format

1. Change **Format** to `CSV`, re-run

- [ ] CSV file generated instead of Excel, same sections as text

### 40c. Oracle / MySQL health check (if a connection is configured)

1. Repeat 40a against an Oracle or MySQL connection

- [ ] Oracle: log shows Active User Sessions, Buffer Cache Hit Ratio, and any tablespaces over 80% usage (section omitted if none)
- [ ] MySQL: log shows Connected Threads

### 40d. Unsupported connection type

1. Point the step at a connection type other than PostgreSQL/Oracle/MySQL (e.g. Snowflake)

- [ ] Step fails with a clear `unsupported database type` error, not a crash

### 40e. Attach to email

1. Add a downstream **Email** step with attachment `{{ steps.<step_name>.output_path }}`
2. Run the pipeline

- [ ] Email received with the health report attached

---

## 41. SSH Server Health Check Step (ssh_health_check)

*(Requires an accessible Linux SSH host — the metric commands, e.g. `free -m`, `df -h`, assume Linux.)*

### 41a. All metrics (default)

1. Create a pipeline: `SSH Health Check Test`
2. Add an **SSH Health Check** step pointing at your SSH connection, leaving **Metrics** unset (all four collected by default)
3. Run the pipeline

- [ ] Step succeeds
- [ ] Excel file has 4 sheets: Load Average, Memory (MB), Disk Usage, Top Processes (CPU)
- [ ] Step log lists a row count per sheet

### 41b. Select specific metrics

1. Set **Metrics** to only `load_average` and `disk_usage`
2. Run the pipeline

- [ ] Report contains only those 2 sheets, not all 4

### 41c. Partial metric failure is tolerated

1. Point the connection at a host that lacks one of the commands (e.g. a minimal container without `ps`)
2. Run the pipeline

- [ ] Step still succeeds with the remaining metrics collected
- [ ] A warning is logged for the failed metric, not a step failure

### 41d. All metrics fail

1. Point at a host where none of the metric commands work (or an SSH connection that can authenticate but has a broken shell)

- [ ] Step fails with `no metrics could be collected`

---

## 42. Script / Data Report Step (data_report)

Turns a pipeline variable (from `ssh_command`'s `output_var` or elsewhere) into a formatted report file — see the SSH → Excel example in `docs/step-types.md`'s `data_report` section.

### 42a. CSV variable → Excel report

1. Create a pipeline: `Data Report Test`
2. Add an **SSH Command** step (or any step that sets a pipeline variable) producing a CSV string with a header row, e.g. command:
   ```
   printf "plan,cnt\nbasic,6\npremium,7\n"
   ```
   with **Output variable** set to `plan_csv`
3. Add a **Data Report** step:

   | Field | Value |
   |---|---|
   | Data variable | `plan_csv` |
   | Data format | `CSV` |
   | Output format | `Excel` |
   | Output filename | `plan_report_{{ current_date }}.xlsx` |
   | Sheet name | `Plans` |

4. Run the pipeline

- [ ] Step succeeds
- [ ] Generated Excel file has a `Plans` sheet with columns `plan`, `cnt` and 2 data rows

### 42b. JSON variable → PDF report

1. Set an upstream variable to a JSON array string, e.g. `[{"plan":"basic","cnt":6},{"plan":"premium","cnt":7}]`
2. Set **Data format** to `JSON`, **Output format** to `PDF`, **Title** to `Plan Report`

- [ ] PDF generated with a title and a table matching the JSON objects' keys/values

### 42c. Empty variable

1. Point **Data variable** at a variable that resolves to an empty string

- [ ] Step succeeds (not fails) with log "No data found in variable; skipping report generation"
- [ ] No output file created, `output_path` empty

### 42d. Column override

1. Set **Columns** to a custom list, e.g. `["Plan Name", "Count"]`, using the same 2-column CSV data from 42a

- [ ] Generated report's header row shows `Plan Name`, `Count` instead of the original `plan`, `cnt`

---

## 43. Conditional Step Execution (run_if)

Gates a step on an earlier result. `run_if` is a Jinja2 expression in the step's
config; when it is false the step is skipped. Reference: `docs/step-types.md`
(Conditional execution).

### 43a. Skipped when false, runs when true

1. Create a pipeline `Conditional Test` with two steps:
   - `check`: a **DB Query** step, `SELECT 1 WHERE false` (zero rows), **Capture rows** ticked
   - `alert`: a **Notification** or **Email** step, with **Run only if** set to `steps.check.rows_affected > 0`
2. Run the pipeline

- [ ] Run History shows `check` as `success` and `alert` as `skipped` (not failed)
- [ ] The pipeline status is `success` and `alert` sent nothing
3. Change `check` to `SELECT 1` (one row) and run again

- [ ] `alert` now runs and sends

### 43b. A skipped step is visible to later steps

1. Add a third step `all_clear` with **Run only if** `steps.alert.skipped`
2. Make `check` return zero rows again and run

- [ ] `alert` is skipped and `all_clear` runs

### 43c. A bad expression is rejected, a broken one fails loudly

1. Enter `steps.check.rows_affected >` (incomplete) in **Run only if** and save

- [ ] Saving is refused with a message naming the step and the problem
2. Enter `steps.typo.rows_affected > 0` (a step that does not exist) and run

- [ ] The step **fails** with `run_if could not be evaluated` instead of being silently skipped
- [ ] With `on_error: stop` the pipeline halts; with `continue` later steps still run

### 43d. DAG mode

1. On the canvas, draw a dependency `check` → `alert` → `follow_up`, with `run_if` only on `alert`
2. Run with `check` returning zero rows

- [ ] `alert` is skipped, and `follow_up` still **runs** (a condition-skipped step does not skip its descendants)
- [ ] A `run_if` that refers to a step that is not an ancestor fails rather than skipping

---

## 44. User Accounts from the CLI

### 44a. Generated password

```powershell
flowforge user create cli_tester --role editor --generate-password
```

- [ ] A password is printed once; it is not written to any file or log (the audit log records only that the user was created)
- [ ] First login with it asks you to set a new password before a session is issued
- [ ] Running the same command again fails with "already exists"

### 44b. Prompted password and no password on the command line

```powershell
flowforge user create cli_tester2 --role viewer
```

- [ ] You are prompted for a password twice and nothing is echoed
- [ ] `flowforge user create --help` shows no `--password` option

### 44c. Delete

```powershell
flowforge user delete cli_tester --yes
flowforge user delete cli_tester2 --yes --purge
```

- [ ] Both accounts disappear from Settings → Users and can no longer log in
- [ ] `--purge` anonymises that user's audit-log entries (their username becomes `[deleted:...]`)
- [ ] Deleting a user that does not exist exits with an error

---

## Notes

| Date | Tester | Section | Result | Notes |
|---|---|---|---|---|
| | | | | |

