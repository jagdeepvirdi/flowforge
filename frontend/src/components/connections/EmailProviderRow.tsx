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
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: 9, background: 'rgba(249,115,22,0.14)', border: '1px solid rgba(249,115,22,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-text)', flexShrink: 0 }}>
          <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{provider.name}</span>
            <span className="mono" style={{ fontSize: 10.5, padding: '1px 6px', borderRadius: 4, background: 'var(--surface-2)', color: 'var(--text-3)' }}>{label}</span>
            {testStatus === 'ok'   && <StatusBadge status="success" label="Verified" />}
            {testStatus === 'fail' && <StatusBadge status="failed"  label="Failed" />}
          </div>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{label} · {provider.is_default ? 'default' : 'not default'}</div>
          {testStatus === 'fail' && testError && (
            <div className="mono" style={{ fontSize: 11, color: 'var(--failure)', marginTop: 4, wordBreak: 'break-all' }}>{testError}</div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
          <StatCol label="Type"    value={provider.provider_type} />
          <StatCol label="Default" value={provider.is_default ? 'Yes' : 'No'} />
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button className="btn btn-sm" onClick={onTest} disabled={testStatus === 'testing'}>
            {testStatus === 'testing' ? <Spinner size={11} /> : <span style={{ width: 6, height: 6, borderRadius: '50%', background: testStatus === 'ok' ? 'var(--success-text)' : 'var(--text-muted)' }} />}
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
