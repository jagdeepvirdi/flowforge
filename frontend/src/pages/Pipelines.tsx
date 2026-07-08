import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Play, Pencil, Trash2, Copy, Upload, Search, ChevronDown, ArrowUpRight, X } from 'lucide-react'
import { getPipelines, deletePipeline, clonePipeline, runPipeline, exportPipeline, importPipeline, promotePipeline, getProjects } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import PageIntro from '../components/shared/PageIntro'
import Sk from '../components/shared/Skeleton'

function describeCron(expr: string): string {
  const p = expr.trim().split(/\s+/)
  if (p.length !== 5) return expr
  const [min, hr, dom, mon, dow] = p
  const hh = (v: string) => String(Number.parseInt(v)).padStart(2, '0')
  const mm = (v: string) => String(Number.parseInt(v)).padStart(2, '0')
  const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  // Every N minutes: */N * * * *
  if (/^\*\/\d+$/.test(min) && hr === '*' && dom === '*' && mon === '*' && dow === '*') {
    const n = Number.parseInt(min.replace('*/', ''))
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
    return `Weekly ${DAYS[Number.parseInt(dow)] ?? dow} ${hh(hr)}:${mm(min)}`
  }
  // Monthly: M H D * *
  if (/^\d+$/.test(min) && /^\d+$/.test(hr) && /^\d+$/.test(dom) && mon === '*' && dow === '*') {
    return `Monthly day ${Number.parseInt(dom)} ${hh(hr)}:${mm(min)}`
  }
  return expr
}

function FilterChip({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  const next = () => onChange(options[(options.indexOf(value) + 1) % options.length])
  return (
    <button className="btn btn-sm !gap-1" onClick={next}>
      <span className="text-text-muted">{label}</span>
      <span>{value}</span>
      <ChevronDown size={11} className="text-text-muted" />
    </button>
  )
}

export default function Pipelines() {
  const [search, setSearch]           = useState('')
  const [statusFilter, setStatusFilter]     = useState('All')
  const [promoteTarget, setPromoteTarget]   = useState<{ id: string; name: string } | null>(null)
  const [promoteProjectId, setPromoteProjectId] = useState('')
  const [promoteWarnings, setPromoteWarnings]   = useState<string[]>([])
  const [scheduleFilter, setScheduleFilter] = useState('Any')
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ['pipelines', activeProjectId],
    queryFn: () => getPipelines(activeProjectId ? { project_id: activeProjectId } : undefined),
  })
  const { data: allProjects = [] } = useQuery({ queryKey: ['projects'], queryFn: getProjects })
  const { mutate: remove } = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const { mutate: clone } = useMutation({
    mutationFn: clonePipeline,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipelines'] }),
  })
  const promoteMut = useMutation({
    mutationFn: ({ id, targetId }: { id: string; targetId: string }) => promotePipeline(id, targetId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['pipelines'] })
      if (data.warnings.length > 0) {
        setPromoteWarnings(data.warnings)
      } else {
        setPromoteTarget(null)
        setPromoteProjectId('')
      }
    },
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
  async function handleImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    doImport(await file.text())
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
    <>
      <TopBar crumbs={['Workspace', 'Pipelines']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 160 }} />
            <Sk h={14} style={{ width: 90 }} />
          </div>
        </div>
        <div className="card overflow-hidden !p-0">
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th className="w-[110px]">Status</th>
                <th className="w-[200px]">Schedule</th>
                <th className="w-[60px]">Steps</th>
                <th className="w-[120px]" />
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={14} style={{ width: '60%' }} /></td>
                  <td><Sk h={18} r={4} style={{ width: 70 }} /></td>
                  <td><Sk h={12} style={{ width: 120 }} /></td>
                  <td><Sk h={12} style={{ width: 20 }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 90, marginLeft: 'auto' }} /></td>
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
      <TopBar
        crumbs={['Workspace', 'Pipelines']}
        helpTopic="pipelines"
        actions={canEdit ? (
          <div className="flex gap-1.5">
            <input ref={importRef} type="file" accept=".yaml,.yml" className="hidden" onChange={handleImportFile} />
            <button className="btn btn-sm btn-ghost" onClick={() => importRef.current?.click()}><Upload size={13} /> Import</button>
            <Link to="/pipelines/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Pipeline</Link>
          </div>
        ) : undefined}
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
        <div className="flex items-center gap-2 mb-4">
          <div className="flex items-center gap-1.5 bg-surface border border-border rounded-r px-3 h-[34px] flex-1 max-w-[360px]">
            <Search size={14} className="text-text-muted" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-transparent border-none outline-none text-text-primary text-[13px] font-[inherit] flex-1"
              placeholder="Filter pipelines…"
            />
          </div>
          <FilterChip label="Status"   value={statusFilter}   options={['All','Active','Disabled']}      onChange={setStatusFilter} />
          <FilterChip label="Schedule" value={scheduleFilter} options={['Any','Scheduled','Manual']}       onChange={setScheduleFilter} />
        </div>

        {filtered.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">{search ? 'No pipelines match your filter.' : 'No pipelines yet.'}</p>
            {!search && canEdit && <Link to="/pipelines/new" className="btn btn-primary">Create your first pipeline</Link>}
          </div>
        ) : (
          <div className="card overflow-hidden !p-0">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th className="w-[110px]">Status</th>
                  <th className="w-[200px]">Schedule</th>
                  <th className="w-[60px]">Steps</th>
                  <th className="w-[120px]" />
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id}>
                    <td>
                      <div className="font-medium text-text-primary">
                        <Link to={`/pipelines/${p.id}/edit`} className="text-text-primary no-underline hover:!text-accent-text">
                          {p.name}
                        </Link>
                      </div>
                      {p.description && <div className="text-[11.5px] text-text-muted mt-0.5">{p.description}</div>}
                    </td>
                    <td><StatusBadge status={p.enabled ? 'active' : 'paused'} label={p.enabled ? 'Active' : 'Disabled'} /></td>
                    <td>
                      {p.schedule ? (
                        <>
                          <div className="text-xs text-text-2">{describeCron(p.schedule)}</div>
                          <div className="mono text-[10.5px] text-text-muted mt-0.5">{p.schedule}</div>
                        </>
                      ) : (
                        <span className="text-text-dim">Manual only</span>
                      )}
                    </td>
                    <td className="mono">{p.steps.length}</td>
                    <td>
                      <div className="flex gap-1 justify-end">
                        <button className="btn btn-sm btn-ghost btn-icon" title="Export YAML" onClick={async () => {
                          const blob = await exportPipeline(p.id)
                          const url = URL.createObjectURL(blob)
                          const a = document.createElement('a')
                          a.href = url; a.download = `${p.name.replace(/\s+/g, '_')}.yaml`; a.click()
                          URL.revokeObjectURL(url)
                        }}>
                          <Upload size={12} className="rotate-180" />
                        </button>
                        {canEdit && (
                          <>
                            <button className="btn btn-sm btn-ghost btn-icon" onClick={() => trigger(p.id)} title="Run now" disabled={!p.enabled}>
                              <Play size={12} />
                            </button>
                            <button className="btn btn-sm btn-ghost btn-icon" title="Clone" onClick={() => clone(p.id)}>
                              <Copy size={12} />
                            </button>
                            {allProjects.length > 1 && (
                              <button className="btn btn-sm btn-ghost btn-icon" title="Promote to another project"
                                onClick={() => { setPromoteTarget({ id: p.id, name: p.name }); setPromoteProjectId(''); setPromoteWarnings([]) }}>
                                <ArrowUpRight size={12} />
                              </button>
                            )}
                            <Link to={`/pipelines/${p.id}/edit`} className="btn btn-sm btn-ghost btn-icon" title="Edit">
                              <Pencil size={12} />
                            </Link>
                            <button
                              className="btn btn-sm btn-ghost btn-icon hover:!text-failure-text"
                              onClick={() => globalThis.confirm(`Delete "${p.name}"?`) && remove(p.id)}
                              title="Delete"
                            >
                              <Trash2 size={12} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Promote modal */}
      {promoteTarget && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="promote-modal-title"
          className="fixed inset-0 bg-[rgba(0,0,0,0.55)] flex items-center justify-center z-[100] p-4"
          onClick={e => { if (e.target === e.currentTarget) { setPromoteTarget(null); setPromoteWarnings([]) } }}
          onKeyDown={e => { if (e.key === 'Escape') { setPromoteTarget(null); setPromoteWarnings([]) } }}
        >
          <div className="card w-full max-w-[440px] !p-6 relative">
            <button onClick={() => { setPromoteTarget(null); setPromoteWarnings([]) }}
              className="absolute top-4 right-4 bg-transparent border-none cursor-pointer text-text-muted">
              <X size={15} />
            </button>

            <h3 id="promote-modal-title" className="m-0 mb-1.5 text-sm font-semibold">Promote Pipeline</h3>
            <p className="text-[13px] text-text-muted m-0 mb-[18px] leading-[1.5]">
              Copy <strong className="text-text-primary">{promoteTarget.name}</strong> to another project.
              The promoted copy starts disabled — enable it after reviewing step configurations.
            </p>

            {promoteWarnings.length > 0 ? (
              <>
                <div className="mb-3.5 py-2.5 px-3 bg-[rgba(249,115,22,0.07)] border border-[rgba(249,115,22,0.25)] rounded-r-sm">
                  <div className="text-xs font-semibold text-accent mb-1.5">Review required</div>
                  <div className="flex flex-col gap-[5px]">
                    {promoteWarnings.map((w, i) => (
                      <div key={i} className="text-xs text-text-2 leading-[1.5]">• {w}</div>
                    ))}
                  </div>
                </div>
                <button className="btn btn-primary w-full"
                  onClick={() => { setPromoteTarget(null); setPromoteWarnings([]) }}>
                  Got it — I'll update the step configs
                </button>
              </>
            ) : (
              <div className="flex flex-col gap-3.5">
                <div className="field">
                  <label htmlFor="promote-project">Target project *</label>
                  <select id="promote-project" className="input" value={promoteProjectId}
                    onChange={e => setPromoteProjectId(e.target.value)}>
                    <option value="">Select target project…</option>
                    {allProjects
                      .filter(p => p.id !== activeProjectId)
                      .map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div className="flex gap-2 justify-end">
                  <button className="btn" onClick={() => setPromoteTarget(null)}>Cancel</button>
                  <button className="btn btn-primary"
                    disabled={!promoteProjectId || promoteMut.isPending}
                    onClick={() => promoteTarget && promoteMut.mutate({ id: promoteTarget.id, targetId: promoteProjectId })}>
                    {promoteMut.isPending ? 'Promoting…' : 'Promote'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
