import Field from './Field'
import type { StepFormProps } from './types'

export default function EmailForm({ cfg, setConfig, step, allSteps, reportConfigs, emailConfigs }: StepFormProps) {
  const capturingSteps = allSteps.filter(
    s => s.step_type === 'db_query'
      && s.step_order < step.step_order
      && Boolean(s.config.capture_rows)
  )
  const precedingReports = allSteps.filter(
    s => s.step_type === 'report' && s.step_order < step.step_order
  )
  const current = (cfg.attachments as string[] ?? [])

  return (
    <>
      <Field label="Email config" htmlFor={`step-${step.id}-email-id`}>
        <select id={`step-${step.id}-email-id`} className="input" value={String(cfg.email_config_id ?? '')} onChange={e => setConfig('email_config_id', e.target.value)}>
          <option value="">Select email config…</option>
          {emailConfigs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
      </Field>
      {/* Query data snippets from upstream capturing db_query steps */}
      {capturingSteps.length > 0 && (
        <Field label="Query data — available in email body">
          <div className="flex flex-col gap-1.5">
            {capturingSteps.map(qs => {
              const ref = qs.name.includes(' ') ? `steps['${qs.name}']` : `steps.${qs.name}`
              const snippets: [string, string][] = [
                [`{{ ${ref}.table_html }}`, 'HTML table (all rows)'],
                [`{{ ${ref}.kv_html }}`, 'Key-value list (first row)'],
                [`{% for row in ${ref}.rows %}{{ row.col }}{% endfor %}`, 'Custom loop'],
              ]
              return (
                <div key={qs.id} className="bg-bg-code rounded-r-sm py-2 px-2.5 flex flex-col gap-[5px]">
                  <span className="text-[11px] text-accent font-semibold">{qs.name}</span>
                  {snippets.map(([snippet, label]) => (
                    <div key={snippet} className="flex items-baseline gap-2">
                      <code className="text-[10.5px] text-text-3 font-mono flex-1 break-all">{snippet}</code>
                      <span className="text-[10px] text-text-dim whitespace-nowrap">{label}</span>
                    </div>
                  ))}
                </div>
              )
            })}
            <span className="text-[11px] text-text-muted">Copy these snippets into your email config body template.</span>
          </div>
        </Field>
      )}
      <Field label="Attachments">
        {/* Quick-add buttons for preceding report steps */}
        {precedingReports.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {precedingReports.map(rs => {
              const stepRef = rs.name.includes(' ') ? `steps['${rs.name}']` : `steps.${rs.name}`
              const variable = `{{ ${stepRef}.output_path }}`
              const already = current.includes(variable)
              const rc = reportConfigs.find(r => r.id === rs.config.report_config_id)
              const filename = rc?.output_filename ?? rs.name
              return (
                <button
                  key={rs.id}
                  type="button"
                  onClick={() => {
                    if (!already) setConfig('attachments', [...current, variable])
                  }}
                  className={`flex items-center gap-1.5 rounded-r-sm py-1 px-2.5 text-[11px] border ${already ? 'bg-[#1a2e1a] border-success text-success cursor-default' : 'bg-surface border-border-strong text-text-3 cursor-pointer'}`}
                >
                  <span className={`font-semibold ${already ? 'text-success' : 'text-accent'}`}>
                    {already ? '✓' : '+'} {rs.name}
                  </span>
                  <span className="text-text-dim font-mono">
                    {filename}
                  </span>
                </button>
              )
            })}
          </div>
        )}
        <textarea className="input mono-input !h-auto !resize-none !text-xs" rows={3}
          value={current.join('\n')}
          onChange={e => setConfig('attachments', e.target.value.split('\n').filter(Boolean))}
          placeholder="{{ steps.my_report.output_path }}"
        />
        <span className="text-[11px] text-text-muted mt-[3px]">
          Click a report above to attach it, or type a path manually. One path per line.
        </span>
      </Field>
    </>
  )
}
