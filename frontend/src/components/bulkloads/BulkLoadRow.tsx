import { Pencil, Trash2, UploadCloud, Copy } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import Spinner from '../shared/Spinner'
import StatCol from '../connections/StatCol'
import type { BulkLoadConfig } from '../../lib/types'
import type { BulkLoadPreview } from '../../lib/api'

export default function BulkLoadRow({ config, testStatus, testError, testResult, onTest, onEdit, onClone, onDelete }: {
  config: BulkLoadConfig
  testStatus?: 'testing' | 'ok' | 'warn' | 'fail'
  testError?: string
  testResult?: BulkLoadPreview
  onTest: () => void
  onEdit: () => void
  onClone: () => void
  onDelete: () => void
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-[9px] flex items-center justify-center shrink-0 bg-[#FB923C22] border border-[#FB923C55] text-[#FB923C]">
          <UploadCloud size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 mb-1">
            <span className="text-sm font-semibold text-text-primary">{config.name}</span>
            <span className="tbadge tbadge-bulk">{(config.file_type || 'csv').toUpperCase()}</span>
            {testStatus === 'ok'   && <StatusBadge status="success" label="Verified" />}
            {testStatus === 'warn' && <StatusBadge status="warn"    label="Verified · warnings" />}
            {testStatus === 'fail' && <StatusBadge status="failed"  label="Failed" />}
          </div>
          <div className="mono text-[11.5px] text-text-muted overflow-hidden text-ellipsis whitespace-nowrap">
            <span>{config.source_directory || '—'}</span>
            {' → '}
            <span>{config.target_table || '—'}</span>
          </div>
          {testStatus === 'fail' && testError && (
            <div className="mono text-[11px] text-failure mt-1 break-all">{testError}</div>
          )}
          {testStatus === 'warn' && testResult && (
            <div className="text-[11px] text-text-3 mt-1">
              {testResult.file_name} · {testResult.insert_error_summary
                ? testResult.insert_error_summary
                : `${testResult.warnings.length} warning${testResult.warnings.length === 1 ? '' : 's'}: ${testResult.warnings[0]}`}
            </div>
          )}
          {testStatus === 'ok' && testResult && (
            <div className="mono text-[11px] text-text-3 mt-1">
              {testResult.file_name} · {testResult.columns.length} columns · {testResult.files_matched} file{testResult.files_matched === 1 ? '' : 's'} matched
            </div>
          )}
        </div>
        <div className="flex gap-6 text-[11.5px] shrink-0">
          <StatCol label="Mode" value={config.load_mode} />
          <StatCol label="Files" value={testResult ? String(testResult.files_matched) : '—'} />
        </div>
        <div className="flex gap-1.5 shrink-0">
          <button className="btn btn-sm" onClick={onTest} disabled={testStatus === 'testing'}>
            {testStatus === 'testing'
              ? <Spinner size={11} />
              : <span className={`w-1.5 h-1.5 rounded-full ${testStatus === 'ok' ? 'bg-success-text' : testStatus === 'warn' ? 'bg-yellow-500' : testStatus === 'fail' ? 'bg-failure' : 'bg-text-muted'}`} />}
            Test
          </button>
          <button className="btn btn-sm btn-ghost btn-icon" title="Edit" onClick={onEdit}><Pencil size={12} /></button>
          <button className="btn btn-sm btn-ghost btn-icon" title="Clone" onClick={onClone}><Copy size={12} /></button>
          <button className="btn btn-sm btn-ghost btn-icon" title="Delete" onClick={onDelete}><Trash2 size={12} /></button>
        </div>
      </div>
    </div>
  )
}
