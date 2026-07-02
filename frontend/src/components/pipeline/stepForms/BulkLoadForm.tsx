import Field from './Field'
import type { StepFormProps } from './types'

export default function BulkLoadForm({ cfg, setConfig, bulkLoadConfigs }: StepFormProps) {
  const selected = bulkLoadConfigs.find(c => c.id === cfg.bulk_load_config_id)
  return (
    <>
      <Field label="Bulk load config">
        <select className="input" value={String(cfg.bulk_load_config_id ?? '')} onChange={e => setConfig('bulk_load_config_id', e.target.value)} style={{ height: 34 }}>
          <option value="">Select bulk load config…</option>
          {bulkLoadConfigs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      {selected && (
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', background: 'var(--bg-code)', borderRadius: 6, padding: '7px 10px', lineHeight: 1.7 }}>
          <span className="mono" style={{ color: 'var(--text-3)' }}>{selected.source_directory}</span>
          <span style={{ color: 'var(--text-dim)' }}> → </span>
          <span className="mono" style={{ color: 'var(--text-3)' }}>{selected.target_table}</span>
        </div>
      )}
      {bulkLoadConfigs.length === 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          No bulk load configs yet. <a href="/bulk-loads/new" style={{ color: 'var(--accent-text)' }}>Create one</a> on the Bulk Loads page first.
        </div>
      )}
    </>
  )
}
