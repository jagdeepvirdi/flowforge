import Field from './Field'
import type { StepFormProps } from './types'

export default function DbQueryForm({ cfg, setConfig, step, dbConnections }: StepFormProps) {
  return (
    <>
      <Field label="Connection">
        <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)}>
          <option value="">Select connection…</option>
          {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      <Field label="SQL Query">
        <textarea className="input mono-input h-auto resize-none" rows={5} value={String(cfg.query ?? '')} onChange={e => setConfig('query', e.target.value)} placeholder="SELECT ..." />
      </Field>
      <div className="grid grid-cols-[1fr_auto] gap-2.5">
        <Field label="Output table (optional)">
          <input className="input mono-input" value={String(cfg.output_table ?? '')} onChange={e => setConfig('output_table', e.target.value)} placeholder="schema.table_name" />
        </Field>
        <Field label="Mode">
          <select className="input w-[140px]" value={String(cfg.mode ?? 'replace')} onChange={e => setConfig('mode', e.target.value)}>
            <option value="replace">Replace</option>
            <option value="append">Append</option>
            <option value="truncate_insert">Truncate + Insert</option>
          </select>
        </Field>
      </div>
      <Field label="Output variable (optional)" htmlFor={`step-${step.id}-out-var`}>
        <input id={`step-${step.id}-out-var`} className="input mono-input" value={String(cfg.output_variable ?? '')} onChange={e => setConfig('output_variable', e.target.value)} placeholder="e.g. subscription_count" />
        <span className="text-[11px] text-text-muted mt-[3px]">
          Captures the first column of the first row as <code className="text-text-3">{'{{ subscription_count }}'}</code> in downstream steps.
        </span>
      </Field>
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={Boolean(cfg.capture_rows)}
          onChange={e => setConfig('capture_rows', e.target.checked)}
        />
        <span className="text-[12.5px] text-text-2">Capture rows for email</span>
      </label>
      {Boolean(cfg.capture_rows) && (
        <div className="pl-[22px] flex flex-col gap-1.5">
          <Field label="Row limit">
            <input
              className="input w-[120px]"
              type="number"
              min={1}
              max={1000}
              value={String(cfg.row_limit ?? 100)}
              onChange={e => setConfig('row_limit', Number.parseInt(e.target.value) || 100)}
            />
          </Field>
          <span className="text-[11px] text-text-muted">
            Makes query results available in downstream email steps as{' '}
            <code className="text-text-3 font-mono">
              {`{{ steps.${step.name || 'this_step'}.table_html }}`}
            </code>
          </span>
        </div>
      )}
    </>
  )
}
