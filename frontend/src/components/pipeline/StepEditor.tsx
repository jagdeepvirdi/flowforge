import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, GripVertical } from 'lucide-react'
import type { PipelineStep } from '../../lib/types'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import FieldTooltip from '../shared/FieldTooltip'
import { STEP_HINTS } from '../../lib/helpContent'
import Field from './stepForms/Field'
import { STEP_FORMS } from './stepForms'

const STEP_META: Record<string, { label: string; cls: string }> = {
  db_procedure:      { label: 'Proc',   cls: 'tbadge-procedure' },
  db_query:          { label: 'Query',  cls: 'tbadge-query' },
  report:            { label: 'Report', cls: 'tbadge-report' },
  email:             { label: 'Email',  cls: 'tbadge-email' },
  drive_upload:      { label: 'Drive',  cls: 'tbadge-drive' },
  ai_analyze:        { label: 'AI',     cls: 'tbadge-transform' },
  data_load:         { label: 'Load',   cls: 'tbadge-load' },
  bulk_load:         { label: 'Bulk',   cls: 'tbadge-bulk' },
  notification:      { label: 'Notify', cls: 'tbadge-email' },
  s3_upload:         { label: 'S3',     cls: 'tbadge-drive' },
  azure_blob_upload: { label: 'Azure',  cls: 'tbadge-drive' },
}

type Props = Readonly<{
  step: PipelineStep
  onChange: (id: string, updates: Partial<PipelineStep>) => void
  onDelete: (id: string) => void
  allSteps: PipelineStep[]
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}>


export default function StepEditor({ step, onChange, onDelete, allSteps, dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs }: Props) {
  const [expanded, setExpanded] = useState(true)
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  const cfg = step.config
  const setConfig = (key: string, value: unknown) =>
    onChange(step.id, { config: { ...cfg, [key]: value } })

  const meta = STEP_META[step.step_type] ?? { label: step.step_type, cls: 'tbadge-query' }
  const StepForm = STEP_FORMS[step.step_type]

  return (
    <div ref={setNodeRef} style={{ ...style, marginBottom: 6 }}>
      <div style={{
        background: expanded ? 'var(--surface)' : 'var(--bg-code)',
        border: `1px solid ${step.parallel_group ? 'rgba(99,102,241,0.5)' : expanded ? 'var(--border-strong)' : 'var(--border)'}`,
        borderLeft: step.parallel_group ? '3px solid #6366f1' : undefined,
        borderRadius: 10,
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px' }}>
          <button {...attributes} {...listeners} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'grab', padding: '2px', display: 'flex' }}>
            <GripVertical size={14} />
          </button>

          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--text-dim)', fontWeight: 700, width: 20, textAlign: 'center', flexShrink: 0 }}>
            {step.step_order}
          </span>

          <span className={`tbadge ${meta.cls}`}>{meta.label}</span>
          {step.parallel_group && (
            <span style={{ fontSize: 10, fontWeight: 600, padding: '1px 5px', borderRadius: 3, background: 'rgba(99,102,241,0.15)', color: '#818CF8', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
              ∥ {step.parallel_group}
            </span>
          )}

          <input
            style={{ background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 13, fontWeight: 500, flex: 1, fontFamily: 'inherit', cursor: 'text' }}
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Retries</span>
            <input
              type="number" min={0} max={10}
              className="input"
              value={Number(cfg.retry_count ?? 0)}
              onChange={e => setConfig('retry_count', Math.max(0, Number(e.target.value)))}
              style={{ width: 46, height: 26, padding: '0 6px', fontSize: 11 }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>delay</span>
            <input
              type="number" min={0} max={3600}
              className="input"
              value={Number(cfg.retry_delay_seconds ?? 30)}
              onChange={e => setConfig('retry_delay_seconds', Math.max(0, Number(e.target.value)))}
              style={{ width: 52, height: 26, padding: '0 6px', fontSize: 11 }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>s</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }} title="Steps sharing the same group name run concurrently">
            <span style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>∥ Group</span>
            <input
              className="input mono-input"
              placeholder="none"
              value={step.parallel_group ?? ''}
              onChange={e => onChange(step.id, { parallel_group: e.target.value.trim() || null })}
              style={{ width: 72, height: 26, padding: '0 6px', fontSize: 11 }}
            />
          </div>

          <button onClick={() => setExpanded(x => !x)} className="btn btn-sm btn-ghost btn-icon">
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <button onClick={() => onDelete(step.id)} className="btn btn-sm btn-ghost btn-icon" style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--failure-text)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
            <Trash2 size={13} />
          </button>
        </div>

        {expanded && (
          <div style={{ padding: '0 14px 14px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 12 }}>
            {/* Contextual hint banner */}
            {STEP_HINTS[step.step_type] && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg-code)', borderRadius: 6, padding: '7px 10px', lineHeight: 1.5 }}>
                {STEP_HINTS[step.step_type].summary}
              </div>
            )}

            {StepForm ? (
              <StepForm
                cfg={cfg}
                setConfig={setConfig}
                step={step}
                allSteps={allSteps}
                dbConnections={dbConnections}
                reportConfigs={reportConfigs}
                emailConfigs={emailConfigs}
                bulkLoadConfigs={bulkLoadConfigs}
              />
            ) : (
              <Field label="Config (JSON)" tooltip="No dedicated form for this step type (a plugin, or a built-in without a form yet) — edit its raw config here.">
                <textarea className="input mono-input" rows={8} value={JSON.stringify(cfg, null, 2)}
                  onChange={e => { try { onChange(step.id, { config: JSON.parse(e.target.value) }) } catch { /* invalid JSON while typing — ignore */ } }}
                  style={{ height: 'auto', resize: 'vertical' }}
                />
              </Field>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
