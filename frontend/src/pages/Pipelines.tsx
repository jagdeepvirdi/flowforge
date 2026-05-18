import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Play, Pencil, Trash2, Search, ChevronDown } from 'lucide-react'
import { getPipelines, deletePipeline, runPipeline } from '../lib/api'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

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
        actions={
          <Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Pipeline</Link>
        }
      />

      <div className="scroll">
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
                  <th style={{ width: 180 }}>Schedule</th>
                  <th style={{ width: 60 }}>Steps</th>
                  <th style={{ width: 80 }}>Enabled</th>
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
                    <td><StatusBadge status={p.enabled ? 'idle' : 'paused'} label={p.enabled ? 'Active' : 'Disabled'} /></td>
                    <td>
                      {p.schedule ? (
                        <>
                          <div style={{ fontSize: 12, color: '#CBD5E1' }}>Scheduled</div>
                          <div className="mono" style={{ fontSize: 10.5, color: '#64748B', marginTop: 2 }}>{p.schedule}</div>
                        </>
                      ) : (
                        <span style={{ color: '#475569' }}>—</span>
                      )}
                    </td>
                    <td className="mono" style={{ color: '#CBD5E1' }}>{p.steps.length}</td>
                    <td>
                      <span style={{ fontSize: 12, color: p.enabled ? '#4ADE80' : '#64748B' }}>
                        {p.enabled ? 'Yes' : 'No'}
                      </span>
                    </td>
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
