import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, ChevronRight, Clock, User } from 'lucide-react'
import { getRuns, getPipelines } from '../lib/api'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

function fmtDur(ms: number | null) {
  if (!ms) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`
}

const TIME_TABS = ['24h', '7d', '30d', 'All']

export default function RunHistory() {
  const [timeTab, setTimeTab]       = useState('All')
  const [filterPipeline, setFilterPipeline] = useState('')
  const [filterStatus, setFilterStatus]     = useState('')
  const [search, setSearch] = useState('')

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

  const filtered = runs.filter(r =>
    (!search || r.pipeline_name.toLowerCase().includes(search.toLowerCase()) || r.id.includes(search))
  )

  const successCount = filtered.filter(r => r.status === 'success').length
  const failedCount  = filtered.filter(r => r.status === 'failed').length
  const runningCount = filtered.filter(r => r.status === 'running').length

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Run History']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
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
          <div style={{ display: 'flex', gap: 1, background: '#21252F', borderRadius: 7, padding: 2, border: '1px solid #2D3143' }}>
            {TIME_TABS.map(t => (
              <button key={t} onClick={() => setTimeTab(t)} style={{
                background: timeTab === t ? '#1A1D27' : 'transparent',
                border: 'none',
                color: timeTab === t ? '#F1F5F9' : '#64748B',
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
            { label: 'Success', value: successCount, color: '#4ADE80', soft: 'rgba(34,197,94,0.1)' },
            { label: 'Failed',  value: failedCount,  color: '#F87171', soft: 'rgba(239,68,68,0.1)' },
            { label: 'Running', value: runningCount, color: '#60A5FA', soft: 'rgba(59,130,246,0.1)' },
          ].map(s => (
            <div key={s.label} className="card" style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color }} />
              <span style={{ fontSize: 11, color: '#64748B', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s.label}</span>
              <span className="mono" style={{ fontSize: 20, fontWeight: 600, color: '#F1F5F9', marginLeft: 'auto' }}>{s.value}</span>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#1A1D27', border: '1px solid #2D3143', borderRadius: 8, padding: '0 12px', height: 34, flex: 1, maxWidth: 320 }}>
            <Search size={14} style={{ color: '#64748B' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: '#F1F5F9', fontSize: 13, fontFamily: 'inherit', flex: 1 }}
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
                <tr><td colSpan={7} style={{ textAlign: 'center', padding: '40px 0', color: '#64748B' }}>
                  {runs.length === 0 ? 'No runs yet. Trigger a pipeline from the Pipelines page.' : 'No runs match your filters.'}
                </td></tr>
              )}
              {filtered.map(r => (
                <tr key={r.id}>
                  <td><StatusBadge status={r.status} animate /></td>
                  <td style={{ color: '#F1F5F9', fontWeight: 500 }}>{r.pipeline_name}</td>
                  <td className="mono" style={{ color: '#94A3B8', fontSize: 11.5 }}>{r.id.slice(0, 12)}…</td>
                  <td>
                    <span style={{ fontSize: 11.5, color: '#94A3B8', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      {r.triggered_by === 'web_ui' || r.triggered_by === 'api' ? <User size={11} /> : <Clock size={11} />}
                      {r.triggered_by}
                    </span>
                  </td>
                  <td className="mono" style={{ color: '#94A3B8', fontSize: 11.5 }}>{new Date(r.started_at).toLocaleString()}</td>
                  <td className="mono" style={{ color: '#CBD5E1', fontSize: 11.5 }}>{fmtDur(r.duration_ms)}</td>
                  <td>
                    <Link to={`/runs/${r.id}`} className="btn btn-sm btn-ghost btn-icon">
                      <ChevronRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
