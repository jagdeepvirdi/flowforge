import { ExternalLink } from 'lucide-react'

export default function DocsCard() {
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
