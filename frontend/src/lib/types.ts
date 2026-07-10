export type Role = 'admin' | 'editor' | 'viewer'

export interface CurrentUser {
  id: string
  username: string
  role: Role
}

export interface User {
  id: string
  username: string
  role: Role
  email: string | null
  mfa_enabled: boolean
  sso_provider: string | null
  created_at: string
}

export interface Project {
  id: string
  name: string
  description: string
  color: string
  is_default: boolean
  created_at: string
  resource_counts?: { pipelines: number; reports: number; emails: number; recipients: number }
}

export type PipelineStatus = 'success' | 'failed' | 'running' | 'cancelled' | 'never run'
// Known built-in types get autocomplete; `(string & {})` keeps the union open for
// community plugin step types registered via FLOWFORGE_PLUGIN_DIR (see docs/plugins.md).
export type StepType =
  | 'db_procedure' | 'db_query' | 'report' | 'email' | 'drive_upload' | 'onedrive_upload'
  | 'ai_analyze' | 'data_load' | 'bulk_load' | 'sftp_transfer' | 'ssh_command'
  | 'db_health_check' | 'data_report' | 'ssh_health_check' | 'notification'
  | 's3_upload' | 'azure_blob_upload'
  | (string & {})
export type OnError = 'stop' | 'continue'
export type ReportFormat = 'excel' | 'csv' | 'pdf' | 'json'
export type ProviderType = 'gmail' | 'microsoft365' | 'smtp' | 'sendgrid' | 'ses' | 'mailgun'
export type DbType = 'postgresql' | 'oracle' | 'mysql' | 'mssql' | 'odbc' | 'redshift' | 'snowflake' | 'bigquery'

export interface Pipeline {
  id: string
  name: string
  description: string
  schedule: string | null
  next_run: string | null
  enabled: boolean
  timeout_minutes: number
  on_failure_webhook_url: string | null
  project_id: string | null
  created_at: string
  updated_at: string
  steps: PipelineStep[]
  variables: PipelineVariable[]
  upstream_deps: PipelineDep[]
  downstream_deps: PipelineDep[]
}

export interface PipelineStep {
  id: string
  pipeline_id: string
  step_order: number
  name: string
  step_type: StepType
  config: Record<string, unknown>
  on_error: OnError
  enabled: boolean
  parallel_group: string | null
}

export interface PipelineDep {
  dep_id: string
  pipeline_id: string
  pipeline_name: string
}

export interface PipelineVariable {
  id?: string
  var_key: string
  var_value: string
  is_secret: boolean
}

export interface WebhookToken {
  id: string
  pipeline_id: string
  label: string
  enabled: boolean
  last_used_at: string | null
  created_at: string
  token?: string   // raw token — only present on creation response
}

export interface PipelineRun {
  id: string
  pipeline_id: string | null   // null when the pipeline has been deleted
  pipeline_name: string
  status: PipelineStatus
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  triggered_by: string
  error_step: string | null
  error_message: string | null
  step_runs?: StepRun[]
}

export interface StepRun {
  id: string
  step_name: string
  step_type: string
  step_order: number
  status: 'success' | 'failed' | 'running' | 'skipped'
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  rows_affected: number | null
  output_path: string | null
  drive_url: string | null
  email_sent_to: string[]
  logs: string | null
  error_message: string | null
}

export interface ColumnConditionalRule {
  operator: 'lt' | 'lte' | 'gt' | 'gte' | 'eq' | 'ne'
  value: number
  bg_color: string     // 6-char hex, no #
  font_color?: string
}

export interface ColumnFormatRule {
  column: string
  number_format?: string
  width?: number
  conditional?: ColumnConditionalRule[]
}

export interface ReportConfig {
  id: string
  name: string
  description: string
  connection_id: string | null
  query: string
  format: ReportFormat
  template_path: string | null
  output_filename: string
  title: string | null
  sheet_name: string | null
  columns: string[]
  column_formatting: ColumnFormatRule[]
  project_id: string | null
  created_at: string
  updated_at: string
}

export interface StepDiff {
  step_name: string
  step_type: string
  step_order: number
  is_new_step: boolean
  rows_current: number | null
  rows_prev: number | null
  rows_delta: number | null
  duration_current: number | null
  duration_prev: number | null
  duration_delta_pct: number | null
  size_current: number | null
  size_prev: number | null
  size_delta: number | null
}

export interface RunDiff {
  prev_run_id: string | null
  steps: StepDiff[]
}

export interface StepTrendPoint {
  date: string
  run_count: number
  success_count: number
  failure_count: number
  avg_duration_ms: number | null
  p95_duration_ms: number | null
  avg_rows_affected: number | null
}

export interface StepTrends {
  window_days: number
  step_type: string | null
  pipeline_id: string | null
  available_step_types: string[]
  series: StepTrendPoint[]
}

export interface EmailConfig {
  id: string
  name: string
  description: string
  provider_id: string | null
  from_name: string | null
  subject: string
  header_text: string | null
  body_template: string
  recipient_group_id: string | null
  to_addresses: string[]
  cc_addresses: string[]
  bcc_addresses: string[]
  attachment_max_mb: number
  drive_folder_id: string | null
  drive_share_message: string | null
  project_id: string | null
  created_at: string
  updated_at: string
}

export interface EmailProvider {
  id: string
  name: string
  provider_type: ProviderType
  is_default: boolean
  created_at: string
  config?: Record<string, unknown>
}

export interface DbConnection {
  id: string
  name: string
  db_type: DbType
  is_default: boolean
  created_at: string
  config?: Record<string, unknown>
}

export interface BulkLoadConfig {
  id: string
  name: string
  description: string
  connection_id: string | null
  source_directory: string
  file_prefix: string
  file_prefix_exclude: string
  file_type: string
  delimiter: string
  header_rows: number
  footer_rows: number
  target_table: string
  load_mode: string
  column_mapping: { source: string; target: string }[]
  use_sqlloader: boolean
  archive_directory: string
  on_no_files: string
  created_at: string
  updated_at: string
}

export interface AnomalyMetric {
  value: number
  mean: number
  std: number
  z_score: number
  pct_diff: number
}

export interface StepAnomaly {
  step_id: string
  step_name: string
  rows_anomaly: AnomalyMetric | null
  duration_anomaly: AnomalyMetric | null
}

export interface RecipientGroup {
  id: string
  name: string
  description: string
  addresses: string[]
  cc_addresses: string[]
  bcc_addresses: string[]
  project_id: string | null
  created_at: string
}
