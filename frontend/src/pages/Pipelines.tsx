import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Play, Pencil, Trash2, Copy, Upload, Search, ChevronDown } from 'lucide-react'
import { getPipelines, deletePipeline, clonePipeline, runPipeline, exportPipeline, importPipeline } from '../lib/api'
import { useProjectStore } from '../lib/store'
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
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span>{value}</span>
      <ChevronDown size={11} style={{ color: 'var(--text-muted)' }} />
    </button>
  )
}

export default function Pipelines() {
  const [search, setSearch]           = useState('')
  const [statusFilter, setStatusFilter]     = useState('All')
  const [scheduleFilter, setScheduleFilter] = useState('Any')
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines', activeProjectId],
    queryFn: () => getPipelines(activeProjectId ? { project_id: activeProjectId } : undefined),
  })
  const { mutate: remove } = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const { mutate: clone } = useMutation({
    mutationFn: clonePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const { mutate: trigger } = useMutation({
    mutationFn: runPipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const importRef = useRef<HTMLInputElement>(null)
  const { mutate: doImport } = useMutation({
    mutationFn: (yamlContent: string) => importPipeline(yamlContent),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => doImport(ev.target!.result as string)
    reader.readAsText(file)
    e.target.value = ''
  }

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
          <div style={{ display: 'flex', gap: 6 }}>
            <input ref={importRef} type="file" accept=".yaml,.yml" style={{ display: 'none' }} onChange={handleImportFile} />
            <button className="btn btn-sm btn-ghost" onClick={() => importRef.current?.click()}><Upload size={13} /> Import</button>
            <Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Pipeline</Link>
          </div>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '0 12px', height: 34, flex: 1, maxWidth: 360 }}>
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: 13, fontFamily: 'inherit', flex: 1 }}
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
                      <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                        <Link to={`/pipelines/${p.id}/edit`} style={{ color: 'var(--text)', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}>
                          {p.name}
                        </Link>
                      </div>
                      {p.description && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{p.description}</div>}
                    </td>
                    <td><StatusBadge status={p.enabled ? 'active' : 'paused'} label={p.enabled ? 'Active' : 'Disabled'} /></td>
                    <td>
                      {p.schedule ? (
                        <>
                          <div style={{ fontSize: 12, color: 'var(--text-2)' }}>{describeCron(p.schedule)}</div>
                          <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 2 }}>{p.schedule}</div>
                        </>
                      ) : (
                        <span style={{ color: 'var(--text-dim)' }}>Manual only</span>
                      )}
                    </td>
                    <td className="mono" style={{ color: 'var(--text-2)' }}>{p.steps.length}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        <button className="btn btn-sm btn-ghost btn-icon" onClick={() => trigger(p.id)} title="Run now" disabled={!p.enabled}>
                          <Play size={12} />
                        </button>
                        <button className="btn btn-sm btn-ghost btn-icon" title="Clone" onClick={() => clone(p.id)}>
                          <Copy size={12} />
                        </button>
                        <button className="btn btn-sm btn-ghost btn-icon" title="Export YAML" onClick={async () => {
                          const blob = await exportPipeline(p.id)
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url; a.download = `${p.name.replace(/\s+/g, '_')}.yaml`; a.click()
                          URL.revokeObjectURL(url)
                        }}>
                          <Upload size={12} style={{ transform: 'rotate(180deg)' }} />
                        </button>
                        <Link to={`/pipelines/${p.id}/edit`} className="btn btn-sm btn-ghost btn-icon" title="Edit">
                          <Pencil size={12} />
                        </Link>
                        <button
                          className="btn btn-sm btn-ghost btn-icon"
                          style={{ color: 'var(--text-muted)' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--failure-text)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
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
