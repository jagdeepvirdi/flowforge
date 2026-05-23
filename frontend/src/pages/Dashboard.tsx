import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Clock, Calendar, History, Pencil, Play } from 'lucide-react'
import { getPipelines, getPipelineRuns, runPipeline, getRuns } from '../lib/api'
import type { Pipeline, PipelineRun } from '../lib/types'
import { useProjectStore } from '../lib/store'
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

function PipelineCard({ pipeline }: { pipeline: Pipeline }) {
  const qc = useQueryClient()
  const { data: runs = [] } = useQuery({
    queryKey: ['pipeline-runs', pipeline.id],
    queryFn: () => getPipelineRuns(pipeline.id),
    refetchInterval: (q) => (q.state.data ?? []).some(r => r.status === 'running') ? 3000 : false,
  })

  const lastRun: PipelineRun | undefined = runs[0]
  const isRunning = lastRun?.status === 'running'

  const { mutate: trigger, isPending } = useMutation({
    mutationFn: () => runPipeline(pipeline.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-runs', pipeline.id] }),
  })

  // Build mini run bars from recent history
  const bars = Array.from({ length: RUN_BARS }).map((_, i) => {
    const r = runs[RUN_BARS - 1 - i]
    if (!r) return 'idle'
    if (r.status === 'success') return 'ok'
    if (r.status === 'running') return 'run'
    if (r.status === 'failed') return 'fail'
    return 'idle'
  })

  const barColor = (b: string) => b === 'ok' ? 'var(--success)' : b === 'fail' ? 'var(--failure)' : b === 'run' ? 'var(--running)' : 'var(--border)'

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', letterSpacing: '-0.01em', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {pipeline.name}
          </div>
          {pipeline.description && (
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{pipeline.description}</div>
          )}
        </div>
        <StatusBadge status={lastRun?.status ?? 'idle'} animate />
      </div>

      {/* Meta row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, padding: '12px 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
        <MetaCol label="Last run" icon={<Clock size={10} />} value={lastRun ? fmtRel(lastRun.started_at) : '—'} />
        <MetaCol label="Duration" value={fmtDur(lastRun?.duration_ms ?? null)} mono />
        <MetaCol label="Next run" icon={<Calendar size={10} />} value={pipeline.schedule ? fmtNext(pipeline.next_run) : '—'} />
      </div>

      {/* Run mini-bars */}
      <div style={{ display: 'flex', gap: 2 }}>
        {bars.map((b, i) => (
          <span key={i} style={{ flex: 1, height: 22, borderRadius: 2, background: barColor(b), opacity: b === 'idle' ? 0.5 : 0.85 }} />
        ))}
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', gap: 6 }}>
        <Link to={`/runs?pipeline=${pipeline.id}`} className="btn btn-sm" style={{ flex: 1 }}>
          <History size={12} /> Runs
        </Link>
        <Link to={`/pipelines/${pipeline.id}/edit`} className="btn btn-sm" style={{ flex: 1 }}>
          <Pencil size={12} /> Edit
        </Link>
        <button
          className="btn btn-primary btn-sm"
          style={{ flex: 1.4 }}
          onClick={() => trigger()}
          disabled={isPending || isRunning || !pipeline.enabled}
        >
          {isPending || isRunning ? <Spinner size={12} /> : <Play size={11} />}
          {isRunning ? 'Running…' : 'Run Now'}
        </button>
      </div>
    </div>
  )
}

function MetaCol({ label, value, icon, mono }: { label: string; value: string; icon?: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: 12.5, color: 'var(--text-2)', display: 'flex', alignItems: 'center', gap: 4, fontFamily: mono ? 'JetBrains Mono, monospace' : 'inherit' }}>
        {icon && <span style={{ color: 'var(--text-muted)' }}>{icon}</span>}
        {value}
      </span>
    </div>
  )
}

export default function Dashboard() {
  const { activeProjectId } = useProjectStore()
  const projectParam = activeProjectId ? { project_id: activeProjectId } : undefined

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines', activeProjectId],
    queryFn: () => getPipelines(projectParam),
  })
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Sk h={28} r={6} style={{ width: 140 }} />
            <Sk h={14} style={{ width: 260 }} />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
          {[0,1,2,3].map(i => (
            <div key={i} className="card" style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Sk h={11} style={{ width: 80 }} />
              <Sk h={28} r={6} style={{ width: 60 }} />
            </div>
          ))}
        </div>
        <div className="sec-h" style={{ marginBottom: 14 }}>
          <Sk h={18} r={4} style={{ width: 80 }} />
          <Sk h={14} r={4} style={{ width: 60 }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
          {[0,1,2].map(i => (
            <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <Sk h={14} style={{ width: '55%' }} />
                  <Sk h={11} style={{ width: '40%' }} />
                </div>
                <Sk h={20} r={4} style={{ width: 60, flexShrink: 0 }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, padding: '12px 0', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>
                {[0,1,2].map(j => (
                  <div key={j} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <Sk h={10} style={{ width: '60%' }} />
                    <Sk h={12} style={{ width: '80%' }} />
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 2 }}>
                {Array.from({ length: 14 }).map((_, j) => (
                  <div key={j} style={{ flex: 1, height: 22, borderRadius: 2, background: 'var(--border)', opacity: 0.5 }} />
                ))}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <Sk h={28} r={6} style={{ flex: 1, width: 'auto' }} />
                <Sk h={28} r={6} style={{ flex: 1, width: 'auto' }} />
                <Sk h={28} r={6} style={{ flex: 1.4, width: 'auto' }} />
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
        actions={<Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={12} /> New Pipeline</Link>}
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
          {stats.map((s, i) => (
            <div key={i} className="card" style={{ padding: '16px 18px' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 28, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '-0.02em', color: s.danger ? 'var(--failure-text)' : 'var(--text)' }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Pipeline grid */}
        <div className="sec-h">
          <h2>Pipelines</h2>
          <Link to="/pipelines" style={{ fontSize: 12, color: 'var(--text-3)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
            View all →
          </Link>
        </div>

        {pipelines.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No pipelines yet.</p>
            <Link to="/pipelines/new" className="btn btn-primary">Create your first pipeline</Link>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 28 }}>
            {pipelines.map(p => <PipelineCard key={p.id} pipeline={p} />)}
          </div>
        )}

        {/* Recent failures */}
        {failedToday.length > 0 && (
          <>
            <div className="sec-h">
              <h2>Recent failures</h2>
              <Link to="/runs?status=failed" style={{ fontSize: 12, color: 'var(--text-3)', textDecoration: 'none' }}>View all failures →</Link>
            </div>
            <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
              <table className="tbl">
                <thead>
                  <tr>
                    <th style={{ width: 20 }} />
                    <th>Pipeline · Step</th>
                    <th>Error</th>
                    <th style={{ width: 90 }}>When</th>
                    <th style={{ width: 80 }} />
                  </tr>
                </thead>
                <tbody>
                  {failedToday.slice(0, 5).map(r => (
                    <tr key={r.id}>
                      <td><span style={{ width: 6, height: 6, display: 'inline-block', borderRadius: '50%', background: 'var(--failure)' }} /></td>
                      <td>
                        <div style={{ fontWeight: 500, color: 'var(--text)' }}>{r.pipeline_name}</div>
                        {r.error_step && <div className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>→ {r.error_step}</div>}
                      </td>
                      <td style={{ color: 'var(--text-3)', fontSize: 12, maxWidth: 360 }}>{r.error_message ?? '—'}</td>
                      <td className="mono" style={{ color: 'var(--text-muted)', fontSize: 11.5 }}>{fmtRel(r.started_at)}</td>
                      <td style={{ textAlign: 'right' }}>
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
