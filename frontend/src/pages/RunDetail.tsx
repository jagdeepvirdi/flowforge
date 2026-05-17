import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { getRun } from '../lib/api'
import type { StepRun } from '../lib/types'
import StatusBadge from '../components/shared/StatusBadge'
import Spinner from '../components/shared/Spinner'

function formatDuration(ms: number | null) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

function StepRunRow({ s }: { s: StepRun }) {
  const [open, setOpen] = useState(s.status === 'failed')

  return (
    <div className="border-b border-border/50 last:border-0">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface2/50 text-left"
        onClick={() => setOpen(x => !x)}
      >
        <StatusBadge status={s.status} />
        <span className="font-medium text-sm text-text-primary flex-1">{s.step_name}</span>
        <span className="text-xs badge-muted mr-2">{s.step_type}</span>
        <span className="text-xs text-text-muted">{formatDuration(s.duration_ms)}</span>
        {s.rows_affected != null && <span className="text-xs text-text-muted">{s.rows_affected} rows</span>}
        {open ? <ChevronUp size={13} className="text-text-muted" /> : <ChevronDown size={13} className="text-text-muted" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-2">
          {s.error_message && (
            <div className="text-xs text-danger bg-danger/10 border border-danger/20 rounded-input px-3 py-2 font-mono whitespace-pre-wrap">
              {s.error_message}
            </div>
          )}
          {s.output_path && (
            <div className="text-xs text-text-muted">
              Output: <span className="text-text-primary font-mono">{s.output_path}</span>
            </div>
          )}
          {s.drive_url && (
            <div className="text-xs">
              <a href={s.drive_url} target="_blank" rel="noreferrer" className="text-accent hover:underline flex items-center gap-1">
                View in Drive <ExternalLink size={11} />
              </a>
            </div>
          )}
          {s.email_sent_to.length > 0 && (
            <div className="text-xs text-text-muted">
              Sent to: {s.email_sent_to.map(addr => (
                <span key={addr} className="badge-muted ml-1">{addr}</span>
              ))}
            </div>
          )}
          {s.logs && (
            <pre className="text-xs font-mono text-text-muted bg-surface2 border border-border rounded-input p-3 overflow-x-auto max-h-48 overflow-y-auto">
              {s.logs}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export default function RunDetail() {
  const { id } = useParams()
  const { data: run, isLoading } = useQuery({
    queryKey: ['run', id],
    queryFn: () => getRun(id!),
    refetchInterval: (query) => query.state.data?.status === 'running' ? 3000 : false,
  })

  if (isLoading || !run) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/runs" className="btn-ghost p-1"><ArrowLeft size={16} /></Link>
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{run.pipeline_name}</h1>
          <p className="text-xs text-text-muted font-mono mt-0.5">{run.id}</p>
        </div>
        <StatusBadge status={run.status} animate />
      </div>

      {/* Meta */}
      <div className="card mb-4 grid grid-cols-3 gap-4 text-sm">
        <div><div className="label">Started</div><div className="font-mono text-xs">{new Date(run.started_at).toLocaleString()}</div></div>
        <div><div className="label">Duration</div><div>{run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(1)}s` : '—'}</div></div>
        <div><div className="label">Triggered by</div><div>{run.triggered_by}</div></div>
      </div>

      {run.error_message && (
        <div className="mb-4 text-danger text-sm bg-danger/10 border border-danger/20 rounded-input px-3 py-2">
          <strong>Failed at step:</strong> {run.error_step}<br />
          {run.error_message}
        </div>
      )}

      {/* Step timeline */}
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border text-xs font-medium text-text-muted uppercase tracking-wide">
          Steps
        </div>
        {(run.step_runs ?? []).map(s => <StepRunRow key={s.id} s={s} />)}
      </div>
    </div>
  )
}
