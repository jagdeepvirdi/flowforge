import { useAuth } from './auth'

const BASE = '/api'

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = useAuth.getState().token
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    const data = await res.json().catch(() => ({}))
    useAuth.getState().clearToken()
    // Don't redirect if already on /login — just surface the error message so the
    // login form can display it (a full reload would wipe React state before render).
    if (globalThis.location.pathname !== '/login') {
      globalThis.location.href = '/login'
    }
    throw new Error(data.error ?? 'Unauthorized')
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error ?? `HTTP ${res.status}`)
  }

  // Do NOT swallow parse failures on a successful (2xx) response — a truncated/empty
  // body (e.g. the Flask dev server restarting mid-request) must surface as a real
  // error, not silently become `{}` and get cast to T. Callers assume the full typed
  // shape is present whenever the promise resolves; a fake empty object breaks that
  // and crashes downstream code that dereferences nested fields unguarded.
  return res.json() as Promise<T>
}

const get  = <T>(path: string)             => request<T>('GET',    path)
const post = <T>(path: string, body?: unknown) => request<T>('POST',   path, body)
const put  = <T>(path: string, body?: unknown) => request<T>('PUT',    path, body)
const del  = <T>(path: string)             => request<T>('DELETE', path)

// Auth
export const login  = (username: string, password: string) =>
  post<{ token: string } | { mfa_required: true; mfa_token: string }>('/auth/login', { username, password })
export const logout = () => post<{ message: string }>('/auth/logout')
export const getMe  = () => get<import('./types').CurrentUser>('/auth/me')

// MFA
export const getMfaStatus    = () => get<{ mfa_enabled: boolean; sso_provider: string | null }>('/auth/mfa/status')
export const mfaEnroll       = () => post<{ provisioning_uri: string; secret: string }>('/auth/mfa/enroll')
export const mfaConfirm      = (code: string) => post<{ backup_codes: string[] }>('/auth/mfa/confirm', { code })
export const mfaDisable      = (password: string) => post<{ message: string }>('/auth/mfa/disable', { password })
export const mfaVerify       = (mfa_token: string, code: string) =>
  post<{ token: string }>('/auth/mfa/verify', { mfa_token, code })
export const mfaUseBackup    = (mfa_token: string, backup_code: string) =>
  post<{ token: string; backup_codes_remaining: number }>('/auth/mfa/use-backup', { mfa_token, backup_code })

// SSO
export const getSsoProviders = () => get<{ google: boolean; microsoft: boolean; saml: boolean }>('/auth/sso/providers')

// GDPR (admin)
export const exportUserData = (id: string) => get<object>(`/users/${id}/export`)
export const purgeUserData  = (id: string) => request<{ message: string; purged: boolean }>('DELETE', `/users/${id}?purge=true`)

// Projects
export const getProjects    = () => get<import('./types').Project[]>('/projects')
export const getProject     = (id: string) => get<import('./types').Project>(`/projects/${id}`)
export const createProject  = (data: { name: string; description?: string; color?: string }) => post<import('./types').Project>('/projects', data)
export const updateProject  = (id: string, data: { name?: string; description?: string; color?: string }) => request<import('./types').Project>('PATCH', `/projects/${id}`, data)
export const deleteProject  = (id: string) => del<{ deleted: string }>(`/projects/${id}`)

// Project members (team-scoped access)
export type ProjectMember = { id: string; user_id: string; username: string | null; role: string | null; created_at: string | null }
export const getProjectMembers    = (projectId: string) => get<ProjectMember[]>(`/projects/${projectId}/members`)
export const addProjectMember     = (projectId: string, userId: string) => post<ProjectMember>(`/projects/${projectId}/members`, { user_id: userId })
export const removeProjectMember  = (projectId: string, userId: string) => del<{ deleted: string }>(`/projects/${projectId}/members/${userId}`)

// Pipelines
export const getPipelines    = (params?: { project_id?: string }) => {
  const qs = params?.project_id ? `?project_id=${params.project_id}` : ''
  return get<import('./types').Pipeline[]>(`/pipelines${qs}`)
}
export const getCronNext     = (expr: string) => get<{ next_runs: string[] }>(`/pipelines/cron-next?expr=${encodeURIComponent(expr)}`)
export const getPipeline     = (id: string) => get<import('./types').Pipeline>(`/pipelines/${id}`)
export const createPipeline  = (data: Partial<import('./types').Pipeline>) => post<import('./types').Pipeline>('/pipelines', data)
export const updatePipeline  = (id: string, data: Partial<import('./types').Pipeline>) => put<import('./types').Pipeline>(`/pipelines/${id}`, data)
export const deletePipeline  = (id: string) => del<{ deleted: string }>(`/pipelines/${id}`)
export const clonePipeline    = (id: string) => post<import('./types').Pipeline>(`/pipelines/${id}/clone`)
export const promotePipeline  = (id: string, target_project_id: string, name_suffix?: string) =>
  post<{ pipeline: import('./types').Pipeline; warnings: string[] }>(`/pipelines/${id}/promote`, { target_project_id, name_suffix })
export const runPipeline      = (id: string) => post<{ run_id: string; status: string; pipeline_name: string }>(`/pipelines/${id}/run`)
export const exportPipeline   = async (id: string): Promise<Blob> => {
  const token = useAuth.getState().token
  const res = await fetch(`${BASE}/pipelines/${id}/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.blob()
}
export const importPipeline   = (yamlContent: string) =>
  post<import('./types').Pipeline>('/pipelines/import', { yaml_content: yamlContent })
export const getPipelineRuns  = (id: string) => get<import('./types').PipelineRun[]>(`/pipelines/${id}/runs`)

// Pipeline dependencies
export const getPipelineDeps    = (id: string) =>
  get<{ upstream: import('./types').PipelineDep[]; downstream: import('./types').PipelineDep[] }>(`/pipelines/${id}/dependencies`)
export const addPipelineDep     = (id: string, upstream_id: string) =>
  post<{ dep_id: string }>(`/pipelines/${id}/dependencies`, { upstream_id })
export const removePipelineDep  = (id: string, dep_id: string) =>
  del<{ deleted: string }>(`/pipelines/${id}/dependencies/${dep_id}`)
export const getDashboardSummary = (projectId?: string) => {
  const qs = projectId ? `?project_id=${projectId}` : ''
  return get<{ pipeline_runs: Record<string, import('./types').PipelineRun[]> }>(`/dashboard/summary${qs}`)
}

// Webhook tokens
export const getWebhookTokens    = (pipelineId: string) => get<import('./types').WebhookToken[]>(`/pipelines/${pipelineId}/webhook-tokens`)
export const createWebhookToken  = (pipelineId: string, label: string) => post<import('./types').WebhookToken>(`/pipelines/${pipelineId}/webhook-tokens`, { label })
export const revokeWebhookToken  = (pipelineId: string, tokenId: string) => del<{ deleted: string }>(`/pipelines/${pipelineId}/webhook-tokens/${tokenId}`)

// Steps
export const addStep    = (pipelineId: string, data: Partial<import('./types').PipelineStep>) =>
  post<import('./types').PipelineStep>(`/pipelines/${pipelineId}/steps`, data)
export const updateStep = (id: string, data: Partial<import('./types').PipelineStep>) =>
  put<import('./types').PipelineStep>(`/pipeline-steps/${id}`, data)
export const deleteStep = (id: string) => del<{ deleted: string }>(`/pipeline-steps/${id}`)
export const getStepTypes = () => get<{ type: string; plugin: boolean }[]>('/step-types')

// Bulk load configs
export const getBulkLoadConfigs   = () => get<import('./types').BulkLoadConfig[]>('/bulk-load-configs')
export const getBulkLoadConfig    = (id: string) => get<import('./types').BulkLoadConfig>(`/bulk-load-configs/${id}`)
export const createBulkLoadConfig = (data: Partial<import('./types').BulkLoadConfig>) => post<import('./types').BulkLoadConfig>('/bulk-load-configs', data)
export const updateBulkLoadConfig = (id: string, data: Partial<import('./types').BulkLoadConfig>) => put<import('./types').BulkLoadConfig>(`/bulk-load-configs/${id}`, data)
export const deleteBulkLoadConfig = (id: string) => del<{ deleted: string }>(`/bulk-load-configs/${id}`)

export interface BulkLoadErrorGroup {
  row_indices: number[]
  column: string | null
  error_type: string
  message: string
  count: number
}
export interface BulkLoadPreview {
  file_name: string
  files_matched: number
  columns: string[]
  sample_rows: unknown[][]
  row_count_sampled: number
  warnings: string[]
  error_groups: BulkLoadErrorGroup[]
  insert_error_summary: string
}
export const validateBulkLoadConfig = (id: string, dryRun = false) =>
  post<BulkLoadPreview>(`/bulk-load-configs/${id}/validate`, dryRun ? { dry_run: true } : undefined)
export const validateBulkLoadConfigRaw = (data: Partial<import('./types').BulkLoadConfig>, dryRun = false) =>
  post<BulkLoadPreview>('/bulk-load-configs/validate-raw', dryRun ? { ...data, dry_run: true } : data)

// Report configs
export const getReportConfigs   = (params?: { project_id?: string }) => {
  const qs = params?.project_id ? `?project_id=${params.project_id}` : ''
  return get<import('./types').ReportConfig[]>(`/report-configs${qs}`)
}
export const getReportConfig    = (id: string) => get<import('./types').ReportConfig>(`/report-configs/${id}`)
export const createReportConfig = (data: Partial<import('./types').ReportConfig>) => post<import('./types').ReportConfig>('/report-configs', data)
export const updateReportConfig = (id: string, data: Partial<import('./types').ReportConfig>) => put<import('./types').ReportConfig>(`/report-configs/${id}`, data)
export const deleteReportConfig = (id: string) => del<{ deleted: string }>(`/report-configs/${id}`)
export const previewReport      = (id: string) => post<{ columns: string[]; rows: unknown[][] }>(`/report-configs/${id}/preview`)
export const profileData = (payload: { columns: string[]; rows: unknown[][] }) =>
  post<{ result: string }>('/ai/data-profile', payload)
export const generateChartConfig = (payload: { columns: string[]; rows: unknown[][]; hint?: string }) =>
  post<{ type: 'bar' | 'line' | 'area' | 'pie' | 'scatter'; x: string; y: string; title: string; available_columns: string[] }>('/ai/chart-config', payload)
type AiQueryPayload =
  | { task: 'explain';  sql: string }
  | { task: 'optimize'; sql: string }
  | { task: 'diagnose'; step_type: string; error: string; logs?: string | null }
export const aiQuery = (payload: AiQueryPayload) =>
  post<{ result: string }>('/ai/query', payload)

// Email configs
export const getEmailConfigs   = (params?: { project_id?: string }) => {
  const qs = params?.project_id ? `?project_id=${params.project_id}` : ''
  return get<import('./types').EmailConfig[]>(`/email-configs${qs}`)
}
export const getEmailConfig    = (id: string) => get<import('./types').EmailConfig>(`/email-configs/${id}`)
export const createEmailConfig = (data: Partial<import('./types').EmailConfig>) => post<import('./types').EmailConfig>('/email-configs', data)
export const updateEmailConfig = (id: string, data: Partial<import('./types').EmailConfig>) => put<import('./types').EmailConfig>(`/email-configs/${id}`, data)
export const deleteEmailConfig  = (id: string) => del<{ deleted: string }>(`/email-configs/${id}`)
export const previewEmailConfig = (id: string) => get<{ subject: string; html: string }>(`/email-configs/${id}/preview`)

// Email providers
export const getEmailProviders  = () => get<import('./types').EmailProvider[]>('/email-providers')
export const getEmailProvider   = (id: string) => get<import('./types').EmailProvider>(`/email-providers/${id}`)
export const createEmailProvider = (data: unknown) => post<import('./types').EmailProvider>('/email-providers', data)
export const updateEmailProvider = (id: string, data: unknown) => put<import('./types').EmailProvider>(`/email-providers/${id}`, data)
export const deleteEmailProvider = (id: string) => del<{ deleted: string }>(`/email-providers/${id}`)
export const testEmailProvider  = (id: string) => post<{ success: boolean; error?: string }>(`/email-providers/${id}/test`)

// DB connections
export const getDbConnections   = () => get<import('./types').DbConnection[]>('/db-connections')
export const getDbConnection    = (id: string) => get<import('./types').DbConnection>(`/db-connections/${id}`)
export const createDbConnection = (data: unknown) => post<import('./types').DbConnection>('/db-connections', data)
export const updateDbConnection = (id: string, data: unknown) => put<import('./types').DbConnection>(`/db-connections/${id}`, data)
export const deleteDbConnection = (id: string) => del<{ deleted: string }>(`/db-connections/${id}`)
export const testDbConnection    = (id: string) => post<{ success: boolean; latency_ms?: number; error?: string }>(`/db-connections/${id}/test`)
export const testDbConnectionRaw = (db_type: string, config: Record<string, unknown>) =>
  post<{ success: boolean; latency_ms?: number; error?: string }>('/db-connections/test-raw', { db_type, config })

// Recipient groups
export const getRecipientGroups   = (params?: { project_id?: string }) => {
  const qs = params?.project_id ? `?project_id=${params.project_id}` : ''
  return get<import('./types').RecipientGroup[]>(`/recipient-groups${qs}`)
}
export const createRecipientGroup = (data: Partial<import('./types').RecipientGroup>) => post<import('./types').RecipientGroup>('/recipient-groups', data)
export const updateRecipientGroup = (id: string, data: Partial<import('./types').RecipientGroup>) => put<import('./types').RecipientGroup>(`/recipient-groups/${id}`, data)
export const deleteRecipientGroup = (id: string) => del<{ deleted: string }>(`/recipient-groups/${id}`)

// Runs
export const getRuns = (params?: { pipeline_id?: string; project_id?: string; status?: string; limit?: number; offset?: number }) => {
  const qs = new URLSearchParams()
  if (params?.pipeline_id) qs.set('pipeline_id', params.pipeline_id)
  if (params?.project_id)  qs.set('project_id',  params.project_id)
  if (params?.status)      qs.set('status', params.status)
  if (params?.limit)       qs.set('limit', String(params.limit))
  if (params?.offset)      qs.set('offset', String(params.offset))
  const q = qs.toString()
  return get<import('./types').PipelineRun[]>(`/runs${q ? `?${q}` : ''}`)
}
export const getRun          = (id: string) => get<import('./types').PipelineRun>(`/runs/${id}`)
export const getRunAnomalies = (id: string) => get<import('./types').StepAnomaly[]>(`/runs/${id}/anomalies`)
export const getRunDiff      = (id: string) => get<import('./types').RunDiff>(`/runs/${id}/diff`)
export const getStepRunTrends = (params?: { step_type?: string; pipeline_id?: string; project_id?: string; days?: number }) => {
  const qs = new URLSearchParams()
  if (params?.step_type)   qs.set('step_type',   params.step_type)
  if (params?.pipeline_id) qs.set('pipeline_id', params.pipeline_id)
  if (params?.project_id)  qs.set('project_id',  params.project_id)
  if (params?.days)        qs.set('days', String(params.days))
  const q = qs.toString()
  return get<import('./types').StepTrends>(`/step-runs/trends${q ? `?${q}` : ''}`)
}
export const getAnomalyNarrative = (payload: {
  step_name: string; metric: 'rows' | 'duration'
  value: number; mean: number; pct_diff: number
}) => post<{ result: string }>('/ai/anomaly-narrative', payload)

// Users (admin)
export const getUsers    = () => get<import('./types').User[]>('/users')
export const createUser  = (data: { username: string; password: string; role: string; email?: string }) =>
  post<import('./types').User>('/users', data)
export const updateUser  = (id: string, data: { role?: string; username?: string }) =>
  request<import('./types').User>('PATCH', `/users/${id}`, data)
export const deleteUser  = (id: string) => del<{ message: string }>(`/users/${id}`)
export const changePassword = (data: { current_password: string; new_password: string }) =>
  post<{ message: string }>('/auth/change-password', data)

// Password reset (no auth required)
export const requestPasswordReset  = (username: string) =>
  post<{ message: string }>('/auth/password-reset/request', { username })
export const confirmPasswordReset  = (token: string, new_password: string) =>
  post<{ message: string }>('/auth/password-reset/confirm', { token, new_password })
export const validateResetToken    = (token: string) =>
  get<{ valid: boolean }>(`/auth/password-reset/validate/${token}`)

// Setup / OAuth status
export type SetupStatus = {
  gmail:        { configured: boolean; sender: string }
  drive:        { configured: boolean; folder_id: string }
  microsoft365: { configured: boolean; sender: string }
  ai: {
    enabled: boolean; ollama_url: string; model: string
    claude: { configured: boolean }
    gemini: { configured: boolean; model: string }
  }
  retention:    { run_days: number; audit_days: number }
}
export const getSetupStatus = () => get<SetupStatus>('/setup/status')

// Data retention settings (DB override, falls back to env vars when unset)
export type RetentionSettings = {
  run_retention_days: number
  audit_retention_days: number
  output_ttl_days: number
  is_custom: { run_retention_days: boolean; audit_retention_days: boolean; output_ttl_days: boolean }
}
export type RetentionUpdate = Partial<{
  run_retention_days: number | null
  audit_retention_days: number | null
  output_ttl_days: number | null
}>
export const getRetentionSettings    = () => get<RetentionSettings>('/settings/retention')
export const updateRetentionSettings = (data: RetentionUpdate) =>
  put<Omit<RetentionSettings, 'is_custom'>>('/settings/retention', data)

// Audit Logs
export type AuditLogEntry = {
  id: string
  timestamp: string
  action: string
  username: string
  user_id: string | null
  ip_address: string | null
  details: Record<string, unknown>
}
export type AuditLogResponse = {
  logs: AuditLogEntry[]
  total: number
  page: number
  pages: number
}
export const getAuditLogs = (params?: { page?: number; action?: string; username?: string }) => {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.action) qs.set('action', params.action)
  if (params?.username) qs.set('username', params.username)
  const q = qs.toString()
  return get<AuditLogResponse>(`/audit-logs${q ? `?${q}` : ''}`)
}

export async function exportAuditLogs(params?: { action?: string; username?: string }): Promise<void> {
  const qs = new URLSearchParams()
  if (params?.action) qs.set('action', params.action)
  if (params?.username) qs.set('username', params.username)
  const q = qs.toString()

  const token = useAuth.getState().token
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/audit-logs/export${q ? `?${q}` : ''}`, { headers })
  if (res.status === 401) {
    useAuth.getState().clearToken()
    globalThis.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`)
  }

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'audit_logs.csv'
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadStepOutput(stepRunId: string, filename: string): Promise<void> {
  const token = useAuth.getState().token
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/step-runs/${stepRunId}/download`, { headers })
  if (res.status === 401) {
    useAuth.getState().clearToken()
    globalThis.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`)
  }

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
