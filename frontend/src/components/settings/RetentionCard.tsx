import Sk from '../shared/Skeleton'
import { StatusBadge, InlineCode } from './common'
import { useCurrentUser } from '../../lib/auth'
import { useRetentionSettings } from '../../hooks/useRetentionSettings'

function RetentionField({
  id, label, value, onChange, min, hint,
}: {
  id: string; label: string; value: string
  onChange: (v: string) => void; min: number; hint: string
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="input" type="number" min={min} value={value}
        onChange={e => onChange(e.target.value)} />
      <span className="text-[11px] text-text-muted">{hint}</span>
    </div>
  )
}

export default function RetentionCard() {
  const me = useCurrentUser()
  const isAdmin = me?.role === 'admin'

  const {
    data, isLoading, form, setForm, error, success, mut,
    outputTtlInvalid, handleSubmit, resetToDefault,
  } = useRetentionSettings()

  if (!isAdmin) {
    return (
      <div className="card flex flex-col gap-3">
        <div className="text-[13px] font-semibold text-text-primary">Data Retention Policies</div>
        {isLoading
          ? <div className="flex gap-3"><Sk h={13} style={{ width: 100 }} /><Sk h={13} style={{ width: 100 }} /><Sk h={13} style={{ width: 100 }} /></div>
          : data && (
            <div className="flex gap-3 flex-wrap">
              <StatusBadge ok label={`Runs: ${data.run_retention_days} days`} />
              <StatusBadge ok label={`Audit: ${data.audit_retention_days} days`} />
              <StatusBadge ok label={`Output files: ${data.output_ttl_days} days`} />
            </div>
          )
        }
        <p className="text-[13px] text-text-muted m-0">
          How long historical pipeline runs, audit logs, and generated report files are kept
          before the nightly background job deletes them. Only admins can change these values.
        </p>
      </div>
    )
  }

  return (
    <div className="card flex flex-col gap-3.5">
      <div className="text-[13px] font-semibold text-text-primary">Data Retention Policies</div>
      <p className="text-[13px] text-text-muted m-0">
        How long historical pipeline runs, audit logs, and generated report files are kept
        before the nightly background job deletes them. Falls back to the server's env var
        default unless overridden below.
      </p>
      {isLoading ? (
        <Sk h={64} r={6} />
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-run" label="Pipeline runs (days)" min={0}
                value={form.run} onChange={v => setForm(f => ({ ...f, run: v }))}
                hint={`0 = keep forever${data?.is_custom.run_retention_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.run_retention_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('run_retention_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-audit" label="Audit log (days)" min={0}
                value={form.audit} onChange={v => setForm(f => ({ ...f, audit: v }))}
                hint={`0 = keep forever${data?.is_custom.audit_retention_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.audit_retention_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('audit_retention_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-output" label="Output files (days)" min={1}
                value={form.outputTtl} onChange={v => setForm(f => ({ ...f, outputTtl: v }))}
                hint={`min 1${data?.is_custom.output_ttl_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.output_ttl_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('output_ttl_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
          </div>
          <p className="text-[11px] text-text-muted m-0">
            Output files can't be set to 0 here — that would delete every report immediately.
            Use <InlineCode>flowforge cleanup --days 0</InlineCode> if you intentionally need
            that; it requires explicit confirmation.
          </p>
          {error && (
            <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
              {error}
            </div>
          )}
          {success && (
            <div className="text-[12.5px] text-success-text bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm py-2 px-3">
              Saved.
            </div>
          )}
          <div>
            <button type="submit" className="btn btn-primary" disabled={mut.isPending || outputTtlInvalid}>
              {mut.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
