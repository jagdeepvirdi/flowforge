import Field from './Field'
import type { StepFormProps } from './types'

export default function DbQueryForm({ cfg, setConfig, step, dbConnections }: StepFormProps) {
  return (
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
      <Field label="Output variable (optional)" htmlFor={`step-${step.id}-out-var`}>
        <input id={`step-${step.id}-out-var`} className="input mono-input" value={String(cfg.output_variable ?? '')} onChange={e => setConfig('output_variable', e.target.value)} placeholder="e.g. subscription_count" />
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
          Captures the first column of the first row as <code style={{ color: 'var(--text-3)' }}>{'{{ subscription_count }}'}</code> in downstream steps.
        </span>
      </Field>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
        <input
          type="checkbox"
          checked={Boolean(cfg.capture_rows)}
          onChange={e => setConfig('capture_rows', e.target.checked)}
        />
        <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>Capture rows for email</span>
      </label>
      {Boolean(cfg.capture_rows) && (
        <div style={{ paddingLeft: 22, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Field label="Row limit">
            <input
              className="input"
              type="number"
              min={1}
              max={1000}
              value={String(cfg.row_limit ?? 100)}
              onChange={e => setConfig('row_limit', Number.parseInt(e.target.value) || 100)}
              style={{ width: 120 }}
            />
          </Field>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Makes query results available in downstream email steps as{' '}
            <code style={{ color: 'var(--text-3)', fontFamily: 'JetBrains Mono, monospace' }}>
              {`{{ steps.${step.name || 'this_step'}.table_html }}`}
            </code>
          </span>
        </div>
      )}
    </>
  )
}
