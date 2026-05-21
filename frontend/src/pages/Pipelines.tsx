import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Play, Pencil, Trash2, Search, ChevronDown } from 'lucide-react'
import { getPipelines, deletePipeline, runPipeline } from '../lib/api'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

function describeCron(expr: string): string {
  const p = expr.trim().split(/\s+/)
  if (p.length !== 5) return expr
  const [min, hr, dom, mon, dow] = p
  const hh = (v: string) => String(parseInt(v)).padStart(2, '0')
  const mm = (v: string) => String(parseInt(v)).padStart(2, '0')
  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  // Every N minutes: */N * * * *
  if (/^\*\/\d+$/.test(min) && hr === '*' && dom === '*' && mon === '*' && dow === '*') {
    const n = parseInt(min.replace('*/', ''))
    return `Every ${n} min`
  }
  // Hourly: M * * * *
  if (/^\d+$/.test(min) && hr === '*' && dom === '*' && mon === '*' && dow === '*') {
    return `Hourly at :${mm(min)}`
  }
  // Daily: M H * * *
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom === '*' && mon === '*' && dow === '*') {
    return `Daily ${hh(hr)}:${mm(min)}`
  }
  // Weekly: M H * * D
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && dom === '*' && mon === '*' && /^\d+$/.test(dow)) {
    return `Weekly ${DAYS[parseInt(dow)] ?? dow} ${hh(hr)}:${mm(min)}`
  }
  // Monthly: M H D * *
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && /^\d+$/.test(dom) && mon === '*' && dow === '*') {
    return `Monthly day ${parseInt(dom)} ${hh(hr)}:${mm(min)}`
  }
  return expr
}

function FilterChip({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  const next = () => onChange(options[(options.indexOf(value) + 1) % options.length])
  return (
    <button className="btn btn-sm" style={{ gap: 4 }} onClick={next}>
      <span style={{ color: '#64748B' }}>{label}</span>
      <span>{value}</span>
      <ChevronDown size={11} style={{ color: '#64748B' }} />
    </button>
  )
}

export default function Pipelines() {
  const [search, setSearch]           = useState('')
  const [statusFilter, setStatusFilter]     = useState('All')
  const [scheduleFilter, setScheduleFilter] = useState('Any')
  const qc = useQueryClient()

  const { data: pipelines = [], isLoading } = useQuery({ queryKey: ['pipelines'], queryFn: getPipelines })
  const { mutate: remove } = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const { mutate: trigger } = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })

  const filtered = pipelines.filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase())) return false
    if (statusFilter === 'Active'   &&  !p.enabled) return false
    if (statusFilter === 'Disabled' &&   p.enabled) return false
    if (scheduleFilter === 'Scheduled' && !p.schedule) return false
    if (scheduleFilter === 'Manual'    &&  p.schedule) return false
    return true
  })

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Pipelines']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Pipelines']}
        helpTopic="pipelines"
        actions={
          <Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Pipeline</Link>
        }
      />

      <div className="scroll">
        <PageIntro page="pipelines" />
        <div className="page-h">
          <div>
            <h1>Pipelines</h1>
            <p>{pipelines.length} pipeline{pipelines.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {/* Filter bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#1A1D27', border: '1px solid #2D3143', borderRadius: 8, padding: '0 12px', height: 34, flex: 1, maxWidth: 360 }}>
            <Search size={14} style={{ color: '#64748B' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: '#F1F5F9', fontSize: 13, fontFamily: 'inherit', flex: 1 }}
              placeholder="Filter pipelines…"
            />
          </div>
          <FilterChip label="Status"   value={statusFilter}   options={['All','Active','Disabled']}      onChange={setStatusFilter} />
          <FilterChip label="Schedule" value={scheduleFilter} options={['Any','Scheduled','Manual']}       onChange={setScheduleFilter} />
        </div>

        {filtered.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">{search ? 'No pipelines match your filter.' : 'No pipelines yet.'}</p>
            {!search && <Link to="/pipelines/new" className="btn btn-primary">Create your first pipeline</Link>}
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ width: 110 }}>Status</th>
                  <th style={{ width: 200 }}>Schedule</th>
                  <th style={{ width: 60 }}>Steps</th>
                  <th style={{ width: 120 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#F1F5F9' }}>
                        <Link to={`/pipelines/${p.id}/edit`} style={{ color: '#F1F5F9', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#FB923C')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#F1F5F9')}>
                          {p.name}
                        </Link>
                      </div>
                      {p.description && <div style={{ fontSize: 11.5, color: '#64748B', marginTop: 2 }}>{p.description}</div>}
                    </td>
                    <td><StatusBadge status={p.enabled ? 'active' : 'paused'} label={p.enabled ? 'Active' : 'Disabled'} /></td>
                    <td>
                      {p.schedule ? (
                        <>
                          <div style={{ fontSize: 12, color: '#CBD5E1' }}>{describeCron(p.schedule)}</div>
                          <div className="mono" style={{ fontSize: 10.5, color: '#64748B', marginTop: 2 }}>{p.schedule}</div>
                        </>
                      ) : (
                        <span style={{ color: '#475569' }}>Manual only</span>
                      )}
                    </td>
                    <td className="mono" style={{ color: '#CBD5E1' }}>{p.steps.length}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        <button className="btn btn-sm btn-ghost btn-icon" onClick={() => trigger(p.id)} title="Run now" disabled={!p.enabled}>
                          <Play size={12} />
                        </button>
                        <Link to={`/pipelines/${p.id}/edit`} className="btn btn-sm btn-ghost btn-icon" title="Edit">
                          <Pencil size={12} />
                        </Link>
                        <button
                          className="btn btn-sm btn-ghost btn-icon"
                          style={{ color: '#64748B' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#F87171')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
                          onClick={() => window.confirm(`Delete "${p.name}"?`) && remove(p.id)}
                          title="Delete"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
