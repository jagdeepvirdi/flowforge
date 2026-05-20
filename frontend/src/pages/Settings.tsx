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
      color: ok ? '#22C55E' : '#64748B',
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
      background: '#21252F', border: '1px solid #2D3143',
      borderRadius: 7, padding: '10px 12px', color: '#CBD5E1',
    }}>
      {children}
    </code>
  )
}

function InlineCode({ children }: { children: string }) {
  return (
    <code className="mono" style={{ fontSize: 11, background: '#21252F', padding: '1px 5px', borderRadius: 3 }}>
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
              <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Google OAuth2 (Gmail + Drive)</div>
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
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
              Run the setup wizard from the CLI to authorize Gmail sending and Google Drive uploads.
            </p>
            <CodeBlock>flowforge setup gmail</CodeBlock>
          </div>

          {/* Microsoft 365 */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Microsoft 365 OAuth2</div>
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
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
              Requires an Azure AD app registration with <InlineCode>Mail.Send</InlineCode> permission.
            </p>
            <CodeBlock>flowforge setup microsoft365</CodeBlock>
          </div>

          {/* YAML export/import */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Pipeline YAML Export / Import</div>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Export or import pipeline definitions as YAML.</p>
            <CodeBlock>flowforge export "My Pipeline" --output pipeline.yaml</CodeBlock>
            <CodeBlock>flowforge import pipeline.yaml</CodeBlock>
          </div>

          {/* Docs */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Documentation</div>
            {([
              ['Getting Started', '/docs/getting-started.md'],
              ['Step Types Reference', '/docs/step-types.md'],
              ['Email Providers', '/docs/email-providers.md'],
            ] as [string, string][]).map(([label, href]) => (
              <a key={href} href={href}
                style={{ color: '#FB923C', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}
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
