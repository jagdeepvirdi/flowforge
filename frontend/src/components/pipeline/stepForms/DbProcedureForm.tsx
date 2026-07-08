import Field from './Field'
import type { StepFormProps } from './types'

export default function DbProcedureForm({ cfg, setConfig, dbConnections }: StepFormProps) {
  return (
    <>
      <Field label="Connection">
        <select className="input" value={String(cfg.connection_id ?? '')} onChange={e => setConfig('connection_id', e.target.value)}>
          <option value="">Select connection…</option>
          {dbConnections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      <Field label="Procedure name">
        <input className="input mono-input" value={String(cfg.procedure ?? '')} onChange={e => setConfig('procedure', e.target.value)} placeholder="pkg.procedure_name" />
      </Field>
      <Field label="Parameters (JSON object)">
        <textarea className="input mono-input h-auto resize-none" rows={3} value={JSON.stringify(cfg.params ?? {}, null, 2)}
          onChange={e => { try { setConfig('params', JSON.parse(e.target.value)) } catch { /* invalid JSON while typing — ignore */ } }}
        />
      </Field>
    </>
  )
}
