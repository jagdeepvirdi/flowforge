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
   | Password | `harpal123` |

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
conn = psycopg2.connect('postgresql://flowforge:harpal123@localhost:5434/flowforge')
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

*(Tests the planned feature once implemented — skip for now or mark N/A)*

- [ ] N/A — feature not yet built

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

## 10. Scheduling

1. Open a pipeline → set a schedule (e.g. every 5 minutes: `*/5 * * * *`)
2. Enable the schedule and wait
3. Check Run History — pipeline should appear as triggered by `scheduler`
4. Disable the schedule

- [ ] Scheduled run appears in history with `triggered_by = scheduler`
- [ ] Schedule disabled without deleting the pipeline

---

## 11. OneDrive Upload

*(Not yet built — backlog item. Skip.)*

- [ ] N/A — feature not yet implemented

---

## Notes

| Date | Tester | Section | Result | Notes |
|---|---|---|---|---|
| | | | | |

