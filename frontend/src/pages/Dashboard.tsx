import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Clock, Calendar, History, Pencil, Play } from 'lucide-react'
import { getPipelines, getDashboardSummary, runPipeline, getRuns } from '../lib/api'
import type { Pipeline, PipelineRun } from '../lib/types'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'

function fmtDur(ms: number | null): string {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

function fmtRel(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function fmtNext(iso: string | null): string {
  if (!iso) return '—'
  const diff = new Date(iso).getTime() - Date.now()
  if (diff < 0) return 'overdue'
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'in <1m'
  if (m < 60) return `in ${m}m`
  const h = Math.floor(m / 60)
  if (h < 24) return `in ${h}h ${m % 60}m`
  return `in ${Math.floor(h / 24)}d ${h % 24}h`
}

const RUN_BARS = 14

function PipelineCard({ pipeline, runs }: { pipeline: Pipeline; runs: PipelineRun[] }) {
  const qc = useQueryClient()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'
  const lastRun: PipelineRun | undefined = runs[0]
  const isRunning = lastRun?.status === 'running'

  const { mutate: trigger, isPending } = useMutation({
    mutationFn: () => runPipeline(pipeline.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard-summary'] }),
  })

  // Build mini run bars from recent history
  const bars = Array.from({ length: RUN_BARS }).map((_, i) => {
    const r = runs[RUN_BARS - 1 - i]
    if (r?.status === 'success') return 'ok'
    if (r?.status === 'running') return 'run'
    if (r?.status === 'failed') return 'fail'
    return 'idle'
  })

  const barColor = (b: string) => {
    if (b === 'ok') return 'var(--success)'
    if (b === 'fail') return 'var(--failure)'
    if (b === 'run') return 'var(--running)'
    return 'var(--border)'
  }

  return (
    <div className="card flex flex-col gap-3.5 p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-[var(--text)] tracking-tight mb-0.5 truncate">
            {pipeline.name}
          </div>
          {pipeline.description && (
            <div className="text-[11.5px] text-[var(--text-muted)] truncate">{pipeline.description}</div>
          )}
        </div>
        <StatusBadge status={lastRun?.status ?? 'idle'} animate />
      </div>

      {/* Meta row */}
      <div className="grid grid-cols-3 gap-3 py-3 border-y border-[var(--border)]">
        <MetaCol label="Last run" icon={<Clock size={10} />} value={lastRun ? fmtRel(lastRun.started_at) : '—'} />
        <MetaCol label="Duration" value={fmtDur(lastRun?.duration_ms ?? null)} mono />
        <MetaCol label="Next run" icon={<Calendar size={10} />} value={pipeline.schedule ? fmtNext(pipeline.next_run) : '—'} />
      </div>

      {/* Run mini-bars */}
      <div className="flex gap-0.5">
        {bars.map((b, i) => ({ b, i })).map(({ b, i }) => (
          <span key={'bar-' + i} className="flex-1 h-[22px] rounded-[2px]" style={{ background: barColor(b), opacity: b === 'idle' ? 0.5 : 0.85 }} />
        ))}
      </div>

      {/* Footer */}
      <div className="flex gap-1.5">
        <Link to={`/runs?pipeline=${pipeline.id}`} className="btn btn-sm flex-1">
          <History size={12} /> Runs
        </Link>
        {canEdit && (
          <>
            <Link to={`/pipelines/${pipeline.id}/edit`} className="btn btn-sm flex-1">
              <Pencil size={12} /> Edit
            </Link>
            <button
              className="btn btn-primary btn-sm flex-[1.4]"
              onClick={() => trigger()}
              disabled={isPending || isRunning || !pipeline.enabled}
            >
              {isPending || isRunning ? <Spinner size={12} /> : <Play size={11} />}
              {isRunning ? 'Running…' : 'Run Now'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function MetaCol({ label, value, icon, mono }: { label: string; value: string; icon?: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10.5px] text-[var(--text-muted)] uppercase tracking-wider font-medium">{label}</span>
      <span className={`text-[12.5px] text-[var(--text-2)] flex items-center gap-1 ${mono ? 'font-mono' : ''}`}>
        {icon && <span className="text-[var(--text-muted)]">{icon}</span>}
        {value}
      </span>
    </div>
  )
}

export default function Dashboard() {
  const { activeProjectId } = useProjectStore()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'
  const projectParam = activeProjectId ? { project_id: activeProjectId } : undefined

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines', activeProjectId],
    queryFn: () => getPipelines(projectParam),
  })

  const { data: summary } = useQuery({
    queryKey: ['dashboard-summary', activeProjectId],
    queryFn: () => getDashboardSummary(activeProjectId ?? undefined),
    refetchInterval: (q) => {
      const runs = Object.values(q.state.data?.pipeline_runs ?? {}).flat()
      return runs.some(r => r.status === 'running') ? 3000 : 5000
    },
  })
  const pipelineRunsMap: Record<string, PipelineRun[]> = summary?.pipeline_runs ?? {}

  const { data: recentRuns = [] } = useQuery({
    queryKey: ['runs', activeProjectId],
    queryFn: () => getRuns({ limit: 50, project_id: activeProjectId ?? undefined }),
    refetchInterval: 5000,
  })

  const today = new Date().toDateString()
  const runsToday    = recentRuns.filter(r => new Date(r.started_at).toDateString() === today)
  const successToday = runsToday.filter(r => r.status === 'success').length
  const failedToday  = runsToday.filter(r => r.status === 'failed')
  const scheduled    = pipelines.filter(p => p.enabled && p.schedule).length
  const successRate  = runsToday.length > 0 ? Math.round((successToday / runsToday.length) * 100) : 100

  const stats = [
    { label: 'Runs today',       value: String(runsToday.length),  delta: null,          spark: true,  danger: false },
    { label: 'Success rate',     value: `${successRate}%`,         delta: null,          spark: true,  danger: false },
    { label: 'Active schedules', value: String(scheduled),         delta: null,          spark: false, danger: false },
    { label: 'Failures (24h)',   value: String(failedToday.length),delta: null,          spark: false, danger: failedToday.length > 0 },
  ]

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Dashboard']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 140 }} />
            <Sk h={14} style={{ width: 260 }} />
          </div>
        </div>
        <div className="grid-stats mb-7">
          {[0,1,2,3].map(i => (
            <div key={i} className="card p-[16px_18px] flex flex-col gap-2.5">
              <Sk h={11} style={{ width: 80 }} />
              <Sk h={28} r={6} style={{ width: 60 }} />
            </div>
          ))}
        </div>
        <div className="sec-h mb-3.5">
          <Sk h={18} r={4} style={{ width: 80 }} />
          <Sk h={14} r={4} style={{ width: 60 }} />
        </div>
        <div className="grid-pipelines">
          {[0,1,2].map(i => (
            <div key={i} className="card flex flex-col gap-3.5 p-4">
              <div className="flex justify-between gap-3">
                <div className="flex-1 flex flex-col gap-1.5">
                  <Sk h={14} style={{ width: '55%' }} />
                  <Sk h={11} style={{ width: '40%' }} />
                </div>
                <Sk h={20} r={4} style={{ width: 60, flexShrink: 0 }} />
              </div>
              <div className="grid grid-cols-3 gap-3 py-3 border-y border-[var(--border)]">
                {[0,1,2].map(j => (
                  <div key={j} className="flex flex-col gap-1">
                    <Sk h={10} style={{ width: '60%' }} />
                    <Sk h={12} style={{ width: '80%' }} />
                  </div>
                ))}
              </div>
              <div className="flex gap-0.5">
                {Array.from({ length: 14 }, (_, j) => j).map(n => (
                  <div key={'sk-bar-' + n} className="flex-1 h-[22px] rounded-[2px] bg-[var(--border)] opacity-50" />
                ))}
              </div>
              <div className="flex gap-1.5">
                <Sk h={28} r={6} className="flex-1 w-auto" />
                <Sk h={28} r={6} className="flex-1 w-auto" />
                <Sk h={28} r={6} className="flex-[1.4] w-auto" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Dashboard']}
        helpTopic="dashboard"
        actions={canEdit ? <Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={12} /> New Pipeline</Link> : undefined}
      />

      <div className="scroll">
        <PageIntro page="dashboard" />
        <div className="page-h">
          <div>
            <h1>Dashboard</h1>
            <p>{pipelines.length} pipeline{pipelines.length !== 1 ? 's' : ''} tracked · {failedToday.length} failure{failedToday.length !== 1 ? 's' : ''} today</p>
          </div>
        </div>

        {/* Stats row */}
        <div className="grid-stats mb-7">
          {stats.map((s) => (
            <div key={s.label} className="card p-[16px_18px]">
              <div className="text-[11px] text-[var(--text-muted)] uppercase tracking-wider font-semibold mb-2">{s.label}</div>
              <div className={`text-[28px] font-semibold font-mono tracking-tight ${s.danger ? 'text-[var(--failure-text)]' : 'text-[var(--text)]'}`}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Pipeline grid */}
        <div className="sec-h">
          <h2>Pipelines</h2>
          <Link to="/pipelines" className="text-[12px] text-[var(--text-3)] no-underline flex items-center gap-1">
            View all →
          </Link>
        </div>

        {pipelines.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No pipelines yet.</p>
            {canEdit && <Link to="/pipelines/new" className="btn btn-primary">Create your first pipeline</Link>}
          </div>
        ) : (
          <div className="grid-pipelines mb-7">
            {pipelines.map(p => <PipelineCard key={p.id} pipeline={p} runs={pipelineRunsMap[p.id] ?? []} />)}
          </div>
        )}

        {/* Recent failures */}
        {failedToday.length > 0 && (
          <>
            <div className="sec-h">
              <h2>Recent failures</h2>
              <Link to="/runs?status=failed" className="text-[12px] text-[var(--text-3)] no-underline">View all failures →</Link>
            </div>
            <div className="card overflow-hidden p-0">
              <table className="tbl">
                <thead>
                  <tr>
                    <th className="w-5" />
                    <th>Pipeline · Step</th>
                    <th>Error</th>
                    <th className="w-[90px]">When</th>
                    <th className="w-20" />
                  </tr>
                </thead>
                <tbody>
                  {failedToday.slice(0, 5).map(r => (
                    <tr key={r.id}>
                      <td><span className="w-1.5 h-1.5 inline-block rounded-full bg-[var(--failure)]" /></td>
                      <td>
                        <div className="font-medium text-[var(--text)]">{r.pipeline_name}</div>
                        {r.error_step && <div className="mono text-[11px] text-[var(--text-muted)] mt-0.5">→ {r.error_step}</div>}
                      </td>
                      <td className="text-[var(--text-3)] text-xs max-w-[360px]">{r.error_message ?? '—'}</td>
                      <td className="mono text-[var(--text-muted)] text-[11.5px]">{fmtRel(r.started_at)}</td>
                      <td className="text-right">
                        <Link to={`/runs/${r.id}`} className="btn btn-sm btn-ghost">View</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  )
}
