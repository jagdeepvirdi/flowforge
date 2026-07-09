import type { PipelineStep } from '../../lib/types'
import FieldTooltip from '../shared/FieldTooltip'
import StepConfigForm from './StepConfigForm'

type Props = Readonly<{
  step: PipelineStep
  onChange: (id: string, updates: Partial<PipelineStep>) => void
  allSteps: PipelineStep[]
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}>

/**
 * Full vertical step editor body: identity fields (name/on_error/retry/
 * parallel_group) plus the shared `StepConfigForm` dispatch. Used by the
 * canvas side panel, where a vertical, single-column layout is the natural
 * fit (the list view keeps its own compact horizontal header for these same
 * fields — see `StepEditor.tsx`).
 */
export default function StepConfigBody({ step, onChange, allSteps, dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs }: Props) {
  const cfg = step.config

  return (
    <div className="flex flex-col gap-3">
      <div className="field">
        <label htmlFor={`panel-step-name-${step.id}`}>Name</label>
        <input
          id={`panel-step-name-${step.id}`}
          className="input"
          value={step.name}
          onChange={e => onChange(step.id, { name: e.target.value })}
          placeholder="Step name"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="field">
          <label className="flex items-center gap-1">On error <FieldTooltip field="on_error" /></label>
          <select
            className="input cursor-pointer"
            value={step.on_error}
            onChange={e => onChange(step.id, { on_error: e.target.value as 'stop' | 'continue' })}
          >
            <option value="stop">Stop on error</option>
            <option value="continue">Continue on error</option>
          </select>
        </div>
        <div className="field" title="Steps sharing the same group name run concurrently">
          <label>∥ Group</label>
          <input
            className="input mono-input"
            placeholder="none"
            value={step.parallel_group ?? ''}
            onChange={e => onChange(step.id, { parallel_group: e.target.value.trim() || null })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="field">
          <label>Retry count</label>
          <input
            type="number" min={0} max={10}
            className="input"
            value={Number(cfg.retry_count ?? 0)}
            onChange={e => onChange(step.id, { config: { ...cfg, retry_count: Math.max(0, Number(e.target.value)) } })}
          />
        </div>
        <div className="field">
          <label>Retry delay (s)</label>
          <input
            type="number" min={0} max={3600}
            className="input"
            value={Number(cfg.retry_delay_seconds ?? 30)}
            onChange={e => onChange(step.id, { config: { ...cfg, retry_delay_seconds: Math.max(0, Number(e.target.value)) } })}
          />
        </div>
      </div>

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
  )
}
