import { ExternalLink } from 'lucide-react'
import TopBar from '../components/shared/TopBar'

export default function Settings() {
  return (
    <>
      <TopBar crumbs={['Workspace', 'Settings']} />
      <div className="scroll" style={{ maxWidth: 680 }}>
        <div className="page-h">
          <h1>Settings</h1>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Google OAuth2 (Gmail + Drive)</div>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
              Run the setup wizard from the CLI to authorize Gmail sending and Google Drive uploads.
            </p>
            <code className="mono" style={{ display: 'block', fontSize: 12, background: '#21252F', border: '1px solid #2D3143', borderRadius: 7, padding: '10px 12px', color: '#CBD5E1' }}>
              flowforge setup gmail
            </code>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Microsoft 365 OAuth2</div>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>
              Requires an Azure AD app registration with <code className="mono" style={{ fontSize: 11, background: '#21252F', padding: '1px 5px', borderRadius: 3 }}>Mail.Send</code> permission.
            </p>
            <code className="mono" style={{ display: 'block', fontSize: 12, background: '#21252F', border: '1px solid #2D3143', borderRadius: 7, padding: '10px 12px', color: '#CBD5E1' }}>
              flowforge setup microsoft365
            </code>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Pipeline YAML Export / Import</div>
            <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Export all pipelines as YAML for backup or migration.</p>
            <code className="mono" style={{ display: 'block', fontSize: 12, background: '#21252F', border: '1px solid #2D3143', borderRadius: 7, padding: '10px 12px', color: '#CBD5E1' }}>
              flowforge export "My Pipeline" --output pipeline.yaml
            </code>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>Documentation</div>
            {[
              ['Getting Started', '/docs/getting-started.md'],
              ['Step Types Reference', '/docs/step-types.md'],
              ['Email Providers', '/docs/email-providers.md'],
            ].map(([label, href]) => (
              <a key={href} href={href} style={{ color: '#FB923C', fontSize: 13, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6 }}
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
