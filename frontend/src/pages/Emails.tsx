import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Pencil, Trash2 } from 'lucide-react'
import { getEmailConfigs, deleteEmailConfig, getEmailProviders } from '../lib/api'
import PageHeader from '../components/shared/PageHeader'
import EmptyState from '../components/shared/EmptyState'
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

  if (isLoading) return <div className="p-8 flex justify-center"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader title="Email Configs" subtitle={`${configs.length} configured`}
        action={<Link to="/emails/new" className="btn-primary"><Plus size={15}/> New Email Config</Link>} />

      {configs.length === 0 ? (
        <EmptyState message="No email configs yet." action={<Link to="/emails/new" className="btn-primary">Create email config</Link>} />
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-xs text-text-muted">
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Provider</th>
                <th className="text-left px-4 py-3">Subject</th>
                <th className="text-left px-4 py-3">Max attachment</th>
                <th className="px-4 py-3"/>
              </tr>
            </thead>
            <tbody>
              {configs.map(c => (
                <tr key={c.id} className="border-b border-border/50 last:border-0 hover:bg-surface2/50">
                  <td className="px-4 py-3">
                    <Link to={`/emails/${c.id}/edit`} className="font-medium text-text-primary hover:text-accent">{c.name}</Link>
                  </td>
                  <td className="px-4 py-3 text-text-muted text-xs">{providerName(c.provider_id)}</td>
                  <td className="px-4 py-3 text-text-muted text-xs truncate max-w-xs">{c.subject}</td>
                  <td className="px-4 py-3 text-text-muted text-xs">{c.attachment_max_mb}MB</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-end">
                      <Link to={`/emails/${c.id}/edit`} className="btn-ghost p-1.5"><Pencil size={14}/></Link>
                      <button className="btn-ghost p-1.5 hover:text-danger" onClick={() => window.confirm(`Delete "${c.name}"?`) && remove(c.id)}><Trash2 size={14}/></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
