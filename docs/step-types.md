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

Generates a report file (Excel, CSV, PDF, or JSON) from a saved report config. The report config holds the query, format, and output filename.

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
| `format` | `excel` \| `csv` \| `pdf` \| `json` |
| `output_filename` | Supports variables: `report_{{ current_month }}.xlsx`. Extension updates automatically when format is changed in the UI. |
| `sheet_name` | Excel only — sheet tab name |
| `template_path` | Excel only — path to a `.xlsx` template file |
| `title` | PDF only — document title |

**JSON format:** Outputs a JSON array of objects, one per row. Column names from `cursor.description` become the object keys. Useful for downstream API consumers or further processing steps.

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

**Quick-attach (Pipeline Builder UI):** Any `report` steps that appear before the email step in the pipeline are shown as one-click buttons above the attachments field, displaying the step name and expected output filename. Clicking inserts `{{ steps.<name>.output_path }}` automatically — no typing required.

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

## data_load

Loads data from a file or SQL query into any configured database table.

```yaml
step_type: data_load
config:
  target_connection_id: <uuid>
  target_table: "staging.sales_{{ current_month }}"
  mode: replace                 # replace | append
  create_if_missing: true       # auto-create table if it doesn't exist
  chunk_size: 1000              # rows per INSERT batch (default 1000)
  column_map:                   # optional — rename source columns
    SRC_COL: target_col
  source:
    type: file                  # file | query
    file_path: "{{ steps.generate_report.output_path }}"
    file_format: csv            # csv | excel — inferred from extension if omitted
    sheet_name: Sheet1          # Excel only
```

Or with a SQL query source:

```yaml
source:
  type: query
  connection_id: <uuid>         # source connection (can differ from target)
  query: >
    SELECT id, name, amount
    FROM source_table
    WHERE month = '{{ current_month }}'
```

**Modes:**

| Mode | Behaviour |
|---|---|
| `replace` | `TRUNCATE` the table, then bulk INSERT all rows |
| `append` | Bulk INSERT only — existing rows untouched |

**`create_if_missing`:** When `true`, FlowForge checks the target table's existence via catalog queries (`information_schema.tables` for PostgreSQL, `user_tables`/`all_tables` for Oracle). If the table is absent it is created automatically with column types inferred from the data (see table below). The step log shows `(table auto-created)`. Subsequent runs skip the create silently.

**Type inference (column types for auto-created tables):**

| Value | PostgreSQL | Oracle |
|---|---|---|
| bool / "true"/"false" | `BOOLEAN` | `NUMBER(1)` |
| int / digit string | `BIGINT` | `NUMBER(18)` |
| float / decimal string | `NUMERIC` | `NUMBER` |
| datetime / ISO timestamp string | `TIMESTAMP` | `TIMESTAMP` |
| date object / YYYY-MM-DD string | `DATE` | `DATE` |
| anything else / empty | `TEXT` | `VARCHAR2(4000)` |

Samples up to 1,000 rows per column. Column names are unquoted to match the INSERT statement on both databases.

**Outputs:**
- `{{ steps.<name>.rows_affected }}` — total rows inserted

---

## bulk_load

Scans a source directory for matching files and bulk-loads them into a target database table. Designed for daily/scheduled file drop patterns (e.g. `SUBS_20260522.csv`). Bulk load configs are managed in the **Bulk Loads** UI page and referenced by `bulk_load_config_id` in the step config.

```yaml
step_type: bulk_load
config:
  bulk_load_config_id: <uuid>   # from Bulk Loads page (all settings live there)
```

Or inline (all fields):

```yaml
step_type: bulk_load
config:
  connection_id: <uuid>
  source_directory: "/data/incoming/"
  file_prefix: "SUBS_"          # only load files starting with this
  file_prefix_exclude: "SUBS_TEST_"  # skip files starting with this
  file_type: csv
  delimiter: ","
  header_rows: 1
  footer_rows: 0
  target_table: "staging.subscriptions"
  load_mode: replace            # replace | append
  column_mapping: []            # optional column rename list
  archive_directory: "/data/archive/{{ current_date }}/"  # move loaded files here
  on_no_files: skip             # skip (succeed) | fail
```

**Load paths:**

| Database | Method |
|---|---|
| PostgreSQL | `COPY FROM STDIN` (fast path) |
| Any other | Chunked `executemany` Python fallback |

**Outputs:**

| Variable | Example |
|---|---|
| `{{ steps.<name>.files_found }}` | `3` |
| `{{ steps.<name>.files_loaded }}` | `3` |
| `{{ steps.<name>.files_failed }}` | `0` |
| `{{ steps.<name>.records_loaded }}` | `147832` |
| `{{ steps.<name>.records_failed }}` | `14` |
| `{{ steps.<name>.duration_sec }}` | `8.3` |

Use these in a downstream `email` step body to send a load-confirmation message without any extra steps.

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

## onedrive_upload

Uploads a file to Microsoft OneDrive via the Microsoft Graph API and returns a shareable anonymous-view link. Uses the same MSAL credentials configured for the Microsoft 365 email provider.

```yaml
step_type: onedrive_upload
config:
  file_path:   "{{ steps.generate_report.output_path }}"
  folder_id:   "root"                                 # OneDrive item ID or 'root'
  rename_to:   "Revenue_{{ current_month }}.xlsx"     # optional — rename in OneDrive
  user_email:  ""                                     # optional — defaults to MICROSOFT_SENDER_EMAIL
```

**`folder_id`:** The item ID of the destination folder in OneDrive. Use `"root"` to place the file directly in the user's root folder. To find an item ID: navigate to the folder in OneDrive on the web, open Developer Tools → Network, and look for the `id` field in Graph API calls, or use the Microsoft Graph Explorer.

**`user_email`:** The Microsoft 365 user whose OneDrive to upload to. If omitted, falls back to `MICROSOFT_SENDER_EMAIL` from the environment.

**Prerequisites:** `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_SENDER_EMAIL` must be set (same as the M365 email provider). The Azure AD app registration needs `Files.ReadWrite.All` (application permission) in addition to `Mail.Send`.

**Large files:** Files larger than 4 MB are automatically uploaded via a resumable upload session (Graph API `createUploadSession`). Files ≤ 4 MB use a single PUT request.

**Outputs:**
- `{{ steps.<name>.drive_url }}` — anonymous view URL for the uploaded file

Use it downstream in an email body:
```
The report is available here: {{ steps.upload_report.drive_url }}
```

**Smart attachment integration:** The `email` step supports OneDrive as a smart-attachment destination. Set `onedrive_folder_id` in the Email Designer to route oversized attachments to OneDrive instead of (or in preference over) Google Drive.

---

## ai_analyze

Runs a SQL query, formats the results as a data table, passes it to an LLM with a user-defined prompt, and stores the response in a pipeline variable. Use it to generate natural-language summaries, anomaly explanations, or commentary that can be embedded in downstream email bodies.

```yaml
step_type: ai_analyze
config:
  connection_id:   <uuid>                              # DB connection (optional — falls back to DB_* env vars)
  query: >
    SELECT region, SUM(revenue) AS total_revenue
    FROM sales
    WHERE month = '{{ current_month }}'
    GROUP BY region
    ORDER BY total_revenue DESC
  prompt: >
    Summarise the regional revenue distribution for {{ current_month }} in 3 sentences.
    Highlight the top and bottom performers and flag any unusual patterns.
  output_variable: ai_summary                          # name of the pipeline variable (default: ai_summary)
  provider:        ollama                              # 'ollama' (default, free, local) | 'claude'
  model:           llama3.2:3b                         # optional — overrides OLLAMA_QUERY_MODEL / default Claude model
  max_rows:        100                                 # rows sent to LLM (default 100, hard cap 500)
```

**How it works:**

1. The SQL query is rendered with Jinja2 variables and executed against the configured connection.
2. Column names and up to `max_rows` rows are formatted as a pipe-delimited text table.
3. The table is prepended to the `prompt` and sent to the AI provider.
4. The response is stored in `output_variable` (top-level context) and in `{{ steps.<name>.ai_summary }}` (step context).

**Providers:**

| `provider` | Requirement | Default model |
|---|---|---|
| `ollama` (default) | Ollama running at `OLLAMA_URL` | `OLLAMA_QUERY_MODEL` (default `llama3.2:3b`) |
| `claude` | `ANTHROPIC_API_KEY` set + `pip install anthropic` | `claude-haiku-4-5-20251001` |

**Using the result downstream:**

In an `email` step's `body_template`:
```html
<p>{{ ai_summary }}</p>
```

Or using the step namespace (useful when multiple ai_analyze steps run):
```html
<p>{{ steps.analyze_revenue.ai_summary }}</p>
```

**`max_rows` guidance:** Keep this below 200 for `llama3.2:3b` (4 GB context limit). Larger models tolerate more. If the query returns more rows than `max_rows`, a truncation note is appended to the prompt so the LLM knows it is working with a sample.

**Outputs:**
- `{{ <output_variable> }}` — LLM response at top-level context (default: `{{ ai_summary }}`)
- `{{ steps.<name>.ai_summary }}` — same value, always accessible as `ai_summary` on the step regardless of `output_variable` name
- `{{ steps.<name>.rows_affected }}` — total rows the query returned (before truncation)

**Error behaviour:** If the query fails or the AI provider is unreachable, the step fails. Set `on_error: continue` to let the pipeline proceed anyway (downstream steps receive an empty `{{ ai_summary }}`).

---

## sftp_transfer

Downloads files from or uploads files to a remote SFTP server. Supports password authentication and private-key authentication (RSA, ECDSA, Ed25519, DSS). Requires `pip install paramiko` (or `pip install 'flowforge[sftp]'`).

```yaml
step_type: sftp_transfer
config:
  # Connection
  host:            sftp.example.com          # required
  port:            22                        # default: 22
  username:        reports                   # required
  password:        "{{ env.SFTP_PASSWORD }}" # use password OR key_path
  key_path:        /home/user/.ssh/id_rsa    # path to private key file
  key_passphrase:  ""                        # optional passphrase for encrypted key
  timeout:         30                        # connection timeout in seconds (default: 30)

  # Transfer
  operation:    download                     # 'download' or 'upload'  (required)
  remote_path:  /data/exports/               # remote file or directory — supports {{ variables }}
  local_path:   /tmp/reports/               # local file or directory — supports {{ variables }}

  # Download-only options
  pattern:      "*.csv"                      # glob filter when remote_path is a directory
                                             # e.g. "REPORT_*.xlsx"  (default: all files)

  # Upload-only options
  create_remote_dirs: true                   # create missing remote directories (default: true)

  # Both operations
  overwrite:    true                         # overwrite existing files (default: true)
                                             # false → skip files that already exist
```

### Download — single file

When `remote_path` points to a file, that file is downloaded to `local_path`. If `local_path` is a directory (or ends with `/`), the remote filename is preserved inside it.

### Download — directory

When `remote_path` points to a directory, all files in that directory are downloaded into `local_path`. Subdirectories are not recursed. Use `pattern` to filter by glob:

```yaml
remote_path: /data/monthly/
local_path:  /tmp/downloads/
pattern:     "REPORT_*.xlsx"
```

### Upload

`local_path` must point to an existing file (directories are not supported for upload). If `remote_path` ends with `/` or `\`, the local filename is appended automatically. Missing remote parent directories are created automatically unless `create_remote_dirs: false`.

```yaml
operation:   upload
local_path:  "{{ steps.generate_report.output_path }}"
remote_path: /outbound/reports/{{ current_month }}/
```

**Outputs (download):**
- `{{ steps.<name>.output_path }}` — path of the downloaded file (single file), or first file downloaded (directory)
- `{{ steps.<name>.files_found }}` — number of files matched (after pattern filter)
- `{{ steps.<name>.files_loaded }}` — number of files successfully downloaded
- `{{ steps.<name>.files_failed }}` — number of files that failed

**Outputs (upload):**
- `{{ steps.<name>.files_loaded }}` — `1` on success, `0` if skipped (overwrite=false)

**Error behaviour:** Connection errors, missing remote paths, and upload failures all fail the step. Set `on_error: continue` to let the pipeline proceed. Partial directory downloads (some files fail) also fail the step and report which files could not be downloaded.

---

## Variable Reference

All config string fields support Jinja2 variables. Available at runtime:

### Date / time (YYYY-MM-DD)

| Variable | Example | Notes |
|---|---|---|
| `{{ current_date }}` | `2026-05-23` | Today |
| `{{ yesterday }}` | `2026-05-22` | |
| `{{ week_start }}` | `2026-05-18` | Monday of current ISO week |
| `{{ week_end }}` | `2026-05-24` | Sunday of current ISO week |
| `{{ month_start }}` | `2026-05-01` | First of current month |
| `{{ month_end }}` | `2026-05-31` | Last of current month |
| `{{ prev_month_start }}` | `2026-04-01` | First of previous month |
| `{{ prev_month_end }}` | `2026-04-30` | Last of previous month |
| `{{ quarter_start }}` | `2026-04-01` | First of current quarter |
| `{{ quarter_end }}` | `2026-06-30` | Last of current quarter |
| `{{ current_month }}` | `2026-05` | YYYY-MM |
| `{{ current_year }}` | `2026` | YYYY |

### Timestamp boundaries (YYYYMMDDHHmmSS — 14 digits)

Use these directly in SQL `BETWEEN` clauses for date-range extracts.

| Variable | Value | Use case |
|---|---|---|
| `{{ day_start_ts }}` | `20260523000000` | Today start |
| `{{ day_end_ts }}` | `20260523235959` | Today end |
| `{{ yesterday_start_ts }}` | `20260522000000` | Yesterday start |
| `{{ yesterday_end_ts }}` | `20260522235959` | Yesterday end |
| `{{ month_start_ts }}` | `20260501000000` | Month start |
| `{{ month_end_ts }}` | `20260531235959` | Month end |
| `{{ prev_month_start_ts }}` | `20260401000000` | Previous month start |
| `{{ prev_month_end_ts }}` | `20260430235959` | Previous month end |

Example:
```sql
WHERE created_ts BETWEEN {{ month_start_ts }} AND {{ month_end_ts }}
```

### Delta / incremental

| Variable | Format | Notes |
|---|---|---|
| `{{ last_success_at }}` | `YYYYMMDDHHmmSS` | `finished_at` of the most recent successful run; empty string on first run |
| `{{ last_success_date }}` | `YYYY-MM-DD` | Same run, date-only format |

Use with a Jinja2 guard for delta queries:
```sql
{% if last_success_at %}
  WHERE updated_ts >= {{ last_success_at }}
{% endif %}
```

### Run metadata

| Variable | Example |
|---|---|
| `{{ timestamp }}` | `23052026143022` (DDMMYYYYHHmmSS — unique per second, for filenames) |
| `{{ run_id }}` | UUID of the current pipeline run |
| `{{ pipeline_name }}` | Name of the running pipeline |

### Environment & pipeline variables

| Variable | Notes |
|---|---|
| `{{ env.VAR_NAME }}` | Any OS environment variable |
| `{{ my_var }}` | Pipeline variable (set in Pipeline Builder → Variables card) |
| `{{ vars.my_var }}` | Same, explicit namespace |
| `{{ subscription_count }}` | Scalar captured by `output_variable` on a db_query step |

### Step outputs

| Variable | Set by |
|---|---|
| `{{ steps.<name>.output_path }}` | `report` step |
| `{{ steps.<name>.drive_url }}` | `drive_upload`, `onedrive_upload`, or `email` step (smart attachment) |
| `{{ steps.<name>.rows_affected }}` | `db_query`, `data_load`, `ai_analyze` steps |
| `{{ steps.<name>.ai_summary }}` | `ai_analyze` step |
| `{{ ai_summary }}` | `ai_analyze` step — also injected to top-level context as `output_variable` |
| `{{ steps.<name>.files_found }}` | `bulk_load`, `sftp_transfer` (download) steps |
| `{{ steps.<name>.files_loaded }}` | `bulk_load`, `sftp_transfer` steps |
| `{{ steps.<name>.files_failed }}` | `sftp_transfer` (download directory) step |
| `{{ steps.<name>.records_loaded }}` | `bulk_load` step |
| `{{ steps.<name>.records_failed }}` | `bulk_load` step |
| `{{ steps.<name>.duration_sec }}` | `bulk_load` step |
