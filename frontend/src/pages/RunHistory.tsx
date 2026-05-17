import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getRuns, getPipelines } from '../lib/api'
import StatusBadge from '../components/shared/StatusBadge'
import PageHeader from '../components/shared/PageHeader'
import Spinner from '../components/shared/Spinner'

function formatDuration(ms: number | null) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

const TRIGGER_BADGES: Record<string, string> = {
  scheduler: 'badge-running',
  cli:       'badge-muted',
  web_ui:    'badge-accent',
  api:       'badge-muted',
}

export default function RunHistory() {
  const [filterPipeline, setFilterPipeline] = useState('')
  const [filterStatus, setFilterStatus]     = useState('')

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs', filterPipeline, filterStatus],
    queryFn: () => getRuns({
      pipeline_id: filterPipeline || undefined,
      status:      filterStatus   || undefined,
      limit: 200,
    }),
    refetchInterval: 10_000,
  })
  const { data: pipelines = [] } = useQuery({ queryKey: ['pipelines'], queryFn: getPipelines })

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader title="Run History" subtitle={`${runs.length} runs`} />

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <select className="input w-52" value={filterPipeline} onChange={e => setFilterPipeline(e.target.value)}>
          <option value="">All pipelines</option>
          {pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="input w-40" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="border-b border-border">
            <tr className="text-xs text-text-muted">
              <th className="text-left px-4 py-3">Pipeline</th>
              <th className="text-left px-4 py-3">Triggered by</th>
              <th className="text-left px-4 py-3">Started</th>
              <th className="text-left px-4 py-3">Duration</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-text-muted">No runs found.</td></tr>
            )}
            {runs.map(r => (
              <tr key={r.id} className="border-b border-border/50 last:border-0 hover:bg-surface2/50">
                <td className="px-4 py-3 font-medium text-text-primary">{r.pipeline_name}</td>
                <td className="px-4 py-3">
                  <span className={TRIGGER_BADGES[r.triggered_by] ?? 'badge-muted'}>
                    {r.triggered_by}
                  </span>
                </td>
                <td className="px-4 py-3 text-text-muted font-mono text-xs">
                  {new Date(r.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-text-muted">{formatDuration(r.duration_ms)}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} animate /></td>
                <td className="px-4 py-3">
                  <Link to={`/runs/${r.id}`} className="text-xs text-accent hover:underline">View →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
