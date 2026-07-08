import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getReportConfigs, deleteReportConfig } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import PageIntro from '../components/shared/PageIntro'
import Sk from '../components/shared/Skeleton'

const FORMAT_META: Record<string, { cls: string }> = {
  excel: { cls: 'tbadge-report' },
  csv:   { cls: 'tbadge-export' },
  pdf:   { cls: 'tbadge-query'  },
}

export default function Reports() {
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['report-configs', activeProjectId],
    queryFn: () => getReportConfigs(activeProjectId ? { project_id: activeProjectId } : undefined),
  })
  const { mutate: remove } = useMutation({
    mutationFn: deleteReportConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report-configs'] }),
  })

  if (isLoading) return (
    <>
      <TopBar crumbs={['Workspace', 'Reports']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 130 }} />
            <Sk h={14} style={{ width: 110 }} />
          </div>
        </div>
        <div className="card !p-0 overflow-hidden">
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th className="w-20">Format</th>
                <th className="w-[280px]">Output filename</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={14} style={{ width: '55%' }} /></td>
                  <td><Sk h={18} r={4} style={{ width: 50 }} /></td>
                  <td><Sk h={12} style={{ width: '80%' }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 50, marginLeft: 'auto' }} /></td>
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
        crumbs={['Workspace', 'Reports']}
        helpTopic="reports"
        actions={canEdit ? <Link to="/reports/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Report</Link> : undefined}
      />
      <div className="scroll">
        <PageIntro page="reports" />
        <div className="page-h">
          <div>
            <h1>Reports</h1>
            <p>{configs.length} report config{configs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No report configs yet.</p>
            <p className="text-[12.5px] text-text-muted m-0 mb-3.5">A report config pairs a SQL query with an output format (Excel, PDF, CSV). Once created, reference it in a pipeline's report step.</p>
            {canEdit && <Link to="/reports/new" className="btn btn-primary">Create first report config</Link>}
          </div>
        ) : (
          <div className="card !p-0 overflow-hidden">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th className="w-20">Format</th>
                  <th className="w-[280px]">Output filename</th>
                  <th className="w-20" />
                </tr>
              </thead>
              <tbody>
                {configs.map(c => {
                  const m = FORMAT_META[c.format] ?? { cls: 'tbadge-query' }
                  return (
                    <tr key={c.id}>
                      <td>
                        <div className="font-medium text-text-primary">
                          <Link to={`/reports/${c.id}/edit`} className="text-text-primary no-underline hover:!text-accent-text">
                            {c.name}
                          </Link>
                        </div>
                        {c.description && <div className="text-[11.5px] text-text-muted mt-0.5">{c.description}</div>}
                      </td>
                      <td><span className={`tbadge ${m.cls}`}>{c.format.toUpperCase()}</span></td>
                      <td className="mono text-[11.5px] !text-text-3">{c.output_filename}</td>
                      {canEdit && (
                        <td>
                          <div className="flex gap-1 justify-end">
                            <Link to={`/reports/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                            <button className="btn btn-sm btn-ghost btn-icon" onClick={() => globalThis.confirm(`Delete "${c.name}"?`) && remove(c.id)}>
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
