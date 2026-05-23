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
    useAuth.getState().clearToken()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`)
  return data as T
}

const get  = <T>(path: string)             => request<T>('GET',    path)
const post = <T>(path: string, body?: unknown) => request<T>('POST',   path, body)
const put  = <T>(path: string, body?: unknown) => request<T>('PUT',    path, body)
const del  = <T>(path: string)             => request<T>('DELETE', path)

// Auth
export const login = (username: string, password: string) =>
  post<{ token: string }>('/auth/login', { username, password })

// Projects
export const getProjects    = () => get<import('./types').Project[]>('/projects')
export const getProject     = (id: string) => get<import('./types').Project>(`/projects/${id}`)
export const createProject  = (data: { name: string; description?: string; color?: string }) => post<import('./types').Project>('/projects', data)
export const updateProject  = (id: string, data: { name?: string; description?: string; color?: string }) => request<import('./types').Project>('PATCH', `/projects/${id}`, data)
export const deleteProject  = (id: string) => del<{ deleted: string }>(`/projects/${id}`)

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
export const runPipeline     = (id: string) => post<{ run_id: string; status: string; pipeline_name: string }>(`/pipelines/${id}/run`)
export const getPipelineRuns = (id: string) => get<import('./types').PipelineRun[]>(`/pipelines/${id}/runs`)

// Steps
export const addStep    = (pipelineId: string, data: Partial<import('./types').PipelineStep>) =>
  post<import('./types').PipelineStep>(`/pipelines/${pipelineId}/steps`, data)
export const updateStep = (id: string, data: Partial<import('./types').PipelineStep>) =>
  put<import('./types').PipelineStep>(`/pipeline-steps/${id}`, data)
export const deleteStep = (id: string) => del<{ deleted: string }>(`/pipeline-steps/${id}`)

// Bulk load configs
export const getBulkLoadConfigs   = () => get<import('./types').BulkLoadConfig[]>('/bulk-load-configs')
export const getBulkLoadConfig    = (id: string) => get<import('./types').BulkLoadConfig>(`/bulk-load-configs/${id}`)
export const createBulkLoadConfig = (data: Partial<import('./types').BulkLoadConfig>) => post<import('./types').BulkLoadConfig>('/bulk-load-configs', data)
export const updateBulkLoadConfig = (id: string, data: Partial<import('./types').BulkLoadConfig>) => put<import('./types').BulkLoadConfig>(`/bulk-load-configs/${id}`, data)
export const deleteBulkLoadConfig = (id: string) => del<{ deleted: string }>(`/bulk-load-configs/${id}`)

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
export const getRun = (id: string) => get<import('./types').PipelineRun>(`/runs/${id}`)

// Setup / OAuth status
export type SetupStatus = {
  gmail:        { configured: boolean; sender: string }
  drive:        { configured: boolean; folder_id: string }
  microsoft365: { configured: boolean; sender: string }
}
export const getSetupStatus = () => get<SetupStatus>('/setup/status')

export async function downloadStepOutput(stepRunId: string, filename: string): Promise<void> {
  const token = useAuth.getState().token
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/step-runs/${stepRunId}/download`, { headers })
  if (res.status === 401) {
    useAuth.getState().clearToken()
    window.location.href = '/login'
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
