import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import {
  getDbConnections, getDbConnection, createDbConnection, updateDbConnection, deleteDbConnection, testDbConnection, testDbConnectionRaw,
  getEmailProviders, getEmailProvider, createEmailProvider, updateEmailProvider, deleteEmailProvider, testEmailProvider,
} from '../lib/api'
import { useCurrentUser } from '../lib/auth'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'
import Field from '../components/connections/Field'
import DbConnectionRow from '../components/connections/DbConnectionRow'
import EmailProviderRow from '../components/connections/EmailProviderRow'
import DbFieldsGeneric from '../components/connections/DbFieldsGeneric'
import DbFieldsOdbc from '../components/connections/DbFieldsOdbc'
import DbFieldsSnowflake from '../components/connections/DbFieldsSnowflake'
import DbFieldsBigQuery from '../components/connections/DbFieldsBigQuery'
import MailFieldsSmtp from '../components/connections/MailFieldsSmtp'
import MailFieldsOAuth from '../components/connections/MailFieldsOAuth'
import MailFieldsSendgrid from '../components/connections/MailFieldsSendgrid'
import MailFieldsSes from '../components/connections/MailFieldsSes'
import MailFieldsMailgun from '../components/connections/MailFieldsMailgun'
import {
  type DbForm, type MailForm,
  emptyDb, emptyMail, defaultDbPort, buildDbConfig, buildMailProviderConfig,
} from '../components/connections/types'

type Tab = 'db' | 'mail'

const TEST_CLS: Record<'ok' | 'fail' | 'idle', string> = {
  ok:   'bg-[rgba(34,197,94,0.08)] border-[rgba(34,197,94,0.3)] text-success-text',
  fail: 'bg-[rgba(239,68,68,0.08)] border-[rgba(239,68,68,0.2)] text-failure-text',
  idle: 'bg-surface2 border-border text-text-3',
}
const TEST_DOT_CLS: Record<'ok' | 'fail' | 'idle', string> = {
  ok: 'bg-success-text', fail: 'bg-failure', idle: 'bg-text-muted',
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
        const cfg = data.config ?? {}
        const str = (v: unknown, fallback = '') => v == null ? fallback : String(v)
        const port = str(cfg.port, defaultDbPort(data.db_type))
        setDbForm({
          name: data.name, db_type: data.db_type as DbForm['db_type'],
          is_default: data.is_default,
          host: str(cfg.host), port, database: str(cfg.database),
          username: str(cfg.username), password: '***',
          driver: str(cfg.driver, 'ODBC Driver 17 for SQL Server'),
          dsn: str(cfg.dsn), connection_string: str(cfg.connection_string),
          account: str(cfg.account), warehouse: str(cfg.warehouse),
          schema_name: str(cfg.schema), role: str(cfg.role),
          project_id: str(cfg.project_id), dataset: str(cfg.dataset),
          credentials_json: cfg.credentials_json ? '***' : '',
        })
      }).catch(() => setFormError('Failed to load connection details'))
    } else {
      getEmailProvider(id).then(data => {
        const cfg = data.config ?? {}
        const str = (v: unknown, fallback = '') => v == null ? fallback : String(v)
        setMailForm({
          name: data.name, provider_type: data.provider_type as MailForm['provider_type'],
          is_default: data.is_default, sender: str(cfg.sender),
          host: str(cfg.host), port: str(cfg.port, '587'),
          username: str(cfg.username), password: '***', use_tls: Boolean(cfg.use_tls ?? true), use_ssl: Boolean(cfg.use_ssl ?? false),
          client_id: str(cfg.client_id), client_secret: '***',
          refresh_token: cfg.refresh_token ? '***' : '', tenant_id: str(cfg.tenant_id),
          api_key: cfg.api_key ? '***' : '', from_email: str(cfg.from_email),
          from_name: str(cfg.from_name),
          aws_access_key_id: cfg.aws_access_key_id ? '***' : '',
          aws_secret_access_key: cfg.aws_secret_access_key ? '***' : '',
          aws_region: str(cfg.aws_region, 'us-east-1'),
          domain: str(cfg.domain), region: str(cfg.region, 'us'),
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

  const testStyleKey = (modalTest.status === 'ok' || modalTest.status === 'fail') ? modalTest.status : 'idle'
  const testCls = TEST_CLS[testStyleKey]
  const testDotCls = TEST_DOT_CLS[testStyleKey]

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
        <div className="flex border-b border-border mb-5">
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => setTab(t.id)} className={`bg-transparent border-none py-2.5 px-4 text-[13px] cursor-pointer -mb-px border-b-2 flex items-center gap-2 font-[inherit] ${active ? 'text-accent font-semibold border-b-accent' : 'text-text-3 font-medium border-b-transparent'}`}>
                {t.label}
                <span className={`text-[10.5px] py-px px-1.5 rounded-full font-mono ${active ? 'text-accent-hover bg-accent-soft' : 'text-text-muted bg-surface2'}`}>
                  {t.count}
                </span>
              </button>
            )
          })}
        </div>

        {/* DB connections */}
        {tab === 'db' && (
          <div className="flex flex-col gap-2.5">
            {dbLoading && [0,1,2].map(i => (
              <div key={i} className="card">
                <div className="flex items-center gap-3.5">
                  <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                  <div className="flex-1 flex flex-col gap-1.5">
                    <div className="flex gap-2.5 items-center">
                      <Sk h={14} style={{ width: 160 }} />
                      <Sk h={14} r={4} style={{ width: 70 }} />
                    </div>
                    <Sk h={11} style={{ width: 130 }} />
                  </div>
                  <div className="flex gap-6 shrink-0">
                    {[55, 30].map(w => (
                      <div key={w} className="flex flex-col gap-1 min-w-[70px]">
                        <Sk h={10} style={{ width: 40 }} />
                        <Sk h={12} style={{ width: w }} />
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <Sk h={28} r={6} style={{ width: 62 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                  </div>
                </div>
              </div>
            ))}
            {dbConns.map(c => (
              <DbConnectionRow
                key={c.id}
                conn={c}
                testStatus={testStatuses[c.id]}
                testError={testErrors[c.id]}
                isAdmin={isAdmin}
                onTest={() => testDb(c.id)}
                onEdit={() => openEdit(c.id)}
                onDelete={() => globalThis.confirm(`Delete "${c.name}"?`) && removeDb(c.id)}
              />
            ))}
            {!dbLoading && dbConns.length === 0 && (
              <div className="card ff-empty">
                <p className="msg">No database connections yet.</p>
                <p className="text-[12.5px] text-text-muted m-0 mb-3.5">Add a PostgreSQL or Oracle connection. Credentials are encrypted at rest with AES-256.</p>
                {isAdmin && <button className="btn btn-primary btn-sm" onClick={openModal}>Add connection</button>}
              </div>
            )}
          </div>
        )}

        {/* Email providers */}
        {tab === 'mail' && (
          <div className="flex flex-col gap-2.5">
            {mailLoading && [0,1,2].map(i => (
              <div key={i} className="card">
                <div className="flex items-center gap-3.5">
                  <Sk h={40} r={9} style={{ width: 40, flexShrink: 0 }} />
                  <div className="flex-1 flex flex-col gap-1.5">
                    <div className="flex gap-2.5 items-center">
                      <Sk h={14} style={{ width: 160 }} />
                      <Sk h={14} r={4} style={{ width: 80 }} />
                    </div>
                    <Sk h={11} style={{ width: 130 }} />
                  </div>
                  <div className="flex gap-6 shrink-0">
                    {[70, 30].map(w => (
                      <div key={w} className="flex flex-col gap-1 min-w-[70px]">
                        <Sk h={10} style={{ width: 40 }} />
                        <Sk h={12} style={{ width: w }} />
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <Sk h={28} r={6} style={{ width: 62 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                    <Sk h={28} r={6} style={{ width: 30 }} />
                  </div>
                </div>
              </div>
            ))}
            {providers.map(p => (
              <EmailProviderRow
                key={p.id}
                provider={p}
                testStatus={testStatuses[p.id]}
                testError={testErrors[p.id]}
                isAdmin={isAdmin}
                onTest={() => testEmail(p.id)}
                onEdit={() => openEdit(p.id)}
                onDelete={() => globalThis.confirm(`Delete "${p.name}"?`) && removeEmail(p.id)}
              />
            ))}
            {!mailLoading && providers.length === 0 && (
              <div className="card ff-empty">
                <p className="msg">No email providers configured yet.</p>
                <p className="text-[12.5px] text-text-muted m-0 mb-3.5">Add a Gmail, Microsoft 365, or SMTP provider. One provider can be shared across many email configs.</p>
                {isAdmin && <button className="btn btn-primary btn-sm" onClick={openModal}>Add email provider</button>}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Add Connection Modal ─────────────────────────────────────────── */}
      {showModal && (
        <div className="fixed inset-0 bg-[rgba(0,0,0,0.6)] flex items-center justify-center z-[100] p-4"
          role="presentation"
          onClick={e => { if (e.target === e.currentTarget) closeModal() }}
          onKeyDown={e => { if (e.key === 'Escape') closeModal() }}>
          <div className="card w-full max-w-[480px] max-h-[90vh] overflow-auto !pt-6 !px-6 !pb-5">

            {/* Header + type tabs */}
            <div className="flex items-center justify-between mb-5">
              <h2 className="m-0 text-[15px] font-semibold text-text-primary">{editId ? 'Edit Connection' : 'Add Connection'}</h2>
              <button className="btn btn-ghost btn-icon" onClick={closeModal}><X size={15} /></button>
            </div>

            {/* DB / Email toggle */}
            <div className="flex gap-2 mb-5">
              {(['db', 'mail'] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)} className={`btn btn-sm ${tab === t ? '!bg-[rgba(249,115,22,0.15)] !text-accent !border-[rgba(249,115,22,0.4)]' : '!bg-transparent !text-text-3'}`}>
                  {t === 'db' ? 'Database' : 'Email Provider'}
                </button>
              ))}
            </div>

            {/* DB form */}
            {tab === 'db' && (
              <form onSubmit={submitDb} className="flex flex-col gap-3.5">
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
                    <option value="redshift">Amazon Redshift</option>
                    <option value="snowflake">Snowflake</option>
                    <option value="bigquery">Google BigQuery</option>
                  </select>
                </Field>

                {dbForm.db_type === 'odbc' ? (
                  <DbFieldsOdbc form={dbForm} setForm={setDbForm} />
                ) : dbForm.db_type === 'snowflake' ? (
                  <DbFieldsSnowflake form={dbForm} setForm={setDbForm} />
                ) : dbForm.db_type === 'bigquery' ? (
                  <DbFieldsBigQuery form={dbForm} setForm={setDbForm} />
                ) : (
                  <DbFieldsGeneric form={dbForm} setForm={setDbForm} />
                )}

                <label className="flex items-center gap-2 text-[13px] text-text-3 cursor-pointer">
                  <input type="checkbox" checked={dbForm.is_default} onChange={e => setDbForm(f => ({ ...f, is_default: e.target.checked }))} />{' '}
                  Set as default connection
                </label>

                {formError && <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">{formError}</div>}

                {modalTest.status !== 'idle' && (
                  <div className={`text-xs py-[7px] px-3 rounded-r-sm border ${testCls}`}>
                    {modalTest.status === 'testing' ? 'Testing connection…' : modalTest.msg}
                  </div>
                )}

                <div className="flex gap-2 justify-end mt-1">
                  <button type="button" className="btn btn-sm" onClick={closeModal}>Cancel</button>
                  <button type="button" className="btn btn-sm" onClick={runModalTest} disabled={modalTest.status === 'testing'}>
                    {modalTest.status === 'testing' ? <Spinner size={11} /> : <span className={`w-1.5 h-1.5 rounded-full ${testDotCls}`} />}
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
              <form onSubmit={submitMail} className="flex flex-col gap-3.5">
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

                {mailForm.provider_type === 'smtp' && <MailFieldsSmtp form={mailForm} setForm={setMailForm} />}
                {(mailForm.provider_type === 'gmail' || mailForm.provider_type === 'microsoft365') && <MailFieldsOAuth form={mailForm} setForm={setMailForm} />}
                {mailForm.provider_type === 'sendgrid' && <MailFieldsSendgrid form={mailForm} setForm={setMailForm} />}
                {mailForm.provider_type === 'ses' && <MailFieldsSes form={mailForm} setForm={setMailForm} />}
                {mailForm.provider_type === 'mailgun' && <MailFieldsMailgun form={mailForm} setForm={setMailForm} />}

                <label className="flex items-center gap-2 text-[13px] text-text-3 cursor-pointer">
                  <input type="checkbox" checked={mailForm.is_default} onChange={e => setMailForm(f => ({ ...f, is_default: e.target.checked }))} />{' '}
                  Set as default provider
                </label>

                {formError && <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">{formError}</div>}

                <div className="flex gap-2 justify-end mt-1">
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
