import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getEmailConfigs, deleteEmailConfig, getEmailProviders } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'

export default function Emails() {
  const qc = useQueryClient()
  const { activeProjectId } = useProjectStore()
  const me = useCurrentUser()
  const canEdit = me?.role !== 'viewer'
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['email-configs', activeProjectId],
    queryFn: () => getEmailConfigs(activeProjectId ? { project_id: activeProjectId } : undefined),
  })
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
        helpTopic="emails"
        actions={canEdit ? <Link to="/emails/new" className="btn btn-primary btn-sm"><Plus size={13} /> New Email Config</Link> : undefined}
      />
      <div className="scroll">
        <PageIntro page="emails" />
        <div className="page-h">
          <div>
            <h1>Email Templates</h1>
            <p>{configs.length} config{configs.length !== 1 ? 's' : ''}</p>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="card ff-empty">
            <p className="msg">No email configs yet.</p>
            <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>An email config stores the subject, body, and recipients for a type of email. You'll also need an Email Provider (Gmail/M365/SMTP) set up under Connections.</p>
            <div style={{ display: 'flex', gap: 10 }}>
              {canEdit && <Link to="/emails/new" className="btn btn-primary">Create email config</Link>}
              <Link to="/connections" className="btn btn-sm">Set up email provider →</Link>
            </div>
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
                      <div style={{ fontWeight: 500, color: 'var(--text)' }}>
                        <Link to={`/emails/${c.id}/edit`} style={{ color: 'var(--text)', textDecoration: 'none' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-text)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text)')}>
                          {c.name}
                        </Link>
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-3)', fontSize: 12 }}>{providerName(c.provider_id)}</td>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--text-2)', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.subject}</td>
                    <td style={{ color: 'var(--text-3)', fontSize: 12 }}>{c.attachment_max_mb}MB</td>
                    {canEdit && (
                      <td>
                        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                          <Link to={`/emails/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}>
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    )}
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
