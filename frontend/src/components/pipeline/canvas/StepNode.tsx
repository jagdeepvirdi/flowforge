import { Handle, Position, type NodeProps, type Node } from '@xyflow/react'
import { Copy, Trash2 } from 'lucide-react'
import { stepMeta } from '../stepMeta'
import type { PipelineStep } from '../../../lib/types'

export type StepNodeData = {
  step: PipelineStep
  onDuplicate: (id: string) => void
  onDelete: (id: string) => void
}

export type StepFlowNode = Node<StepNodeData, 'step'>

export default function StepNode({ data, selected }: NodeProps<StepFlowNode>) {
  const { step, onDuplicate, onDelete } = data
  const meta = stepMeta(step.step_type)

  return (
    <div
      className={`group rounded-[10px] border bg-surface px-3 py-2.5 w-[220px] cursor-pointer transition-colors ${
        selected ? 'border-accent shadow-[0_0_0_2px_var(--accent-soft)]' : step.parallel_group ? 'border-indigo-500/50' : 'border-border-strong'
      } ${step.parallel_group ? 'border-l-[3px] border-l-indigo-500' : ''}`}
      data-testid={`canvas-node-${step.id}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-border-strong !border-none !w-1.5 !h-1.5" />
      <Handle type="source" position={Position.Right} className="!bg-border-strong !border-none !w-1.5 !h-1.5" />

      <div className="flex items-center gap-1.5 mb-1">
        <span className="font-mono text-[10px] text-text-dim font-bold shrink-0">{step.step_order}</span>
        <span className={`tbadge ${meta.cls}`}>{meta.label}</span>
        {step.parallel_group && (
          <span className="text-[9px] font-semibold py-px px-[4px] rounded-[3px] bg-indigo-500/15 text-indigo-400 font-mono whitespace-nowrap ml-auto">
            ∥ {step.parallel_group}
          </span>
        )}
      </div>

      <div className="text-[12.5px] font-medium text-text-primary truncate" title={step.name}>
        {step.name}
      </div>

      <div className="flex items-center justify-end gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={e => { e.stopPropagation(); onDuplicate(step.id) }}
          className="btn btn-sm btn-ghost btn-icon text-text-muted hover:text-text"
          title="Duplicate step"
        >
          <Copy size={11} />
        </button>
        <button
          onClick={e => { e.stopPropagation(); onDelete(step.id) }}
          className="btn btn-sm btn-ghost btn-icon text-text-muted hover:text-failure-text"
          title="Delete step"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  )
}
