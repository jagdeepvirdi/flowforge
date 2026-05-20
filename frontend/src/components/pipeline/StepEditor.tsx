import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, GripVertical } from 'lucide-react'
import type { PipelineStep, StepType } from '../../lib/types'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import FieldTooltip from '../shared/FieldTooltip'
import { STEP_HINTS } from '../../lib/helpContent'

const STEP_META: Record<StepType, { label: string; cls: string }> = {
  db_procedure: { label: 'Proc',   cls: 'tbadge-procedure' },
  db_query:     { label: 'Query',  cls: 'tbadge-query' },
  report:       { label: 'Report', cls: 'tbadge-report' },
  email:        { label: 'Email',  cls: 'tbadge-email' },
  drive_upload: { label: 'Drive',  cls: 'tbadge-drive' },
  ai_analyze:   { label: 'AI',     cls: 'tbadge-transform' },
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

  const meta = STEP_META[step.step_type] ?? { label: step.step_type, cls: 'tbadge-query' }

  return (
    <div ref={setNodeRef} style={{ ...style, marginBottom: 6 }}>
      <div style={{
        background: expanded ? '#1A1D27' : '#161922',
        border: `1px solid ${expanded ? '#3A3F52' : '#2D3143'}`,
        borderRadius: 10,
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px' }}>
          <button {...attributes} {...listeners} style={{ background: 'transparent', border: 'none', color: '#475569', cursor: 'grab', padding: '2px', display: 'flex' }}>
            <GripVertical size={14} />
          </button>

          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#475569', fontWeight: 700, width: 20, textAlign: 'center', flexShrink: 0 }}>
            {step.step_order}
          </span>

          <span className={`tbadge ${meta.cls}`}>{meta.label}</span>

          <input
            style={{ background: 'transparent', border: 'none', outline: 'none', color: '#F1F5F9', fontSize: 13, fontWeight: 500, flex: 1, fontFamily: 'inherit', cursor: 'text' }}
            value={step.name}
            onChange={e => onChange(step.id, { name: e.target.value })}
            placeholder="Step name"
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <select
              className="btn btn-sm"
              value={step.on_error}
              onChange={e => onChange(step.id, { on_error: e.target.value as 'stop' | 'continue' })}
              style={{ cursor: 'pointer', fontSize: 11, height: 26, padding: '0 8px' }}
            >
              <option value="stop">Stop on error</option>
              <option value="continue">Continue on error</option>
            </select>
            <FieldTooltip field="on_error" />
          </div>

          <button onClick={() => setExpanded(x => !x)} className="btn btn-sm btn-ghost btn-icon">
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <button onClick={() => onDelete(step.id)} className="btn btn-sm btn-ghost btn-icon" style={{ color: '#64748B' }}
            onMouseEnter={e => (e.currentTarget.style.color = '#F87171')}
            onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}>
            <Trash2 size={13} />
          </button>
        </div>

        {expanded && (
          <div style={{ padding: '0 14px 14px', borderTop: '1px solid #2D3143', display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 12 }}>
            {/* Contextual hint banner */}
            {STEP_HINTS[step.step_type] && (
              <div style={{ fontSize: 12, color: '#64748B', background: '#161922', borderRadius: 6, padding: '7px 10px', lineHeight: 1.5 }}>
                {STEP_HINTS[step.step_type].summary}
              </div>
            )}

            {step.step_type === 'db_procedure' && (
              <>
                <Field label="Connection">
                  <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)} style={{ height: 34 }}>
                    <option value="">Select connection…</option>
                    {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </Field>
                <Field label="Procedure name">
                  <input className="input mono-input" value={String(cfg.procedure ?? '')} onChange={e => setConfig('procedure', e.target.value)} placeholder="pkg.procedure_name" />
                </Field>
                <Field label="Parameters (JSON object)">
                  <textarea className="input mono-input" rows={3} value={JSON.stringify(cfg.params ?? {}, null, 2)}
                    onChange={e => { try { setConfig('params', JSON.parse(e.target.value)) } catch {} }}
                    style={{ height: 'auto', resize: 'none' }}
                  />
                </Field>
              </>
            )}

            {step.step_type === 'db_query' && (
              <>
                <Field label="Connection">
                  <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)} style={{ height: 34 }}>
                    <option value="">Select connection…</option>
                    {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </Field>
                <Field label="SQL Query">
                  <textarea className="input mono-input" rows={5} value={String(cfg.query ?? '')} onChange={e => setConfig('query', e.target.value)} placeholder="SELECT ..." style={{ height: 'auto', resize: 'none' }} />
                </Field>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10 }}>
                  <Field label="Output table (optional)">
                    <input className="input mono-input" value={String(cfg.output_table ?? '')} onChange={e => setConfig('output_table', e.target.value)} placeholder="schema.table_name" />
                  </Field>
                  <Field label="Mode">
                    <select className="input" value={String(cfg.mode ?? 'replace')} onChange={e => setConfig('mode', e.target.value)} style={{ height: 34, width: 140 }}>
                      <option value="replace">Replace</option>
                      <option value="append">Append</option>
                      <option value="truncate_insert">Truncate + Insert</option>
                    </select>
                  </Field>
                </div>
                <Field label="Output variable (optional)">
                  <input className="input mono-input" value={String(cfg.output_variable ?? '')} onChange={e => setConfig('output_variable', e.target.value)} placeholder="e.g. subscription_count" />
                  <span style={{ fontSize: 11, color: '#64748B', marginTop: 3 }}>
                    Captures the first column of the first row as <code style={{ color: '#94A3B8' }}>{'{{ subscription_count }}'}</code> in downstream steps.
                  </span>
                </Field>
              </>
            )}

            {step.step_type === 'report' && (
              <Field label="Report config">
                <select className="input" value={String(cfg.report_config_id ?? '')} onChange={e => setConfig('report_config_id', e.target.value)} style={{ height: 34 }}>
                  <option value="">Select report config…</option>
                  {reportConfigs.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              </Field>
            )}

            {step.step_type === 'email' && (
              <>
                <Field label="Email config">
                  <select className="input" value={String(cfg.email_config_id ?? '')} onChange={e => setConfig('email_config_id', e.target.value)} style={{ height: 34 }}>
                    <option value="">Select email config…</option>
                    {emailConfigs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                </Field>
                <Field label="Attachments (one path per line, supports {{ variables }})">
                  <textarea className="input mono-input" rows={3}
                    value={(cfg.attachments as string[] ?? []).join('\n')}
                    onChange={e => setConfig('attachments', e.target.value.split('\n').filter(Boolean))}
                    style={{ height: 'auto', resize: 'none' }}
                  />
                </Field>
              </>
            )}

            {step.step_type === 'drive_upload' && (
              <>
                <Field label="File path (supports {{ variables }})">
                  <input className="input mono-input" value={String(cfg.file_path ?? '')} onChange={e => setConfig('file_path', e.target.value)} />
                </Field>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <Field label="Drive folder ID" tooltip={<FieldTooltip field="drive_folder_id" />}>
                    <input className="input" value={String(cfg.folder_id ?? '')} onChange={e => setConfig('folder_id', e.target.value)} />
                  </Field>
                  <Field label="Rename to (optional)">
                    <input className="input" value={String(cfg.rename_to ?? '')} onChange={e => setConfig('rename_to', e.target.value)} placeholder="report_{{ current_month }}.xlsx" />
                  </Field>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Field({ label, children, tooltip }: { label: string; children: React.ReactNode; tooltip?: React.ReactNode }) {
  return (
    <div className="field">
      <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {label}
        {tooltip}
      </label>
      {children}
    </div>
  )
}
