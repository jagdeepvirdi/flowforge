# Step Types Reference

Every pipeline step has a `step_type` that determines what it does and what config fields it accepts. Steps run in order; each step's outputs are available to subsequent steps via `{{ steps.<name>.* }}` variables.

---

## Common Fields

All steps share these fields (set in the pipeline builder, not in `config`):

| Field | Type | Description |
|---|---|---|
| `name` | string | Step name — used as the key in `{{ steps.<name> }}` |
| `step_order` | integer | Execution order (1-based, drag to reorder in UI) |
| `on_error` | `stop` \| `continue` | Whether to halt the pipeline or continue when this step fails |
| `enabled` | boolean | Disable to skip without deleting |

---

## db_procedure

Calls a stored procedure or package in any configured database connection.

```yaml
step_type: db_procedure
config:
  connection_id: <uuid>           # DB connection from Connections page
  procedure: pkg_revenue.populate # Oracle: package.procedure; PostgreSQL: schema.func
  params:
    period:  "{{ current_month }}"
    run_id:  "{{ run_id }}"
```

**Notes:**
- PostgreSQL: maps to `CALL procedure_name(...)`. Functions that return void also work.
- Oracle: generates `BEGIN package.procedure(:param1, :param2); END;` — the `package.procedure` dot syntax is handled automatically.
- All param values support `{{ variables }}`.
- Step succeeds when the procedure returns without raising an exception.

**Outputs:** none (no `{{ steps.<name>.* }}` values set).

---

## db_query

Runs a SQL query and optionally writes results to a target table. Can also capture a scalar value into the pipeline context.

```yaml
step_type: db_query
config:
  connection_id: <uuid>
  query: >
    SELECT count(*) AS subscription_count
    FROM subscriptions
    WHERE month = '{{ current_month }}'
  output_table:    staging.monthly_counts   # optional — write rows to this table
  mode:            replace                  # replace | append | truncate_insert
  output_variable: subscription_count       # optional — capture first col of first row
```

**Modes:**

| Mode | Behaviour |
|---|---|
| `replace` | Truncates the output table, then inserts all rows |
| `append` | Inserts rows without touching existing data |
| `truncate_insert` | Same as `replace`, explicit alias |

**`output_variable`:** When set, the first column of the first row is captured and injected into the pipeline context as `{{ subscription_count }}`. Use it in downstream email body templates or step configs.

**Outputs:**
- `{{ steps.<name>.rows_affected }}` — number of rows returned by the query

---

## report

Generates a report file (Excel, CSV, or PDF) from a saved report config. The report config holds the query, format, and output filename.

```yaml
step_type: report
config:
  report_config_id: <uuid>   # from Report Designer
```

The report config itself (stored in `report_configs` table) contains:

| Field | Description |
|---|---|
| `connection_id` | Database to run the query against |
| `query` | SQL query — supports `{{ variables }}` |
| `format` | `excel` \| `csv` \| `pdf` |
| `output_filename` | Supports variables: `report_{{ current_month }}.xlsx` |
| `sheet_name` | Excel only — sheet tab name |
| `template_path` | Excel only — path to a `.xlsx` template file |
| `title` | PDF only — document title |

**Outputs:**
- `{{ steps.<name>.output_path }}` — absolute path to the generated file

Use this in the `email` step's `attachments` field:
```yaml
attachments:
  - "{{ steps.generate_report.output_path }}"
```

---

## email

Sends an email using a saved email config and provider. Supports smart attachments.

```yaml
step_type: email
config:
  email_config_id: <uuid>    # from Email Designer
  attachments:
    - "{{ steps.generate_report.output_path }}"
    - "/absolute/path/to/file.csv"
```

The email config (stored in `email_configs` table) contains:

| Field | Description |
|---|---|
| `provider_id` | Email provider (Gmail / M365 / SMTP) |
| `from_name` | Display name in the From field |
| `subject` | Supports `{{ variables }}` |
| `body_template` | HTML + Jinja2 template |
| `recipient_group_id` | Recipient group, or use `to_addresses` directly |
| `to_addresses` | Direct list of recipient emails |
| `cc_addresses` | CC list |
| `bcc_addresses` | BCC list |
| `attachment_max_mb` | Smart attachment threshold (default: 10 MB) |
| `drive_folder_id` | Drive folder for large-file uploads |
| `drive_share_message` | Jinja2 template for the Drive link message |

**Smart attachments:** If any attachment file exceeds `attachment_max_mb`, it is uploaded to Google Drive automatically and a shareable link is added to the email body in place of the direct attachment.

**Outputs:**
- `{{ steps.<name>.drive_url }}` — Drive URL if any attachment was uploaded (last upload URL)

---

## drive_upload

Uploads a file to Google Drive and creates a shareable link.

```yaml
step_type: drive_upload
config:
  file_path:  "{{ steps.generate_report.output_path }}"
  folder_id:  "{{ env.GOOGLE_DRIVE_FOLDER_ID }}"   # or hardcoded folder ID
  rename_to:  "Revenue_{{ current_month }}.xlsx"    # optional — rename in Drive
```

The folder ID is the last segment of the Drive folder URL:
`https://drive.google.com/drive/folders/`**`<this-part>`**

**Outputs:**
- `{{ steps.<name>.drive_url }}` — shareable Drive link for the uploaded file

Use it downstream in an email body:
```
The report is available here: {{ steps.upload_to_drive.drive_url }}
```

---

## Variable Reference

All config string fields support Jinja2 variables. Available at runtime:

| Variable | Example |
|---|---|
| `{{ current_date }}` | `2026-05-20` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ yesterday }}` | `2026-05-19` |
| `{{ week_start }}` | `2026-05-18` (Monday of current ISO week) |
| `{{ week_end }}` | `2026-05-24` (Sunday of current ISO week) |
| `{{ month_start }}` | `2026-05-01` |
| `{{ month_end }}` | `2026-05-31` |
| `{{ quarter_start }}` | `2026-04-01` |
| `{{ quarter_end }}` | `2026-06-30` |
| `{{ timestamp }}` | `20052026143022` |
| `{{ run_id }}` | UUID of the current run |
| `{{ pipeline_name }}` | Name of the running pipeline |
| `{{ env.VAR_NAME }}` | Any environment variable |
| `{{ steps.<name>.output_path }}` | File path from a previous report step |
| `{{ steps.<name>.drive_url }}` | Drive URL from a previous drive_upload or email step |
| `{{ steps.<name>.rows_affected }}` | Row count from a previous db_query step |
| `{{ my_var }}` | Any pipeline variable (set in Pipeline Builder → Variables) |
| `{{ vars.my_var }}` | Same, explicit namespace |
| `{{ subscription_count }}` | Scalar captured by `output_variable` in a db_query step |
