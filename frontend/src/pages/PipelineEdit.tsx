import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import { Plus, Save, ArrowLeft, Trash2, Copy, Link as LinkIcon, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getPipeline, createPipeline, updatePipeline,
  addStep, updateStep, deleteStep,
  getDbConnections, getReportConfigs, getEmailConfigs, getBulkLoadConfigs,
  getCronNext,
  getWebhookTokens, createWebhookToken, revokeWebhookToken,
  getPipelines,
  addPipelineDep, removePipelineDep,
} from '../lib/api'
import type { Pipeline, PipelineStep, StepType, WebhookToken } from '../lib/types'
import { useProjectStore } from '../lib/store'
import StepEditor from '../components/pipeline/StepEditor'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import FieldTooltip from '../components/shared/FieldTooltip'
import RouteErrorBoundary from '../components/shared/RouteErrorBoundary'

const STEP_TYPES: StepType[] = ['db_procedure', 'db_query', 'report', 'email', 'drive_upload', 'data_load', 'bulk_load']

function newStep(type: StepType, order: number): PipelineStep {
  return {
    id: `_new_${Date.now()}`,
    pipeline_id: '',
    step_order: order,
    name: `${type.replace('_', ' ')} step`,
    step_type: type,
    config: {},
    on_error: 'stop',
    enabled: true,
    parallel_group: null,
  }
}

function PipelineVariablesCard({ vars, setVars }: {
  vars: { key: string; value: string; is_secret: boolean }[]
  setVars: React.Dispatch<React.SetStateAction<{ key: string; value: string; is_secret: boolean }[]>>
}) {
  const updateVar = (i: number, updates: any) => {
    setVars(prev => prev.map((v, j) => j === i ? { ...v, ...updates } : v))
  }
  const removeVar = (i: number) => {
    setVars(prev => prev.filter((_, j) => j !== i))
  }
  const addVar = () => {
    setVars(v => [...v, { key: '', value: '', is_secret: false }])
  }

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div>
          <span className="text-xs font-semibold text-[var(--text)]">Pipeline Variables</span>
          <span className="text-[11px] text-[var(--text-muted)] ml-2">
            available as <code className="text-[11px] bg-[var(--surface)] p-[1px_5px] rounded-[3px]">{'{{ var_name }}'}</code> in all step configs
          </span>
        </div>
        <button type="button" className="btn btn-sm" onClick={addVar}>
          <Plus size={10} /> Add variable
        </button>
      </div>

      {vars.length === 0 ? (
        <p className="text-xs text-[var(--text-muted)] m-0">
          No variables. Add one to pass constants like currency codes, environment names, or date ranges to all steps.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 pb-1 border-b border-[var(--border)]">
            {(['Name', 'Value', 'Secret', ''] as const).map(h => (
              <span key={h} className="text-[11px] text-[var(--text-muted)] font-semibold">{h}</span>
            ))}
          </div>
          {vars.map((v, i) => ({ v, i })).map(({ v, i }) => (
            <div key={v.key + ':' + i} className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-center">
              <input
                className="input mono-input !text-xs !h-[30px]"
                placeholder="currency"
                value={v.key}
                onChange={e => updateVar(i, { key: e.target.value })}
              />
              <input
                className="input !text-xs !h-[30px]"
                placeholder={v.is_secret ? '(unchanged)' : 'USD'}
                value={v.value}
                type={v.is_secret ? 'password' : 'text'}
                onChange={e => updateVar(i, { value: e.target.value })}
              />
              <label className="flex items-center gap-1.5 cursor-pointer whitespace-nowrap text-xs text-[var(--text-muted)]">
                <input
                  type="checkbox"
                  checked={v.is_secret}
                  onChange={e => updateVar(i, { is_secret: e.target.checked })}
                />{' '}
                Secret
              </label>
              <button
                type="button"
                onClick={() => removeVar(i)}
                className="bg-transparent border-none text-[var(--failure)] cursor-pointer p-1"
                title="Remove variable"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <p className="text-[11px] text-[var(--text-muted)] mt-1 mb-0">
            Built-in date vars: <code className="text-[11px]">{'{{ current_date }}'}</code> <code className="text-[11px]">{'{{ month_start_ts }}'}</code> <code className="text-[11px]">{'{{ prev_month_start_ts }}'}</code> <code className="text-[11px]">{'{{ last_success_at }}'}</code>
          </p>
        </div>
      )}
    </div>
  )
}

function DependenciesCard({
  upstreamDeps, setUpstreamDeps, allPipelines, thisPipelineId,
}: {
  upstreamDeps: import('../lib/types').PipelineDep[]
  setUpstreamDeps: React.Dispatch<React.SetStateAction<import('../lib/types').PipelineDep[]>>
  allPipelines: import('../lib/types').Pipeline[]
  thisPipelineId: string | undefined
}) {
  const available = allPipelines.filter(
    p => p.id !== thisPipelineId && !upstreamDeps.some(d => d.pipeline_id === p.id)
  )

  function addDep(pipelineId: string) {
    const p = allPipelines.find(x => x.id === pipelineId)
    if (!p) return
    setUpstreamDeps(prev => [...prev, { dep_id: `_new_${Date.now()}`, pipeline_id: p.id, pipeline_name: p.name }])
  }

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div>
          <span className="text-xs font-semibold text-[var(--text)]">Upstream Dependencies</span>
          <span className="text-[11px] text-[var(--text-muted)] ml-2">
            this pipeline runs automatically when all listed pipelines succeed
          </span>
        </div>
      </div>

      {upstreamDeps.length === 0 ? (
        <p className="text-xs text-[var(--text-muted)] m-0">
          No dependencies. This pipeline runs on its own schedule or when triggered manually.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5 mb-2.5">
          {upstreamDeps.map(dep => (
            <div key={dep.dep_id} className="flex items-center gap-2">
              <span style={{ fontSize: 12, color: 'var(--text-2)', flex: 1, padding: '4px 8px', background: 'var(--surface-2)', borderRadius: 5, border: '1px solid var(--border)' }}>
                {dep.pipeline_name}
              </span>
              <button
                type="button"
                onClick={() => setUpstreamDeps(prev => prev.filter(d => d.dep_id !== dep.dep_id))}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--failure)', padding: '2px 4px' }}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {available.length > 0 && (
        <select
          className="input"
          style={{ fontSize: 12, maxWidth: 320 }}
          value=""
          onChange={e => { if (e.target.value) addDep(e.target.value) }}
        >
          <option value="">+ Add upstream dependency…</option>
          {available.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      )}
    </div>
  )
}

export default function PipelineEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: existing, isLoading } = useQuery({
    queryKey: ['pipeline', id],
    queryFn: () => getPipeline(id!),
    enabled: !isNew,
  })
  const { data: dbConns = [] }      = useQuery({ queryKey: ['db-connections'],   queryFn: getDbConnections })
  const { data: reportCfgs = [] }   = useQuery({ queryKey: ['report-configs'],   queryFn: () => getReportConfigs() })
  const { data: emailCfgs = [] }    = useQuery({ queryKey: ['email-configs'],    queryFn: () => getEmailConfigs() })
  const { data: bulkLoadCfgs = [] } = useQuery({ queryKey: ['bulk-load-configs'],queryFn: getBulkLoadConfigs })
  const { data: allPipelines = [] } = useQuery({ queryKey: ['pipelines'],        queryFn: () => getPipelines() })

  const [name, setName]           = useState('')
  const [desc, setDesc]           = useState('')
  const [schedule, setSchedule]   = useState('')
  const [enabled, setEnabled]     = useState(true)
  const [timeout, setTimeout_]    = useState(60)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [steps, setSteps]         = useState<PipelineStep[]>([])
  const [vars, setVars]           = useState<{ key: string; value: string; is_secret: boolean }[]>([])
  const [upstreamDeps, setUpstreamDeps] = useState<import('../lib/types').PipelineDep[]>([])
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (existing) {
      setName(existing.name)
      setDesc(existing.description ?? '')
      setSchedule(existing.schedule ?? '')
      setEnabled(existing.enabled)
      setTimeout_(existing.timeout_minutes)
      setWebhookUrl(existing.on_failure_webhook_url ?? '')
      setSteps([...existing.steps].sort((a, b) => a.step_order - b.step_order))
      setUpstreamDeps(existing.upstream_deps ?? [])
      setVars((existing.variables ?? []).map(v => ({
        key: v.var_key,
        value: v.is_secret ? '' : v.var_value,
        is_secret: v.is_secret,
      })))
    }
  }, [existing])

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const handleDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const from = steps.findIndex(s => s.id === active.id)
    const to   = steps.findIndex(s => s.id === over.id)
    const reordered = arrayMove(steps, from, to).map((s, i) => ({ ...s, step_order: i + 1 }))
    setSteps(reordered)
  }

  const handleStepChange = (stepId: string, updates: Partial<PipelineStep>) => {
    setSteps(prev => prev.map(s => s.id === stepId ? { ...s, ...updates } : s))
  }

  const handleStepDelete = (stepId: string) => {
    setSteps(prev => prev.filter(s => s.id !== stepId).map((s, i) => ({ ...s, step_order: i + 1 })))
  }

  const addNewStep = (type: StepType) => {
    setSteps(prev => [...prev, newStep(type, prev.length + 1)])
  }

  const handleSave = async () => {
    const errs: Record<string, string> = {}
    if (!name.trim()) errs.name = 'Pipeline name is required'
    if (timeout < 1) errs.timeout = 'Timeout must be at least 1 minute'
    if (Object.keys(errs).length) { setFieldErrors(errs); return }
    setFieldErrors({})
    setSaving(true)
    setError('')
    try {
      const validVars = vars
        .filter(v => v.key.trim())
        .map(v => ({ var_key: v.key.trim(), var_value: v.value, is_secret: v.is_secret }))

      let pipeline: Pipeline
      if (isNew) {
        pipeline = await createPipeline({ name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout, on_failure_webhook_url: webhookUrl || null, variables: validVars, project_id: activeProjectId ?? undefined })
      } else {
        pipeline = await updatePipeline(id!, { name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout, on_failure_webhook_url: webhookUrl || null, variables: validVars })
      }

      // Sync steps: delete removed, update existing, add new
      const existingIds = new Set((existing?.steps ?? []).map(s => s.id))
      const currentIds  = new Set(steps.filter(s => !s.id.startsWith('_new_')).map(s => s.id))

      for (const s of (existing?.steps ?? [])) {
        if (!currentIds.has(s.id)) await deleteStep(s.id)
      }
      for (const s of steps) {
        const payload = {
          name: s.name, step_type: s.step_type, config: s.config,
          on_error: s.on_error, step_order: s.step_order, enabled: s.enabled,
          parallel_group: s.parallel_group || null,
        }
        if (s.id.startsWith('_new_')) {
          await addStep(pipeline.id, payload)
        } else if (existingIds.has(s.id)) {
          await updateStep(s.id, payload)
        }
      }

      // Sync upstream dependencies
      if (!isNew) {
        const existingDepIds = new Set((existing?.upstream_deps ?? []).map(d => d.dep_id))
        const currentDepIds  = new Set(upstreamDeps.map(d => d.dep_id))
        // Remove dropped deps
        for (const d of (existing?.upstream_deps ?? [])) {
          if (!currentDepIds.has(d.dep_id)) await removePipelineDep(pipeline.id, d.dep_id)
        }
        // Add new deps (ones without a real dep_id)
        for (const d of upstreamDeps) {
          if (!existingDepIds.has(d.dep_id)) await addPipelineDep(pipeline.id, d.pipeline_id)
        }
      } else {
        for (const d of upstreamDeps) {
          await addPipelineDep(pipeline.id, d.pipeline_id)
        }
      }

      qc.invalidateQueries({ queryKey: ['pipelines'] })
      qc.invalidateQueries({ queryKey: ['pipeline', id] })
      navigate('/pipelines')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const crumbs = isNew ? ['Workspace', 'Pipelines', 'New Pipeline'] : ['Workspace', 'Pipelines', name || 'Edit Pipeline']

  if (!isNew && isLoading) return (
    <>
      <TopBar crumbs={crumbs} actions={
        <div className="flex gap-2">
          <Sk h={28} r={6} className="w-[68px]" />
          <Sk h={28} r={6} className="w-[68px]" />
        </div>
      } />
      <div className="scroll">
        <div className="card mb-4 flex flex-col gap-3">
          <Sk h={13} className="w-[55px]" />
          <div className="grid grid-cols-2 gap-3">
            {[0,1,2,3].map(i => (
              <div key={i} className="field">
                <Sk h={12} className="w-[70px] mb-1.5" />
                <Sk h={34} r={6} />
              </div>
            ))}
          </div>
          <div className="field">
            <Sk h={12} className="w-[80px] mb-1.5" />
            <Sk h={64} r={6} />
          </div>
        </div>
        <div className="card mb-4 flex flex-col gap-3">
          <Sk h={13} className="w-[100px]" />
          {[0,1].map(i => (
            <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2.5 items-center">
              <Sk h={34} r={6} />
              <Sk h={34} r={6} />
              <Sk h={28} r={6} className="w-7" />
            </div>
          ))}
        </div>
        <div className="card flex flex-col gap-3">
          <Sk h={13} className="w-20" />
          <Sk h={64} r={6} />
          <Sk h={64} r={6} />
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div className="flex gap-2">
            <Link to="/pipelines" className="btn btn-sm"><ArrowLeft size={12} />{' '}Back</Link>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={12} /> : <Save size={12} />}{' '}Save
            </button>
          </div>
        }
      />

      <div className="scroll">
        {error && (
          <div className="mb-3.5 p-[8px_12px] bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-[7px] text-[12.5px] text-[var(--failure-text)]">{error}</div>
        )}

        {/* Basic info */}
        <div className="card mb-4 flex flex-col gap-3">
          <div className="text-xs font-semibold text-[var(--text)]">Details</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="field">
              <label htmlFor="pipeline-name">Name *</label>
              <input id="pipeline-name" className="input" data-testid="pipeline-name" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} />
              {fieldErrors.name && <span className="text-[11.5px] text-[var(--failure)]">{fieldErrors.name}</span>}
            </div>
            <div className="field">
              <label className="flex items-center gap-1">
                Schedule{' '}
                <FieldTooltip field="cron" />
              </label>
              {(!id || existing) && (
                <CronBuilder key={id ?? 'new'} defaultValue={schedule} onChange={setSchedule} />
              )}
            </div>
          </div>
          <div className="field">
            <label htmlFor="pipeline-desc">Description</label>
            <input id="pipeline-desc" className="input" value={desc} onChange={e => setDesc(e.target.value)} />
          </div>
          <div className="flex items-center gap-5">
            <label className="flex items-center gap-2 cursor-pointer text-[13px]">
              <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} className="accent-[var(--accent)] w-[15px] h-[15px]" />
              <span className="text-[var(--text)]">Enabled</span>
            </label>
            <div className="flex items-center gap-2">
              <span className="text-[11.5px] text-[var(--text-muted)] font-medium">Timeout (min)</span>
              <input className="input w-[70px] h-[30px] p-[4px_8px] text-xs" type="number" min={1} value={timeout} onChange={e => { setTimeout_(+e.target.value); if (fieldErrors.timeout) setFieldErrors(f => ({ ...f, timeout: '' })) }} />
              {fieldErrors.timeout && <span className="text-[11.5px] text-[var(--failure)]">{fieldErrors.timeout}</span>}
            </div>
            <div className="flex items-center gap-2 flex-1">
              <span className="text-[11.5px] text-[var(--text-muted)] font-medium whitespace-nowrap">Failure webhook</span>
              <input className="input flex-1 h-[30px] p-[4px_8px] text-xs" type="url" placeholder="https://hooks.slack.com/…" value={webhookUrl} onChange={e => setWebhookUrl(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Pipeline Variables */}
        <PipelineVariablesCard vars={vars} setVars={setVars} />

        {/* Upstream Dependencies */}
        <DependenciesCard
          upstreamDeps={upstreamDeps}
          setUpstreamDeps={setUpstreamDeps}
          allPipelines={allPipelines}
          thisPipelineId={id}
        />

        {/* Webhook tokens — only shown when editing an existing pipeline */}
        {!isNew && id && <WebhookCard pipelineId={id} />}

        {/* Steps */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-[var(--text)]">Steps <span className="font-mono text-[var(--text-muted)] text-[11px]">({steps.length})</span></span>
            <div className="flex gap-1 flex-wrap justify-end">
              {STEP_TYPES.map(t => (
                <button key={t} className="btn btn-sm" onClick={() => addNewStep(t)}>
                  <Plus size={10} /> {t.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>

          <RouteErrorBoundary label="Step editor">
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                {steps.map(step => (
                  <StepEditor
                    key={step.id}
                    step={step}
                    onChange={handleStepChange}
                    onDelete={handleStepDelete}
                    allSteps={steps}
                    dbConnections={dbConns.map(c => ({ id: c.id, name: c.name }))}
                    reportConfigs={reportCfgs.map(r => ({ id: r.id, name: r.name, output_filename: r.output_filename }))}
                    emailConfigs={emailCfgs.map(e => ({ id: e.id, name: e.name }))}
                    bulkLoadConfigs={bulkLoadCfgs.map(b => ({ id: b.id, name: b.name, source_directory: b.source_directory, target_table: b.target_table }))}
                  />
                ))}
              </SortableContext>
            </DndContext>
          </RouteErrorBoundary>

          {steps.length === 0 && (
            <div className="card ff-empty border-dashed py-6">
              <p className="msg">Add steps using the buttons above.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ─── WebhookCard ─────────────────────────────────────────────────────────────

function WebhookCard({ pipelineId }: { pipelineId: string }) {
  const qc = useQueryClient()
  const [newLabel, setNewLabel] = useState('')
  const [creating, setCreating] = useState(false)
  const [justCreated, setJustCreated] = useState<WebhookToken | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: tokens = [], isLoading } = useQuery({
    queryKey: ['webhook-tokens', pipelineId],
    queryFn: () => getWebhookTokens(pipelineId),
  })

  const baseUrl = window.location.origin
  const triggerUrl = justCreated
    ? `${baseUrl}/api/pipelines/${pipelineId}/trigger?token=${justCreated.token}`
    : ''

  const handleCreate = async () => {
    setCreating(true)
    try {
      const created = await createWebhookToken(pipelineId, newLabel.trim())
      setJustCreated(created)
      setNewLabel('')
      qc.invalidateQueries({ queryKey: ['webhook-tokens', pipelineId] })
    } finally {
      setCreating(false)
    }
  }

  const handleRevoke = async (tokenId: string) => {
    if (!confirm('Revoke this token? Any integrations using it will stop working.')) return
    await revokeWebhookToken(pipelineId, tokenId)
    qc.invalidateQueries({ queryKey: ['webhook-tokens', pipelineId] })
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(triggerUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <LinkIcon size={13} className="text-[var(--text-muted)]" />
          <span className="text-xs font-semibold text-[var(--text)]">Webhook / API Trigger</span>
        </div>
      </div>

      <p className="text-[11.5px] text-[var(--text-muted)] mb-3 mt-0">
        Trigger this pipeline from external systems using{' '}
        <code className="text-[11px] bg-[var(--surface)] p-[1px_5px] rounded-[3px]">
          POST /api/pipelines/{pipelineId.slice(0, 8)}…/trigger?token=&lt;token&gt;
        </code>
      </p>

      {/* New token after creation — show URL once */}
      {justCreated && (
        <div className="mb-3 p-[10px_12px] bg-[rgba(34,197,94,0.06)] border border-[rgba(34,197,94,0.2)] rounded-md">
          <div className="text-[11.5px] text-[var(--success-text)] font-semibold mb-1.5">
            Token created — copy the URL now. It will not be shown again.
          </div>
          <div className="flex gap-1.5 items-center">
            <input
              readOnly
              value={triggerUrl}
              className="flex-1 bg-[var(--bg)] border border-[var(--border)] rounded-[5px] p-[5px_8px] text-[11px] font-mono text-[var(--text)] outline-none"
            />
            <button className="btn btn-sm" onClick={handleCopy} title="Copy URL">
              <Copy size={11} /> {copied ? 'Copied!' : 'Copy'}
            </button>
            <button
              className="btn btn-sm text-[var(--text-muted)]"
              onClick={() => setJustCreated(null)}
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Token list */}
      {isLoading ? (
        <p className="text-[11.5px] text-[var(--text-muted)]">Loading…</p>
      ) : tokens.length === 0 && !justCreated ? (
        <p className="text-[11.5px] text-[var(--text-muted)] mb-3">No tokens yet. Generate one below to enable API triggers.</p>
      ) : (
        <div className="mb-3">
          {tokens.map(t => (
            <div key={t.id} className="flex items-center gap-2 py-1.5 border-b border-[var(--border)]">
              <span className="flex-1 text-xs text-[var(--text)]">{t.label || <em className="text-[var(--text-muted)]">unlabelled</em>}</span>
              <span className="text-[10.5px] text-[var(--text-muted)] font-mono">
                {t.last_used_at ? `last used ${new Date(t.last_used_at).toLocaleDateString()}` : 'never used'}
              </span>
              <button
                className="btn btn-sm text-[var(--failure-text)]"
                onClick={() => handleRevoke(t.id)}
                title="Revoke token"
              >
                <Trash2 size={11} /> Revoke
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Create new token */}
      <div className="flex gap-1.5 items-center">
        <input
          className="input !h-8 !text-xs flex-1"
          placeholder="Label (e.g. GitHub Actions, Zapier)"
          value={newLabel}
          onChange={e => setNewLabel(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !creating && handleCreate()}
        />
        <button
          className="btn btn-sm btn-primary"
          onClick={handleCreate}
          disabled={creating}
          title="Generate a new webhook token"
        >
          {creating ? <RefreshCw size={11} /> : <Plus size={11} />} Generate token
        </button>
      </div>
    </div>
  )
}


// ─── CronBuilder ─────────────────────────────────────────────────────────────

type Freq = 'none' | 'minutely' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'custom'
interface CronState { n: number; minute: number; hour: number; weekday: number; monthDay: number }
const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

function detectFreq(cron: string): Freq {
  if (!cron) return 'none'
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return 'custom'
  const [min, hr, dom, mon, dow] = p
  if (/^\*\/\d+$/.test(min) && hr==='*' && dom==='*' && mon==='*' && dow==='*') return 'minutely'
  if (/^\d+$/.test(min) && hr==='*' && dom==='*' && mon==='*' && dow==='*') return 'hourly'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom==='*' && mon==='*' && dow==='*') return 'daily'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom==='*' && mon==='*' && /^\d+$/.test(dow)) return 'weekly'
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && /^\d+$/.test(dom) && mon==='*' && dow==='*') return 'monthly'
  return 'custom'
}

function parseCronState(cron: string): CronState {
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return { n: 5, minute: 0, hour: 8, weekday: 1, monthDay: 1 }
  const [min, hr, dom, , dow] = p
  return {
    n:        Number.parseInt(min.replace('*/', '')) || 5,
    minute:   Number.parseInt(min) || 0,
    hour:     Number.parseInt(hr) || 8,
    weekday:  Number.parseInt(dow) || 1,
    monthDay: Number.parseInt(dom) || 1,
  }
}

function buildCronStr(freq: Freq, s: CronState): string {
  switch (freq) {
    case 'minutely': return `*/${s.n} * * * *`
    case 'hourly':   return `${s.minute} * * * *`
    case 'daily':    return `${s.minute} ${s.hour} * * *`
    case 'weekly':   return `${s.minute} ${s.hour} * * ${s.weekday}`
    case 'monthly':  return `${s.minute} ${s.hour} ${s.monthDay} * *`
    default:         return ''
  }
}

function CronBuilder({ defaultValue, onChange }: { defaultValue: string; onChange: (v: string) => void }) {
  const [freq, setFreq]       = useState<Freq>(() => detectFreq(defaultValue))
  const [state, setCronState] = useState<CronState>(() => parseCronState(defaultValue))
  const [rawCron, setRawCron] = useState(defaultValue)
  const mounted = useRef(false)

  const currentCron = (() => {
    if (freq === 'custom') return rawCron
    if (freq === 'none') return ''
    return buildCronStr(freq, state)
  })()

  useEffect(() => {
    if (!mounted.current) { mounted.current = true; return }
    onChange(currentCron)
  }, [currentCron])

  const { data: nextData } = useQuery({
    queryKey: ['cron-next', currentCron],
    queryFn:  () => getCronNext(currentCron),
    enabled:  !!currentCron && currentCron.trim().split(/\s+/).length === 5,
    staleTime: 60_000,
    retry: false,
  })

  const upd = (key: keyof CronState, val: number) => setCronState(s => ({ ...s, [key]: val }))

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 flex-wrap">
        <select className="input !h-[34px] !w-40" value={freq} onChange={e => setFreq(e.target.value as Freq)}>
          <option value="none">No schedule</option>
          <option value="minutely">Every N minutes</option>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="custom">Custom (raw cron)</option>
        </select>

        {freq === 'minutely' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">every</span>
          <input className="input !w-16 !h-[34px]" type="number" min={1} max={59} value={state.n} onChange={e => upd('n', +e.target.value)} />
          <span className="text-[12.5px] text-[var(--text-3)]">minutes</span>
        </>)}

        {freq === 'hourly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">at</span>
          <span className="text-[12.5px] text-[var(--text-3)] font-mono">:</span>
          <input className="input !w-16 !h-[34px]" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} title="Minute past the hour (0–59)" />
          <span className="text-[12.5px] text-[var(--text-3)]">each hour</span>
        </>)}

        {(freq === 'daily' || freq === 'weekly' || freq === 'monthly') && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">at</span>
          <select className="input !h-[34px] !w-20" value={state.hour} onChange={e => upd('hour', +e.target.value)}>
            {Array.from({length: 24}, (_, i) => i).map(h => <option key={h} value={h}>{String(h).padStart(2,'0')}:00</option>)}
          </select>
          <input className="input !w-14 !h-[34px]" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} title="Minute (0–59)" />
        </>)}

        {freq === 'weekly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">on</span>
          <select className="input !h-[34px] !w-[110px]" value={state.weekday} onChange={e => upd('weekday', +e.target.value)}>
            {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </select>
        </>)}

        {freq === 'monthly' && (<>
          <span className="text-[12.5px] text-[var(--text-3)]">on day</span>
          <input className="input !w-16 !h-[34px]" type="number" min={1} max={31} value={state.monthDay} onChange={e => upd('monthDay', +e.target.value)} />
        </>)}

        {freq === 'custom' && (
          <input className="input mono-input !w-40 !h-[34px]" value={rawCron} onChange={e => setRawCron(e.target.value)} placeholder="0 8 * * 1-5" />
        )}
      </div>

      {currentCron && freq !== 'custom' && (
        <div className="font-mono text-[11px] text-[var(--text-dim)]">
          {currentCron}
        </div>
      )}

      {nextData?.next_runs && nextData.next_runs.length > 0 && (
        <div className="text-[11.5px] text-[var(--text-muted)] flex flex-wrap gap-[4px_14px]">
          <span className="text-[var(--text-dim)] font-medium mr-1">Next runs:</span>
          {nextData.next_runs.map((t) => (
            <span key={t} className="font-mono">
              {new Date(t).toLocaleString('en-US', { weekday:'short', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', timeZoneName:'short' })}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
