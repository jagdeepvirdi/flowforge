import type { PipelineStep } from '../../lib/types'
import { STEP_HINTS } from '../../lib/helpContent'
import Field from './stepForms/Field'
import { STEP_FORMS } from './stepForms'

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
 * The hint banner + `STEP_FORMS[step_type]` config dispatch (or raw-JSON
 * fallback for types without a dedicated form). Shared by the list view's
 * inline card body and the canvas side panel so config editing never drifts
 * between the two.
 */
export default function StepConfigForm({ step, onChange, allSteps, dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs }: Props) {
  const cfg = step.config
  const setConfig = (key: string, value: unknown) =>
    onChange(step.id, { config: { ...cfg, [key]: value } })

  const StepForm = STEP_FORMS[step.step_type]

  return (
    <div className="flex flex-col gap-2.5">
      {STEP_HINTS[step.step_type] && (
        <div className="text-xs text-text-muted bg-bg-code rounded-r-sm py-[7px] px-2.5 leading-normal">
          {STEP_HINTS[step.step_type].summary}
        </div>
      )}

      {StepForm ? (
        <StepForm
          cfg={cfg}
          setConfig={setConfig}
          step={step}
          allSteps={allSteps}
          dbConnections={dbConnections}
          reportConfigs={reportConfigs}
          emailConfigs={emailConfigs}
          bulkLoadConfigs={bulkLoadConfigs}
        />
      ) : (
        <Field label="Config (JSON)" tooltip="No dedicated form for this step type (a plugin, or a built-in without a form yet) — edit its raw config here.">
          <textarea className="input mono-input h-auto resize-y" rows={8} value={JSON.stringify(cfg, null, 2)}
            onChange={e => { try { onChange(step.id, { config: JSON.parse(e.target.value) }) } catch { /* invalid JSON while typing — ignore */ } }}
          />
        </Field>
      )}
    </div>
  )
}
