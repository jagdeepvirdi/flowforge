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
      <div className="flex gap-0 rounded-r-sm overflow-hidden border border-border-strong w-fit">
        {(['file', 'query'] as const).map(t => (
          <button
            key={t}
            type="button"
            onClick={() => switchSourceType(t)}
            className={`py-[5px] px-4 text-xs font-semibold border-none cursor-pointer transition-colors duration-150 ${sourceType === t ? 'bg-accent text-white' : 'bg-transparent text-text-muted'}`}
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
              <div className="flex flex-wrap gap-1.5 mb-2">
                {precedingFileSteps.map(rs => {
                  const stepRef = rs.name.includes(' ') ? `steps['${rs.name}']` : `steps.${rs.name}`
                  const variable = `{{ ${stepRef}.output_path }}`
                  const already = String(src.file_path ?? '') === variable
                  return (
                    <button
                      key={rs.id}
                      type="button"
                      onClick={() => { if (!already) setSrc('file_path', variable) }}
                      className={`flex items-center gap-1.5 rounded-r-sm py-1 px-2.5 text-[11px] border ${already ? 'bg-[#1a2e1a] border-success text-success cursor-default' : 'bg-surface border-border-strong text-text-3 cursor-pointer'}`}
                    >
                      <span className={`font-semibold ${already ? 'text-success' : 'text-accent'}`}>
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

          <div className="grid grid-cols-2 gap-2.5">
            <Field label="File format">
              <select
                className="input"
                value={String(src.file_format ?? '')}
                onChange={e => setSrc('file_format', e.target.value)}
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
            >
              <option value="">Select source connection…</option>
              {dbConnections.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </Field>
          <Field label="SQL Query">
            <textarea
              className="input mono-input !h-auto !resize-none"
              rows={5}
              value={String(src.query ?? '')}
              onChange={e => setSrc('query', e.target.value)}
              placeholder={`SELECT id, name, amount\nFROM orders\nWHERE month = '{{ current_month }}'`}
            />
          </Field>
        </>
      )}

      {/* ── Target ───────────────────────────────────────────────────────── */}
      <div className="border-t border-border pt-2.5 flex flex-col gap-2.5">
        <Field label="Target connection">
          <select
            className="input"
            value={String(cfg.target_connection_id ?? '')}
            onChange={e => setConfig('target_connection_id', e.target.value)}
          >
            <option value="">Select target connection…</option>
            {dbConnections.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-[1fr_auto] gap-2.5 items-end">
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
              className="input !w-[120px]"
              value={String(cfg.mode ?? 'replace')}
              onChange={e => setConfig('mode', e.target.value)}
            >
              <option value="replace">Replace</option>
              <option value="append">Append</option>
            </select>
          </Field>
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={Boolean(cfg.create_if_missing)}
            onChange={e => setConfig('create_if_missing', e.target.checked)}
          />
          <span className="text-[12.5px] text-text-2">
            Create table if it doesn't exist
          </span>
        </label>
        {!!cfg.create_if_missing && (
          <span className="text-[11px] text-text-muted pl-[22px]">
            Column types are inferred from the data (INTEGER, NUMERIC, DATE, TIMESTAMP, TEXT). Samples up to 1,000 rows.
          </span>
        )}
      </div>

      {/* ── Advanced (collapsible) ────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setShowAdvanced(x => !x)}
        className="flex items-center gap-1.5 bg-transparent border-none text-text-muted text-[11.5px] cursor-pointer py-0.5 px-0 font-medium"
      >
        <Settings2 size={12} />
        Advanced options
        {showAdvanced ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {showAdvanced && (
        <div className="flex flex-col gap-2.5 pl-3 border-l-2 border-border">
          <Field label="Chunk size (rows per batch)">
            <input
              className="input !w-[120px]"
              type="number"
              min={1}
              max={10000}
              value={String(cfg.chunk_size ?? 1000)}
              onChange={e => setConfig('chunk_size', Number.parseInt(e.target.value) || 1000)}
            />
            <span className="text-[11px] text-text-muted mt-[3px]">
              Rows sent per bulk insert call. Default 1000.
            </span>
          </Field>
          <Field label="Column map (JSON) — optional">
            <textarea
              className="input mono-input !h-auto !resize-none !text-xs"
              rows={4}
              value={columnMapRaw}
              onChange={e => {
                try { setConfig('column_map', JSON.parse(e.target.value)) } catch { /* invalid JSON while typing — ignore */ }
              }}
              placeholder={'{\n  "SOURCE_COL": "target_col"\n}'}
            />
            <span className="text-[11px] text-text-muted mt-[3px]">
              Rename source columns to match the target schema. Leave empty to use source names as-is.
            </span>
          </Field>
        </div>
      )}
    </>
  )
}
