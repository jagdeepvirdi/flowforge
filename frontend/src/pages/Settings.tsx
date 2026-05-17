import { ExternalLink } from 'lucide-react'
import PageHeader from '../components/shared/PageHeader'

export default function Settings() {
  return (
    <div className="p-8 max-w-2xl">
      <PageHeader title="Settings" />

      <div className="space-y-4">
        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Google OAuth2 (Gmail + Drive)</h2>
          <p className="text-sm text-text-muted mb-4">
            Run the setup wizard from the CLI to authorize Gmail sending and Google Drive uploads.
          </p>
          <code className="block text-xs font-mono bg-surface2 border border-border rounded-input px-3 py-2 text-text-primary">
            flowforge setup gmail
          </code>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Microsoft 365 OAuth2</h2>
          <p className="text-sm text-text-muted mb-4">
            Requires an Azure AD app registration with <code className="text-xs bg-surface2 px-1 rounded">Mail.Send</code> permission.
          </p>
          <code className="block text-xs font-mono bg-surface2 border border-border rounded-input px-3 py-2 text-text-primary">
            flowforge setup microsoft365
          </code>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Pipeline YAML Export / Import</h2>
          <p className="text-sm text-text-muted mb-3">Export all pipelines as YAML for backup or migration.</p>
          <div className="flex gap-2">
            <code className="block text-xs font-mono bg-surface2 border border-border rounded-input px-3 py-2 text-text-primary flex-1">
              flowforge export &quot;My Pipeline&quot; --output pipeline.yaml
            </code>
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Documentation</h2>
          <div className="space-y-2">
            {[
              ['Getting Started', '/docs/getting-started.md'],
              ['Step Types Reference', '/docs/step-types.md'],
              ['Email Providers', '/docs/email-providers.md'],
            ].map(([label, href]) => (
              <a key={href} href={href} className="flex items-center gap-2 text-sm text-accent hover:underline">
                {label} <ExternalLink size={12}/>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
