import { ExternalLink } from 'lucide-react'
import Sk from '../shared/Skeleton'
import { StatusBadge, CodeBlock, InlineCode } from './common'
import type { SetupStatus } from '../../lib/api'

export default function Microsoft365Card({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
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
