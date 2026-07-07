import { Pencil, Trash2 } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import Spinner from '../shared/Spinner'
import type { EmailProvider } from '../../lib/types'
import StatCol from './StatCol'
import { PROVIDER_LABELS } from './types'

export default function EmailProviderRow({ provider, testStatus, testError, isAdmin, onTest, onEdit, onDelete }: {
  provider: EmailProvider
  testStatus?: 'testing' | 'ok' | 'fail'
  testError?: string
  isAdmin: boolean
  onTest: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const label = PROVIDER_LABELS[provider.provider_type] ?? provider.provider_type

  return (
    <div className="card p-4">
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-[9px] flex items-center justify-center shrink-0 bg-accent-soft border border-[rgba(249,115,22,0.3)] text-accent-text">
          <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 mb-1">
            <span className="text-sm font-semibold text-text-primary">{provider.name}</span>
            <span className="mono text-[10.5px] py-px px-1.5 rounded bg-surface2 text-text-3">{label}</span>
            {testStatus === 'ok'   && <StatusBadge status="success" label="Verified" />}
            {testStatus === 'fail' && <StatusBadge status="failed"  label="Failed" />}
          </div>
          <div className="mono text-[11.5px] text-text-muted">{label} · {provider.is_default ? 'default' : 'not default'}</div>
          {testStatus === 'fail' && testError && (
            <div className="mono text-[11px] text-failure mt-1 break-all">{testError}</div>
          )}
        </div>
        <div className="flex gap-6 text-[11.5px] shrink-0">
          <StatCol label="Type"    value={provider.provider_type} />
          <StatCol label="Default" value={provider.is_default ? 'Yes' : 'No'} />
        </div>
        <div className="flex gap-1.5 shrink-0">
          <button className="btn btn-sm" onClick={onTest} disabled={testStatus === 'testing'}>
            {testStatus === 'testing' ? <Spinner size={11} /> : <span className={`w-1.5 h-1.5 rounded-full ${testStatus === 'ok' ? 'bg-success-text' : 'bg-text-muted'}`} />}
            Test
          </button>
          {isAdmin && (
            <>
              <button className="btn btn-sm btn-ghost btn-icon" onClick={onEdit}><Pencil size={12} /></button>
              <button className="btn btn-sm btn-ghost btn-icon" onClick={onDelete}>
                <Trash2 size={12} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
