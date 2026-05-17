import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, CheckCircle, XCircle, Loader } from 'lucide-react'
import {
  getDbConnections, createDbConnection, deleteDbConnection, testDbConnection,
  getEmailProviders, createEmailProvider, deleteEmailProvider, testEmailProvider,
} from '../lib/api'
import type { DbType, ProviderType } from '../lib/types'
import PageHeader from '../components/shared/PageHeader'
import Spinner from '../components/shared/Spinner'

function DbConnectionForm({ onAdd }: { onAdd: (data: unknown) => void }) {
  const [name, setName]     = useState('')
  const [type, setType]     = useState<DbType>('postgresql')
  const [host, setHost]     = useState('')
  const [port, setPort]     = useState('5432')
  const [db, setDb]         = useState('')
  const [user, setUser]     = useState('')
  const [pass, setPass]     = useState('')
  const [open, setOpen]     = useState(false)

  const submit = () => {
    onAdd({ name, db_type: type, config: { host, port, database: db, user, password: pass } })
    setOpen(false); setName(''); setHost(''); setDb(''); setUser(''); setPass('')
  }

  if (!open) return <button className="btn-secondary text-sm" onClick={() => setOpen(true)}><Plus size={14}/> Add DB Connection</button>

  return (
    <div className="card border-accent/30 space-y-3 mt-3">
      <div className="grid grid-cols-2 gap-3">
        <div><label className="label">Name</label><input className="input" value={name} onChange={e => setName(e.target.value)}/></div>
        <div><label className="label">Type</label>
          <select className="input" value={type} onChange={e => setType(e.target.value as DbType)}>
            <option value="postgresql">PostgreSQL</option>
            <option value="oracle">Oracle</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2"><label className="label">Host</label><input className="input" value={host} onChange={e => setHost(e.target.value)}/></div>
        <div><label className="label">Port</label><input className="input" value={port} onChange={e => setPort(e.target.value)}/></div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div><label className="label">Database</label><input className="input" value={db} onChange={e => setDb(e.target.value)}/></div>
        <div><label className="label">User</label><input className="input" value={user} onChange={e => setUser(e.target.value)}/></div>
        <div><label className="label">Password</label><input className="input" type="password" value={pass} onChange={e => setPass(e.target.value)}/></div>
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={submit}>Add</button>
        <button className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  )
}

function EmailProviderForm({ onAdd }: { onAdd: (data: unknown) => void }) {
  const [name, setName]       = useState('')
  const [type, setType]       = useState<ProviderType>('smtp')
  const [fields, setFields]   = useState<Record<string, string>>({})
  const [open, setOpen]       = useState(false)
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setFields(f => ({ ...f, [k]: e.target.value }))

  const submit = () => {
    onAdd({ name, provider_type: type, config: fields })
    setOpen(false); setName(''); setFields({})
  }

  if (!open) return <button className="btn-secondary text-sm" onClick={() => setOpen(true)}><Plus size={14}/> Add Email Provider</button>

  return (
    <div className="card border-accent/30 space-y-3 mt-3">
      <div className="grid grid-cols-2 gap-3">
        <div><label className="label">Name</label><input className="input" value={name} onChange={e => setName(e.target.value)}/></div>
        <div><label className="label">Type</label>
          <select className="input" value={type} onChange={e => setType(e.target.value as ProviderType)}>
            <option value="smtp">SMTP</option>
            <option value="gmail">Gmail</option>
            <option value="microsoft365">Microsoft 365</option>
          </select>
        </div>
      </div>
      {type === 'smtp' && (
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Host</label><input className="input" value={fields.host ?? ''} onChange={set('host')}/></div>
          <div><label className="label">Port</label><input className="input" value={fields.port ?? '587'} onChange={set('port')}/></div>
          <div><label className="label">Username</label><input className="input" value={fields.username ?? ''} onChange={set('username')}/></div>
          <div><label className="label">Password</label><input className="input" type="password" value={fields.password ?? ''} onChange={set('password')}/></div>
        </div>
      )}
      {type === 'gmail' && (
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Client ID</label><input className="input" value={fields.client_id ?? ''} onChange={set('client_id')}/></div>
          <div><label className="label">Client Secret</label><input className="input" type="password" value={fields.client_secret ?? ''} onChange={set('client_secret')}/></div>
          <div><label className="label">Refresh Token</label><input className="input" type="password" value={fields.refresh_token ?? ''} onChange={set('refresh_token')}/></div>
          <div><label className="label">Sender email</label><input className="input" value={fields.sender ?? ''} onChange={set('sender')}/></div>
        </div>
      )}
      {type === 'microsoft365' && (
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Tenant ID</label><input className="input" value={fields.tenant_id ?? ''} onChange={set('tenant_id')}/></div>
          <div><label className="label">Client ID</label><input className="input" value={fields.client_id ?? ''} onChange={set('client_id')}/></div>
          <div><label className="label">Client Secret</label><input className="input" type="password" value={fields.client_secret ?? ''} onChange={set('client_secret')}/></div>
          <div><label className="label">Sender email</label><input className="input" value={fields.sender_email ?? ''} onChange={set('sender_email')}/></div>
        </div>
      )}
      <div className="flex gap-2">
        <button className="btn-primary" onClick={submit}>Add</button>
        <button className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </div>
  )
}

function TestResult({ result }: { result: { success: boolean; latency_ms?: number; error?: string } | null; testing: boolean }) {
  if (!result) return null
  return result.success
    ? <span className="text-success text-xs flex items-center gap-1"><CheckCircle size={12}/> OK{result.latency_ms != null ? ` (${result.latency_ms}ms)` : ''}</span>
    : <span className="text-danger text-xs flex items-center gap-1"><XCircle size={12}/> {result.error}</span>
}

export default function Connections() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<'db' | 'email'>('db')
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; latency_ms?: number; error?: string }>>({})
  const [testing, setTesting] = useState<Record<string, boolean>>({})

  const { data: dbConns = [], isLoading: dbLoading }   = useQuery({ queryKey: ['db-connections'], queryFn: getDbConnections })
  const { data: providers = [], isLoading: emailLoading } = useQuery({ queryKey: ['email-providers'], queryFn: getEmailProviders })

  const { mutate: addDb }       = useMutation({ mutationFn: createDbConnection,    onSuccess: () => qc.invalidateQueries({ queryKey: ['db-connections'] }) })
  const { mutate: removeDb }    = useMutation({ mutationFn: deleteDbConnection,    onSuccess: () => qc.invalidateQueries({ queryKey: ['db-connections'] }) })
  const { mutate: addEmail }    = useMutation({ mutationFn: createEmailProvider,   onSuccess: () => qc.invalidateQueries({ queryKey: ['email-providers'] }) })
  const { mutate: removeEmail } = useMutation({ mutationFn: deleteEmailProvider,   onSuccess: () => qc.invalidateQueries({ queryKey: ['email-providers'] }) })

  const testDb = (id: string) => {
    setTesting(t => ({ ...t, [id]: true }))
    testDbConnection(id)
      .then(result => setTestResults(r => ({ ...r, [id]: result })))
      .catch(e => setTestResults(r => ({ ...r, [id]: { success: false, error: String(e) } })))
      .finally(() => setTesting(t => ({ ...t, [id]: false })))
  }
  const testEmail = (id: string) => {
    setTesting(t => ({ ...t, [id]: true }))
    testEmailProvider(id)
      .then(result => setTestResults(r => ({ ...r, [id]: result })))
      .catch(e => setTestResults(r => ({ ...r, [id]: { success: false, error: String(e) } })))
      .finally(() => setTesting(t => ({ ...t, [id]: false })))
  }

  const isLoading = tab === 'db' ? dbLoading : emailLoading

  return (
    <div className="p-8">
      <PageHeader title="Connections" />

      <div className="flex gap-1 mb-6 border-b border-border">
        {(['db', 'email'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors ${tab === t ? 'border-accent text-accent' : 'border-transparent text-text-muted hover:text-text-primary'}`}>
            {t === 'db' ? 'DB Connections' : 'Email Providers'}
          </button>
        ))}
      </div>

      {isLoading ? <Spinner /> : (
        <>
          {tab === 'db' && (
            <>
              <div className="card overflow-hidden p-0 mb-4">
                <table className="w-full text-sm">
                  <thead className="border-b border-border">
                    <tr className="text-xs text-text-muted">
                      <th className="text-left px-4 py-3">Name</th>
                      <th className="text-left px-4 py-3">Type</th>
                      <th className="text-left px-4 py-3">Status</th>
                      <th className="px-4 py-3"/>
                    </tr>
                  </thead>
                  <tbody>
                    {dbConns.length === 0 && <tr><td colSpan={4} className="text-center py-6 text-text-muted">No connections.</td></tr>}
                    {dbConns.map(c => (
                      <tr key={c.id} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-3 font-medium text-text-primary">{c.name}</td>
                        <td className="px-4 py-3"><span className="badge-muted">{c.db_type}</span></td>
                        <td className="px-4 py-3">
                          {testing[c.id] ? <Loader size={13} className="animate-spin text-accent"/> : <TestResult result={testResults[c.id] ?? null} testing={!!testing[c.id]}/>}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 justify-end">
                            <button className="btn-secondary text-xs py-1" onClick={() => testDb(c.id)}>Test</button>
                            <button className="btn-ghost p-1.5 hover:text-danger" onClick={() => window.confirm(`Delete "${c.name}"?`) && removeDb(c.id)}><Trash2 size={14}/></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <DbConnectionForm onAdd={data => addDb(data)} />
            </>
          )}

          {tab === 'email' && (
            <>
              <div className="card overflow-hidden p-0 mb-4">
                <table className="w-full text-sm">
                  <thead className="border-b border-border">
                    <tr className="text-xs text-text-muted">
                      <th className="text-left px-4 py-3">Name</th>
                      <th className="text-left px-4 py-3">Type</th>
                      <th className="text-left px-4 py-3">Status</th>
                      <th className="px-4 py-3"/>
                    </tr>
                  </thead>
                  <tbody>
                    {providers.length === 0 && <tr><td colSpan={4} className="text-center py-6 text-text-muted">No providers.</td></tr>}
                    {providers.map(p => (
                      <tr key={p.id} className="border-b border-border/50 last:border-0">
                        <td className="px-4 py-3 font-medium text-text-primary">{p.name}</td>
                        <td className="px-4 py-3"><span className="badge-muted">{p.provider_type}</span></td>
                        <td className="px-4 py-3">
                          {testing[p.id] ? <Loader size={13} className="animate-spin text-accent"/> : <TestResult result={testResults[p.id] ?? null} testing={!!testing[p.id]}/>}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1 justify-end">
                            <button className="btn-secondary text-xs py-1" onClick={() => testEmail(p.id)}>Test</button>
                            <button className="btn-ghost p-1.5 hover:text-danger" onClick={() => window.confirm(`Delete "${p.name}"?`) && removeEmail(p.id)}><Trash2 size={14}/></button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <EmailProviderForm onAdd={data => addEmail(data)} />
            </>
          )}
        </>
      )}
    </div>
  )
}
