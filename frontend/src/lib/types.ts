// MAINT-02: pipeline/run response types below are generated from
// docs/openapi/pipelines.yaml (the source of truth for those two route files)
// rather than hand-written — see frontend/src/lib/generated/pipelines.ts and
// `npm run generate:api-types`. Request-shaped types (variables/steps accepted
// on create/update) and types used by routes outside that spec's scope stay
// hand-written here.
import type { components } from './generated/pipelines'

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

export type PipelineDep = components['schemas']['PipelineDep']

/** Step-level dependency edge within one pipeline (Phase 14 Option B). */
export interface StepDep {
  dep_id: string
  upstream_step_id: string
  downstream_step_id: string
}

export interface PipelineVariable {
  id?: string
  var_key: string
  var_value: string
  is_secret: boolean
}

export type WebhookToken = components['schemas']['WebhookToken']
export type PipelineRun = components['schemas']['PipelineRun']
export type StepRun = components['schemas']['StepRun']

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

export type StepDiff = components['schemas']['StepDiff']
export type RunDiff = components['schemas']['RunDiff']
export type StepTrendPoint = components['schemas']['StepTrendPoint']
export type StepTrends = components['schemas']['StepTrends']

export interface EmailConfig {
  id: string
  name: string
  description: string
  provider_id: string | null
  from_name: string | null
  subject: string
  header_text: string | null
  body_template: string
  body_format: 'html' | 'text'
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

export type AnomalyMetric = NonNullable<components['schemas']['AnomalyDetail']>
export type StepAnomaly = components['schemas']['StepAnomaly']

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
