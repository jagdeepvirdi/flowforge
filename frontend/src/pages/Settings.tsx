import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ExternalLink, CheckCircle2, XCircle, BrainCircuit } from 'lucide-react'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'
import { getSetupStatus, changePassword } from '../lib/api'

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

function GoogleOAuthCard({ status, isLoading }: { status: any; isLoading: boolean }) {
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

function Microsoft365Card({ status, isLoading }: { status: any; isLoading: boolean }) {
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

function AiOllamaCard({ status, isLoading }: { status: any; isLoading: boolean }) {
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

function RetentionCard({ status, isLoading }: { status: any; isLoading: boolean }) {
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

export default function Settings() {
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

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Change Password */}
          <ChangePasswordCard />

          {/* Gmail + Drive */}
          <GoogleOAuthCard status={status} isLoading={isLoading} />

          {/* Microsoft 365 */}
          <Microsoft365Card status={status} isLoading={isLoading} />

          {/* AI Features */}
          <AiOllamaCard status={status} isLoading={isLoading} />

          {/* Retention Policies */}
          <RetentionCard status={status} isLoading={isLoading} />

          {/* YAML export/import */}
          <YamlCard />

          {/* Docs */}
          <DocsCard />

        </div>
      </div>
    </>
  )
}
