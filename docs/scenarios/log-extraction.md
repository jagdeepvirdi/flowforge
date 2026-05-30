# Scenario: Remote Script & Log Processing

Build a pipeline that runs a script on a remote server via SSH, queries the DB table the script updated, generates an Excel report, and emails both the Excel and the raw script log as attachments.

---

## What This Pipeline Does

```
[SSH: run script] ──▶ updates DB table + saves log file
                                    ↓
                         [Report: query DB table] ──▶ Excel file
                                    ↓
              [Email: log + Excel attached]
```

| Step | Type | Purpose |
|---|---|---|
| `run_extraction` | `ssh_command` | Run remote script; save stdout/stderr to `.log` file |
| `generate_report` | `report` | Query the DB table the script populated; produce Excel |
| `send_results` | `email` | Attach both files and send |

Three steps total. No intermediate steps, no bash piping, no manual file management.

---

## Prerequisites

1. **SSH Connection** — add your server in **Connections → SSH**. Note its UUID.
2. **DB Connection** — add the database the script writes to in **Connections → Database**. Note its UUID.
3. **Report Config** — create a report config in the **Report Designer** that queries the table the script populates. Note its UUID.
4. **Email Config** — set up an email config with recipient list and body template (see below). Note its UUID.

---

## Import the Template

Go to **Settings → Import Pipeline** and upload `examples/log-extraction-pipeline.yaml`.  
Replace the four `<YOUR_*_ID>` placeholders with your actual UUIDs, then enable the pipeline.

---

## How `save_output` Works

The `ssh_command` step has a `save_output: true` option. When enabled:

- stdout (and stderr if `include_stderr: true`) is written to a file in the output directory
- `output_path` is set on the step result — identical to how `report` steps work
- The file is saved **even if the command exits non-zero**, so you can attach the crash log to the alert email for diagnosis
- Downstream steps reference it as `{{ steps.run_extraction.output_path }}`

```yaml
step_type: ssh_command
config:
  ssh_connection_id: <uuid>
  command: "python /scripts/nightly_extract.py --date {{ current_date }}"
  save_output: true
  output_filename: "extract_{{ current_date }}.log"
  include_stderr: true   # append STDERR section to the file (default: true)
```

---

## Email Body Template

The body can reference both the script run and the report directly.  
Paste this into your Email Config's body template:

```html
<h2>Nightly Data Extract — {{ current_date }}</h2>

<p>The nightly extraction script completed successfully.</p>

<table style="border-collapse:collapse;font-family:monospace;font-size:13px">
  <tr>
    <td style="padding:4px 16px 4px 0;color:#666">Script log</td>
    <td>Attached — <code>extract_{{ current_date }}.log</code></td>
  </tr>
  <tr>
    <td style="padding:4px 16px 4px 0;color:#666">Excel report</td>
    <td>Attached — query results from the updated table</td>
  </tr>
</table>

<p style="margin-top:16px;color:#444;font-size:12px">
  Pipeline: {{ pipeline_name }} &nbsp;|&nbsp; Run ID: {{ run_id }}
</p>
```

---

## Alerting Variant — Attach Log on Failure Only

If you only want the email when the script fails, set `send_only_on_failure: true` on the pipeline and set `on_error: stop` on the script step. The script log is always saved (even on failure), so it will be available when the alert fires.

```yaml
# Pipeline settings
send_only_on_failure: true

# ssh_command step
on_error: stop      # halt the pipeline so the email step is skipped on success
```

The email body template for the alert variant:

```html
<h2>⚠ Extraction Script Failed — {{ current_date }}</h2>

<p>The nightly extraction script exited with an error.
The full stdout/stderr log is attached for diagnosis.</p>

<p style="color:#666;font-size:12px">Pipeline: {{ pipeline_name }}</p>
```

---

## Common Remote Script Patterns

### Python script updating a PostgreSQL table
```bash
python /opt/scripts/extract_orders.py \
  --date {{ current_date }} \
  --db-url "{{ env.SOURCE_DB_URL }}" \
  --target-table staging.orders_{{ current_month }}
```

### Shell script with explicit log file reference
```bash
bash /opt/scripts/run_etl.sh {{ current_date }} 2>&1
```
Set `include_stderr: false` (stderr is already merged with stdout by `2>&1`).

### Oracle SQL*Plus script
```bash
sqlplus -S user/pass@//host/service @/scripts/load_data.sql {{ current_date }}
```

### Checking the script exists before running (fail fast)
```bash
test -f /opt/scripts/extract.py && python /opt/scripts/extract.py --date {{ current_date }}
```

---

## Attaching Multiple Files

The `email` step accepts any number of attachments — mix report files, script logs, and health check reports freely:

```yaml
step_type: email
config:
  email_config_id: <uuid>
  attachments:
    - "{{ steps.run_extraction.output_path }}"     # script log (.log)
    - "{{ steps.generate_report.output_path }}"    # Excel report (.xlsx)
    - "{{ steps.check_db.output_path }}"           # DB health check (.xlsx)
```

Smart attachment applies: any file over `attachment_max_mb` is automatically uploaded to Google Drive and a link is included in the email body instead.

---

## Scheduling

The pipeline can run on any schedule. Typical choices for nightly extraction:

| Schedule | Cron | When |
|---|---|---|
| 2 AM daily | `0 2 * * *` | Every night |
| 1 AM weekdays | `0 1 * * 1-5` | Business nights only |
| Every 6 hours | `0 */6 * * *` | Continuous intraday |
