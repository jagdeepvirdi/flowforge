import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Pencil, X } from 'lucide-react'
import {
  getDbConnections, getDbConnection, createDbConnection, updateDbConnection, deleteDbConnection, testDbConnection, testDbConnectionRaw,
  getEmailProviders, getEmailProvider, createEmailProvider, updateEmailProvider, deleteEmailProvider, testEmailProvider,
} from '../lib/api'

import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'

type Tab = 'db' | 'mail'

const DB_COLORS: Record<string, string> = { postgresql: '#3B82F6', oracle: '#EF4444', mysql: '#14B8A6' }
const DB_LABELS: Record<string, string>  = { postgresql: 'PostgreSQL', oracle: 'Oracle', mysql: 'MySQL' }

function StatCol({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 70 }}>
      <span style={{ fontSize: 10, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 3 }}>{label}</span>
      <span className="mono" style={{ fontSize: 12, color: '#CBD5E1', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

// ── modal state types ────────────────────────────────────────────────────────

type DbForm = {
  name: string; db_type: 'postgresql' | 'oracle'
  host: string; port: string; database: string; username: string; password: string
  is_default: boolean
}

type MailForm = {
  name: string; provider_type: 'gmail' | 'microsoft365' | 'smtp'
  // smtp
  host: string; port: string; username: string; password: string
  use_tls: boolean
  // gmail/m365
  client_id: string; client_secret: string; sender: string
  tenant_id: string
  is_default: boolean
}

const emptyDb = (): DbForm => ({
  name: '', db_type: 'postgresql', host: 'localhost', port: '5432',
  database: '', username: '', password: '', is_default: false,
})

const emptyMail = (): MailForm => ({
  name: '', provider_type: 'smtp', host: '', port: '587',
  username: '', password: '', use_tls: true,
  client_id: '', client_secret: '', sender: '', tenant_id: '',
  is_default: false,
})

// ── field helpers ────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  )
}

// ── main component ───────────────────────────────────────────────────────────

export default function Connections() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('db')
  const [testStatuses, setTestStatuses] = useState<Record<string, 'testing' | 'ok' | 'fail'>>({})
  const [showModal, setShowModal] = useState(false)
  const [editId, setEditId]       = useState<string | null>(null)
  const [dbForm, setDbForm]       = useState<DbForm>(emptyDb())
  const [mailForm, setMailForm]   = useState<MailForm>(emptyMail())
  const [formError, setFormError] = useState('')
  const [modalTest, setModalTest] = useState<{ status: 'idle' | 'testing' | 'ok' | 'fail'; msg: string }>({ status: 'idle', msg: '' })

  const { data: dbConns = [], isLoading: dbLoading }   = useQuery({ queryKey: ['db-connections'],  queryFn: getDbConnections })
  const { data: providers = [], isLoading: mailLoading } = useQuery({ queryKey: ['email-providers'], queryFn: getEmailProviders })

  const { mutate: removeDb }    = useMutation({ mutationFn: deleteDbConnection,  onSuccess: () => qc.invalidateQueries({ queryKey: ['db-connections'] }) })
  const { mutate: removeEmail } = useMutation({ mutationFn: deleteEmailProvider, onSuccess: () => qc.invalidateQueries({ queryKey: ['email-providers'] }) })

  const { mutate: addDb, isPending: addingDb } = useMutation({
    mutationFn: createDbConnection,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['db-connections'] }); closeModal() },
    onError: (e: Error) => setFormError(e.message),
  })
  const { mutate: saveDb, isPending: savingDb } = useMutation({
    mutationFn: ({ id, data }: { id: string; data: unknown }) => updateDbConnection(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['db-connections'] }); closeModal() },
    onError: (e: Error) => setFormError(e.message),
  })

  const { mutate: addMail, isPending: addingMail } = useMutation({
    mutationFn: createEmailProvider,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['email-providers'] }); closeModal() },
    onError: (e: Error) => setFormError(e.message),
  })
  const { mutate: saveMail, isPending: savingMail } = useMutation({
    mutationFn: ({ id, data }: { id: string; data: unknown }) => updateEmailProvider(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['email-providers'] }); closeModal() },
    onError: (e: Error) => setFormError(e.message),
  })

  function openModal() { setEditId(null); setDbForm(emptyDb()); setMailForm(emptyMail()); setFormError(''); setModalTest({ status: 'idle', msg: '' }); setShowModal(true) }
  function closeModal() { setShowModal(false); setEditId(null); setFormError(''); setModalTest({ status: 'idle', msg: '' }) }

  function runModalTest() {
    setModalTest({ status: 'testing', msg: '' })
    testDbConnectionRaw(dbForm.db_type, {
      host: dbForm.host, port: Number(dbForm.port),
      database: dbForm.database, username: dbForm.username, password: dbForm.password,
    }).then(r => setModalTest({ status: 'ok', msg: `Connected · ${r.latency_ms}ms` }))
      .catch(e => setModalTest({ status: 'fail', msg: e.message }))
  }

  function openEdit(id: string) {
    setEditId(id); setFormError(''); setModalTest({ status: 'idle', msg: '' }); setShowModal(true)
    if (tab === 'db') {
      getDbConnection(id).then(data => {
        const cfg = (data as any).config ?? {}
        setDbForm({ name: data.name, db_type: data.db_type as DbForm['db_type'], is_default: data.is_default,
          host: cfg.host ?? '', port: String(cfg.port ?? 5432), database: cfg.database ?? '',
          username: cfg.username ?? '', password: '***' })
      }).catch(() => setFormError('Failed to load connection details'))
    } else {
      getEmailProvider(id).then(data => {
        const cfg = (data as any).config ?? {}
        setMailForm({ name: data.name, provider_type: data.provider_type as MailForm['provider_type'],
          is_default: data.is_default, sender: cfg.sender ?? '',
          host: cfg.host ?? '', port: String(cfg.port ?? 587),
          username: cfg.username ?? '', password: '***', use_tls: cfg.use_tls ?? true,
          client_id: cfg.client_id ?? '', client_secret: '***', tenant_id: cfg.tenant_id ?? '' })
      }).catch(() => setFormError('Failed to load provider details'))
    }
  }

  function submitDb(e: React.FormEvent) {
    e.preventDefault(); setFormError('')
    const payload = {
      name: dbForm.name, db_type: dbForm.db_type, is_default: dbForm.is_default,
      config: { host: dbForm.host, port: Number(dbForm.port), database: dbForm.database,
                username: dbForm.username, password: dbForm.password },
    }
    if (editId) saveDb({ id: editId, data: payload })
    else addDb(payload)
  }

  function submitMail(e: React.FormEvent) {
    e.preventDefault(); setFormError('')
    const config: Record<string, unknown> = { sender: mailForm.sender }
    if (mailForm.provider_type === 'smtp') {
      Object.assign(config, { host: mailForm.host, port: Number(mailForm.port),
        username: mailForm.username, password: mailForm.password, use_tls: mailForm.use_tls })
    } else if (mailForm.provider_type === 'gmail') {
      Object.assign(config, { client_id: mailForm.client_id, client_secret: mailForm.client_secret })
    } else {
      Object.assign(config, { tenant_id: mailForm.tenant_id,
        client_id: mailForm.client_id, client_secret: mailForm.client_secret })
    }
    const payload = { name: mailForm.name, provider_type: mailForm.provider_type, is_default: mailForm.is_default, config }
    if (editId) saveMail({ id: editId, data: payload })
    else addMail(payload)
  }

  const testDb = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    testDbConnection(id)
      .then(() => setTestStatuses(s => ({ ...s, [id]: 'ok' })))
      .catch(() => setTestStatuses(s => ({ ...s, [id]: 'fail' })))
  }
  const testEmail = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    testEmailProvider(id)
      .then(() => setTestStatuses(s => ({ ...s, [id]: 'ok' })))
      .catch(() => setTestStatuses(s => ({ ...s, [id]: 'fail' })))
  }

  const TABS = [
    { id: 'db' as Tab,   label: 'Databases',      count: dbConns.length },
    { id: 'mail' as Tab, label: 'Email Providers', count: providers.length },
  ]

  const submitting = addingDb || addingMail || savingDb || savingMail

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Connections']}
        actions={<button className="btn btn-primary btn-sm" onClick={openModal}><Plus size={13} /> Add Connection</button>}
      />

      <div className="scroll">
        <div className="page-h">
          <div>
            <h1>Connections</h1>
            <p>Manage data sources and email providers · credentials are encrypted at rest</p>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #2D3143', marginBottom: 20 }}>
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                background: 'transparent', border: 'none',
                color: active ? '#F97316' : '#94A3B8',
                padding: '10px 16px', fontSize: 13,
                fontWeight: active ? 600 : 500,
                cursor: 'pointer',
                borderBottom: active ? '2px solid #F97316' : '2px solid transparent',
                marginBottom: -1,
                display: 'flex', alignItems: 'center', gap: 8,
                fontFamily: 'inherit',
              }}>
                {t.label}
                <span style={{ fontSize: 10.5, color: active ? '#FB923C' : '#64748B', background: active ? 'rgba(249,115,22,0.14)' : '#21252F', padding: '1px 6px', borderRadius: 999, fontFamily: 'JetBrains Mono, monospace' }}>
                  {t.count}
                </span>
              </button>
            )
          })}
        </div>

        {/* DB connections */}
        {tab === 'db' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {dbLoading && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>}
            {dbConns.map(c => {
              const color = DB_COLORS[c.db_type] ?? '#64748B'
              const label = DB_LABELS[c.db_type] ?? c.db_type
              const ts = testStatuses[c.id]
              return (
                <div key={c.id} className="card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 9, background: `${color}22`, border: `1px solid ${color}55`, display: 'flex', alignItems: 'center', justifyContent: 'center', color, flexShrink: 0 }}>
                      <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                        <ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>
                      </svg>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9' }}>{c.name}</span>
                        <span className="mono" style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 4, background: '#21252F', color: '#94A3B8' }}>{label}</span>
                        {ts === 'ok'   && <StatusBadge status="success" label="Healthy" />}
                        {ts === 'fail' && <StatusBadge status="failed"  label="Unreachable" />}
                      </div>
                      <div className="mono" style={{ fontSize: 11.5, color: '#64748B' }}>{c.db_type} · {c.is_default ? 'default' : 'not default'}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
                      <StatCol label="Type"    value={label} />
                      <StatCol label="Default" value={c.is_default ? 'Yes' : 'No'} />
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button className="btn btn-sm" onClick={() => testDb(c.id)} disabled={ts === 'testing'}>
                        {ts === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: ts === 'ok' ? '#4ADE80' : '#64748B' }} />}
                        Test
                      </button>
                      <button className="btn btn-sm btn-ghost btn-icon" onClick={() => openEdit(c.id)}><Pencil size={12} /></button>
                      <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${c.name}"?`) && removeDb(c.id)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
            {!dbLoading && dbConns.length === 0 && (
              <div className="card ff-empty"><p className="msg">No database connections yet.</p></div>
            )}
          </div>
        )}

        {/* Email providers */}
        {tab === 'mail' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {mailLoading && <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Spinner /></div>}
            {providers.map(p => {
              const ts = testStatuses[p.id]
              return (
                <div key={p.id} className="card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 9, background: 'rgba(249,115,22,0.14)', border: '1px solid rgba(249,115,22,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#FB923C', flexShrink: 0 }}>
                      <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>
                      </svg>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9' }}>{p.name}</span>
                        <span className="mono" style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 4, background: '#21252F', color: '#94A3B8' }}>{p.provider_type}</span>
                        {ts === 'ok'   && <StatusBadge status="success" label="Verified" />}
                        {ts === 'fail' && <StatusBadge status="failed"  label="Failed" />}
                      </div>
                      <div className="mono" style={{ fontSize: 11.5, color: '#64748B' }}>{p.provider_type} · {p.is_default ? 'default' : 'not default'}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
                      <StatCol label="Type"    value={p.provider_type} />
                      <StatCol label="Default" value={p.is_default ? 'Yes' : 'No'} />
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button className="btn btn-sm" onClick={() => testEmail(p.id)} disabled={ts === 'testing'}>
                        {ts === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: ts === 'ok' ? '#4ADE80' : '#64748B' }} />}
                        Test
                      </button>
                      <button className="btn btn-sm btn-ghost btn-icon" onClick={() => openEdit(p.id)}><Pencil size={12} /></button>
                      <button className="btn btn-sm btn-ghost btn-icon" onClick={() => window.confirm(`Delete "${p.name}"?`) && removeEmail(p.id)}>
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
            {!mailLoading && providers.length === 0 && (
              <div className="card ff-empty"><p className="msg">No email providers configured yet.</p></div>
            )}
          </div>
        )}
      </div>

      {/* ── Add Connection Modal ─────────────────────────────────────────── */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: 16 }}
          onClick={e => { if (e.target === e.currentTarget) closeModal() }}>
          <div className="card" style={{ width: '100%', maxWidth: 480, maxHeight: '90vh', overflow: 'auto', padding: '24px 24px 20px' }}>

            {/* Header + type tabs */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#F1F5F9' }}>{editId ? 'Edit Connection' : 'Add Connection'}</h2>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={15} /></button>
            </div>

            {/* DB / Email toggle */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {(['db', 'mail'] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)} className="btn btn-sm" style={{
                  background: tab === t ? 'rgba(249,115,22,0.15)' : 'transparent',
                  color: tab === t ? '#F97316' : '#94A3B8',
                  border: `1px solid ${tab === t ? 'rgba(249,115,22,0.4)' : '#2D3143'}`,
                }}>
                  {t === 'db' ? 'Database' : 'Email Provider'}
                </button>
              ))}
            </div>

            {/* DB form */}
            {tab === 'db' && (
              <form onSubmit={submitDb} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Field label="Name">
                  <input className="input" value={dbForm.name} onChange={e => setDbForm(f => ({ ...f, name: e.target.value }))} placeholder="Production DB" required />
                </Field>

                <Field label="Type">
                  <select className="input" value={dbForm.db_type} onChange={e => setDbForm(f => ({ ...f, db_type: e.target.value as DbForm['db_type'] }))}>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="oracle">Oracle</option>
                  </select>
                </Field>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
                  <Field label="Host">
                    <input className="input" value={dbForm.host} onChange={e => setDbForm(f => ({ ...f, host: e.target.value }))} placeholder="localhost" required />
                  </Field>
                  <Field label="Port">
                    <input className="input" type="number" value={dbForm.port} onChange={e => setDbForm(f => ({ ...f, port: e.target.value }))} required />
                  </Field>
                </div>

                <Field label="Database">
                  <input className="input" value={dbForm.database} onChange={e => setDbForm(f => ({ ...f, database: e.target.value }))} placeholder="mydb" required />
                </Field>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <Field label="Username">
                    <input className="input" value={dbForm.username} onChange={e => setDbForm(f => ({ ...f, username: e.target.value }))} required />
                  </Field>
                  <Field label="Password">
                    <input className="input" type="password" value={dbForm.password} onChange={e => setDbForm(f => ({ ...f, password: e.target.value }))} />
                  </Field>
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#94A3B8', cursor: 'pointer' }}>
                  <input type="checkbox" checked={dbForm.is_default} onChange={e => setDbForm(f => ({ ...f, is_default: e.target.checked }))} />
                  Set as default connection
                </label>

                {formError && <div style={{ fontSize: 12.5, color: '#F87171', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>{formError}</div>}

                {modalTest.status !== 'idle' && (
                  <div style={{ fontSize: 12, padding: '7px 12px', borderRadius: 6, background: modalTest.status === 'ok' ? 'rgba(34,197,94,0.08)' : modalTest.status === 'fail' ? 'rgba(239,68,68,0.08)' : '#21252F', border: `1px solid ${modalTest.status === 'ok' ? 'rgba(34,197,94,0.3)' : modalTest.status === 'fail' ? 'rgba(239,68,68,0.2)' : '#2D3143'}`, color: modalTest.status === 'ok' ? '#4ADE80' : modalTest.status === 'fail' ? '#F87171' : '#94A3B8' }}>
                    {modalTest.status === 'testing' ? 'Testing connection…' : modalTest.msg}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
                  <button type="button" className="btn btn-sm" onClick={closeModal}>Cancel</button>
                  <button type="button" className="btn btn-sm" onClick={runModalTest} disabled={modalTest.status === 'testing'}>
                    {modalTest.status === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: modalTest.status === 'ok' ? '#4ADE80' : modalTest.status === 'fail' ? '#EF4444' : '#64748B' }} />}
                    Test
                  </button>
                  <button type="submit" className="btn btn-primary btn-sm" disabled={submitting}>
                    {submitting ? <Spinner size={11} /> : null} {editId ? 'Update Connection' : 'Save Connection'}
                  </button>
                </div>
              </form>
            )}

            {/* Email provider form */}
            {tab === 'mail' && (
              <form onSubmit={submitMail} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Field label="Name">
                  <input className="input" value={mailForm.name} onChange={e => setMailForm(f => ({ ...f, name: e.target.value }))} placeholder="Company Gmail" required />
                </Field>

                <Field label="Provider">
                  <select className="input" value={mailForm.provider_type} onChange={e => setMailForm(f => ({ ...f, provider_type: e.target.value as MailForm['provider_type'] }))}>
                    <option value="smtp">SMTP (Generic)</option>
                    <option value="gmail">Gmail (OAuth2)</option>
                    <option value="microsoft365">Microsoft 365 (OAuth2)</option>
                  </select>
                </Field>

                <Field label="Sender Email">
                  <input className="input" type="email" value={mailForm.sender} onChange={e => setMailForm(f => ({ ...f, sender: e.target.value }))} placeholder="you@example.com" required />
                </Field>

                {mailForm.provider_type === 'smtp' && (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
                      <Field label="SMTP Host">
                        <input className="input" value={mailForm.host} onChange={e => setMailForm(f => ({ ...f, host: e.target.value }))} placeholder="smtp.gmail.com" required />
                      </Field>
                      <Field label="Port">
                        <input className="input" type="number" value={mailForm.port} onChange={e => setMailForm(f => ({ ...f, port: e.target.value }))} required />
                      </Field>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <Field label="Username">
                        <input className="input" value={mailForm.username} onChange={e => setMailForm(f => ({ ...f, username: e.target.value }))} />
                      </Field>
                      <Field label="Password">
                        <input className="input" type="password" value={mailForm.password} onChange={e => setMailForm(f => ({ ...f, password: e.target.value }))} />
                      </Field>
                    </div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#94A3B8', cursor: 'pointer' }}>
                      <input type="checkbox" checked={mailForm.use_tls} onChange={e => setMailForm(f => ({ ...f, use_tls: e.target.checked }))} />
                      Use TLS
                    </label>
                  </>
                )}

                {(mailForm.provider_type === 'gmail' || mailForm.provider_type === 'microsoft365') && (
                  <>
                    {mailForm.provider_type === 'microsoft365' && (
                      <Field label="Tenant ID">
                        <input className="input" value={mailForm.tenant_id} onChange={e => setMailForm(f => ({ ...f, tenant_id: e.target.value }))} placeholder="your-tenant-id" required />
                      </Field>
                    )}
                    <Field label="Client ID">
                      <input className="input" value={mailForm.client_id} onChange={e => setMailForm(f => ({ ...f, client_id: e.target.value }))} required />
                    </Field>
                    <Field label="Client Secret">
                      <input className="input" type="password" value={mailForm.client_secret} onChange={e => setMailForm(f => ({ ...f, client_secret: e.target.value }))} required />
                    </Field>
                  </>
                )}

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#94A3B8', cursor: 'pointer' }}>
                  <input type="checkbox" checked={mailForm.is_default} onChange={e => setMailForm(f => ({ ...f, is_default: e.target.checked }))} />
                  Set as default provider
                </label>

                {formError && <div style={{ fontSize: 12.5, color: '#F87171', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>{formError}</div>}

                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
                  <button type="button" className="btn btn-sm" onClick={closeModal}>Cancel</button>
                  <button type="submit" className="btn btn-primary btn-sm" disabled={submitting}>
                    {submitting ? <Spinner size={11} /> : null} {editId ? 'Update Provider' : 'Save Provider'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  )
}
