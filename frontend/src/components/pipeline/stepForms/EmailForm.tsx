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
        <select id={`step-${step.id}-email-id`} className="input" value={String(cfg.email_config_id ?? '')} onChange={e => setConfig('email_config_id', e.target.value)} style={{ height: 34 }}>
          <option value="">Select email config…</option>
          {emailConfigs.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
      </Field>
      {/* Query data snippets from upstream capturing db_query steps */}
      {capturingSteps.length > 0 && (
        <Field label="Query data — available in email body">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {capturingSteps.map(qs => {
              const ref = qs.name.includes(' ') ? `steps['${qs.name}']` : `steps.${qs.name}`
              const snippets: [string, string][] = [
                [`{{ ${ref}.table_html }}`, 'HTML table (all rows)'],
                [`{{ ${ref}.kv_html }}`, 'Key-value list (first row)'],
                [`{% for row in ${ref}.rows %}{{ row.col }}{% endfor %}`, 'Custom loop'],
              ]
              return (
                <div key={qs.id} style={{ background: 'var(--bg-code)', borderRadius: 6, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>{qs.name}</span>
                  {snippets.map(([snippet, label]) => (
                    <div key={snippet} style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <code style={{ fontSize: 10.5, color: 'var(--text-3)', fontFamily: 'JetBrains Mono, monospace', flex: 1, wordBreak: 'break-all' }}>{snippet}</code>
                      <span style={{ fontSize: 10, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{label}</span>
                    </div>
                  ))}
                </div>
              )
            })}
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Copy these snippets into your email config body template.</span>
          </div>
        </Field>
      )}
      <Field label="Attachments">
        {/* Quick-add buttons for preceding report steps */}
        {precedingReports.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
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
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: already ? '#1a2e1a' : 'var(--surface)',
                    border: `1px solid ${already ? 'var(--success)' : 'var(--border-strong)'}`,
                    borderRadius: 6, padding: '4px 10px', cursor: already ? 'default' : 'pointer',
                    fontSize: 11, color: already ? 'var(--success)' : 'var(--text-3)',
                  }}
                >
                  <span style={{ fontWeight: 600, color: already ? 'var(--success)' : 'var(--accent)' }}>
                    {already ? '✓' : '+'} {rs.name}
                  </span>
                  <span style={{ color: 'var(--text-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
                    {filename}
                  </span>
                </button>
              )
            })}
          </div>
        )}
        <textarea className="input mono-input" rows={3}
          value={current.join('\n')}
          onChange={e => setConfig('attachments', e.target.value.split('\n').filter(Boolean))}
          placeholder="{{ steps.my_report.output_path }}"
          style={{ height: 'auto', resize: 'none', fontSize: 12 }}
        />
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
          Click a report above to attach it, or type a path manually. One path per line.
        </span>
      </Field>
    </>
  )
}
