import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play, Clock, CheckCircle, AlertCircle, Calendar } from 'lucide-react'
import { getPipelines, getPipelineRuns, runPipeline, getRuns } from '../lib/api'
import type { Pipeline, PipelineRun } from '../lib/types'
import StatusBadge from '../components/shared/StatusBadge'
import Spinner from '../components/shared/Spinner'

function formatDuration(ms: number | null): string {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function PipelineCard({ pipeline }: { pipeline: Pipeline }) {
  const qc = useQueryClient()
  const { data: runs = [] } = useQuery({
    queryKey: ['pipeline-runs', pipeline.id],
    queryFn: () => getPipelineRuns(pipeline.id),
    refetchInterval: (query) => (query.state.data ?? []).some(r => r.status === 'running') ? 3000 : false,
  })

  const lastRun: PipelineRun | undefined = runs[0]
  const isRunning = lastRun?.status === 'running'

  const { mutate: trigger, isPending } = useMutation({
    mutationFn: () => runPipeline(pipeline.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-runs', pipeline.id] }),
  })

  return (
    <div className="card hover:border-border/80 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <h3 className="font-medium text-text-primary truncate">{pipeline.name}</h3>
          {pipeline.description && (
            <p className="text-xs text-text-muted truncate mt-0.5">{pipeline.description}</p>
          )}
        </div>
        <StatusBadge status={lastRun?.status ?? 'never run'} animate />
      </div>

      <div className="flex items-center gap-4 text-xs text-text-muted mb-4">
        {pipeline.schedule && (
          <span className="flex items-center gap-1">
            <Calendar size={11} />
            <span className="font-mono">{pipeline.schedule}</span>
          </span>
        )}
        {lastRun && (
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {formatRelative(lastRun.started_at)}
            {lastRun.duration_ms != null && ` · ${formatDuration(lastRun.duration_ms)}`}
          </span>
        )}
      </div>

      <button
        className="btn-secondary w-full justify-center text-xs"
        onClick={() => trigger()}
        disabled={isPending || isRunning || !pipeline.enabled}
      >
        {isPending || isRunning ? <Spinner size={13} /> : <Play size={13} />}
        {isRunning ? 'Running…' : 'Run Now'}
      </button>
    </div>
  )
}

export default function Dashboard() {
  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: getPipelines,
  })
  const { data: recentRuns = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: () => getRuns({ limit: 50 }),
    refetchInterval: 5000,
  })

  const today = new Date().toDateString()
  const runsToday = recentRuns.filter(r => new Date(r.started_at).toDateString() === today)
  const successToday = runsToday.filter(r => r.status === 'success').length
  const failedToday = runsToday.filter(r => r.status === 'failed')
  const scheduled = pipelines.filter(p => p.enabled && p.schedule).length
  const successRate = runsToday.length > 0 ? Math.round((successToday / runsToday.length) * 100) : 100

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="p-8">
      <h1 className="text-xl font-semibold text-text-primary mb-6">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Runs today',       value: runsToday.length, icon: Play,         color: 'text-accent' },
          { label: 'Success rate',     value: `${successRate}%`, icon: CheckCircle,  color: 'text-success' },
          { label: 'Active schedules', value: scheduled,          icon: Calendar,     color: 'text-running' },
          { label: 'Failures today',   value: failedToday.length, icon: AlertCircle,  color: 'text-danger' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card flex items-center gap-3">
            <div className={`${color} opacity-80`}><Icon size={20} /></div>
            <div>
              <div className="text-xl font-semibold text-text-primary">{value}</div>
              <div className="text-xs text-text-muted">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Pipeline cards */}
      <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide mb-3">Pipelines</h2>
      {pipelines.length === 0 ? (
        <div className="card text-center py-10 text-text-muted text-sm">
          No pipelines yet. <a href="/pipelines/new" className="text-accent hover:underline">Create one →</a>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
          {pipelines.map(p => <PipelineCard key={p.id} pipeline={p} />)}
        </div>
      )}

      {/* Recent failures */}
      {failedToday.length > 0 && (
        <>
          <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide mb-3">Recent Failures</h2>
          <div className="card">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-text-muted border-b border-border">
                  <th className="text-left pb-2">Pipeline</th>
                  <th className="text-left pb-2">Error step</th>
                  <th className="text-left pb-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {failedToday.slice(0, 5).map(r => (
                  <tr key={r.id} className="border-b border-border/50 last:border-0">
                    <td className="py-2 font-medium text-text-primary">{r.pipeline_name}</td>
                    <td className="py-2 text-danger text-xs font-mono">{r.error_step ?? '—'}</td>
                    <td className="py-2 text-text-muted">{formatRelative(r.started_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
