# FlowForge — Manual Testing Guide

Use this document to verify each major feature end-to-end before shipping or
after a significant change. Work through each section in order — earlier
sections create the connections and configs that later sections depend on.

Mark each checkbox as you complete it.

---

## Prerequisites

- FlowForge server running: `python -m flowforge web` (or via the PowerShell
  start script)
- PostgreSQL running on `localhost:5434`
- Browser open at `http://localhost:5000`
- Logged in as `admin`

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
3. Run OAuth2 setup if not already done: `python -m flowforge setup gmail`
4. Fill in Client ID, Client Secret, Refresh Token, Sender email
5. Save and test

- [ ] Gmail provider saved

### 1c. Microsoft 365 provider

1. Go to **Connections → Email providers → Add provider**
2. Select **Microsoft 365**
3. Fill in Tenant ID, Client ID, Client Secret, Sender email
   (requires an Azure AD app registration with `Mail.Send` permission)
4. Run: `python -m flowforge setup microsoft365` to complete device-code auth
5. Save and test

- [ ] M365 provider saved
- [ ] Test send succeeds (check inbox at `jagdeep.singh.virdi@gmail.com`)

### 1d. SMTP provider (optional — covers Outlook, Yahoo, custom)

1. Go to **Connections → Email providers → Add provider**
2. Select **SMTP**
3. Fill in host, port, credentials
4. Save and test

- [ ] SMTP provider saved

---

## 2. Bulk Load

Sample data is committed at `D:\Project\flowforge\sample_data\bulk_load\`.

### 2a. Create the target table

Run once in any SQL client (pgAdmin, DBeaver, or the one-liner below):

```powershell
python -c "
import psycopg2
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
| Source directory | `D:\Project\flowforge\sample_data\bulk_load\incoming` |
| File type | `CSV` |
| File prefix | `SUBS_` |
| Header rows | `1` |
| Footer rows | `0` |
| Delimiter | `,` |
| On no files | `Skip (succeed)` |
| Archive directory | `D:\Project\flowforge\sample_data\bulk_load\archive\{{ current_date }}` |

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
| basic | active | 7 | 209.93 |
| basic | cancelled | 1 | 29.99 |
| premium | active | 6 | 599.94 |
| premium | suspended | 1 | 99.99 |
| standard | active | 4 | 239.96 |
| standard | cancelled | 1 | 59.99 |

- [ ] Data matches expected

### 2e. Re-run test (restore files first)

```powershell
Copy-Item "D:\Project\flowforge\sample_data\bulk_load\archive\*\SUBS_*.csv" `
          "D:\Project\flowforge\sample_data\bulk_load\incoming\"
```

Run the pipeline again. Because load mode is **Replace**, the table should
still have exactly 20 rows after the second run (not 40).

- [ ] Second run succeeds with 20 rows, not 40

---

## 3. DB Query Step

### 3a. Simple query — write to output table

1. Create a pipeline: `Query Test`
2. Add a **DB Query** step:

   | Field | Value |
   |---|---|
   | Connection | `FlowForge DB` |
   | Query | `SELECT plan, status, COUNT(*) AS cnt, SUM(monthly_amount) AS mrr FROM public.bulk_test_subscribers GROUP BY plan, status ORDER BY plan, status` |
   | Output table | `public.subscriber_summary` |
   | Mode | `Replace` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] `public.subscriber_summary` created and populated (6 rows)

### 3b. Query with Jinja2 variable

1. Add a pipeline variable: `target_plan = premium`
2. Edit the query step to use it:
   ```sql
   SELECT * FROM public.bulk_test_subscribers
   WHERE plan = '{{ target_plan }}'
   ```
3. Run — should return only premium subscribers

- [ ] Variable resolved correctly in SQL

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
- [ ] Email received at `jagdeep.singh.virdi@gmail.com`
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

### 4a. PostgreSQL function

Create a test function first:

```sql
CREATE OR REPLACE FUNCTION public.ff_test_proc(p_plan TEXT)
RETURNS void AS $$
BEGIN
  RAISE NOTICE 'ff_test_proc called with plan=%', p_plan;
END;
$$ LANGUAGE plpgsql;
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

| Field | Value |
|---|---|
| Connection | Your Oracle connection |
| Procedure | `PKG_NAME.PROC_NAME` |
| Parameters | `{ "param1": "value1" }` |

- [ ] Oracle procedure executes successfully

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
   | To | `jagdeep.singh.virdi@gmail.com` |
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
   | File path | `D:\Project\flowforge\sample_data\bulk_load\incoming\SUBS_20260522_001.csv` |
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
   | File path | `D:\Project\flowforge\sample_data\bulk_load\incoming\SUBS_20260522_001.csv` |
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

## 14. AI Features (UI — Ollama required)

*(Requires Ollama running locally: `ollama serve`. Pull a model first:
`ollama pull llama3.2:3b`. All features are best-effort — if Ollama is
unreachable the button shows "AI unavailable" and the rest of the UI works normally.)*

### 14a. AI Chart Generator

1. Go to **Reports → Report Designer** → write or load a query with numeric columns
2. Click **Preview** to run the query and show the data table
3. Click **Visualize** (AI sparkle button in the Preview panel toolbar)

- [ ] A chart config card appears below the preview table
- [ ] Chart type, X axis, and Y axis are populated with sensible suggestions
- [ ] Recharts chart renders immediately (bar, line, area, pie, or scatter)
- [ ] User can change chart type and axes via dropdowns — chart updates live
- [ ] If Ollama is unreachable: "AI unavailable — is Ollama running?" shown, no crash

### 14b. SQL Explainer

1. Open any report in **Report Designer**
2. Write or paste a SQL query with joins and filters
3. Click **Explain** (button in the SQL editor header)

- [ ] Dismissible explanation panel appears below the SQL editor
- [ ] Panel describes tables/joins, filters, aggregations, and potential issues in plain English
- [ ] "via Ollama" label visible
- [ ] Dismiss button closes the panel

### 14c. SQL Optimizer

1. Same SQL editor — click **Optimize** (button alongside Explain)

- [ ] Side-by-side diff panel appears: original (red tint) vs suggested (green tint)
- [ ] Suggested SQL is extracted cleanly (no prose mixed in)
- [ ] **Accept** replaces the SQL editor content with the suggestion
- [ ] **Dismiss** closes the panel without changing the SQL

### 14d. Pipeline Failure Diagnosis

1. Create a pipeline with a step that will intentionally fail (e.g. a DB query with a syntax error)
2. Run the pipeline — it fails
3. Go to **Run History → Run Detail → Logs tab**
4. Find the failed step — click **Explain this error**

- [ ] 2–4 sentence diagnosis appears below the error message
- [ ] Diagnosis explains the cause and suggests a fix in plain English
- [ ] "via Ollama" label visible
- [ ] Dismissible; other steps are unaffected

### 14e. Data Profiler

1. Open **Report Designer** with a query that has multiple column types
2. Click **Preview** to load the data
3. Click **Summarise** (button in TopBar, visible after preview runs)
4. First time: opt-in banner appears — "Your preview rows will be sent to your local Ollama instance. No data leaves your machine."

- [ ] Consent banner shown on first use per session
- [ ] After accepting: profile card appears with 3–5 sentence narrative
- [ ] Narrative mentions structure, value ranges, or notable patterns
- [ ] Profile card is dismissible
- [ ] Re-running the query clears the old profile card
- [ ] Consent persists for the session (banner not shown again after accepting)

### 14f. Run History Anomaly Alerts

1. Run a pipeline at least 5 times so baseline statistics accumulate
2. Simulate an anomalous run — e.g. a query that returns far fewer rows than usual (add a WHERE clause to drastically reduce results)
3. Go to **Run History → Run Detail** for the anomalous run

- [ ] Warning badge appears on the step whose `rows_affected` is a statistical outlier (>2σ)
- [ ] Optional Ollama narrative sentence appears alongside the badge explaining the anomaly
- [ ] Steps within normal range show no badge
- [ ] No badge on first 1–2 runs (insufficient baseline)

### 14g. AI global disable

1. Set `FLOWFORGE_AI_ENABLED=false` in `.env` and restart the server
2. Open Report Designer, Run Detail, etc.

- [ ] All AI buttons (Visualize, Explain, Optimize, Explain this error, Summarise) are hidden
- [ ] No AI endpoints reachable — `/api/ai/*` returns 503
3. Reset to `FLOWFORGE_AI_ENABLED=true` (or remove the var) and restart

- [ ] All AI buttons reappear

---

## 15. AI Analyze Step (ai_analyze)

*(Requires Ollama running locally, or `ANTHROPIC_API_KEY` set for Claude provider.)*

### 15a. Basic ai_analyze step — Ollama

1. Create a pipeline: `AI Analyze Test`
2. Add an **AI Analyze** step:

   | Field | Value |
   |---|---|
   | Name | `revenue_summary` |
   | Connection | `FlowForge DB` |
   | Query | `SELECT plan, status, COUNT(*) AS cnt, SUM(monthly_amount) AS mrr FROM public.bulk_test_subscribers GROUP BY plan, status ORDER BY mrr DESC` |
   | Prompt | `Summarise the key revenue trends from this subscriber breakdown in 3 sentences. Highlight the top plan.` |
   | Provider | `ollama` |
   | Model | `llama3.2:3b` |
   | Output variable | `ai_summary` |
   | Max rows | `50` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] Step run log shows the LLM response
- [ ] `rows_affected` in log matches the query row count

### 15b. AI summary in email body

1. Add an **Email** step after `revenue_summary`:
   - Body: `<p>AI Summary:</p><p>{{ ai_summary }}</p>`
2. Run the pipeline

- [ ] Email received with the LLM response in the body (not the literal `{{ ai_summary }}`)

### 15c. Step-namespace access

1. Add a second AI Analyze step named `churn_analysis` with a different query
2. In the email body use `{{ steps.revenue_summary.ai_summary }}` and `{{ steps.churn_analysis.ai_summary }}`

- [ ] Both summaries appear in the email body correctly attributed

### 15d. Custom output_variable

1. Set `output_variable` to `revenue_narrative` on the step
2. In the email body use `{{ revenue_narrative }}`

- [ ] Email body contains the LLM response via the custom variable name

### 15e. max_rows truncation

1. Set `max_rows` to `3` on a query that returns more rows
2. Run the pipeline — check the step log

- [ ] Log shows "Showing first 3 of N rows" note was appended to the prompt
- [ ] `rows_affected` still shows the total (not 3)

### 15f. Ollama unreachable

1. Stop Ollama (`Ctrl+C` the `ollama serve` process)
2. Run the pipeline

- [ ] Step fails with a clear "Ollama" error message
- [ ] Set `on_error: continue` — pipeline continues; `{{ ai_summary }}` is empty in downstream steps

---

## 16. SFTP Transfer Step (sftp_transfer)

*(Requires an accessible SFTP server. For local testing:
`docker run -p 2222:22 -e SSH_USERS="testuser:1001" atmoz/sftp` or
use any accessible SFTP endpoint you have credentials for.)*

### 16a. Download single file

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
   | Local path | `D:\Project\flowforge\sample_data\sftp_test\` |

3. Run the pipeline

- [ ] Step succeeds
- [ ] File downloaded to `sample_data\sftp_test\test_file.csv`
- [ ] `output_path` visible in step run log
- [ ] `files_loaded = 1` in log

### 16b. Download directory with glob pattern

1. Edit the step:
   - Remote path: `/upload/` (a directory)
   - Pattern: `*.csv`
   - Local path: `D:\Project\flowforge\sample_data\sftp_test\`

- [ ] Only `.csv` files downloaded (any `.txt` or other files skipped)
- [ ] `files_found` and `files_loaded` counts visible in log

### 16c. overwrite=false skips existing

1. Run the download step again with `overwrite: false`

- [ ] Step succeeds
- [ ] `files_loaded = 0` — already-downloaded files are skipped, not overwritten
- [ ] No error

### 16d. Upload file

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

### 16e. Private key authentication

1. Configure the step with `key_path` (path to a local private key) instead of `password`
2. Run the pipeline

- [ ] Step connects successfully using the private key
- [ ] No error about missing password

### 16f. Invalid host / credentials

1. Set the host to a non-existent server and run

- [ ] Step fails with a clear "SFTP error" message
- [ ] Pipeline error recorded in Run History with the step name

---

## Notes

| Date | Tester | Section | Result | Notes |
|---|---|---|---|---|
| | | | | |

