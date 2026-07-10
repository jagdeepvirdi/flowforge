import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, CheckCircle2, XCircle, BrainCircuit, Shield, ShieldCheck, ShieldOff } from 'lucide-react'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import Sk from '../components/shared/Skeleton'
import PageIntro from '../components/shared/PageIntro'
import { useCurrentUser } from '../lib/auth'
import {
  getSetupStatus, changePassword, getMfaStatus, mfaEnroll, mfaConfirm, mfaDisable, type SetupStatus,
  getRetentionSettings, updateRetentionSettings,
} from '../lib/api'

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-[5px] text-xs font-medium ${ok ? 'text-success' : 'text-text-muted'}`}>
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
    <code className="mono block text-xs bg-surface2 border border-border rounded-[7px] py-2.5 px-3 text-text-2">
      {children}
    </code>
  )
}

function InlineCode({ children }: { children: string }) {
  return (
    <code className="mono text-[11px] bg-surface2 py-px px-[5px] rounded-[3px]">
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
    <div className="card flex flex-col gap-3.5">
      <div className="text-[13px] font-semibold text-text-primary">Change Password</div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
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
          <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
            {error}
          </div>
        )}
        {success && (
          <div className="text-[12.5px] text-success-text bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm py-2 px-3">
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
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-[13px] font-semibold text-text-primary">Google OAuth2 (Gmail + Drive)</div>
        {isLoading
          ? <div className="flex gap-3"><Sk h={13} style={{ width: 110 }} /><Sk h={13} style={{ width: 90 }} /></div>
          : status && (
            <div className="flex gap-3">
              <StatusBadge
                ok={status.gmail.configured}
                label={status.gmail.configured ? `Gmail · ${status.gmail.sender}` : 'Gmail not configured'}
              />
              <StatusBadge ok={status.drive.configured} label={driveLabel} />
            </div>
          )
        }
      </div>
      <p className="text-[13px] text-text-muted m-0">
        Requires a Google Cloud project with Gmail API enabled and a Desktop OAuth2 credential.
        Run the CLI wizard to complete the OAuth flow and save your refresh token.
      </p>
      <CodeBlock>flowforge setup gmail</CodeBlock>
      <a href="/api/docs/gmail-oauth2-setup.md" target="_blank" rel="noreferrer"
        className="text-xs text-accent-text no-underline inline-flex items-center gap-[5px] hover:underline">
        Step-by-step Gmail setup guide <ExternalLink size={11} />
      </a>
    </div>
  )
}

function Microsoft365Card({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-[13px] font-semibold text-text-primary">Microsoft 365 OAuth2</div>
        {isLoading
          ? <Sk h={13} style={{ width: 100 }} />
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
      <p className="text-[13px] text-text-muted m-0">
        Requires an Azure AD app registration with <InlineCode>Mail.Send</InlineCode> application permission
        and admin consent. You will need your Tenant ID, Client ID, and Client Secret from the Azure portal.
      </p>
      <CodeBlock>flowforge setup microsoft365</CodeBlock>
      <a href="/api/docs/microsoft365-oauth2-setup.md" target="_blank" rel="noreferrer"
        className="text-xs text-accent-text no-underline inline-flex items-center gap-[5px] hover:underline">
        Step-by-step Microsoft 365 setup guide <ExternalLink size={11} />
      </a>
    </div>
  )
}

function AiOllamaCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[7px] text-[13px] font-semibold text-text-primary">
          <BrainCircuit size={15} className="text-text-muted" />
          AI Features
        </div>
        {isLoading
          ? <Sk h={13} style={{ width: 120 }} />
          : status && (
            <StatusBadge
              ok={status.ai.enabled}
              label={status.ai.enabled ? `Enabled · ${status.ai.ollama_url}` : 'Disabled'}
            />
          )
        }
      </div>
      <p className="text-[13px] text-text-muted m-0">
        SQL Explain, SQL Optimize, Data Profiler, Chart Generator, and Pipeline Failure Diagnosis all
        route through a local <InlineCode>Ollama</InlineCode> instance by default — no data leaves your
        machine and there is no API cost. If Claude or Gemini is configured below, they're used as an
        automatic fallback only when Ollama is unreachable (Claude first, then Gemini).
        Set <InlineCode>FLOWFORGE_AI_ENABLED=false</InlineCode> to hide all AI buttons and disable all AI endpoints.
      </p>
      {status && !status.ai.enabled && (
        <div className="py-2 px-3 bg-[rgba(239,68,68,0.06)] border border-[rgba(239,68,68,0.15)] rounded-r-sm text-xs text-text-2">
          AI is currently disabled. Remove or change the env var below and restart to re-enable.
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <CodeBlock>FLOWFORGE_AI_ENABLED=true   # set to false to disable all AI features</CodeBlock>
        <CodeBlock>OLLAMA_URL=http://localhost:11434</CodeBlock>
        <CodeBlock>OLLAMA_CHART_MODEL=llama3.2:3b   # model for chart & profile tasks</CodeBlock>
        <CodeBlock>OLLAMA_QUERY_MODEL=llama3.2:3b   # model for explain/optimize/diagnose</CodeBlock>
      </div>

      <div className="h-px bg-border my-0.5" />

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[13px] font-medium text-text-primary">Claude / Gemini fallback &amp; ai_analyze providers</span>
        </div>
        <p className="text-[13px] text-text-muted m-0">
          Configuring a key here enables it as the Ollama-unreachable fallback above, and makes it
          selectable in the <InlineCode>ai_analyze</InlineCode> pipeline step via
          <InlineCode>provider: "claude"</InlineCode> or <InlineCode>provider: "gemini"</InlineCode>.
        </p>

        <div className="flex items-center justify-between mt-1">
          <span className="text-[13px] text-text-2">Claude API (Anthropic)</span>
          {isLoading
            ? <Sk h={13} style={{ width: 90 }} />
            : status && (
              <StatusBadge
                ok={status.ai.claude.configured}
                label={status.ai.claude.configured ? 'Key configured' : 'Not configured'}
              />
            )
          }
        </div>
        <CodeBlock>ANTHROPIC_API_KEY=   # requires: pip install anthropic</CodeBlock>

        <div className="flex items-center justify-between mt-1">
          <span className="text-[13px] text-text-2">Gemini API (Google, free tier)</span>
          {isLoading
            ? <Sk h={13} style={{ width: 90 }} />
            : status && (
              <StatusBadge
                ok={status.ai.gemini.configured}
                label={status.ai.gemini.configured ? `Key configured · ${status.ai.gemini.model}` : 'Not configured'}
              />
            )
          }
        </div>
        <CodeBlock>GEMINI_API_KEY=   # free tier: aistudio.google.com/apikey</CodeBlock>
        <CodeBlock>GEMINI_QUERY_MODEL=gemini-2.5-flash</CodeBlock>
      </div>
    </div>
  )
}

function YamlCard() {
  return (
    <div className="card flex flex-col gap-3">
      <div className="text-[13px] font-semibold text-text-primary">Pipeline YAML Export / Import</div>
      <p className="text-[13px] text-text-muted m-0">Export or import pipeline definitions as YAML.</p>
      <CodeBlock>flowforge export "My Pipeline" --output pipeline.yaml</CodeBlock>
      <CodeBlock>flowforge import pipeline.yaml</CodeBlock>
    </div>
  )
}

function DocsCard() {
  return (
    <div className="card flex flex-col gap-2.5">
      <div className="text-[13px] font-semibold text-text-primary">Documentation</div>
      {([
        ['Getting Started',          '/api/docs/getting-started.md'],
        ['Step Types Reference',     '/api/docs/step-types.md'],
        ['Email Providers (all)',    '/api/docs/email-providers.md'],
        ['Gmail OAuth2 Setup',       '/api/docs/gmail-oauth2-setup.md'],
        ['Microsoft 365 Setup',      '/api/docs/microsoft365-oauth2-setup.md'],
      ] as [string, string][]).map(([label, href]) => (
        <a key={href} href={href} target="_blank" rel="noreferrer"
          className="text-accent-text text-[13px] no-underline inline-flex items-center gap-1.5 hover:underline">
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
    <div className="card flex flex-col gap-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[7px] text-[13px] font-semibold text-text-primary">
          {enabled ? <ShieldCheck size={15} className="text-success" /> : <Shield size={15} className="text-text-muted" />}
          Two-Factor Authentication (MFA)
        </div>
        <span className={`text-[11px] font-semibold py-0.5 px-2 rounded uppercase tracking-[0.06em] ${enabled ? 'bg-[rgba(34,197,94,0.12)] text-success-text' : 'bg-[rgba(107,114,128,0.12)] text-text-muted'}`}>
          {enabled ? 'Active' : 'Disabled'}
        </span>
      </div>

      <p className="text-[13px] text-text-muted m-0">
        {enabled
          ? 'MFA is active on your account. You will be asked for a TOTP code on every login.'
          : 'Add a second factor to your account using any TOTP authenticator app (Google Authenticator, Authy, 1Password, etc.).'}
      </p>

      {error && (
        <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
          {error}
        </div>
      )}

      {/* ── Not enrolled → start enrollment ── */}
      {!enabled && phase === 'idle' && (
        <button className="btn btn-primary self-start"
          onClick={() => { setError(''); enrollMut.mutate() }}
          disabled={enrollMut.isPending}>
          {enrollMut.isPending ? <Spinner size={13} /> : 'Enable MFA'}
        </button>
      )}

      {/* ── Scan QR / copy secret ── */}
      {phase === 'confirming' && (
        <div className="flex flex-col gap-3.5">
          <p className="text-[13px] text-text-2 m-0">
            Scan the QR code with your authenticator app, then enter the 6-digit code to confirm.
          </p>
          {qrDataUrl
            ? <img src={qrDataUrl} alt="MFA QR code" width={160} height={160} className="rounded-r border border-border bg-white" />
            : (
              <div className="flex flex-col gap-1.5">
                <span className="text-xs text-text-muted">Manual entry secret:</span>
                <div className="flex gap-2 items-center">
                  <code className="mono text-[13px] bg-surface2 border border-border rounded-r-sm py-1.5 px-2.5 flex-1 [overflow-wrap:anywhere]">
                    {secret}
                  </code>
                  <button className="btn whitespace-nowrap text-xs" onClick={copySecret}>
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <a href={uri} className="text-xs text-accent-text">Open in authenticator app</a>
              </div>
            )
          }
          <form onSubmit={e => { e.preventDefault(); confirmMut.mutate() }} className="flex flex-col gap-2.5">
            <div className="field">
              <label htmlFor="mfa-confirm-code">Verification code</label>
              <input
                id="mfa-confirm-code"
                className="input mono tracking-[0.3em] text-lg text-center max-w-40"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                autoFocus
                required
              />
            </div>
            <div className="flex gap-2">
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
        <div className="flex flex-col gap-3">
          <div className="py-2.5 px-3.5 bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm text-[13px] text-success-text">
            MFA activated! Save these backup codes — they are shown only once.
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {backupCodes.map(c => (
              <code key={c} className="mono text-[13px] bg-surface2 border border-border rounded py-[5px] px-2.5 text-center">
                {c}
              </code>
            ))}
          </div>
          <button className="btn btn-primary self-start" onClick={() => { setPhase('idle'); setBackupCodes([]) }}>
            Done — I've saved my backup codes
          </button>
        </div>
      )}

      {/* ── Disable MFA ── */}
      {enabled && phase === 'idle' && (
        <button
          className="btn self-start text-failure-text flex items-center gap-[5px]"
          onClick={() => { setPhase('disabling'); setError('') }}
        >
          <ShieldOff size={13} /> Disable MFA
        </button>
      )}

      {phase === 'disabling' && (
        <form onSubmit={e => { e.preventDefault(); disableMut.mutate() }} className="flex flex-col gap-2.5">
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
          <div className="flex gap-2">
            <button type="submit" className="btn text-failure-text" disabled={disableMut.isPending}>
              {disableMut.isPending ? 'Disabling…' : 'Disable MFA'}
            </button>
            <button type="button" className="btn" onClick={() => { setPhase('idle'); setError('') }}>Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}

function RetentionField({
  id, label, value, onChange, min, hint,
}: {
  id: string; label: string; value: string
  onChange: (v: string) => void; min: number; hint: string
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} className="input" type="number" min={min} value={value}
        onChange={e => onChange(e.target.value)} />
      <span className="text-[11px] text-text-muted">{hint}</span>
    </div>
  )
}

function RetentionCard() {
  const qc = useQueryClient()
  const me = useCurrentUser()
  const isAdmin = me?.role === 'admin'

  const { data, isLoading } = useQuery({
    queryKey: ['retention-settings'],
    queryFn: getRetentionSettings,
  })

  const [form, setForm] = useState({ run: '', audit: '', outputTtl: '' })
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState(false)

  // Sync fetched data into local editable form state, adjusted during render
  // (React's documented pattern for this) rather than in an effect.
  const [prevData, setPrevData] = useState(data)
  if (data !== prevData) {
    setPrevData(data)
    if (data) {
      setForm({
        run:       String(data.run_retention_days),
        audit:     String(data.audit_retention_days),
        outputTtl: String(data.output_ttl_days),
      })
    }
  }

  const mut = useMutation({
    mutationFn: updateRetentionSettings,
    onSuccess: () => {
      setSuccess(true)
      setError('')
      qc.invalidateQueries({ queryKey: ['retention-settings'] })
    },
    onError: (e: Error) => { setError(e.message); setSuccess(false) },
  })

  const outputTtlNum = Number(form.outputTtl)
  const outputTtlInvalid = form.outputTtl.trim() === '' || !Number.isInteger(outputTtlNum) || outputTtlNum < 1

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess(false)
    if (outputTtlInvalid) {
      setError('Output file TTL must be at least 1 day — 0 would delete every generated report immediately.')
      return
    }
    mut.mutate({
      run_retention_days: Number(form.run),
      audit_retention_days: Number(form.audit),
      output_ttl_days: outputTtlNum,
    })
  }

  function resetToDefault(field: 'run_retention_days' | 'audit_retention_days' | 'output_ttl_days') {
    setError('')
    setSuccess(false)
    mut.mutate({ [field]: null })
  }

  if (!isAdmin) {
    return (
      <div className="card flex flex-col gap-3">
        <div className="text-[13px] font-semibold text-text-primary">Data Retention Policies</div>
        {isLoading
          ? <div className="flex gap-3"><Sk h={13} style={{ width: 100 }} /><Sk h={13} style={{ width: 100 }} /><Sk h={13} style={{ width: 100 }} /></div>
          : data && (
            <div className="flex gap-3 flex-wrap">
              <StatusBadge ok label={`Runs: ${data.run_retention_days} days`} />
              <StatusBadge ok label={`Audit: ${data.audit_retention_days} days`} />
              <StatusBadge ok label={`Output files: ${data.output_ttl_days} days`} />
            </div>
          )
        }
        <p className="text-[13px] text-text-muted m-0">
          How long historical pipeline runs, audit logs, and generated report files are kept
          before the nightly background job deletes them. Only admins can change these values.
        </p>
      </div>
    )
  }

  return (
    <div className="card flex flex-col gap-3.5">
      <div className="text-[13px] font-semibold text-text-primary">Data Retention Policies</div>
      <p className="text-[13px] text-text-muted m-0">
        How long historical pipeline runs, audit logs, and generated report files are kept
        before the nightly background job deletes them. Falls back to the server's env var
        default unless overridden below.
      </p>
      {isLoading ? (
        <Sk h={64} r={6} />
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
          <div className="grid grid-cols-3 gap-3">
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-run" label="Pipeline runs (days)" min={0}
                value={form.run} onChange={v => setForm(f => ({ ...f, run: v }))}
                hint={`0 = keep forever${data?.is_custom.run_retention_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.run_retention_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('run_retention_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-audit" label="Audit log (days)" min={0}
                value={form.audit} onChange={v => setForm(f => ({ ...f, audit: v }))}
                hint={`0 = keep forever${data?.is_custom.audit_retention_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.audit_retention_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('audit_retention_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
            <div className="flex flex-col gap-1">
              <RetentionField
                id="retention-output" label="Output files (days)" min={1}
                value={form.outputTtl} onChange={v => setForm(f => ({ ...f, outputTtl: v }))}
                hint={`min 1${data?.is_custom.output_ttl_days ? ' · custom' : ' · default'}`}
              />
              {data?.is_custom.output_ttl_days && (
                <button type="button" className="btn btn-sm w-fit" onClick={() => resetToDefault('output_ttl_days')} disabled={mut.isPending}>
                  Use default
                </button>
              )}
            </div>
          </div>
          <p className="text-[11px] text-text-muted m-0">
            Output files can't be set to 0 here — that would delete every report immediately.
            Use <InlineCode>flowforge cleanup --days 0</InlineCode> if you intentionally need
            that; it requires explicit confirmation.
          </p>
          {error && (
            <div className="text-[12.5px] text-failure-text bg-[rgba(239,68,68,0.08)] border border-[rgba(239,68,68,0.2)] rounded-r-sm py-2 px-3">
              {error}
            </div>
          )}
          {success && (
            <div className="text-[12.5px] text-success-text bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] rounded-r-sm py-2 px-3">
              Saved.
            </div>
          )}
          <div>
            <button type="submit" className="btn btn-primary" disabled={mut.isPending || outputTtlInvalid}>
              {mut.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

type Tab = 'account' | 'email' | 'ai' | 'system' | 'docs'

const TABS: { id: Tab; label: string }[] = [
  { id: 'account', label: 'Account' },
  { id: 'email', label: 'Email' },
  { id: 'ai', label: 'AI' },
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
      <div className="scroll max-w-[680px]">
        <PageIntro page="settings" />
        <div className="page-h">
          <h1>Settings</h1>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border mb-5">
          {TABS.map(t => {
            const active = tab === t.id
            return (
              <button key={t.id} onClick={() => setTab(t.id)} className={`bg-transparent border-none py-2.5 px-4 text-[13px] cursor-pointer -mb-px border-b-2 ${active ? 'text-accent font-semibold border-b-accent' : 'text-text-3 font-medium border-b-transparent'}`}>
                {t.label}
              </button>
            )
          })}
        </div>

        <div className="flex flex-col gap-3.5">

          {tab === 'account' && (
            <>
              <ChangePasswordCard />
              <MfaCard />
            </>
          )}

          {tab === 'email' && (
            <>
              <GoogleOAuthCard status={status} isLoading={isLoading} />
              <Microsoft365Card status={status} isLoading={isLoading} />
            </>
          )}

          {tab === 'ai' && (
            <AiOllamaCard status={status} isLoading={isLoading} />
          )}

          {tab === 'system' && (
            <>
              <RetentionCard />
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
