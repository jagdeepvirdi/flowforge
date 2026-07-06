import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ExternalLink, CheckCircle2, XCircle, BrainCircuit, Shield, ShieldCheck, ShieldOff } from 'lucide-react'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'
import { getSetupStatus, changePassword, getMfaStatus, mfaEnroll, mfaConfirm, mfaDisable, type SetupStatus } from '../lib/api'

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 12, fontWeight: 500,
      color: ok ? 'var(--success)' : 'var(--text-muted)',
    }}>
      {ok
        ? <CheckCircle2 size={13} />
        : <XCircle size={13} />
      }
      {label}
    </span>
  )
}

function CodeBlock({ children }: { children: string }) {
  return (
    <code className="mono" style={{
      display: 'block', fontSize: 12,
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderRadius: 7, padding: '10px 12px', color: 'var(--text-2)',
    }}>
      {children}
    </code>
  )
}

function InlineCode({ children }: { children: string }) {
  return (
    <code className="mono" style={{ fontSize: 11, background: 'var(--surface-2)', padding: '1px 5px', borderRadius: 3 }}>
      {children}
    </code>
  )
}

function ChangePasswordCard() {
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' })
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState(false)

  const mut = useMutation({
    mutationFn: () => changePassword({ current_password: form.current_password, new_password: form.new_password }),
    onSuccess: () => {
      setSuccess(true)
      setError('')
      setForm({ current_password: '', new_password: '', confirm: '' })
    },
    onError: (e: Error) => { setError(e.message); setSuccess(false) },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (form.new_password.length < 8) { setError('New password must be at least 8 characters'); return }
    if (form.new_password !== form.confirm) { setError('Passwords do not match'); return }
    mut.mutate()
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Change Password</div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div className="field">
          <label htmlFor="settings-current-password">Current Password</label>
          <input id="settings-current-password" className="input" type="password" value={form.current_password}
            onChange={e => setForm(f => ({ ...f, current_password: e.target.value }))} required />
        </div>
        <div className="field">
          <label htmlFor="settings-new-password">New Password</label>
          <input id="settings-new-password" className="input" type="password" value={form.new_password}
            onChange={e => setForm(f => ({ ...f, new_password: e.target.value }))} required />
        </div>
        <div className="field">
          <label htmlFor="settings-confirm-password">Confirm New Password</label>
          <input id="settings-confirm-password" className="input" type="password" value={form.confirm}
            onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))} required />
        </div>
        {error && (
          <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ fontSize: 12.5, color: 'var(--success-text)', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, padding: '8px 12px' }}>
            Password changed successfully.
          </div>
        )}
        <div>
          <button type="submit" className="btn btn-primary" disabled={mut.isPending}>
            {mut.isPending ? 'Saving…' : 'Change Password'}
          </button>
        </div>
      </form>
    </div>
  )
}

function GoogleOAuthCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  const driveLabel = !status ? '' : status.drive.configured
    ? (status.drive.folder_id ? 'Drive · folder set' : 'Drive · no folder')
    : 'Drive not configured'

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Google OAuth2 (Gmail + Drive)</div>
        {isLoading
          ? <Spinner size={14} />
          : status && (
            <div style={{ display: 'flex', gap: 12 }}>
              <StatusBadge
                ok={status.gmail.configured}
                label={status.gmail.configured ? `Gmail · ${status.gmail.sender}` : 'Gmail not configured'}
              />
              <StatusBadge ok={status.drive.configured} label={driveLabel} />
            </div>
          )
        }
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
        Requires a Google Cloud project with Gmail API enabled and a Desktop OAuth2 credential.
        Run the CLI wizard to complete the OAuth flow and save your refresh token.
      </p>
      <CodeBlock>flowforge setup gmail</CodeBlock>
      <a href="/api/docs/gmail-oauth2-setup.md" target="_blank" rel="noreferrer"
        style={{ fontSize: 12, color: 'var(--accent-text)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 5 }}
        onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
        onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}>
        Step-by-step Gmail setup guide <ExternalLink size={11} />
      </a>
    </div>
  )
}

function Microsoft365Card({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Microsoft 365 OAuth2</div>
        {isLoading
          ? <Spinner size={14} />
          : status && (
            <StatusBadge
              ok={status.microsoft365.configured}
              label={status.microsoft365.configured
                ? `M365 · ${status.microsoft365.sender}`
                : 'M365 not configured'}
            />
          )
        }
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
        Requires an Azure AD app registration with <InlineCode>Mail.Send</InlineCode> application permission
        and admin consent. You will need your Tenant ID, Client ID, and Client Secret from the Azure portal.
      </p>
      <CodeBlock>flowforge setup microsoft365</CodeBlock>
      <a href="/api/docs/email-providers.md" target="_blank" rel="noreferrer"
        style={{ fontSize: 12, color: 'var(--accent-text)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 5 }}
        onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
        onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}>
        Step-by-step Microsoft 365 setup guide <ExternalLink size={11} />
      </a>
    </div>
  )
}

function AiOllamaCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
          <BrainCircuit size={15} style={{ color: 'var(--text-muted)' }} />
          AI Features (Ollama)
        </div>
        {isLoading
          ? <Spinner size={14} />
          : status && (
            <StatusBadge
              ok={status.ai.enabled}
              label={status.ai.enabled ? `Enabled · ${status.ai.ollama_url}` : 'Disabled'}
            />
          )
        }
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
        SQL Explain, SQL Optimize, Data Profiler, Chart Generator, and Pipeline Failure Diagnosis all
        route through a local <InlineCode>Ollama</InlineCode> instance — no data leaves your machine and there is no API cost.
        Set <InlineCode>FLOWFORGE_AI_ENABLED=false</InlineCode> to hide all AI buttons and disable all AI endpoints.
      </p>
      {status && !status.ai.enabled && (
        <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)', borderRadius: 6, fontSize: 12, color: 'var(--text-2)' }}>
          AI is currently disabled. Remove or change the env var below and restart to re-enable.
        </div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <CodeBlock>FLOWFORGE_AI_ENABLED=true   # set to false to disable all AI features</CodeBlock>
        <CodeBlock>OLLAMA_URL=http://localhost:11434</CodeBlock>
        <CodeBlock>OLLAMA_CHART_MODEL=llama3.2:3b   # model for chart & profile tasks</CodeBlock>
        <CodeBlock>OLLAMA_QUERY_MODEL=llama3.2:3b   # model for explain/optimize/diagnose</CodeBlock>
      </div>
    </div>
  )
}

function YamlCard() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Pipeline YAML Export / Import</div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Export or import pipeline definitions as YAML.</p>
      <CodeBlock>flowforge export "My Pipeline" --output pipeline.yaml</CodeBlock>
      <CodeBlock>flowforge import pipeline.yaml</CodeBlock>
    </div>
  )
}

function DocsCard() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Documentation</div>
      {([
        ['Getting Started',          '/api/docs/getting-started.md'],
        ['Step Types Reference',     '/api/docs/step-types.md'],
        ['Email Providers (all)',    '/api/docs/email-providers.md'],
        ['Gmail OAuth2 Setup',       '/api/docs/gmail-oauth2-setup.md'],
      ] as [string, string][]).map(([label, href]) => (
        <a key={href} href={href} target="_blank" rel="noreferrer"
          style={{ color: 'var(--accent-text)', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}
          onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
          onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}>
          {label} <ExternalLink size={12} />
        </a>
      ))}
    </div>
  )
}

type MfaPhase = 'idle' | 'enrolling' | 'confirming' | 'backup-codes' | 'disabling'

function MfaCard() {
  const { data: mfaStatus, refetch } = useQuery({
    queryKey: ['mfa-status'],
    queryFn: getMfaStatus,
  })

  const [phase, setPhase]               = useState<MfaPhase>('idle')
  const [qrDataUrl, setQrDataUrl]       = useState('')
  const [secret, setSecret]             = useState('')
  const [uri, setUri]                   = useState('')
  const [code, setCode]                 = useState('')
  const [password, setPassword]         = useState('')
  const [backupCodes, setBackupCodes]   = useState<string[]>([])
  const [error, setError]               = useState('')
  const [copied, setCopied]             = useState(false)

  const enrollMut = useMutation({
    mutationFn: mfaEnroll,
    onSuccess: async (data) => {
      setSecret(data.secret)
      setUri(data.provisioning_uri)
      try {
        const QRCode = await import('qrcode')
        const url = await QRCode.default.toDataURL(data.provisioning_uri, { width: 200, margin: 2 })
        setQrDataUrl(url)
      } catch {
        setQrDataUrl('')
      }
      setPhase('confirming')
      setError('')
    },
    onError: (e: Error) => setError(e.message),
  })

  const confirmMut = useMutation({
    mutationFn: () => mfaConfirm(code),
    onSuccess: (data) => {
      setBackupCodes(data.backup_codes)
      setPhase('backup-codes')
      setError('')
      refetch()
    },
    onError: (e: Error) => setError(e.message),
  })

  const disableMut = useMutation({
    mutationFn: () => mfaDisable(password),
    onSuccess: () => {
      setPhase('idle')
      setPassword('')
      setError('')
      refetch()
    },
    onError: (e: Error) => setError(e.message),
  })

  const copySecret = () => {
    navigator.clipboard.writeText(secret)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const enabled = mfaStatus?.mfa_enabled ?? false

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
          {enabled ? <ShieldCheck size={15} style={{ color: 'var(--success)' }} /> : <Shield size={15} style={{ color: 'var(--text-muted)' }} />}
          Two-Factor Authentication (MFA)
        </div>
        <span style={{
          fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
          background: enabled ? 'rgba(34,197,94,0.12)' : 'rgba(107,114,128,0.12)',
          color: enabled ? 'var(--success-text)' : 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.06em',
        }}>
          {enabled ? 'Active' : 'Disabled'}
        </span>
      </div>

      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
        {enabled
          ? 'MFA is active on your account. You will be asked for a TOTP code on every login.'
          : 'Add a second factor to your account using any TOTP authenticator app (Google Authenticator, Authy, 1Password, etc.).'}
      </p>

      {error && (
        <div style={{ fontSize: 12.5, color: 'var(--failure-text)', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '8px 12px' }}>
          {error}
        </div>
      )}

      {/* ── Not enrolled → start enrollment ── */}
      {!enabled && phase === 'idle' && (
        <button className="btn btn-primary" style={{ alignSelf: 'flex-start' }}
          onClick={() => { setError(''); enrollMut.mutate() }}
          disabled={enrollMut.isPending}>
          {enrollMut.isPending ? <Spinner size={13} /> : 'Enable MFA'}
        </button>
      )}

      {/* ── Scan QR / copy secret ── */}
      {phase === 'confirming' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ fontSize: 13, color: 'var(--text-2)', margin: 0 }}>
            Scan the QR code with your authenticator app, then enter the 6-digit code to confirm.
          </p>
          {qrDataUrl
            ? <img src={qrDataUrl} alt="MFA QR code" width={160} height={160} style={{ borderRadius: 8, border: '1px solid var(--border)', background: '#fff' }} />
            : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Manual entry secret:</span>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <code className="mono" style={{ fontSize: 13, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 6, padding: '6px 10px', flex: 1, overflowWrap: 'anywhere' }}>
                    {secret}
                  </code>
                  <button className="btn" onClick={copySecret} style={{ whiteSpace: 'nowrap', fontSize: 12 }}>
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <a href={uri} style={{ fontSize: 12, color: 'var(--accent-text)' }}>Open in authenticator app</a>
              </div>
            )
          }
          <form onSubmit={e => { e.preventDefault(); confirmMut.mutate() }} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="field">
              <label htmlFor="mfa-confirm-code">Verification code</label>
              <input
                id="mfa-confirm-code"
                className="input mono"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                autoFocus
                required
                style={{ letterSpacing: '0.3em', fontSize: 18, textAlign: 'center', maxWidth: 160 }}
              />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary" disabled={confirmMut.isPending || code.length !== 6}>
                {confirmMut.isPending ? 'Activating…' : 'Activate MFA'}
              </button>
              <button type="button" className="btn" onClick={() => { setPhase('idle'); setError('') }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* ── Show backup codes once ── */}
      {phase === 'backup-codes' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ padding: '10px 14px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, fontSize: 13, color: 'var(--success-text)' }}>
            MFA activated! Save these backup codes — they are shown only once.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {backupCodes.map(c => (
              <code key={c} className="mono" style={{ fontSize: 13, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '5px 10px', textAlign: 'center' }}>
                {c}
              </code>
            ))}
          </div>
          <button className="btn btn-primary" style={{ alignSelf: 'flex-start' }} onClick={() => { setPhase('idle'); setBackupCodes([]) }}>
            Done — I've saved my backup codes
          </button>
        </div>
      )}

      {/* ── Disable MFA ── */}
      {enabled && phase === 'idle' && (
        <button
          className="btn"
          style={{ alignSelf: 'flex-start', color: 'var(--failure-text)', display: 'flex', alignItems: 'center', gap: 5 }}
          onClick={() => { setPhase('disabling'); setError('') }}
        >
          <ShieldOff size={13} /> Disable MFA
        </button>
      )}

      {phase === 'disabling' && (
        <form onSubmit={e => { e.preventDefault(); disableMut.mutate() }} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="field">
            <label htmlFor="mfa-disable-password">Confirm your password to disable MFA</label>
            <input
              id="mfa-disable-password"
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoFocus
              required
            />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="submit" className="btn" style={{ color: 'var(--failure-text)' }} disabled={disableMut.isPending}>
              {disableMut.isPending ? 'Disabling…' : 'Disable MFA'}
            </button>
            <button type="button" className="btn" onClick={() => { setPhase('idle'); setError('') }}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}

function RetentionCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Data Retention Policies</div>
        {isLoading
          ? <Spinner size={14} />
          : status && (
            <div style={{ display: 'flex', gap: 12 }}>
              <StatusBadge
                ok={true}
                label={`Runs: ${status.retention.run_days} days`}
              />
              <StatusBadge
                ok={true}
                label={`Audit: ${status.retention.audit_days} days`}
              />
            </div>
          )
        }
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>
        Determines how long historical pipeline runs and audit logs are kept before being automatically purged by the nightly background job.
        Configured via environment variables.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <CodeBlock>FLOWFORGE_RUN_RETENTION_DAYS=90     # defaults to 90</CodeBlock>
        <CodeBlock>FLOWFORGE_AUDIT_RETENTION_DAYS=365  # defaults to RUN_RETENTION_DAYS</CodeBlock>
      </div>
    </div>
  )
}

type Tab = 'account' | 'email-ai' | 'system' | 'docs'

const TABS: { id: Tab; label: string }[] = [
  { id: 'account', label: 'Account' },
  { id: 'email-ai', label: 'Email & AI' },
  { id: 'system', label: 'System' },
  { id: 'docs', label: 'Docs' },
]

export default function Settings() {
  const [tab, setTab] = useState<Tab>('account')

  const { data: status, isLoading } = useQuery({
    queryKey: ['setup-status'],
    queryFn: getSetupStatus,
    staleTime: 30_000,
  })

  return (
    <>
      <TopBar crumbs={['Workspace', 'Settings']} helpTopic="settings" />
      <div className="scroll" style={{ maxWidth: 680 }}>
        <PageIntro page="settings" />
        <div className="page-h">
          <h1>Settings</h1>
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
                borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
                marginBottom: -1, cursor: 'pointer',
              }}>
                {t.label}
              </button>
            )
          })}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {tab === 'account' && (
            <>
              <ChangePasswordCard />
              <MfaCard />
            </>
          )}

          {tab === 'email-ai' && (
            <>
              <GoogleOAuthCard status={status} isLoading={isLoading} />
              <Microsoft365Card status={status} isLoading={isLoading} />
              <AiOllamaCard status={status} isLoading={isLoading} />
            </>
          )}

          {tab === 'system' && (
            <>
              <RetentionCard status={status} isLoading={isLoading} />
              <YamlCard />
            </>
          )}

          {tab === 'docs' && (
            <DocsCard />
          )}

        </div>
      </div>
    </>
  )
}
