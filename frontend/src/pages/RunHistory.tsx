import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, ChevronRight, Clock, User, Download } from 'lucide-react'
import { getRuns, getPipelines } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useAuth } from '../lib/auth'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'
import StepTrendsPanel from '../components/runs/StepTrendsPanel'

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
  const { token } = useAuth()

  // Reset pagination whenever a filter changes — adjusted during render
  // (React's documented pattern for this) rather than in an effect, since
  // activeProjectId comes from an external store this component doesn't
  // control locally, so there's no single onChange handler to hook into.
  const [prevFilters, setPrevFilters] = useState([filterPipeline, filterStatus, activeProjectId])
  if (prevFilters[0] !== filterPipeline || prevFilters[1] !== filterStatus || prevFilters[2] !== activeProjectId) {
    setPrevFilters([filterPipeline, filterStatus, activeProjectId])
    setLimit(PAGE_SIZE)
  }

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

  const handleExportCSV = () => {
    const params = new URLSearchParams()
    if (filterPipeline && filterPipeline !== '__deleted__') params.set('pipeline_id', filterPipeline)
    if (filterStatus) params.set('status', filterStatus)
    if (activeProjectId) params.set('project_id', activeProjectId)
    params.set('format', 'csv')

    const url = `/api/runs/export?${params.toString()}`
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    fetch(url, { headers })
      .then(res => {
        if (!res.ok) throw new Error(`Export failed: ${res.status}`)
        return res.blob()
      })
      .then(blob => {
        const objectUrl = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = `run_history_${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(objectUrl)
      })
      .catch(err => console.error('Export failed:', err))
  }

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Run History']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 160 }} />
            <Sk h={14} style={{ width: 80 }} />
          </div>
          <Sk h={32} r={7} style={{ width: 190 }} />
        </div>
        <div className="grid grid-cols-3 gap-3 mb-[18px]">
          {[0,1,2].map(i => (
            <div key={i} className="card py-3.5 px-4 flex items-center gap-3">
              <div className="w-2 h-2 rounded-[2px] bg-border shrink-0" />
              <Sk h={11} style={{ width: 55 }} />
              <Sk h={20} r={4} style={{ width: 36, marginLeft: 'auto' }} />
            </div>
          ))}
        </div>
        <div className="card overflow-hidden p-0">
          <table className="tbl">
            <thead>
              <tr>
                <th className="w-[110px]">Status</th>
                <th>Pipeline</th>
                <th className="w-[150px]">Run ID</th>
                <th className="w-[130px]">Trigger</th>
                <th className="w-[170px]">Started</th>
                <th className="w-[90px]">Duration</th>
                <th className="w-10" />
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

  const STATS = [
    { label: 'Success', value: successCount, dotCls: 'bg-success-text' },
    { label: 'Failed',  value: failedCount,  dotCls: 'bg-failure-text' },
    { label: 'Running', value: runningCount, dotCls: 'bg-running-text' },
  ]

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
          <div className="flex gap-px bg-surface2 rounded-[7px] p-0.5 border border-border">
            {TIME_TABS.map(t => (
              <button key={t} onClick={() => setTimeTab(t)} className={`border-none py-[5px] px-3 rounded-[5px] text-xs cursor-pointer font-[inherit] ${timeTab === t ? 'bg-surface text-text-primary font-semibold' : 'bg-transparent text-text-muted font-medium'}`}>{t}</button>
            ))}
          </div>
        </div>

        {/* Mini stats */}
        <div className="grid grid-cols-3 gap-3 mb-[18px]">
          {STATS.map(s => (
            <div key={s.label} className="card py-3.5 px-4 flex items-center gap-3">
              <span className={`w-2 h-2 rounded-[2px] ${s.dotCls}`} />
              <span className="text-[11px] text-text-muted font-semibold uppercase tracking-[0.04em]">{s.label}</span>
              <span className="mono text-xl font-semibold text-text-primary ml-auto">{s.value}</span>
            </div>
          ))}
        </div>

        <StepTrendsPanel pipelineId={(filterPipeline && filterPipeline !== '__deleted__') ? filterPipeline : undefined} />

        {/* Filters */}
        <div className="flex items-center gap-2 mb-3.5">
          <div className="flex items-center gap-1.5 bg-surface border border-border rounded-r px-3 h-[34px] flex-1 max-w-[320px]">
            <Search size={14} className="text-text-muted" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-transparent border-none outline-none text-text-primary text-[13px] font-[inherit] flex-1"
              placeholder="Search by run ID, pipeline…"
            />
          </div>
          <select
            className="btn btn-sm"
            value={filterPipeline}
            onChange={e => setFilterPipeline(e.target.value)}
          >
            <option value="">All pipelines</option>
            {pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            <option value="__deleted__">Deleted pipelines</option>
          </select>
          <select
            className="btn btn-sm"
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            className="btn btn-sm ml-auto flex items-center gap-1.5"
            onClick={handleExportCSV}
            disabled={filtered.length === 0}
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>

        <div className="card overflow-hidden p-0">
          <table className="tbl">
            <thead>
              <tr>
                <th className="w-[110px]">Status</th>
                <th>Pipeline</th>
                <th className="w-[150px]">Run ID</th>
                <th className="w-[130px]">Trigger</th>
                <th className="w-[170px]">Started</th>
                <th className="w-[90px]">Duration</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="text-center py-10 px-0 text-text-muted">
                  {runs.length === 0 ? 'No runs yet. Trigger a pipeline from the Pipelines page.' : 'No runs match your filters.'}
                </td></tr>
              )}
              {filtered.map(r => (
                <tr key={r.id}>
                  <td><StatusBadge status={r.status} animate /></td>
                  <td className="text-text-primary font-medium">
                    {r.pipeline_name}
                    {r.pipeline_id === null && (
                      <span className="text-[10.5px] text-text-dim font-normal ml-1.5">(deleted)</span>
                    )}
                  </td>
                  <td className="mono text-text-3 text-[11.5px]">{r.id.slice(0, 12)}…</td>
                  <td>
                    <span className="text-[11.5px] text-text-3 inline-flex items-center gap-[5px]">
                      {r.triggered_by === 'web_ui' || r.triggered_by === 'api' ? <User size={11} /> : <Clock size={11} />}
                      {r.triggered_by}
                    </span>
                  </td>
                  <td className="mono text-text-3 text-[11.5px]">{r.started_at ? new Date(r.started_at).toLocaleString() : '—'}</td>
                  <td className="mono text-[11.5px]">{fmtDur(r.duration_ms)}</td>
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
            <div className="py-3 px-0 text-center border-t border-border">
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
