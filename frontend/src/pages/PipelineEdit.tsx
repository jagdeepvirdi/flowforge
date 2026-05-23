import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import { Plus, Save, ArrowLeft, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  getPipeline, createPipeline, updatePipeline,
  addStep, updateStep, deleteStep,
  getDbConnections, getReportConfigs, getEmailConfigs, getBulkLoadConfigs,
  getCronNext,
} from '../lib/api'
import type { Pipeline, PipelineStep, StepType } from '../lib/types'
import { useProjectStore } from '../lib/store'
import StepEditor from '../components/pipeline/StepEditor'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import FieldTooltip from '../components/shared/FieldTooltip'

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
  }
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
  const { data: dbConns = [] } = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })
  const { data: reportCfgs = [] } = useQuery({ queryKey: ['report-configs'], queryFn: () => getReportConfigs() })
  const { data: emailCfgs = [] } = useQuery({ queryKey: ['email-configs'], queryFn: () => getEmailConfigs() })
  const { data: bulkLoadCfgs = [] } = useQuery({ queryKey: ['bulk-load-configs'], queryFn: getBulkLoadConfigs })

  const [name, setName]           = useState('')
  const [desc, setDesc]           = useState('')
  const [schedule, setSchedule]   = useState('')
  const [enabled, setEnabled]     = useState(true)
  const [timeout, setTimeout_]    = useState(60)
  const [steps, setSteps]         = useState<PipelineStep[]>([])
  const [vars, setVars]           = useState<{ key: string; value: string; is_secret: boolean }[]>([])
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
      setSteps([...existing.steps].sort((a, b) => a.step_order - b.step_order))
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
        pipeline = await createPipeline({ name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout, variables: validVars, project_id: activeProjectId ?? undefined })
      } else {
        pipeline = await updatePipeline(id!, { name, description: desc, schedule: schedule || null, enabled, timeout_minutes: timeout, variables: validVars })
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

  const crumbs = isNew ? ['Workspace', 'Pipelines', 'New Pipeline'] : ['Workspace', 'Pipelines', name || 'Edit Pipeline']

  if (!isNew && isLoading) return (
    <><TopBar crumbs={crumbs} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={crumbs}
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/pipelines" className="btn btn-sm"><ArrowLeft size={12} /> Back</Link>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? <Spinner size={12} /> : <Save size={12} />} Save
            </button>
          </div>
        }
      />

      <div className="scroll">
        {error && (
          <div style={{ marginBottom: 14, padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 7, fontSize: 12.5, color: '#F87171' }}>{error}</div>
        )}

        {/* Basic info */}
        <div className="card" style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Details</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="field">
              <label>Name *</label>
              <input className="input" value={name} onChange={e => { setName(e.target.value); if (fieldErrors.name) setFieldErrors(f => ({ ...f, name: '' })) }} />
              {fieldErrors.name && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.name}</span>}
            </div>
            <div className="field">
              <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                Schedule
                <FieldTooltip field="cron" />
              </label>
              {(!id || existing) && (
                <CronBuilder key={id ?? 'new'} defaultValue={schedule} onChange={setSchedule} />
              )}
            </div>
          </div>
          <div className="field">
            <label>Description</label>
            <input className="input" value={desc} onChange={e => setDesc(e.target.value)} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
              <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} style={{ accentColor: 'var(--accent)', width: 15, height: 15 }} />
              <span style={{ color: 'var(--text)' }}>Enabled</span>
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontWeight: 500 }}>Timeout (min)</span>
              <input className="input" type="number" min={1} value={timeout} onChange={e => { setTimeout_(+e.target.value); if (fieldErrors.timeout) setFieldErrors(f => ({ ...f, timeout: '' })) }} style={{ width: 70, height: 30, padding: '4px 8px', fontSize: 12 }} />
              {fieldErrors.timeout && <span style={{ fontSize: 11.5, color: 'var(--failure)' }}>{fieldErrors.timeout}</span>}
            </div>
          </div>
        </div>

        {/* Pipeline Variables */}
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Pipeline Variables</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                available as <code style={{ fontSize: 11, background: '#1A1D27', padding: '1px 5px', borderRadius: 3 }}>{'{{ var_name }}'}</code> in all step configs
              </span>
            </div>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => setVars(v => [...v, { key: '', value: '', is_secret: false }])}
            >
              <Plus size={10} /> Add variable
            </button>
          </div>

          {vars.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
              No variables. Add one to pass constants like currency codes, environment names, or date ranges to all steps.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {/* Header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 8, paddingBottom: 4, borderBottom: '1px solid #2D3143' }}>
                {(['Name', 'Value', 'Secret', ''] as const).map(h => (
                  <span key={h} style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{h}</span>
                ))}
              </div>
              {vars.map((v, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 8, alignItems: 'center' }}>
                  <input
                    className="input mono-input"
                    placeholder="currency"
                    value={v.key}
                    onChange={e => setVars(prev => prev.map((r, j) => j === i ? { ...r, key: e.target.value } : r))}
                    style={{ fontSize: 12, height: 30 }}
                  />
                  <input
                    className="input"
                    placeholder={v.is_secret ? '(unchanged)' : 'USD'}
                    value={v.value}
                    type={v.is_secret ? 'password' : 'text'}
                    onChange={e => setVars(prev => prev.map((r, j) => j === i ? { ...r, value: e.target.value } : r))}
                    style={{ fontSize: 12, height: 30 }}
                  />
                  <label style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', whiteSpace: 'nowrap', fontSize: 12, color: 'var(--text-muted)' }}>
                    <input
                      type="checkbox"
                      checked={v.is_secret}
                      onChange={e => setVars(prev => prev.map((r, j) => j === i ? { ...r, is_secret: e.target.checked } : r))}
                    />
                    Secret
                  </label>
                  <button
                    type="button"
                    onClick={() => setVars(prev => prev.filter((_, j) => j !== i))}
                    style={{ background: 'transparent', border: 'none', color: '#EF4444', cursor: 'pointer', padding: 4 }}
                    title="Remove variable"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
              <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                Built-in date vars: <code style={{ fontSize: 11 }}>{'{{ current_date }}'}</code> <code style={{ fontSize: 11 }}>{'{{ month_start_ts }}'}</code> <code style={{ fontSize: 11 }}>{'{{ prev_month_start_ts }}'}</code> <code style={{ fontSize: 11 }}>{'{{ last_success_at }}'}</code>
              </p>
            </div>
          )}
        </div>

        {/* Steps */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>Steps <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 11 }}>({steps.length})</span></span>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
              {STEP_TYPES.map(t => (
                <button key={t} className="btn btn-sm" onClick={() => addNewStep(t)}>
                  <Plus size={10} /> {t.replace(/_/g, ' ')}
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
                  allSteps={steps}
                  dbConnections={dbConns.map(c => ({ id: c.id, name: c.name }))}
                  reportConfigs={reportCfgs.map(r => ({ id: r.id, name: r.name, output_filename: r.output_filename }))}
                  emailConfigs={emailCfgs.map(e => ({ id: e.id, name: e.name }))}
                  bulkLoadConfigs={bulkLoadCfgs.map(b => ({ id: b.id, name: b.name, source_directory: b.source_directory, target_table: b.target_table }))}
                />
              ))}
            </SortableContext>
          </DndContext>

          {steps.length === 0 && (
            <div className="card ff-empty" style={{ borderStyle: 'dashed', padding: '24px 0' }}>
              <p className="msg">Add steps using the buttons above.</p>
            </div>
          )}
        </div>
      </div>
    </>
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
    n:        parseInt(min.replace('*/', '')) || 5,
    minute:   parseInt(min) || 0,
    hour:     parseInt(hr) || 8,
    weekday:  parseInt(dow) || 1,
    monthDay: parseInt(dom) || 1,
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

  const currentCron = freq === 'custom' ? rawCron : freq === 'none' ? '' : buildCronStr(freq, state)

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
  const muted: React.CSSProperties = { fontSize: 12.5, color: '#94A3B8' }
  const row:   React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={row}>
        <select className="input" value={freq} onChange={e => setFreq(e.target.value as Freq)} style={{ height: 34, width: 160 }}>
          <option value="none">No schedule</option>
          <option value="minutely">Every N minutes</option>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="custom">Custom (raw cron)</option>
        </select>

        {freq === 'minutely' && (<>
          <span style={muted}>every</span>
          <input className="input" type="number" min={1} max={59} value={state.n} onChange={e => upd('n', +e.target.value)} style={{ width: 64, height: 34 }} />
          <span style={muted}>minutes</span>
        </>)}

        {freq === 'hourly' && (<>
          <span style={muted}>at</span>
          <span style={{ ...muted, fontFamily: 'var(--font-mono)' }}>:</span>
          <input className="input" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} style={{ width: 64, height: 34 }} title="Minute past the hour (0–59)" />
          <span style={muted}>each hour</span>
        </>)}

        {(freq === 'daily' || freq === 'weekly' || freq === 'monthly') && (<>
          <span style={muted}>at</span>
          <select className="input" value={state.hour} onChange={e => upd('hour', +e.target.value)} style={{ height: 34, width: 80 }}>
            {Array.from({length: 24}, (_, i) => <option key={i} value={i}>{String(i).padStart(2,'0')}:00</option>)}
          </select>
          <input className="input" type="number" min={0} max={59} value={state.minute} onChange={e => upd('minute', +e.target.value)} style={{ width: 56, height: 34 }} title="Minute (0–59)" />
        </>)}

        {freq === 'weekly' && (<>
          <span style={muted}>on</span>
          <select className="input" value={state.weekday} onChange={e => upd('weekday', +e.target.value)} style={{ height: 34, width: 110 }}>
            {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
          </select>
        </>)}

        {freq === 'monthly' && (<>
          <span style={muted}>on day</span>
          <input className="input" type="number" min={1} max={31} value={state.monthDay} onChange={e => upd('monthDay', +e.target.value)} style={{ width: 64, height: 34 }} />
        </>)}

        {freq === 'custom' && (
          <input className="input mono-input" value={rawCron} onChange={e => setRawCron(e.target.value)} placeholder="0 8 * * 1-5" style={{ width: 160, height: 34 }} />
        )}
      </div>

      {currentCron && freq !== 'custom' && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
          {currentCron}
        </div>
      )}

      {nextData?.next_runs && nextData.next_runs.length > 0 && (
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', display: 'flex', flexWrap: 'wrap', gap: '4px 14px' }}>
          <span style={{ color: 'var(--text-dim)', fontWeight: 500, marginRight: 4 }}>Next runs:</span>
          {nextData.next_runs.map((t, i) => (
            <span key={i} style={{ fontFamily: 'var(--font-mono)' }}>
              {new Date(t).toLocaleString('en-US', { weekday:'short', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit', timeZoneName:'short' })}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
