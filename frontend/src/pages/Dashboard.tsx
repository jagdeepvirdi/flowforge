import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Clock, Calendar, History, Pencil, Play } from 'lucide-react'
import { getPipelines, getPipelineRuns, runPipeline, getRuns } from '../lib/api'
import type { Pipeline, PipelineRun } from '../lib/types'
import { useProjectStore } from '../lib/store'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
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

  const barColor = (b: string) => b === 'ok' ? '#22C55E' : b === 'fail' ? '#EF4444' : b === 'run' ? '#3B82F6' : '#2D3143'

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9', letterSpacing: '-0.01em', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {pipeline.name}
          </div>
          {pipeline.description && (
            <div style={{ fontSize: 11.5, color: '#64748B', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{pipeline.description}</div>
          )}
        </div>
        <StatusBadge status={lastRun?.status ?? 'idle'} animate />
      </div>

      {/* Meta row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, padding: '12px 0', borderTop: '1px solid #2D3143', borderBottom: '1px solid #2D3143' }}>
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
      <span style={{ fontSize: 10.5, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: 12.5, color: '#CBD5E1', display: 'flex', alignItems: 'center', gap: 4, fontFamily: mono ? 'JetBrains Mono, monospace' : 'inherit' }}>
        {icon && <span style={{ color: '#64748B' }}>{icon}</span>}
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
    <><TopBar crumbs={['Workspace', 'Dashboard']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}><Spinner /></div></>
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
              <div style={{ fontSize: 11, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 8 }}>{s.label}</div>
              <div style={{ fontSize: 28, fontWeight: 600, fontFamily: 'JetBrains Mono, monospace', letterSpacing: '-0.02em', color: s.danger ? '#F87171' : '#F1F5F9' }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Pipeline grid */}
        <div className="sec-h">
          <h2>Pipelines</h2>
          <Link to="/pipelines" style={{ fontSize: 12, color: '#94A3B8', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
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
              <Link to="/runs?status=failed" style={{ fontSize: 12, color: '#94A3B8', textDecoration: 'none' }}>View all failures →</Link>
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
                      <td><span style={{ width: 6, height: 6, display: 'inline-block', borderRadius: '50%', background: '#EF4444' }} /></td>
                      <td>
                        <div style={{ fontWeight: 500, color: '#F1F5F9' }}>{r.pipeline_name}</div>
                        {r.error_step && <div className="mono" style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>→ {r.error_step}</div>}
                      </td>
                      <td style={{ color: '#94A3B8', fontSize: 12, maxWidth: 360 }}>{r.error_message ?? '—'}</td>
                      <td className="mono" style={{ color: '#64748B', fontSize: 11.5 }}>{fmtRel(r.started_at)}</td>
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
