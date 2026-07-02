import { useState } from 'react'
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react'
import Field from './Field'
import type { StepFormProps } from './types'

export default function DataLoadForm({ cfg, setConfig, allSteps, step, dbConnections }: StepFormProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const src = (cfg.source as Record<string, unknown>) ?? {}
  const sourceType = String(src.type ?? 'file')

  const setSrc = (key: string, value: unknown) =>
    setConfig('source', { ...src, [key]: value })

  const switchSourceType = (type: string) =>
    setConfig('source', { type })

  // Preceding steps that produce a file (report steps)
  const precedingFileSteps = allSteps.filter(
    s => s.step_type === 'report' && s.step_order < step.step_order
  )

  const columnMapRaw = cfg.column_map
    ? JSON.stringify(cfg.column_map, null, 2)
    : '{}'

  return (
    <>
      {/* Source type toggle */}
      <div style={{ display: 'flex', gap: 0, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border-strong)', width: 'fit-content' }}>
        {(['file', 'query'] as const).map(t => (
          <button
            key={t}
            type="button"
            onClick={() => switchSourceType(t)}
            style={{
              padding: '5px 16px',
              fontSize: 12,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: sourceType === t ? 'var(--accent)' : 'transparent',
              color: sourceType === t ? '#fff' : 'var(--text-muted)',
              transition: 'background 0.15s',
            }}
          >
            {t === 'file' ? 'File source' : 'SQL Query source'}
          </button>
        ))}
      </div>

      {/* ── File source ───────────────────────────────────────────────────── */}
      {sourceType === 'file' && (
        <>
          <Field label="File path (supports {{ variables }})">
            {/* Quick-attach from preceding report steps */}
            {precedingFileSteps.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                {precedingFileSteps.map(rs => {
                  const stepRef = rs.name.includes(' ') ? `steps['${rs.name}']` : `steps.${rs.name}`
                  const variable = `{{ ${stepRef}.output_path }}`
                  const already = String(src.file_path ?? '') === variable
                  return (
                    <button
                      key={rs.id}
                      type="button"
                      onClick={() => { if (!already) setSrc('file_path', variable) }}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        background: already ? '#1a2e1a' : 'var(--surface)',
                        border: `1px solid ${already ? 'var(--success)' : 'var(--border-strong)'}`,
                        borderRadius: 6, padding: '4px 10px',
                        cursor: already ? 'default' : 'pointer',
                        fontSize: 11,
                        color: already ? 'var(--success)' : 'var(--text-3)',
                      }}
                    >
                      <span style={{ fontWeight: 600, color: already ? 'var(--success)' : 'var(--accent)' }}>
                        {already ? '✓' : '+'} {rs.name}
                      </span>
                    </button>
                  )
                })}
              </div>
            )}
            <input
              className="input mono-input"
              value={String(src.file_path ?? '')}
              onChange={e => setSrc('file_path', e.target.value)}
              placeholder="{{ steps.generate_report.output_path }}"
            />
          </Field>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <Field label="File format">
              <select
                className="input"
                value={String(src.file_format ?? '')}
                onChange={e => setSrc('file_format', e.target.value)}
                style={{ height: 34 }}
              >
                <option value="">Auto-detect from extension</option>
                <option value="csv">CSV</option>
                <option value="excel">Excel (.xlsx)</option>
              </select>
            </Field>
            <Field label="Sheet name (Excel only, optional)">
              <input
                className="input"
                value={String(src.sheet_name ?? '')}
                onChange={e => setSrc('sheet_name', e.target.value)}
                placeholder="Sheet1"
              />
            </Field>
          </div>
        </>
      )}

      {/* ── SQL Query source ──────────────────────────────────────────────── */}
      {sourceType === 'query' && (
        <>
          <Field label="Source connection">
            <select
              className="input"
              value={String(src.connection_id ?? '')}
              onChange={e => setSrc('connection_id', e.target.value)}
              style={{ height: 34 }}
            >
              <option value="">Select source connection…</option>
              {dbConnections.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </Field>
          <Field label="SQL Query">
            <textarea
              className="input mono-input"
              rows={5}
              value={String(src.query ?? '')}
              onChange={e => setSrc('query', e.target.value)}
              placeholder={`SELECT id, name, amount\nFROM orders\nWHERE month = '{{ current_month }}'`}
              style={{ height: 'auto', resize: 'none' }}
            />
          </Field>
        </>
      )}

      {/* ── Target ───────────────────────────────────────────────────────── */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Field label="Target connection">
          <select
            className="input"
            value={String(cfg.target_connection_id ?? '')}
            onChange={e => setConfig('target_connection_id', e.target.value)}
            style={{ height: 34 }}
          >
            <option value="">Select target connection…</option>
            {dbConnections.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </Field>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 10, alignItems: 'end' }}>
          <Field label="Target table (supports {{ variables }})">
            <input
              className="input mono-input"
              value={String(cfg.target_table ?? '')}
              onChange={e => setConfig('target_table', e.target.value)}
              placeholder="staging.sales_{{ current_month }}"
            />
          </Field>
          <Field label="Mode">
            <select
              className="input"
              value={String(cfg.mode ?? 'replace')}
              onChange={e => setConfig('mode', e.target.value)}
              style={{ height: 34, width: 120 }}
            >
              <option value="replace">Replace</option>
              <option value="append">Append</option>
            </select>
          </Field>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
          <input
            type="checkbox"
            checked={Boolean(cfg.create_if_missing)}
            onChange={e => setConfig('create_if_missing', e.target.checked)}
          />
          <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
            Create table if it doesn't exist
          </span>
        </label>
        {!!cfg.create_if_missing && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)', paddingLeft: 22 }}>
            Column types are inferred from the data (INTEGER, NUMERIC, DATE, TIMESTAMP, TEXT). Samples up to 1,000 rows.
          </span>
        )}
      </div>

      {/* ── Advanced (collapsible) ────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setShowAdvanced(x => !x)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'transparent', border: 'none',
          color: 'var(--text-muted)', fontSize: 11.5, cursor: 'pointer',
          padding: '2px 0', fontWeight: 500,
        }}
      >
        <Settings2 size={12} />
        Advanced options
        {showAdvanced ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {showAdvanced && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingLeft: 12, borderLeft: '2px solid var(--border)' }}>
          <Field label="Chunk size (rows per batch)">
            <input
              className="input"
              type="number"
              min={1}
              max={10000}
              value={String(cfg.chunk_size ?? 1000)}
              onChange={e => setConfig('chunk_size', Number.parseInt(e.target.value) || 1000)}
              style={{ width: 120 }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
              Rows sent per bulk insert call. Default 1000.
            </span>
          </Field>
          <Field label="Column map (JSON) — optional">
            <textarea
              className="input mono-input"
              rows={4}
              value={columnMapRaw}
              onChange={e => {
                try { setConfig('column_map', JSON.parse(e.target.value)) } catch { /* invalid JSON while typing — ignore */ }
              }}
              placeholder={'{\n  "SOURCE_COL": "target_col"\n}'}
              style={{ height: 'auto', resize: 'none', fontSize: 12 }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
              Rename source columns to match the target schema. Leave empty to use source names as-is.
            </span>
          </Field>
        </div>
      )}
    </>
  )
}
