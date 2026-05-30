import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Pencil, X } from 'lucide-react'
import {
  getDbConnections, getDbConnection, createDbConnection, updateDbConnection, deleteDbConnection, testDbConnection, testDbConnectionRaw,
  getEmailProviders, getEmailProvider, createEmailProvider, updateEmailProvider, deleteEmailProvider, testEmailProvider,
} from '../lib/api'
import { useCurrentUser } from '../lib/auth'
import StatusBadge from '../components/shared/StatusBadge'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'
import FieldTooltip from '../components/shared/FieldTooltip'

type Tab = 'db' | 'mail'

const DB_COLORS: Record<string, string> = { postgresql: '#3B82F6', oracle: '#EF4444', mysql: '#14B8A6', mssql: '#A855F7', odbc: '#6B7280' }
const DB_LABELS: Record<string, string>  = { postgresql: 'PostgreSQL', oracle: 'Oracle', mysql: 'MySQL', mssql: 'SQL Server', odbc: 'ODBC' }
const PROVIDER_LABELS: Record<string, string> = { gmail: 'Gmail', microsoft365: 'Microsoft 365', smtp: 'SMTP', sendgrid: 'SendGrid', ses: 'AWS SES', mailgun: 'Mailgun' }

function StatCol({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: 70 }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600, marginBottom: 3 }}>{label}</span>
      <span className="mono" style={{ fontSize: 12, color: 'var(--text-2)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

// ── modal state types ────────────────────────────────────────────────────────

type DbForm = {
  name: string; db_type: 'postgresql' | 'oracle' | 'mysql' | 'mssql' | 'odbc'
  host: string; port: string; database: string; username: string; password: string
  driver: string        // mssql only
  dsn: string           // odbc only
  connection_string: string  // odbc only
  is_default: boolean
}

type MailForm = {
  name: string; provider_type: 'gmail' | 'microsoft365' | 'smtp' | 'sendgrid' | 'ses' | 'mailgun'
  // smtp
  host: string; port: string; username: string; password: string
  use_tls: boolean
  // gmail/m365
  client_id: string; client_secret: string; refresh_token: string; sender: string
  tenant_id: string
  // sendgrid / mailgun / ses
  api_key: string; from_email: string; from_name: string
  // ses
  aws_access_key_id: string; aws_secret_access_key: string; aws_region: string
  // mailgun
  domain: string; region: string
  is_default: boolean
}

const emptyDb = (): DbForm => ({
  name: '', db_type: 'postgresql', host: 'localhost', port: '5432',
  database: '', username: '', password: '',
  driver: 'ODBC Driver 17 for SQL Server', dsn: '', connection_string: '',
  is_default: false,
})

const emptyMail = (): MailForm => ({
  name: '', provider_type: 'smtp', host: '', port: '587',
  username: '', password: '', use_tls: true,
  client_id: '', client_secret: '', refresh_token: '', sender: '', tenant_id: '',
  api_key: '', from_email: '', from_name: '',
  aws_access_key_id: '', aws_secret_access_key: '', aws_region: 'us-east-1',
  domain: '', region: 'us',
  is_default: false,
})

// ── helpers ──────────────────────────────────────────────────────────────────

function defaultDbPort(dbType: string): string {
  if (dbType === 'oracle') return '1521'
  if (dbType === 'mysql')  return '3306'
  if (dbType === 'mssql')  return '1433'
  return '5432'
}


function buildMailProviderConfig(form: MailForm): Record<string, unknown> {
  if (form.provider_type === 'smtp') {
    return { host: form.host, port: Number(form.port), username: form.username, password: form.password, use_tls: form.use_tls, sender: form.sender }
  }
  if (form.provider_type === 'gmail') {
    return { client_id: form.client_id, client_secret: form.client_secret, refresh_token: form.refresh_token, sender: form.sender }
  }
  if (form.provider_type === 'microsoft365') {
    return { tenant_id: form.tenant_id, client_id: form.client_id, client_secret: form.client_secret, sender: form.sender }
  }
  if (form.provider_type === 'sendgrid') {
    return { api_key: form.api_key, from_email: form.from_email, from_name: form.from_name }
  }
  if (form.provider_type === 'ses') {
    return { aws_access_key_id: form.aws_access_key_id, aws_secret_access_key: form.aws_secret_access_key, aws_region: form.aws_region, from_email: form.from_email, from_name: form.from_name }
  }
  if (form.provider_type === 'mailgun') {
    return { api_key: form.api_key, domain: form.domain, from_email: form.from_email, from_name: form.from_name, region: form.region }
  }
  return {}
}

function Field({ label, children, tooltip }: { label: string; children: React.ReactNode; tooltip?: React.ReactNode }) {
  return (
    <div className="field">
      <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{label}{tooltip}</label>
      {children}
    </div>
  )
}

// ── main component ───────────────────────────────────────────────────────────

export default function Connections() {
  const qc = useQueryClient()
  const me = useCurrentUser()
  const isAdmin = me?.role === 'admin'
  const [tab, setTab] = useState<Tab>('db')
  const [testStatuses, setTestStatuses] = useState<Record<string, 'testing' | 'ok' | 'fail'>>({})
  const [testErrors, setTestErrors]     = useState<Record<string, string>>({})
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

  function buildDbConfig(form: DbForm): Record<string, unknown> {
    if (form.db_type === 'odbc') {
      return { dsn: form.dsn, connection_string: form.connection_string }
    }
    const cfg: Record<string, unknown> = {
      host: form.host, port: Number(form.port),
      database: form.database, username: form.username, password: form.password,
    }
    if (form.db_type === 'mssql') cfg.driver = form.driver
    return cfg
  }

  function runModalTest() {
    setModalTest({ status: 'testing', msg: '' })
    testDbConnectionRaw(dbForm.db_type, buildDbConfig(dbForm))
      .then(r => setModalTest({ status: 'ok', msg: `Connected · ${r.latency_ms}ms` }))
      .catch(e => setModalTest({ status: 'fail', msg: e.message }))
  }

  function openEdit(id: string) {
    setEditId(id); setFormError(''); setModalTest({ status: 'idle', msg: '' }); setShowModal(true)
    if (tab === 'db') {
      getDbConnection(id).then(data => {
        const cfg = (data as any).config ?? {}
        const port = String(cfg.port ?? defaultDbPort(data.db_type))
        setDbForm({
          name: data.name, db_type: data.db_type as DbForm['db_type'],
          is_default: data.is_default,
          host: cfg.host ?? '', port, database: cfg.database ?? '',
          username: cfg.username ?? '', password: '***',
          driver: cfg.driver ?? 'ODBC Driver 17 for SQL Server',
          dsn: cfg.dsn ?? '', connection_string: cfg.connection_string ?? '',
        })
      }).catch(() => setFormError('Failed to load connection details'))
    } else {
      getEmailProvider(id).then(data => {
        const cfg = (data as any).config ?? {}
        setMailForm({
          name: data.name, provider_type: data.provider_type as MailForm['provider_type'],
          is_default: data.is_default, sender: cfg.sender ?? '',
          host: cfg.host ?? '', port: String(cfg.port ?? 587),
          username: cfg.username ?? '', password: '***', use_tls: cfg.use_tls ?? true,
          client_id: cfg.client_id ?? '', client_secret: '***',
          refresh_token: cfg.refresh_token ? '***' : '', tenant_id: cfg.tenant_id ?? '',
          api_key: cfg.api_key ? '***' : '', from_email: cfg.from_email ?? '',
          from_name: cfg.from_name ?? '',
          aws_access_key_id: cfg.aws_access_key_id ? '***' : '',
          aws_secret_access_key: cfg.aws_secret_access_key ? '***' : '',
          aws_region: cfg.aws_region ?? 'us-east-1',
          domain: cfg.domain ?? '', region: cfg.region ?? 'us',
        })
      }).catch(() => setFormError('Failed to load provider details'))
    }
  }

  function submitDb(e: React.FormEvent) {
    e.preventDefault(); setFormError('')
    const payload = {
      name: dbForm.name, db_type: dbForm.db_type, is_default: dbForm.is_default,
      config: buildDbConfig(dbForm),
    }
    if (editId) saveDb({ id: editId, data: payload })
    else addDb(payload)
  }

  function submitMail(e: React.FormEvent) {
    e.preventDefault(); setFormError('')
    const payload = { name: mailForm.name, provider_type: mailForm.provider_type, is_default: mailForm.is_default, config: buildMailProviderConfig(mailForm) }
    if (editId) saveMail({ id: editId, data: payload })
    else addMail(payload)
  }

  const testDb = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    setTestErrors(e => ({ ...e, [id]: '' }))
    testDbConnection(id)
      .then(() => setTestStatuses(s => ({ ...s, [id]: 'ok' })))
      .catch((err: Error) => {
        console.error('DB connection test failed:', err.message)
        setTestStatuses(s => ({ ...s, [id]: 'fail' }))
        setTestErrors(e => ({ ...e, [id]: err.message }))
      })
  }
  const testEmail = (id: string) => {
    setTestStatuses(s => ({ ...s, [id]: 'testing' }))
    setTestErrors(e => ({ ...e, [id]: '' }))
    testEmailProvider(id)
      .then(() => setTestStatuses(s => ({ ...s, [id]: 'ok' })))
      .catch((err: Error) => {
        console.error('Email provider test failed:', err.message)
        setTestStatuses(s => ({ ...s, [id]: 'fail' }))
        setTestErrors(e => ({ ...e, [id]: err.message }))
      })
  }

  const TABS = [
    { id: 'db' as Tab,   label: 'Databases',      count: dbConns.length },
    { id: 'mail' as Tab, label: 'Email Providers', count: providers.length },
  ]

  const submitting = addingDb || addingMail || savingDb || savingMail

  const TEST_STYLES = {
    ok: {
      bg: 'rgba(34,197,94,0.08)',
      border: 'rgba(34,197,94,0.3)',
      color: 'var(--success-text)',
      dot: 'var(--success-text)',
    },
    fail: {
      bg: 'rgba(239,68,68,0.08)',
      border: 'rgba(239,68,68,0.2)',
      color: 'var(--failure-text)',
      dot: 'var(--failure)',
    },
    idle: {
      bg: 'var(--surface-2)',
      border: 'var(--border)',
      color: 'var(--text-3)',
      dot: 'var(--text-muted)',
    },
  }
  const testStyleKey = (modalTest.status === 'ok' || modalTest.status === 'fail') ? modalTest.status : 'idle'
  const testStyles = TEST_STYLES[testStyleKey]

  const testBg     = testStyles.bg
  const testBorder = testStyles.border
  const testColor  = testStyles.color
  const dotBg      = testStyles.dot

  return (
    <>
      <TopBar
        crumbs={['Workspace', 'Connections']}
        helpTopic="connections"
        actions={isAdmin ? <button className="btn btn-primary btn-sm" onClick={openModal}><Plus size={13} /> Add Connection</button> : undefined}
      />

      <div className="scroll">
        <PageIntro page="connections" />
        <div className="page-h">
          <div>
            <h1>Connections</h1>
            <p>Manage data sources and email providers · credentials are encrypted at rest</p>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                background: 'transparent', border: 'none',
                color: active ? 'var(--accent)' : 'var(--text-3)',
                padding: '10px 16px', fontSize: 13,
                fontWeight: active ? 600 : 500,
                cursor: 'pointer',
                borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                marginBottom: -1,
                display: 'flex', alignItems: 'center', gap: 8,
                fontFamily: 'inherit',
              }}>
                {t.label}
                <span style={{ fontSize: 10.5, color: active ? 'var(--accent-h)' : 'var(--text-muted)', background: active ? 'var(--accent-soft)' : 'var(--surface-2)', padding: '1px 6px', borderRadius: 999, fontFamily: 'var(--font-mono)' }}>
                  {t.count}
                </span>
              </button>
            )
          })}
        </div>

        {/* DB connections */}
        {tab === 'db' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {dbLoading && [0,1,2].map(i => (
              <div key={i} className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <Sk h={14} style={{ width: 160 }} />
                      <Sk h={14} r={4} style={{ width: 70 }} />
                    </div>
                    <Sk h={11} style={{ width: 130 }} />
                  </div>
                  <div style={{ display: 'flex', gap: 24, flexShrink: 0 }}>
                    {[55, 30].map(w => (
                      <div key={w} style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 70 }}>
                        <Sk h={10} style={{ width: 40 }} />
                        <Sk h={12} style={{ width: w }} />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <Sk h={28} r={6} style={{ width: 62 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                  </div>
                </div>
              </div>
            ))}
            {dbConns.map(c => {
              const color = DB_COLORS[c.db_type] ?? 'var(--text-muted)'
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
                        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{c.name}</span>
                        <span className="mono" style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 4, background: 'var(--surface-2)', color: 'var(--text-3)' }}>{label}</span>
                        {ts === 'ok'   && <StatusBadge status="success" label="Healthy" />}
                        {ts === 'fail' && <StatusBadge status="failed"  label="Unreachable" />}
                      </div>
                      <div className="mono" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{c.db_type} · {c.is_default ? 'default' : 'not default'}</div>
                      {ts === 'fail' && testErrors[c.id] && (
                        <div className="mono" style={{ fontSize: 11, color: 'var(--failure)', marginTop: 4, wordBreak: 'break-all' }}>{testErrors[c.id]}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
                      <StatCol label="Type"    value={label} />
                      <StatCol label="Default" value={c.is_default ? 'Yes' : 'No'} />
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button className="btn btn-sm" onClick={() => testDb(c.id)} disabled={ts === 'testing'}>
                        {ts === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: ts === 'ok' ? 'var(--success-text)' : 'var(--text-muted)' }} />}
                        Test
                      </button>
                      {isAdmin && (
                        <>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => openEdit(c.id)}><Pencil size={12} /></button>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => globalThis.confirm(`Delete "${c.name}"?`) && removeDb(c.id)}>
                            <Trash2 size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            {!dbLoading && dbConns.length === 0 && (
              <div className="card ff-empty">
                <p className="msg">No database connections yet.</p>
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>Add a PostgreSQL or Oracle connection. Credentials are encrypted at rest with AES-256.</p>
                {isAdmin && <button className="btn btn-primary btn-sm" onClick={openModal}>Add connection</button>}
              </div>
            )}
          </div>
        )}

        {/* Email providers */}
        {tab === 'mail' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {mailLoading && [0,1,2].map(i => (
              <div key={i} className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <Sk h={14} style={{ width: 160 }} />
                      <Sk h={14} r={4} style={{ width: 80 }} />
                    </div>
                    <Sk h={11} style={{ width: 130 }} />
                  </div>
                  <div style={{ display: 'flex', gap: 24, flexShrink: 0 }}>
                    {[70, 30].map(w => (
                      <div key={w} style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 70 }}>
                        <Sk h={10} style={{ width: 40 }} />
                        <Sk h={12} style={{ width: w }} />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <Sk h={28} r={6} style={{ width: 62 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                  </div>
                </div>
              </div>
            ))}
            {providers.map(p => {
              const ts = testStatuses[p.id]
              return (
                <div key={p.id} className="card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 9, background: 'rgba(249,115,22,0.14)', border: '1px solid rgba(249,115,22,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-text)', flexShrink: 0 }}>
                      <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>
                      </svg>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{p.name}</span>
                        <span className="mono" style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 4, background: 'var(--surface-2)', color: 'var(--text-3)' }}>{PROVIDER_LABELS[p.provider_type] ?? p.provider_type}</span>
                        {ts === 'ok'   && <StatusBadge status="success" label="Verified" />}
                        {ts === 'fail' && <StatusBadge status="failed"  label="Failed" />}
                      </div>
                      <div className="mono" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{PROVIDER_LABELS[p.provider_type] ?? p.provider_type} · {p.is_default ? 'default' : 'not default'}</div>
                      {ts === 'fail' && testErrors[p.id] && (
                        <div className="mono" style={{ fontSize: 11, color: 'var(--failure)', marginTop: 4, wordBreak: 'break-all' }}>{testErrors[p.id]}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
                      <StatCol label="Type"    value={p.provider_type} />
                      <StatCol label="Default" value={p.is_default ? 'Yes' : 'No'} />
                    </div>
                    <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                      <button className="btn btn-sm" onClick={() => testEmail(p.id)} disabled={ts === 'testing'}>
                        {ts === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: ts === 'ok' ? 'var(--success-text)' : 'var(--text-muted)' }} />}
                        Test
                      </button>
                      {isAdmin && (
                        <>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => openEdit(p.id)}><Pencil size={12} /></button>
                          <button className="btn btn-sm btn-ghost btn-icon" onClick={() => globalThis.confirm(`Delete "${p.name}"?`) && removeEmail(p.id)}>
                            <Trash2 size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
            {!mailLoading && providers.length === 0 && (
              <div className="card ff-empty">
                <p className="msg">No email providers configured yet.</p>
                <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '0 0 14px' }}>Add a Gmail, Microsoft 365, or SMTP provider. One provider can be shared across many email configs.</p>
                {isAdmin && <button className="btn btn-primary btn-sm" onClick={openModal}>Add email provider</button>}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Add Connection Modal ─────────────────────────────────────────── */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: 16 }}
          role="presentation"
          onClick={e => { if (e.target === e.currentTarget) closeModal() }}
          onKeyDown={e => { if (e.key === 'Escape') closeModal() }}>
          <div className="card" style={{ width: '100%', maxWidth: 480, maxHeight: '90vh', overflow: 'auto', padding: '24px 24px 20px' }}>

            {/* Header + type tabs */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>{editId ? 'Edit Connection' : 'Add Connection'}</h2>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={15} /></button>
            </div>

            {/* DB / Email toggle */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
              {(['db', 'mail'] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)} className="btn btn-sm" style={{
                  background: tab === t ? 'rgba(249,115,22,0.15)' : 'transparent',
                  color: tab === t ? 'var(--accent)' : 'var(--text-3)',
                  border: `1px solid ${tab === t ? 'rgba(249,115,22,0.4)' : 'var(--border)'}`,
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
                  <select className="input" value={dbForm.db_type} onChange={e => {
                    const t = e.target.value as DbForm['db_type']
                    setDbForm(f => ({ ...f, db_type: t, port: defaultDbPort(t) }))
                  }}>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="oracle">Oracle</option>
                    <option value="mysql">MySQL / MariaDB</option>
                    <option value="mssql">SQL Server (MSSQL)</option>
                    <option value="odbc">Generic ODBC</option>
                  </select>
                </Field>

                {/* ODBC-specific fields */}
                {dbForm.db_type === 'odbc' ? (
                  <>
                    <Field label="DSN (Data Source Name)" tooltip={<FieldTooltip field="db_host_port" />}>
                      <input className="input" value={dbForm.dsn}
                        onChange={e => setDbForm(f => ({ ...f, dsn: e.target.value }))}
                        placeholder="my_dsn  (leave blank to use connection string)" />
                    </Field>
                    <Field label="Connection String">
                      <input className="input" value={dbForm.connection_string}
                        onChange={e => setDbForm(f => ({ ...f, connection_string: e.target.value }))}
                        placeholder='Driver={...};Server=...;Database=...;UID=...;PWD=...' />
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                        DSN takes precedence if both are set.
                      </span>
                    </Field>
                  </>
                ) : (
                  <>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 10 }}>
                      <Field label="Host" tooltip={<FieldTooltip field={dbForm.db_type === 'oracle' ? 'oracle_connection' : 'db_host_port'} />}>
                        <input className="input" value={dbForm.host} onChange={e => setDbForm(f => ({ ...f, host: e.target.value }))} placeholder="localhost" required />
                      </Field>
                      <Field label="Port">
                        <input className="input" type="number" value={dbForm.port} onChange={e => setDbForm(f => ({ ...f, port: e.target.value }))} required />
                      </Field>
                    </div>

                    <Field label={dbForm.db_type === 'oracle' ? 'Service Name' : 'Database'}>
                      <input className="input" value={dbForm.database} onChange={e => setDbForm(f => ({ ...f, database: e.target.value }))}
                        placeholder={dbForm.db_type === 'oracle' ? 'ORCL' : 'mydb'} required />
                    </Field>

                    {dbForm.db_type === 'mssql' && (
                      <Field label="ODBC Driver">
                        <input className="input" value={dbForm.driver}
                          onChange={e => setDbForm(f => ({ ...f, driver: e.target.value }))}
                          placeholder="ODBC Driver 17 for SQL Server" />
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                          Install: <code style={{ color: 'var(--text-3)' }}>msodbcsql17</code> or <code style={{ color: 'var(--text-3)' }}>msodbcsql18</code>
                        </span>
                      </Field>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <Field label="Username">
                        <input className="input" value={dbForm.username} onChange={e => setDbForm(f => ({ ...f, username: e.target.value }))} required />
                      </Field>
                      <Field label="Password">
                        <input className="input" type="password" value={dbForm.password} onChange={e => setDbForm(f => ({ ...f, password: e.target.value }))} />
                      </Field>
                    </div>
                  </>
                )}

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-3)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={dbForm.is_default} onChange={e => setDbForm(f => ({ ...f, is_default: e.target.checked }))} />{' '}
                  Set as default connection
                </label>

                {formError && <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>{formError}</div>}

                {modalTest.status !== 'idle' && (
                  <div style={{ fontSize: 12, padding: '7px 12px', borderRadius: 6, background: testBg, border: `1px solid ${testBorder}`, color: testColor }}>
                    {modalTest.status === 'testing' ? 'Testing connection…' : modalTest.msg}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
                  <button type="button" className="btn btn-sm" onClick={closeModal}>Cancel</button>
                  <button type="button" className="btn btn-sm" onClick={runModalTest} disabled={modalTest.status === 'testing'}>
                    {modalTest.status === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotBg }} />}
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
                    <option value="sendgrid">SendGrid</option>
                    <option value="ses">AWS SES</option>
                    <option value="mailgun">Mailgun</option>
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
                    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-3)', cursor: 'pointer' }}>
                      <input type="checkbox" checked={mailForm.use_tls} onChange={e => setMailForm(f => ({ ...f, use_tls: e.target.checked }))} />{' '}
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
                    {mailForm.provider_type === 'gmail' && (
                      <Field label="Refresh Token">
                        <input className="input" type="password" value={mailForm.refresh_token} onChange={e => setMailForm(f => ({ ...f, refresh_token: e.target.value }))}
                          placeholder="Paste refresh token from OAuth2 setup" required />
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                          Run <code style={{ color: 'var(--text-3)' }}>flowforge setup gmail</code> in the terminal to generate this token.
                        </span>
                      </Field>
                    )}
                  </>
                )}

                {/* SendGrid */}
                {mailForm.provider_type === 'sendgrid' && (
                  <>
                    <Field label="API Key">
                      <input className="input" type="password" value={mailForm.api_key} onChange={e => setMailForm(f => ({ ...f, api_key: e.target.value }))} required />
                    </Field>
                    <Field label="From Email">
                      <input className="input" type="email" value={mailForm.from_email} onChange={e => setMailForm(f => ({ ...f, from_email: e.target.value }))} required />
                    </Field>
                    <Field label="From Name (optional)">
                      <input className="input" value={mailForm.from_name} onChange={e => setMailForm(f => ({ ...f, from_name: e.target.value }))} />
                    </Field>
                  </>
                )}

                {/* AWS SES */}
                {mailForm.provider_type === 'ses' && (
                  <>
                    <Field label="AWS Access Key ID">
                      <input className="input mono-input" value={mailForm.aws_access_key_id} onChange={e => setMailForm(f => ({ ...f, aws_access_key_id: e.target.value }))} required />
                    </Field>
                    <Field label="AWS Secret Access Key">
                      <input className="input" type="password" value={mailForm.aws_secret_access_key} onChange={e => setMailForm(f => ({ ...f, aws_secret_access_key: e.target.value }))} required />
                    </Field>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                      <Field label="AWS Region">
                        <input className="input mono-input" value={mailForm.aws_region} onChange={e => setMailForm(f => ({ ...f, aws_region: e.target.value }))} placeholder="us-east-1" required />
                      </Field>
                      <Field label="From Email">
                        <input className="input" type="email" value={mailForm.from_email} onChange={e => setMailForm(f => ({ ...f, from_email: e.target.value }))} required />
                      </Field>
                    </div>
                    <Field label="From Name (optional)">
                      <input className="input" value={mailForm.from_name} onChange={e => setMailForm(f => ({ ...f, from_name: e.target.value }))} />
                    </Field>
                  </>
                )}

                {/* Mailgun */}
                {mailForm.provider_type === 'mailgun' && (
                  <>
                    <Field label="API Key">
                      <input className="input" type="password" value={mailForm.api_key} onChange={e => setMailForm(f => ({ ...f, api_key: e.target.value }))} required />
                    </Field>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10 }}>
                      <Field label="Domain">
                        <input className="input mono-input" value={mailForm.domain} onChange={e => setMailForm(f => ({ ...f, domain: e.target.value }))} placeholder="mg.yourdomain.com" required />
                      </Field>
                      <Field label="Region">
                        <select className="input" value={mailForm.region} onChange={e => setMailForm(f => ({ ...f, region: e.target.value }))} style={{ height: 34 }}>
                          <option value="us">US</option>
                          <option value="eu">EU</option>
                        </select>
                      </Field>
                    </div>
                    <Field label="From Email">
                      <input className="input" type="email" value={mailForm.from_email} onChange={e => setMailForm(f => ({ ...f, from_email: e.target.value }))} required />
                    </Field>
                    <Field label="From Name (optional)">
                      <input className="input" value={mailForm.from_name} onChange={e => setMailForm(f => ({ ...f, from_name: e.target.value }))} />
                    </Field>
                  </>
                )}

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-3)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={mailForm.is_default} onChange={e => setMailForm(f => ({ ...f, is_default: e.target.checked }))} />{' '}
                  Set as default provider
                </label>

                {formError && <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>{formError}</div>}

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
