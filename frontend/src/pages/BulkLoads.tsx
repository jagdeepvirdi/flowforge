import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getBulkLoadConfigs, deleteBulkLoadConfig } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

export default function BulkLoads() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['bulk-load-configs'],
    queryFn: getBulkLoadConfigs,
  })
  const { mutate: remove } = useMutation({
    mutationFn: deleteBulkLoadConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bulk-load-configs'] }),
  })

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Bulk Loads']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Bulk Loads']}
        helpTopic="pipelines"
        actions={
          <Link to="/bulk-loads/new" className="btn btn-primary btn-sm">
            <Plus size={13} /> New Bulk Load
          </Link>
        }
      />

      <div className="scroll">
        <PageIntro page="pipelines" />

        <div className="page-h">
          <div>
            <h1>Bulk Loads</h1>
            <p>{configs.length} bulk load config{configs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No bulk load configs yet.</p>
            <p style={{ fontSize: 12.5, color: '#64748B', margin: '0 0 14px' }}>
              A bulk load config defines the source directory, file pattern, and target table.
              Once created, reference it in a pipeline's Bulk Load step.
            </p>
            <Link to="/bulk-loads/new" className="btn btn-primary">Create first bulk load config</Link>
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Source directory</th>
                  <th>Target table</th>
                  <th style={{ width: 70 }}>Type</th>
                  <th style={{ width: 80 }}>Mode</th>
                  <th style={{ width: 80 }} />
                </tr>
              </thead>
              <tbody>
                {configs.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#F1F5F9' }}>
                        <Link to={`/bulk-loads/${c.id}/edit`} style={{ color: '#F1F5F9', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#FB923C')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#F1F5F9')}>
                          {c.name}
                        </Link>
                      </div>
                      {c.description && <div style={{ fontSize: 11.5, color: '#64748B', marginTop: 2 }}>{c.description}</div>}
                      {c.file_prefix && (
                        <div className="mono" style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>
                          prefix: {c.file_prefix}
                        </div>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: '#94A3B8' }}>
                      {c.source_directory || <span style={{ color: '#475569' }}>—</span>}
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: '#94A3B8' }}>
                      {c.target_table || <span style={{ color: '#475569' }}>—</span>}
                    </td>
                    <td>
                      <span className="tbadge tbadge-bulk">
                        {(c.file_type || 'csv').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: '#94A3B8', fontSize: 12 }}>{c.load_mode}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        <Link to={`/bulk-loads/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                        <button
                          className="btn btn-sm btn-ghost btn-icon"
                          style={{ color: '#64748B' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#F87171')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
                          onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}
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
