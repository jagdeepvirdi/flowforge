import Field from './Field'
import type { StepFormProps } from './types'

export default function BulkLoadForm({ cfg, setConfig, bulkLoadConfigs }: StepFormProps) {
  const selected = bulkLoadConfigs.find(c => c.id === cfg.bulk_load_config_id)
  return (
    <>
      <Field label="Bulk load config">
        <select className="input" value={String(cfg.bulk_load_config_id ?? '')} onChange={e => setConfig('bulk_load_config_id', e.target.value)}>
          <option value="">Select bulk load config…</option>
          {bulkLoadConfigs.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </Field>
      {selected && (
        <div className="text-[11.5px] text-text-muted bg-bg-code rounded-r-sm py-[7px] px-2.5 leading-[1.7]">
          <span className="mono text-text-3">{selected.source_directory}</span>
          <span className="text-text-dim"> → </span>
          <span className="mono text-text-3">{selected.target_table}</span>
        </div>
      )}
      {bulkLoadConfigs.length === 0 && (
        <div className="text-xs text-text-muted">
          No bulk load configs yet. <a href="/bulk-loads/new" className="text-accent-text">Create one</a> on the Bulk Loads page first.
        </div>
      )}
    </>
  )
}
