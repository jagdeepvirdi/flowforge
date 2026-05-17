import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, GripVertical } from 'lucide-react'
import type { PipelineStep, StepType } from '../../lib/types'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const STEP_TYPE_LABELS: Record<StepType, string> = {
  db_procedure: 'DB Procedure',
  db_query:     'DB Query',
  report:       'Report',
  email:        'Email',
  drive_upload: 'Drive Upload',
  ai_analyze:   'AI Analyze',
}

interface Props {
  step: PipelineStep
  onChange: (id: string, updates: Partial<PipelineStep>) => void
  onDelete: (id: string) => void
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string }[]
  emailConfigs:  { id: string; name: string }[]
}

export default function StepEditor({ step, onChange, onDelete, dbConnections, reportConfigs, emailConfigs }: Props) {
  const [expanded, setExpanded] = useState(true)
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  const cfg = step.config as Record<string, unknown>
  const setConfig = (key: string, value: unknown) =>
    onChange(step.id, { config: { ...cfg, [key]: value } })

  return (
    <div ref={setNodeRef} style={style} className="card mb-2 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-2.5 bg-surface2 border-b border-border mb-3">
        <button {...attributes} {...listeners} className="text-text-muted cursor-grab active:cursor-grabbing">
          <GripVertical size={14} />
        </button>
        <span className="badge-accent text-xs">{STEP_TYPE_LABELS[step.step_type]}</span>
        <input
          className="input flex-1 py-1 text-sm font-medium"
          value={step.name}
          onChange={e => onChange(step.id, { name: e.target.value })}
          placeholder="Step name"
        />
        <select
          className="input w-28 py-1 text-xs"
          value={step.on_error}
          onChange={e => onChange(step.id, { on_error: e.target.value as 'stop' | 'continue' })}
        >
          <option value="stop">Stop on error</option>
          <option value="continue">Continue on error</option>
        </select>
        <button onClick={() => setExpanded(x => !x)} className="btn-ghost p-1">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        <button onClick={() => onDelete(step.id)} className="btn-ghost p-1 hover:text-danger">
          <Trash2 size={14} />
        </button>
      </div>

      {expanded && (
        <div className="space-y-3">
          {step.step_type === 'db_procedure' && (
            <>
              <Field label="Connection">
                <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)}>
                  <option value="">Select connection…</option>
                  {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </Field>
              <Field label="Procedure name">
                <input className="input font-mono text-sm" value={String(cfg.procedure ?? '')} onChange={e => setConfig('procedure', e.target.value)} placeholder="pkg.procedure_name" />
              </Field>
              <Field label="Parameters (JSON object)">
                <textarea className="input font-mono text-sm resize-none" rows={3} value={JSON.stringify(cfg.params ?? {}, null, 2)} onChange={e => { try { setConfig('params', JSON.parse(e.target.value)) } catch {} }} />
              </Field>
            </>
          )}

          {step.step_type === 'db_query' && (
            <>
              <Field label="Connection">
                <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)}>
                  <option value="">Select connection…</option>
                  {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </Field>
              <Field label="SQL Query">
                <textarea className="input font-mono text-sm resize-none" rows={5} value={String(cfg.query ?? '')} onChange={e => setConfig('query', e.target.value)} placeholder="SELECT ..." />
              </Field>
              <Field label="Output table (optional)">
                <input className="input font-mono text-sm" value={String(cfg.output_table ?? '')} onChange={e => setConfig('output_table', e.target.value)} placeholder="schema.table_name" />
              </Field>
              <Field label="Mode">
                <select className="input" value={String(cfg.mode ?? 'replace')} onChange={e => setConfig('mode', e.target.value)}>
                  <option value="replace">Replace</option>
                  <option value="append">Append</option>
                  <option value="truncate_insert">Truncate + Insert</option>
                </select>
              </Field>
            </>
          )}

          {step.step_type === 'report' && (
            <Field label="Report config">
              <select className="input" value={String(cfg.report_config_id ?? '')} onChange={e => setConfig('report_config_id', e.target.value)}>
                <option value="">Select report config…</option>
                {reportConfigs.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </Field>
          )}

          {step.step_type === 'email' && (
            <>
              <Field label="Email config">
                <select className="input" value={String(cfg.email_config_id ?? '')} onChange={e => setConfig('email_config_id', e.target.value)}>
                  <option value="">Select email config…</option>
                  {emailConfigs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
              </Field>
              <Field label="Attachments (one path per line, supports {{ variables }})">
                <textarea className="input font-mono text-sm resize-none" rows={3}
                  value={(cfg.attachments as string[] ?? []).join('\n')}
                  onChange={e => setConfig('attachments', e.target.value.split('\n').filter(Boolean))} />
              </Field>
            </>
          )}

          {step.step_type === 'drive_upload' && (
            <>
              <Field label="File path (supports {{ variables }})">
                <input className="input font-mono text-sm" value={String(cfg.file_path ?? '')} onChange={e => setConfig('file_path', e.target.value)} />
              </Field>
              <Field label="Drive folder ID">
                <input className="input" value={String(cfg.folder_id ?? '')} onChange={e => setConfig('folder_id', e.target.value)} />
              </Field>
              <Field label="Rename to (optional)">
                <input className="input" value={String(cfg.rename_to ?? '')} onChange={e => setConfig('rename_to', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
              </Field>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}
