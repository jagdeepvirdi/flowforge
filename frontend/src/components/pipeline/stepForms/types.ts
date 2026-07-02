import type { PipelineStep } from '../../../lib/types'

export interface StepFormProps {
  cfg: Record<string, unknown>
  setConfig: (key: string, value: unknown) => void
  step: PipelineStep
  allSteps: PipelineStep[]
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}
