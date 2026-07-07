import Field from './Field'
import type { StepFormProps } from './types'

export default function ReportForm({ cfg, setConfig, step, reportConfigs }: StepFormProps) {
  return (
    <Field label="Report config" htmlFor={`step-${step.id}-report-id`}>
      <select id={`step-${step.id}-report-id`} className="input" value={String(cfg.report_config_id ?? '')} onChange={e => setConfig('report_config_id', e.target.value)}>
        <option value="">Select report config…</option>
        {reportConfigs.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
      </select>
    </Field>
  )
}
