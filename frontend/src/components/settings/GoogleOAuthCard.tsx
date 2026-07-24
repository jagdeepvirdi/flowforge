import { ExternalLink } from 'lucide-react'
import Sk from '../shared/Skeleton'
import { StatusBadge, CodeBlock } from './common'
import type { SetupStatus } from '../../lib/api'

export default function GoogleOAuthCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
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
