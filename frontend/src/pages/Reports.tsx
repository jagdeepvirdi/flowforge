import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getReportConfigs, deleteReportConfig } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

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
    <><TopBar crumbs={['Workspace', 'Reports']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
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
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>A report config pairs a SQL query with an output format (Excel, PDF, CSV). Once created, reference it in a pipeline's report step.</p>
            {canEdit && <Link to="/reports/new" className="btn btn-primary">Create first report config</Link>}
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ width: 80 }}>Format</th>
                  <th style={{ width: 280 }}>Output filename</th>
                  <th style={{ width: 80 }} />
                </tr>
              </thead>
              <tbody>
                {configs.map(c => {
                  const m = FORMAT_META[c.format] ?? { cls: 'tbadge-query' }
                  return (
                    <tr key={c.id}>
                      <td>
                        <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                          <Link to={`/reports/${c.id}/edit`} style={{ color: 'var(--text)', textDecoration: 'none' }}
                            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
                            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}>
                            {c.name}
                          </Link>
                        </div>
                        {c.description && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{c.description}</div>}
                      </td>
                      <td><span className={`tbadge ${m.cls}`}>{c.format.toUpperCase()}</span></td>
                      <td className="mono" style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{c.output_filename}</td>
                      {canEdit && (
                        <td>
                          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                            <Link to={`/reports/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                            <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}>
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
