import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import { Plus, Save, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getPipeline, createPipeline, updatePipeline,
  addStep, updateStep, deleteStep,
  getDbConnections, getReportConfigs, getEmailConfigs,
} from '../lib/api'
import type { Pipeline, PipelineStep, StepType } from '../lib/types'
import StepEditor from '../components/pipeline/StepEditor'
import PageHeader from '../components/shared/PageHeader'
import Spinner from '../components/shared/Spinner'

const STEP_TYPES: StepType[] = ['db_procedure', 'db_query', 'report', 'email', 'drive_upload']

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
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })
  const { data: reportCfgs = [] } = useQuery({ queryKey: ['report-configs'], queryFn: getReportConfigs })
  const { data: emailCfgs = [] } = useQuery({ queryKey: ['email-configs'], queryFn: getEmailConfigs })

  const [name, setName]           = useState('')
  const [desc, setDesc]           = useState('')
  const [schedule, setSchedule]   = useState('')
  const [enabled, setEnabled]     = useState(true)
  const [timeout, setTimeout_]    = useState(60)
  const [steps, setSteps]         = useState<PipelineStep[]>([])
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  useEffect(() => {
    if (existing) {
      setName(existing.name)
      setDesc(existing.description ?? '')
      setSchedule(existing.schedule ?? '')
      setEnabled(existing.enabled)
      setTimeout_(existing.timeout_minutes)
      setSteps([...existing.steps].sort((a, b) => a.step_order - b.step_order))
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
    if (!name.trim()) { setError('Pipeline name is required'); return }
    setSaving(true)
    setError('')
    try {
      let pipeline: Pipeline
      if (isNew) {
        pipeline = await createPipeline({ name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout })
      } else {
        pipeline = await updatePipeline(id!, { name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout })
      }

      // Sync steps: delete removed, update existing, add new
      const existingIds = new Set((existing?.steps ?? []).map(s => s.id))
      const currentIds  = new Set(steps.filter(s => !s.id.startsWith('_new_')).map(s => s.id))

      // Delete removed steps
      for (const s of (existing?.steps ?? [])) {
        if (!currentIds.has(s.id)) await deleteStep(s.id)
      }
      // Update/add steps in order
      for (const s of steps) {
        const payload = { name: s.name, step_type: s.step_type, config: s.config, on_error: s.on_error, step_order: s.step_order, enabled: s.enabled }
        if (s.id.startsWith('_new_')) {
          await addStep(pipeline.id, payload)
        } else if (existingIds.has(s.id)) {
          await updateStep(s.id, payload)
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

  if (!isNew && isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8 max-w-3xl">
      <PageHeader
        title={isNew ? 'New Pipeline' : 'Edit Pipeline'}
        action={
          <div className="flex gap-2">
            <Link to="/pipelines" className="btn-secondary"><ArrowLeft size={14}/> Back</Link>
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={14} /> : <Save size={14} />} Save
            </button>
          </div>
        }
      />

      {error && (
        <div className="mb-4 text-danger text-sm bg-danger/10 border border-danger/20 rounded-input px-3 py-2">{error}</div>
      )}

      {/* Basic info */}
      <div className="card mb-4 space-y-4">
        <h2 className="text-sm font-medium text-text-primary">Details</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Name *</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Schedule (cron expression)</label>
            <input className="input font-mono text-sm" value={schedule} onChange={e => setSchedule(e.target.value)} placeholder="0 6 * * 1" />
          </div>
        </div>
        <div>
          <label className="label">Description</label>
          <input className="input" value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)}
              className="w-4 h-4 accent-accent" />
            <span className="text-sm text-text-primary">Enabled</span>
          </label>
          <div className="flex items-center gap-2">
            <label className="label mb-0">Timeout (min)</label>
            <input className="input w-20" type="number" min={1} value={timeout} onChange={e => setTimeout_(+e.target.value)} />
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-text-primary">Steps</h2>
          <div className="flex gap-1">
            {STEP_TYPES.map(t => (
              <button key={t} className="btn-secondary text-xs py-1 px-2" onClick={() => addNewStep(t)}>
                <Plus size={11} /> {t.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
            {steps.map(step => (
              <StepEditor
                key={step.id}
                step={step}
                onChange={handleStepChange}
                onDelete={handleStepDelete}
                dbConnections={dbConns.map(c => ({ id: c.id, name: c.name }))}
                reportConfigs={reportCfgs.map(r => ({ id: r.id, name: r.name }))}
                emailConfigs={emailCfgs.map(e => ({ id: e.id, name: e.name }))}
              />
            ))}
          </SortableContext>
        </DndContext>

        {steps.length === 0 && (
          <div className="card text-center py-6 text-text-muted text-sm border-dashed">
            Add steps using the buttons above.
          </div>
        )}
      </div>
    </div>
  )
}
