import { useState, useEffect } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, ChevronRight, Clock, User } from 'lucide-react'
import { getRuns, getPipelines } from '../lib/api'
import { useProjectStore } from '../lib/store'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'

function fmtDur(ms: number | null) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

const PAGE_SIZE = 50
const TIME_TABS = ['24h', '7d', '30d', 'All']

export default function RunHistory() {
  const [timeTab, setTimeTab]       = useState('All')
  const [filterPipeline, setFilterPipeline] = useState('')
  const [filterStatus, setFilterStatus]     = useState('')
  const [search, setSearch] = useState('')
  const [limit, setLimit]   = useState(PAGE_SIZE)
  const { activeProjectId } = useProjectStore()

  useEffect(() => { setLimit(PAGE_SIZE) }, [filterPipeline, filterStatus, activeProjectId])

  const { data: runs = [], isLoading, isFetching } = useQuery({
    queryKey: ['runs', filterPipeline, filterStatus, limit, activeProjectId],
    queryFn: () => getRuns({
      // '__deleted__' is handled client-side; don't send it as a UUID to the API
      pipeline_id: (filterPipeline && filterPipeline !== '__deleted__') ? filterPipeline : undefined,
      status:      filterStatus   || undefined,
      project_id:  activeProjectId ?? undefined,
      limit,
    }),
    placeholderData: keepPreviousData,
    refetchInterval: 10_000,
  })
  const { data: pipelines = [] } = useQuery({
    queryKey: ['pipelines', activeProjectId],
    queryFn: () => getPipelines(activeProjectId ? { project_id: activeProjectId } : undefined),
  })

  const filtered = runs.filter(r =>
    (!search || r.pipeline_name.toLowerCase().includes(search.toLowerCase()) || r.id.includes(search)) &&
    (filterPipeline !== '__deleted__' || r.pipeline_id === null)
  )

  const successCount = filtered.filter(r => r.status === 'success').length
  const failedCount  = filtered.filter(r => r.status === 'failed').length
  const runningCount = filtered.filter(r => r.status === 'running').length

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Run History']} />
      <div className="scroll">
        <div className="page-h">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Sk h={28} r={6} style={{ width: 160 }} />
            <Sk h={14} style={{ width: 80 }} />
          </div>
          <Sk h={32} r={7} style={{ width: 190 }} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 18 }}>
          {[0,1,2].map(i => (
            <div key={i} className="card" style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: 'var(--border)', flexShrink: 0 }} />
              <Sk h={11} style={{ width: 55 }} />
              <Sk h={20} r={4} style={{ width: 36, marginLeft: 'auto' }} />
            </div>
          ))}
        </div>
        <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Status</th>
                <th>Pipeline</th>
                <th style={{ width: 150 }}>Run ID</th>
                <th style={{ width: 130 }}>Trigger</th>
                <th style={{ width: 170 }}>Started</th>
                <th style={{ width: 90 }}>Duration</th>
                <th style={{ width: 40 }} />
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 8 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={20} r={4} style={{ width: 72 }} /></td>
                  <td><Sk h={14} style={{ width: '65%' }} /></td>
                  <td><Sk h={14} style={{ width: 100 }} /></td>
                  <td><Sk h={14} style={{ width: 75 }} /></td>
                  <td><Sk h={14} style={{ width: 140 }} /></td>
                  <td><Sk h={14} style={{ width: 50 }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 24 }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )

  return (
    <>
      <TopBar crumbs={['Workspace', 'Run History']} helpTopic="runs" />

      <div className="scroll">
        <PageIntro page="runs" />
        <div className="page-h">
          <div>
            <h1>Run History</h1>
            <p>{filtered.length} runs</p>
          </div>
          {/* Time tabs */}
          <div style={{ display: 'flex', gap: 1, background: 'var(--surface-2)', borderRadius: 7, padding: 2, border: '1px solid var(--border)' }}>
            {TIME_TABS.map(t => (
              <button key={t} onClick={() => setTimeTab(t)} style={{
                background: timeTab === t ? 'var(--surface)' : 'transparent',
                border: 'none',
                color: timeTab === t ? 'var(--text)' : 'var(--text-muted)',
                padding: '5px 12px',
                borderRadius: 5,
                fontSize: 12,
                fontWeight: timeTab === t ? 600 : 500,
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}>{t}</button>
            ))}
          </div>
        </div>

        {/* Mini stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 18 }}>
          {[
            { label: 'Success', value: successCount, color: 'var(--success-text)', soft: 'rgba(34,197,94,0.1)' },
            { label: 'Failed',  value: failedCount,  color: 'var(--failure-text)', soft: 'rgba(239,68,68,0.1)' },
            { label: 'Running', value: runningCount, color: 'var(--running-text)', soft: 'rgba(59,130,246,0.1)' },
          ].map(s => (
            <div key={s.label} className="card" style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color }} />
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s.label}</span>
              <span className="mono" style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', marginLeft: 'auto' }}>{s.value}</span>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '0 12px', height: 34, flex: 1, maxWidth: 320 }}>
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 13, fontFamily: 'inherit', flex: 1 }}
              placeholder="Search by run ID, pipeline…"
            />
          </div>
          <select
            className="btn btn-sm"
            value={filterPipeline}
            onChange={e => setFilterPipeline(e.target.value)}
            style={{ cursor: 'pointer' }}
          >
            <option value="">All pipelines</option>
            {pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            <option value="__deleted__">Deleted pipelines</option>
          </select>
          <select
            className="btn btn-sm"
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            style={{ cursor: 'pointer' }}
          >
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Status</th>
                <th>Pipeline</th>
                <th style={{ width: 150 }}>Run ID</th>
                <th style={{ width: 130 }}>Trigger</th>
                <th style={{ width: 170 }}>Started</th>
                <th style={{ width: 90 }}>Duration</th>
                <th style={{ width: 40 }} />
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                  {runs.length === 0 ? 'No runs yet. Trigger a pipeline from the Pipelines page.' : 'No runs match your filters.'}
                </td></tr>
              )}
              {filtered.map(r => (
                <tr key={r.id}>
                  <td><StatusBadge status={r.status} animate /></td>
                  <td style={{ color: 'var(--text)', fontWeight: 500 }}>
                    {r.pipeline_name}
                    {r.pipeline_id === null && (
                      <span style={{ fontSize: 10.5, color: 'var(--text-dim)', fontWeight: 400, marginLeft: 6 }}>(deleted)</span>
                    )}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-3)', fontSize: 11.5 }}>{r.id.slice(0, 12)}…</td>
                  <td>
                    <span style={{ fontSize: 11.5, color: 'var(--text-3)', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      {r.triggered_by === 'web_ui' || r.triggered_by === 'api' ? <User size={11} /> : <Clock size={11} />}
                      {r.triggered_by}
                    </span>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-3)', fontSize: 11.5 }}>{new Date(r.started_at).toLocaleString()}</td>
                  <td className="mono" style={{ color: 'var(--text-2)', fontSize: 11.5 }}>{fmtDur(r.duration_ms)}</td>
                  <td>
                    <Link to={`/runs/${r.id}`} className="btn btn-sm btn-ghost btn-icon">
                      <ChevronRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {runs.length === limit && (
            <div style={{ padding: '12px 0', textAlign: 'center', borderTop: '1px solid var(--border)' }}>
              <button
                className="btn btn-sm"
                onClick={() => setLimit(l => l + PAGE_SIZE)}
                disabled={isFetching}
              >
                {isFetching ? <Spinner size={11} /> : null} Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
