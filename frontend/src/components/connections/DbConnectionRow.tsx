import { Pencil, Trash2 } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import Spinner from '../shared/Spinner'
import type { DbConnection } from '../../lib/types'
import StatCol from './StatCol'
import { DB_COLORS, DB_LABELS } from './types'

export default function DbConnectionRow({ conn, testStatus, testError, isAdmin, onTest, onEdit, onDelete }: {
  conn: DbConnection
  testStatus?: 'testing' | 'ok' | 'fail'
  testError?: string
  isAdmin: boolean
  onTest: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  const color = DB_COLORS[conn.db_type] ?? 'var(--text-muted)'
  const label = DB_LABELS[conn.db_type] ?? conn.db_type

  return (
    <div className="card p-4">
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-[9px] flex items-center justify-center shrink-0" style={{ background: `${color}22`, border: `1px solid ${color}55`, color }}>
          <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 mb-1">
            <span className="text-sm font-semibold text-text-primary">{conn.name}</span>
            <span className="mono text-[10.5px] py-px px-1.5 rounded bg-surface2 text-text-3">{label}</span>
            {testStatus === 'ok'   && <StatusBadge status="success" label="Healthy" />}
            {testStatus === 'fail' && <StatusBadge status="failed"  label="Unreachable" />}
          </div>
          <div className="mono text-[11.5px] text-text-muted">{conn.db_type} · {conn.is_default ? 'default' : 'not default'}</div>
          {testStatus === 'fail' && testError && (
            <div className="mono text-[11px] text-failure mt-1 break-all">{testError}</div>
          )}
        </div>
        <div className="flex gap-6 text-[11.5px] shrink-0">
          <StatCol label="Type"    value={label} />
          <StatCol label="Default" value={conn.is_default ? 'Yes' : 'No'} />
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
