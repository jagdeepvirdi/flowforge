import { useQuery } from '@tanstack/react-query'
import { ExternalLink, CheckCircle2, XCircle } from 'lucide-react'
import TopBar from '../components/shared/TopBar'
import Spinner from '../components/shared/Spinner'
import PageIntro from '../components/shared/PageIntro'
import { getSetupStatus } from '../lib/api'

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

          {/* Gmail + Drive */}
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
                    <StatusBadge
                      ok={status.drive.configured}
                      label={status.drive.configured
                        ? status.drive.folder_id ? 'Drive · folder set' : 'Drive · no folder'
                        : 'Drive not configured'}
                    />
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

          {/* Microsoft 365 */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Microsoft 365 OAuth2</div>
              {isLoading
                ? <Spinner size={14} />
                : status && (
                  <StatusBadge
                    ok={status.microsoft365.configured}
                    label={status.microsoft365.configured
                      ? `Connected · ${status.microsoft365.sender}`
                      : 'Not configured'}
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

          {/* YAML export/import */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Pipeline YAML Export / Import</div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Export or import pipeline definitions as YAML.</p>
            <CodeBlock>flowforge export "My Pipeline" --output pipeline.yaml</CodeBlock>
            <CodeBlock>flowforge import pipeline.yaml</CodeBlock>
          </div>

          {/* Docs */}
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

        </div>
      </div>
    </>
  )
}
