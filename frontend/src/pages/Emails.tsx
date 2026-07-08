import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getEmailConfigs, deleteEmailConfig, getEmailProviders } from '../lib/api'
import { useProjectStore } from '../lib/store'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import PageIntro from '../components/shared/PageIntro'
import Sk from '../components/shared/Skeleton'

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
    <>
      <TopBar crumbs={['Workspace', 'Email Templates']} />
      <div className="scroll">
        <div className="page-h">
          <div className="flex flex-col gap-2">
            <Sk h={28} r={6} style={{ width: 200 }} />
            <Sk h={14} style={{ width: 80 }} />
          </div>
        </div>
        <div className="card !p-0 overflow-hidden">
          <table className="tbl">
            <thead>
              <tr>
                <th>Name</th>
                <th className="w-[140px]">Provider</th>
                <th>Subject</th>
                <th className="w-[100px]">Max attach</th>
                <th className="w-20" />
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }, (_, i) => i).map(n => (
                <tr key={'sk-' + n}>
                  <td><Sk h={14} style={{ width: '55%' }} /></td>
                  <td><Sk h={12} style={{ width: 90 }} /></td>
                  <td><Sk h={12} style={{ width: '70%' }} /></td>
                  <td><Sk h={12} style={{ width: 50 }} /></td>
                  <td><Sk h={24} r={4} style={{ width: 24, marginLeft: 'auto' }} /></td>
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
            <p className="text-[12.5px] text-text-muted m-0 mb-3.5">An email config stores the subject, body, and recipients for a type of email. You'll also need an Email Provider (Gmail/M365/SMTP) set up under Connections.</p>
            <div className="flex gap-2.5">
              {canEdit && <Link to="/emails/new" className="btn btn-primary">Create email config</Link>}
              <Link to="/connections" className="btn btn-sm">Set up email provider →</Link>
            </div>
          </div>
        ) : (
          <div className="card !p-0 overflow-hidden">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th className="w-[140px]">Provider</th>
                  <th>Subject</th>
                  <th className="w-[100px]">Max attach</th>
                  <th className="w-20" />
                </tr>
              </thead>
              <tbody>
                {configs.map(c => (
                  <tr key={c.id}>
                    <td>
                      <div className="font-medium text-text-primary">
                        <Link to={`/emails/${c.id}/edit`} className="text-text-primary no-underline hover:!text-accent-text">
                          {c.name}
                        </Link>
                      </div>
                    </td>
                    <td className="!text-text-3 text-xs">{providerName(c.provider_id)}</td>
                    <td className="mono text-xs max-w-[320px] overflow-hidden text-ellipsis whitespace-nowrap">{c.subject}</td>
                    <td className="!text-text-3 text-xs">{c.attachment_max_mb}MB</td>
                    {canEdit && (
                      <td>
                        <div className="flex gap-1 justify-end">
                          <Link to={`/emails/${c.id}/edit`} className="btn btn-sm btn-ghost btn-icon"><Pencil size={12} /></Link>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => globalThis.confirm(`Delete "${c.name}"?`) && remove(c.id)}>
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
