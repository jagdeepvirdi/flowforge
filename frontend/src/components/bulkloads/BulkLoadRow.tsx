import { Pencil, Trash2, UploadCloud } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import Spinner from '../shared/Spinner'
import StatCol from '../connections/StatCol'
import type { BulkLoadConfig } from '../../lib/types'
import type { BulkLoadPreview } from '../../lib/api'

const ACCENT = '#FB923C'

export default function BulkLoadRow({ config, testStatus, testError, testResult, onTest, onEdit, onDelete }: {
  config: BulkLoadConfig
  testStatus?: 'testing' | 'ok' | 'warn' | 'fail'
  testError?: string
  testResult?: BulkLoadPreview
  onTest: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: 9, background: `${ACCENT}22`, border: `1px solid ${ACCENT}55`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: ACCENT, flexShrink: 0 }}>
          <UploadCloud size={18} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{config.name}</span>
            <span className="tbadge tbadge-bulk">{(config.file_type || 'csv').toUpperCase()}</span>
            {testStatus === 'ok'   && <StatusBadge status="success" label="Verified" />}
            {testStatus === 'warn' && <StatusBadge status="warn"    label="Verified · warnings" />}
            {testStatus === 'fail' && <StatusBadge status="failed"  label="Failed" />}
          </div>
          <div className="mono" style={{ fontSize: 11.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            <span>{config.source_directory || '—'}</span>
            {' → '}
            <span>{config.target_table || '—'}</span>
          </div>
          {testStatus === 'fail' && testError && (
            <div className="mono" style={{ fontSize: 11, color: 'var(--failure)', marginTop: 4, wordBreak: 'break-all' }}>{testError}</div>
          )}
          {testStatus === 'warn' && testResult && (
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
              {testResult.file_name} · {testResult.insert_error_summary
                ? testResult.insert_error_summary
                : `${testResult.warnings.length} warning${testResult.warnings.length === 1 ? '' : 's'}: ${testResult.warnings[0]}`}
            </div>
          )}
          {testStatus === 'ok' && testResult && (
            <div className="mono" style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}>
              {testResult.file_name} · {testResult.columns.length} columns · {testResult.files_matched} file{testResult.files_matched === 1 ? '' : 's'} matched
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: 11.5, flexShrink: 0 }}>
          <StatCol label="Mode" value={config.load_mode} />
          <StatCol label="Files" value={testResult ? String(testResult.files_matched) : '—'} />
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button className="btn btn-sm" onClick={onTest} disabled={testStatus === 'testing'}>
            {testStatus === 'testing'
              ? <Spinner size={11} />
              : <span style={{ width: 6, height: 6, borderRadius: '50%', background: testStatus === 'ok' ? 'var(--success-text)' : testStatus === 'warn' ? '#EAB308' : testStatus === 'fail' ? 'var(--failure)' : 'var(--text-muted)' }} />}
            Test
          </button>
          <button className="btn btn-sm btn-ghost btn-icon" onClick={onEdit}><Pencil size={12} /></button>
          <button className="btn btn-sm btn-ghost btn-icon" onClick={onDelete}><Trash2 size={12} /></button>
        </div>
      </div>
    </div>
  )
}
