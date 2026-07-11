import { Plus, Trash2 } from 'lucide-react'
import CollapsibleCard from '../shared/CollapsibleCard'

export type PipelineVar = { key: string; value: string; is_secret: boolean }

export default function PipelineVariablesCard({ vars, setVars }: {
  vars: PipelineVar[]
  setVars: React.Dispatch<React.SetStateAction<PipelineVar[]>>
}) {
  const updateVar = (i: number, updates: Partial<PipelineVar>) => {
    setVars(prev => prev.map((v, j) => j === i ? { ...v, ...updates } : v))
  }
  const removeVar = (i: number) => {
    setVars(prev => prev.filter((_, j) => j !== i))
  }
  const addVar = () => {
    setVars(v => [...v, { key: '', value: '', is_secret: false }])
  }

  return (
    <CollapsibleCard
      title="Pipeline Variables"
      headerExtra={
        <span className="text-[11px] text-[var(--text-muted)]">
          available as <code className="text-[11px] bg-[var(--surface)] p-[1px_5px] rounded-[3px]">{'{{ var_name }}'}</code> in all step configs
        </span>
      }
      actions={
        <button type="button" className="btn btn-sm" onClick={addVar}>
          <Plus size={10} /> Add variable
        </button>
      }
    >
      {vars.length === 0 ? (
        <p className="text-xs text-[var(--text-muted)] m-0">
          No variables. Add one to pass constants like currency codes, environment names, or date ranges to all steps.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 pb-1 border-b border-[var(--border)]">
            {(['Name', 'Value', 'Secret', ''] as const).map(h => (
              <span key={h} className="text-[11px] text-[var(--text-muted)] font-semibold">{h}</span>
            ))}
          </div>
          {vars.map((v, i) => ({ v, i })).map(({ v, i }) => (
            <div key={v.key + ':' + i} className="grid grid-cols-[1fr_1fr_auto_auto] gap-2 items-center">
              <input
                className="input mono-input text-xs h-[30px]"
                placeholder="currency"
                value={v.key}
                onChange={e => updateVar(i, { key: e.target.value })}
              />
              <input
                className="input text-xs h-[30px]"
                placeholder={v.is_secret ? '(unchanged)' : 'USD'}
                value={v.value}
                type={v.is_secret ? 'password' : 'text'}
                onChange={e => updateVar(i, { value: e.target.value })}
              />
              <label className="flex items-center gap-1.5 cursor-pointer whitespace-nowrap text-xs text-[var(--text-muted)]">
                <input
                  type="checkbox"
                  checked={v.is_secret}
                  onChange={e => updateVar(i, { is_secret: e.target.checked })}
                />{' '}
                Secret
              </label>
              <button
                type="button"
                onClick={() => removeVar(i)}
                className="bg-transparent border-none text-[var(--failure)] cursor-pointer p-1"
                title="Remove variable"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <p className="text-[11px] text-[var(--text-muted)] mt-1 mb-0">
            Built-in date vars: <code className="text-[11px]">{'{{ current_date }}'}</code> <code className="text-[11px]">{'{{ month_start_ts }}'}</code> <code className="text-[11px]">{'{{ prev_month_start_ts }}'}</code> <code className="text-[11px]">{'{{ last_success_at }}'}</code>
          </p>
        </div>
      )}
    </CollapsibleCard>
  )
}
