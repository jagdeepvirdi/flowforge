import { useState } from 'react'
import { useNavigate, useParams, type NavigateFunction } from 'react-router-dom'
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { Plus, Save, ArrowLeft, List as ListIcon, LayoutGrid } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getPipeline, createPipeline, updatePipeline,
  addStep, updateStep, deleteStep,
  getDbConnections, getReportConfigs, getEmailConfigs, getBulkLoadConfigs,
  getStepTypes,
  getPipelines,
  addPipelineDep, removePipelineDep,
} from '../lib/api'
import type {
  Pipeline, PipelineDep, PipelineStep, StepType,
  DbConnection, ReportConfig, EmailConfig, BulkLoadConfig,
} from '../lib/types'
import { useProjectStore } from '../lib/store'
import { reorderSteps, renumberSteps, duplicateStep as duplicateStepHelper } from '../lib/pipelineReorder'
import StepEditor from '../components/pipeline/StepEditor'
import PipelineCanvas from '../components/pipeline/canvas/PipelineCanvas'
import PipelineVariablesCard, { type PipelineVar } from '../components/pipeline/PipelineVariablesCard'
import DependenciesCard from '../components/pipeline/DependenciesCard'
import WebhookCard from '../components/pipeline/WebhookCard'
import CronBuilder from '../components/pipeline/CronBuilder'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import FieldTooltip from '../components/shared/FieldTooltip'
import RouteErrorBoundary from '../components/shared/RouteErrorBoundary'

const STEP_TYPES: StepType[] = ['db_procedure', 'db_query', 'report', 'email', 'drive_upload', 'data_load', 'bulk_load', 'notification', 's3_upload', 'azure_blob_upload']

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

export default function PipelineEdit() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()
  const qc = useQueryClient()

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
  const { data: stepTypes = STEP_TYPES.map(type => ({ type, plugin: false })) } =
    useQuery({ queryKey: ['step-types'], queryFn: getStepTypes })

  const crumbs = isNew ? ['Workspace', 'Pipelines', 'New Pipeline'] : ['Workspace', 'Pipelines', 'Edit Pipeline']

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

  // Keyed by id so navigating between two different pipelines' edit pages (or
  // between /new and an edit page) always mounts a fresh form instance —
  // local state is seeded once from `existing` below, not synced via effect.
  return (
    <PipelineForm
      key={id ?? 'new'}
      id={id}
      isNew={isNew}
      existing={existing}
      dbConns={dbConns}
      reportCfgs={reportCfgs}
      emailCfgs={emailCfgs}
      bulkLoadCfgs={bulkLoadCfgs}
      allPipelines={allPipelines}
      stepTypes={stepTypes}
      navigate={navigate}
      qc={qc}
    />
  )
}

function PipelineForm({
  id, isNew, existing, dbConns, reportCfgs, emailCfgs, bulkLoadCfgs, allPipelines, stepTypes, navigate, qc,
}: {
  id?: string
  isNew: boolean
  existing?: Pipeline
  dbConns: DbConnection[]
  reportCfgs: ReportConfig[]
  emailCfgs: EmailConfig[]
  bulkLoadCfgs: BulkLoadConfig[]
  allPipelines: Pipeline[]
  stepTypes: { type: string; plugin: boolean }[]
  navigate: NavigateFunction
  qc: QueryClient
}) {
  const { activeProjectId } = useProjectStore()

  const [name, setName]           = useState(existing?.name ?? '')
  const [desc, setDesc]           = useState(existing?.description ?? '')
  const [schedule, setSchedule]   = useState(existing?.schedule ?? '')
  const [enabled, setEnabled]     = useState(existing?.enabled ?? true)
  const [timeout, setTimeout_]    = useState(existing?.timeout_minutes ?? 60)
  const [webhookUrl, setWebhookUrl] = useState(existing?.on_failure_webhook_url ?? '')
  const [steps, setSteps]         = useState<PipelineStep[]>(
    existing ? [...existing.steps].sort((a, b) => a.step_order - b.step_order) : [],
  )
  const [vars, setVars]           = useState<PipelineVar[]>(
    (existing?.variables ?? []).map(v => ({
      key: v.var_key,
      value: v.is_secret ? '' : v.var_value,
      is_secret: v.is_secret,
    })),
  )
  const [upstreamDeps, setUpstreamDeps] = useState<PipelineDep[]>(existing?.upstream_deps ?? [])
  const [view, setView]           = useState<'list' | 'canvas'>('list')
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const handleDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const from = steps.findIndex(s => s.id === active.id)
    const to   = steps.findIndex(s => s.id === over.id)
    setSteps(prev => reorderSteps(prev, from, to))
  }

  const handleStepChange = (stepId: string, updates: Partial<PipelineStep>) => {
    setSteps(prev => prev.map(s => s.id === stepId ? { ...s, ...updates } : s))
  }

  const handleStepDelete = (stepId: string) => {
    setSteps(prev => renumberSteps(prev.filter(s => s.id !== stepId)))
  }

  const handleStepDuplicate = (stepId: string) => {
    setSteps(prev => duplicateStepHelper(prev, stepId))
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
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-semibold text-[var(--text)]">Steps <span className="font-mono text-[var(--text-muted)] text-[11px]">({steps.length})</span></span>
              <div className="flex gap-px p-px bg-surface2 rounded-[7px] border border-border">
                <button
                  className={`btn btn-sm ${view === 'list' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setView('list')}
                  title="List view"
                  data-testid="view-toggle-list"
                >
                  <ListIcon size={12} />
                </button>
                <button
                  className={`btn btn-sm ${view === 'canvas' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setView('canvas')}
                  title="Canvas view"
                  data-testid="view-toggle-canvas"
                >
                  <LayoutGrid size={12} />
                </button>
              </div>
            </div>
            <div className="flex gap-1 flex-wrap justify-end">
              {stepTypes
                .filter(st => (STEP_TYPES as string[]).includes(st.type) || st.plugin)
                .map(st => (
                  <button key={st.type} className="btn btn-sm" onClick={() => addNewStep(st.type)} title={st.plugin ? 'Plugin step type' : undefined}>
                    <Plus size={10} /> {st.type.replace(/_/g, ' ')}{st.plugin ? ' (plugin)' : ''}
                  </button>
                ))}
            </div>
          </div>

          <RouteErrorBoundary label="Step editor">
            {view === 'list' ? (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                  {steps.map(step => (
                    <StepEditor
                      key={step.id}
                      step={step}
                      onChange={handleStepChange}
                      onDelete={handleStepDelete}
                      onDuplicate={handleStepDuplicate}
                      allSteps={steps}
                      dbConnections={dbConns.map(c => ({ id: c.id, name: c.name }))}
                      reportConfigs={reportCfgs.map(r => ({ id: r.id, name: r.name, output_filename: r.output_filename }))}
                      emailConfigs={emailCfgs.map(e => ({ id: e.id, name: e.name }))}
                      bulkLoadConfigs={bulkLoadCfgs.map(b => ({ id: b.id, name: b.name, source_directory: b.source_directory, target_table: b.target_table }))}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            ) : (
              <PipelineCanvas
                steps={steps}
                onStepsChange={setSteps}
                onDuplicate={handleStepDuplicate}
                onDelete={handleStepDelete}
                dbConnections={dbConns.map(c => ({ id: c.id, name: c.name }))}
                reportConfigs={reportCfgs.map(r => ({ id: r.id, name: r.name, output_filename: r.output_filename }))}
                emailConfigs={emailCfgs.map(e => ({ id: e.id, name: e.name }))}
                bulkLoadConfigs={bulkLoadCfgs.map(b => ({ id: b.id, name: b.name, source_directory: b.source_directory, target_table: b.target_table }))}
              />
            )}
          </RouteErrorBoundary>

          {view === 'list' && steps.length === 0 && (
            <div className="card ff-empty border-dashed py-6">
              <p className="msg">Add steps using the buttons above.</p>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
