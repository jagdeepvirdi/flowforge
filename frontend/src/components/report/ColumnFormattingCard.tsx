import { Plus, Trash2, X } from 'lucide-react'
import type { ColumnFormatRule, ColumnConditionalRule } from '../../lib/types'

const NUMBER_FORMAT_PRESETS = [
  { label: 'Integer',       value: '#,##0' },
  { label: '2 decimals',    value: '#,##0.00' },
  { label: 'Currency $',    value: '$#,##0.00' },
  { label: 'Percentage',    value: '0.00%' },
  { label: 'Date DD/MM/YY', value: 'DD/MM/YYYY' },
  { label: 'Date MM/DD/YY', value: 'MM/DD/YYYY' },
  { label: 'Date ISO',      value: 'YYYY-MM-DD' },
  { label: 'Datetime',      value: 'YYYY-MM-DD HH:MM:SS' },
]

const OPERATORS: { value: ColumnConditionalRule['operator']; label: string }[] = [
  { value: 'lt',  label: '<' },
  { value: 'lte', label: '≤' },
  { value: 'gt',  label: '>' },
  { value: 'gte', label: '≥' },
  { value: 'eq',  label: '=' },
  { value: 'ne',  label: '≠' },
]

export default function ColumnFormattingCard({
  rules, setRules,
}: {
  rules: ColumnFormatRule[]
  setRules: React.Dispatch<React.SetStateAction<ColumnFormatRule[]>>
}) {
  const updateRule = (i: number, patch: Partial<ColumnFormatRule>) =>
    setRules(prev => prev.map((r, j) => j === i ? { ...r, ...patch } : r))

  const addCond = (i: number) =>
    setRules(prev => prev.map((r, j) => j === i
      ? { ...r, conditional: [...(r.conditional ?? []), { operator: 'lt', value: 0, bg_color: 'FFC7CE', font_color: '9C0006' }] }
      : r))

  const updateCond = (ri: number, ci: number, patch: Partial<ColumnConditionalRule>) =>
    setRules(prev => prev.map((r, j) => j === ri
      ? { ...r, conditional: (r.conditional ?? []).map((c, k) => k === ci ? { ...c, ...patch } : c) }
      : r))

  const removeCond = (ri: number, ci: number) =>
    setRules(prev => prev.map((r, j) => j === ri
      ? { ...r, conditional: (r.conditional ?? []).filter((_, k) => k !== ci) }
      : r))

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold">Column Formatting</div>
        <button type="button" className="btn btn-sm"
          onClick={() => setRules(r => [...r, { column: '', number_format: '', width: undefined, conditional: [] }])}>
          <Plus size={10} /> Add rule
        </button>
      </div>
      {rules.length === 0 && (
        <p className="text-xs text-text-muted m-0">
          No formatting rules. Add one to apply number formats and conditional cell colours to Excel output.
        </p>
      )}
      {rules.map((rule, i) => (
        <div key={i} className="border border-border rounded-[7px] py-2.5 px-3 flex flex-col gap-2">
          {/* Rule header */}
          <div className="flex items-center gap-2">
            <input
              className="input flex-1 h-7 text-xs"
              placeholder="Column name (exact)"
              value={rule.column}
              onChange={e => updateRule(i, { column: e.target.value })}
            />
            <select
              className="input h-7 text-xs max-w-40"
              value={rule.number_format ?? ''}
              onChange={e => updateRule(i, { number_format: e.target.value })}
            >
              <option value="">Number format…</option>
              {NUMBER_FORMAT_PRESETS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
            <input
              className="input mono-input w-20 h-7 text-xs"
              placeholder="custom"
              value={rule.number_format ?? ''}
              onChange={e => updateRule(i, { number_format: e.target.value })}
            />
            <input
              className="input w-14 h-7 text-xs"
              type="number"
              placeholder="width"
              value={rule.width ?? ''}
              onChange={e => updateRule(i, { width: e.target.value ? Number(e.target.value) : undefined })}
              min={3} max={255}
            />
            <button type="button" onClick={() => setRules(r => r.filter((_, j) => j !== i))}
              className="bg-transparent border-none cursor-pointer text-text-muted py-0.5 px-1">
              <Trash2 size={12} />
            </button>
          </div>

          {/* Conditional rules */}
          {(rule.conditional ?? []).map((cond, ci) => (
            <div key={ci} className="flex items-center gap-1.5 pl-2 border-l-2 border-border">
              <span className="text-[11px] text-text-muted whitespace-nowrap">if value</span>
              <select className="input w-[46px] h-[26px] text-xs px-1"
                value={cond.operator}
                onChange={e => updateCond(i, ci, { operator: e.target.value as ColumnConditionalRule['operator'] })}>
                {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <input className="input w-16 h-[26px] text-xs" type="number"
                value={cond.value} onChange={e => updateCond(i, ci, { value: Number(e.target.value) })} />
              <span className="text-[11px] text-text-muted">bg</span>
              <input type="color" value={`#${cond.bg_color}`}
                onChange={e => updateCond(i, ci, { bg_color: e.target.value.slice(1) })}
                className="w-7 h-[26px] cursor-pointer border border-border rounded p-px" />
              <span className="text-[11px] text-text-muted">text</span>
              <input type="color" value={cond.font_color ? `#${cond.font_color}` : '#000000'}
                onChange={e => updateCond(i, ci, { font_color: e.target.value.slice(1) })}
                className="w-7 h-[26px] cursor-pointer border border-border rounded p-px" />
              <button type="button" onClick={() => removeCond(i, ci)}
                className="bg-transparent border-none cursor-pointer text-text-muted py-0.5 px-1">
                <X size={11} />
              </button>
            </div>
          ))}
          <button type="button" className="btn btn-sm self-start text-[11px]"
            onClick={() => addCond(i)}>
            <Plus size={9} /> Add condition
          </button>
        </div>
      ))}
    </div>
  )
}
