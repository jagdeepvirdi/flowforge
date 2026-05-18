import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getEmailConfigs, deleteEmailConfig, getEmailProviders } from '../lib/api'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

export default function Emails() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery({ queryKey: ['email-configs'], queryFn: getEmailConfigs })
  const { data: providers = [] } = useQuery({ queryKey: ['email-providers'], queryFn: getEmailProviders })
  const { mutate: remove } = useMutation({
    mutationFn: deleteEmailConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-configs'] }),
  })

  const providerName = (id: string | null) => providers.find(p => p.id === id)?.name ?? '—'

  if (isLoading) return (
    <><TopBar crumbs={['Workspace', 'Email Templates']} />
    <div className="scroll" style={{ display: 'flex', justifyContent: 'center' }}><Spinner /></div></>
  )

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Email Templates']}
        actions={<Link to="/emails/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Email Config</Link>}
      />
      <div className="scroll">
        <div className="page-h">
          <div>
            <h1>Email Templates</h1>
            <p>{configs.length} config{configs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No email configs yet.</p>
            <Link to="/emails/new" className="btn btn-primary">Create email config</Link>
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th style={{ width: 140 }}>Provider</th>
                  <th>Subject</th>
                  <th style={{ width: 100 }}>Max attach</th>
                  <th style={{ width: 80 }} />
                </tr>
              </thead>
              <tbody>
                {configs.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div style={{ fontWeight: 500, color: '#F1F5F9' }}>
                        <Link to={`/emails/${c.id}/edit`} style={{ color: '#F1F5F9', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#FB923C')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#F1F5F9')}>
                          {c.name}
                        </Link>
                      </div>
                    </td>
                    <td style={{ color: '#94A3B8', fontSize: 12 }}>{providerName(c.provider_id)}</td>
                    <td className="mono" style={{ fontSize: 12, color: '#CBD5E1', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.subject}</td>
                    <td style={{ color: '#94A3B8', fontSize: 12 }}>{c.attachment_max_mb}MB</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                        <Link to={`/emails/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                        <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}>
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
