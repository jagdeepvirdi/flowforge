/* Centralised help content — intro cards, glossary, step hints, field tooltips. */

export interface IntroCard {
  title: string
  body:  string
}

export const INTRO_CARDS: Record<string, IntroCard> = {
  dashboard: {
    title: 'Your pipeline control center',
    body:  'See every pipeline\'s last run status at a glance, trigger runs manually with Run Now, and monitor active jobs in real time. The sidebar shows today\'s run count.',
  },
  pipelines: {
    title: 'What is a pipeline?',
    body:  'A pipeline is an ordered list of steps that run in sequence: query a database, generate a report, send an email, upload to Drive. Each step gets the outputs of previous steps via {{ variables }}.',
  },
  reports: {
    title: 'What is a report config?',
    body:  'A report config pairs a SQL query with an output format (Excel / PDF / CSV). When a pipeline\'s report step runs, it executes the query and writes the file. The output path is available to downstream steps as {{ steps.step_name.output_path }}.',
  },
  emails: {
    title: 'What is an email config?',
    body:  'An email config defines the subject, body, and recipients for one kind of email. It references an Email Provider (Gmail / M365 / SMTP) for delivery. Attach report files by referencing {{ steps.report_step.output_path }} in the attachments field.',
  },
  connections: {
    title: 'Database connections & email providers',
    body:  'DB Connections store credentials for your data-source databases (PostgreSQL, Oracle). Email Providers store OAuth2 / SMTP credentials for sending mail. All credentials are encrypted at rest with AES-256.',
  },
  recipients: {
    title: 'What are recipient groups?',
    body:  'Recipient groups are named lists of email addresses — "Finance Team", "Management", "All Staff". Assign a group to an email config instead of typing addresses every time. Groups can be shared across many email configs.',
  },
  runs: {
    title: 'Run history',
    body:  'Every pipeline execution is recorded here — triggered by the scheduler, CLI, or Run Now. Click a run to see step-by-step timing, expandable logs, generated file links, and email recipients.',
  },
  settings: {
    title: 'Settings & OAuth setup',
    body:  'Connect FlowForge to Gmail or Microsoft 365 via OAuth2, and configure Google Drive for smart attachments. Status badges show which providers are fully wired up.',
  },
}

export interface GlossaryEntry {
  term:  string
  def:   string
  where: string
}

export const GLOSSARY: GlossaryEntry[] = [
  { term: 'Pipeline',        def: 'An ordered sequence of steps that run one after another. Created in the Pipeline Builder.',                                              where: 'Pipelines page' },
  { term: 'Step',            def: 'A single unit of work inside a pipeline — a DB call, report generation, email send, or Drive upload.',                                  where: 'Pipeline Builder' },
  { term: 'Step Type',       def: 'The kind of work a step does: db_procedure, db_query, report, email, drive_upload.',                                                    where: 'Pipeline Builder' },
  { term: 'Report Config',   def: 'Stores a SQL query + output format (Excel/PDF/CSV). Referenced by report steps.',                                                       where: 'Reports page' },
  { term: 'Email Config',    def: 'Stores subject, body template, recipients, and smart-attachment settings. Referenced by email steps.',                                   where: 'Emails page' },
  { term: 'Email Provider',  def: 'Gmail, Microsoft 365, or SMTP credentials used to actually send mail. One config can be shared across many email configs.',             where: 'Connections page' },
  { term: 'Recipient Group', def: 'A named list of email addresses. Assign to an email config so you don\'t type addresses every time.',                                   where: 'Recipients page' },
  { term: 'Smart Attachment',def: 'If a report file exceeds the size threshold, FlowForge uploads it to Google Drive and puts a link in the email instead of attaching.',  where: 'Email config → Smart Attachment' },
  { term: 'Run',             def: 'One execution of a pipeline — has a status (running / success / failed / cancelled) and a full step-by-step log.',                      where: 'Run History page' },
  { term: 'Step Run',        def: 'The record of one step within a run — includes duration, rows affected, output path, and error message.',                               where: 'Run Detail page' },
  { term: 'Pipeline Variable', def: 'A key-value pair attached to a pipeline. Available as {{ my_var }} in all config strings. Secrets are encrypted and masked in the UI.', where: 'Pipeline Builder → Variables' },
  { term: 'on_error',        def: '"stop" halts the pipeline when this step fails. "continue" logs the error and moves to the next step.',                                 where: 'Each step\'s header' },
]

export interface StepHint {
  summary: string
  tips:    string[]
}

export const STEP_HINTS: Record<string, StepHint> = {
  db_procedure: {
    summary: 'Calls a stored procedure or package in your database.',
    tips: [
      'Oracle packages use package.procedure syntax — e.g. pkg_revenue.populate_monthly',
      'Params support Jinja2 variables: { "period": "{{ current_month }}" }',
      'The step succeeds when the procedure returns without error.',
    ],
  },
  db_query: {
    summary: 'Runs a SQL query and optionally writes results to a table.',
    tips: [
      'replace — truncates the output table, then inserts all rows.',
      'append — inserts rows without touching existing data.',
      'truncate_insert — same as replace but explicit.',
      'Leave output table blank to run the query without writing results.',
      'Output variable: captures the first column of the first row as a named variable — e.g. set "subscription_count" then use {{ subscription_count }} in later steps.',
    ],
  },
  report: {
    summary: 'Generates an Excel, PDF, or CSV file from a report config.',
    tips: [
      'The output file path is available to later steps as {{ steps.this_step_name.output_path }}',
      'Use that path in the email step\'s Attachments field to attach the file.',
      'Create or edit report configs on the Reports page.',
    ],
  },
  email: {
    summary: 'Sends an email using a configured email config and provider.',
    tips: [
      'Attachments field: one path per line. Supports {{ variables }}.',
      'Use {{ steps.report_step.output_path }} to attach a file from a previous report step.',
      'Smart attachment: if the file exceeds the size threshold it\'s uploaded to Drive automatically.',
    ],
  },
  drive_upload: {
    summary: 'Uploads a file to Google Drive and creates a shareable link.',
    tips: [
      'The Drive link is available to later steps as {{ steps.this_step_name.drive_url }}',
      'Folder ID: the part after /folders/ in the Drive folder URL.',
      'Rename to supports {{ variables }} — e.g. Report_{{ current_month }}.xlsx',
    ],
  },
  data_load: {
    summary: 'Bulk-loads data into a target database table from a file or SQL query.',
    tips: [
      'Source: File — attach a CSV or Excel from a preceding report step using the quick-attach buttons.',
      'Source: SQL Query — run a query on any source connection and load its results into the target.',
      'replace — truncates the target table then bulk inserts all rows.',
      'append — inserts rows without touching existing data.',
      'Target table supports {{ variables }} — e.g. staging.sales_{{ current_month }}.',
      'Column map: rename source columns to match the target table schema.',
    ],
  },
  bulk_load: {
    summary: 'Scans a directory for files and bulk-loads all matching files into a database table.',
    tips: [
      'file_prefix — only load files whose name starts with this string (e.g. SUBS_).',
      'file_prefix_exclude — skip files that start with this string.',
      'PostgreSQL: uses COPY FROM STDIN — fastest native path.',
      'Oracle + use_sqlloader: generates a .ctl file and calls sqlldr subprocess — direct-path load.',
      'Python fallback: works on any DB without external tools, loads in 10,000-row chunks.',
      'archive_directory: loaded files are moved here after a successful load. Supports {{ variables }}.',
      'on_no_files: "skip" succeeds silently when no matching files exist; "fail" stops the pipeline.',
      'Output variables: {{ steps.this_step.files_found }}, {{ steps.this_step.files_loaded }}, {{ steps.this_step.records_loaded }} — use in a follow-up email step.',
    ],
  },
}

export interface TooltipContent {
  text:    string
  example?: string
}

export const TOOLTIPS: Record<string, TooltipContent> = {
  cron: {
    text:    'Five space-separated fields: minute hour day-of-month month day-of-week',
    example: '0 8 * * 1-5  →  weekdays at 8 am\n0 9 1 * *    →  1st of every month at 9 am\n*/15 * * * *  →  every 15 minutes',
  },
  variables: {
    text:    'Jinja2 variables resolved at runtime',
    example: '{{ current_date }}    →  2026-05-20\n{{ current_month }}   →  2026-05\n{{ current_year }}    →  2026\n{{ yesterday }}       →  2026-05-19\n{{ week_start }}      →  2026-05-18  (Monday)\n{{ week_end }}        →  2026-05-24  (Sunday)\n{{ month_start }}     →  2026-05-01\n{{ month_end }}       →  2026-05-31\n{{ quarter_start }}   →  2026-04-01\n{{ quarter_end }}     →  2026-06-30\n{{ run_id }}          →  UUID\n{{ pipeline_name }}   →  My Pipeline\n{{ steps.step_name.output_path }}\n{{ env.MY_ENV_VAR }}',
  },
  drive_folder_id: {
    text:    'The folder ID is the last segment of the Drive folder URL.',
    example: 'https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ\n                                        ↑ this part',
  },
  attachment_max_mb: {
    text:    'Files larger than this threshold are uploaded to Google Drive instead of attached directly. A shareable link is added to the email body.',
    example: 'Default: 10 MB\nSet to 0 to always attach directly (not recommended for large reports).',
  },
  body_template: {
    text:    'HTML email body. Supports Jinja2 templating — use {{ variables }} anywhere.',
    example: '<p>Hi,</p>\n<p>Please find the {{ current_month }} report below.</p>\n{% if drive_links %}\n  {{ drive_links[0].url }}\n{% endif %}',
  },
  on_error: {
    text:    'Controls what happens when this step fails.',
    example: 'stop     →  pipeline stops immediately, remaining steps skipped\ncontinue →  error is logged, pipeline continues to next step',
  },
  db_host_port: {
    text:    'PostgreSQL defaults: host=localhost, port=5432\nOracle defaults: host=localhost, port=1521',
    example: 'PostgreSQL:  localhost / 5432 / mydb\nOracle host: localhost / 1521\nOracle service: ORCL  (or use TNS alias in host)',
  },
  oracle_connection: {
    text:    'Two supported formats for Oracle connections.',
    example: 'Format 1 — host + port + service name (Easy Connect):\n  host: db.example.com\n  port: 1521\n  database: ORCL\n\nFormat 2 — TNS alias (requires tnsnames.ora):\n  host: MY_TNS_ALIAS\n  port: (ignored)\n  database: (ignored)',
  },
}
