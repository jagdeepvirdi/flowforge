import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, GripVertical, Copy } from 'lucide-react'
import type { PipelineStep } from '../../lib/types'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import FieldTooltip from '../shared/FieldTooltip'
import { stepMeta } from './stepMeta'
import StepConfigForm from './StepConfigForm'

type Props = Readonly<{
  step: PipelineStep
  onChange: (id: string, updates: Partial<PipelineStep>) => void
  onDelete: (id: string) => void
  onDuplicate: (id: string) => void
  allSteps: PipelineStep[]
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}>


export default function StepEditor({ step, onChange, onDelete, onDuplicate, allSteps, dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs }: Props) {
  const [expanded, setExpanded] = useState(true)
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: step.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  const cfg = step.config
  const setConfig = (key: string, value: unknown) =>
    onChange(step.id, { config: { ...cfg, [key]: value } })

  const meta = stepMeta(step.step_type)

  return (
    <div ref={setNodeRef} style={style} className="mb-1.5">
      <div className={`rounded-[10px] overflow-hidden border ${expanded ? 'bg-surface' : 'bg-bg-code'} ${step.parallel_group ? 'border-indigo-500/50' : expanded ? 'border-border-strong' : 'border-border'} ${step.parallel_group ? 'border-l-[3px] border-l-indigo-500' : ''}`}>
        {/* Header */}
        <div className="flex items-center gap-2.5 py-3 px-3.5">
          <button {...attributes} {...listeners} className="bg-transparent border-none text-text-dim cursor-grab p-0.5 flex">
            <GripVertical size={14} />
          </button>

          <span className="font-mono text-[11px] text-text-dim font-bold w-5 text-center shrink-0">
            {step.step_order}
          </span>

          <span className={`tbadge ${meta.cls}`}>{meta.label}</span>
          {step.parallel_group && (
            <span className="text-[10px] font-semibold py-px px-[5px] rounded-[3px] bg-indigo-500/15 text-indigo-400 font-mono whitespace-nowrap">
              ∥ {step.parallel_group}
            </span>
          )}

          <input
            className="bg-transparent border-none outline-none text-text-primary text-[13px] font-medium flex-1 font-[inherit] cursor-text"
            value={step.name}
            onChange={e => onChange(step.id, { name: e.target.value })}
            placeholder="Step name"
          />

          <div className="flex items-center gap-1">
            <select
              className="btn btn-sm cursor-pointer text-[11px] h-[26px] py-0 px-2"
              value={step.on_error}
              onChange={e => onChange(step.id, { on_error: e.target.value as 'stop' | 'continue' })}
            >
              <option value="stop">Stop on error</option>
              <option value="continue">Continue on error</option>
            </select>
            <FieldTooltip field="on_error" />
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[11px] text-text-muted whitespace-nowrap">Retries</span>
            <input
              type="number" min={0} max={10}
              className="input w-[46px] h-[26px] py-0 px-1.5 text-[11px]"
              value={Number(cfg.retry_count ?? 0)}
              onChange={e => setConfig('retry_count', Math.max(0, Number(e.target.value)))}
            />
            <span className="text-[11px] text-text-muted whitespace-nowrap">delay</span>
            <input
              type="number" min={0} max={3600}
              className="input w-[52px] h-[26px] py-0 px-1.5 text-[11px]"
              value={Number(cfg.retry_delay_seconds ?? 30)}
              onChange={e => setConfig('retry_delay_seconds', Math.max(0, Number(e.target.value)))}
            />
            <span className="text-[11px] text-text-muted">s</span>
          </div>

          <div className="flex items-center gap-1" title="Steps sharing the same group name run concurrently">
            <span className="text-[11px] text-text-muted whitespace-nowrap">∥ Group</span>
            <input
              className="input mono-input w-[72px] h-[26px] py-0 px-1.5 text-[11px]"
              placeholder="none"
              value={step.parallel_group ?? ''}
              onChange={e => onChange(step.id, { parallel_group: e.target.value.trim() || null })}
            />
          </div>

          <button onClick={() => setExpanded(x => !x)} className="btn btn-sm btn-ghost btn-icon">
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <button onClick={() => onDuplicate(step.id)} className="btn btn-sm btn-ghost btn-icon text-text-muted hover:text-text" title="Duplicate step">
            <Copy size={13} />
          </button>
          <button onClick={() => onDelete(step.id)} className="btn btn-sm btn-ghost btn-icon text-text-muted hover:text-failure-text">
            <Trash2 size={13} />
          </button>
        </div>

        {expanded && (
          <div className="pt-3 pr-3.5 pb-3.5 pl-3.5 border-t border-border">
            <StepConfigForm
              step={step}
              onChange={onChange}
              allSteps={allSteps}
              dbConnections={dbConnections}
              reportConfigs={reportConfigs}
              emailConfigs={emailConfigs}
              bulkLoadConfigs={bulkLoadConfigs}
            />
          </div>
        )}
      </div>
    </div>
  )
}
