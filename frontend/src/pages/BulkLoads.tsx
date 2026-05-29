import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getBulkLoadConfigs, deleteBulkLoadConfig } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Sk from '../components/shared/Skeleton'
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
    <>
      <TopBar crumbs={['Workspace', 'Bulk Loads']} />
      <div className="scroll">
        <div className="page-h">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Sk h={28} r={6} style={{ width: 140 }} />
            <Sk h={14} style={{ width: 180 }} />
          </div>
        </div>
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
              {Array.from({ length: 5 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={14} style={{ width: '70%' }} /></td>
                  <td><Sk h={14} style={{ width: '80%' }} /></td>
                  <td><Sk h={14} style={{ width: '75%' }} /></td>
                  <td><Sk h={20} r={4} style={{ width: 42 }} /></td>
                  <td><Sk h={14} style={{ width: 50 }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 60 }} /></td>
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
            <p>{configs.length} bulk load config{configs.length === 1 ? '' : 's'}</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No bulk load configs yet.</p>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>
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
                      <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                        <Link to={`/bulk-loads/${c.id}/edit`} style={{ color: 'var(--text)', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}>
                          {c.name}
                        </Link>
                      </div>
                      {c.description && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 2 }}>{c.description}</div>}
                      {c.file_prefix && (
                        <div className="mono" style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                          prefix: {c.file_prefix}
                        </div>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--text-3)' }}>
                      {c.source_directory || <span style={{ color: 'var(--text-dim)' }}>—</span>}
                    </td>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--text-3)' }}>
                      {c.target_table || <span style={{ color: 'var(--text-dim)' }}>—</span>}
                    </td>
                    <td>
                      <span className="tbadge tbadge-bulk">
                        {(c.file_type || 'csv').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-3)', fontSize: 12 }}>{c.load_mode}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        <Link to={`/bulk-loads/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                        <button
                          className="btn btn-sm btn-ghost btn-icon"
                          style={{ color: 'var(--text-muted)' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--failure-text)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                          onClick={() => globalThis.confirm(`Delete "${c.name}"?`) && remove(c.id)}
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
