import { BrainCircuit } from 'lucide-react'
import Sk from '../shared/Skeleton'
import { StatusBadge, CodeBlock } from './common'
import type { SetupStatus } from '../../lib/api'

export default function BrainCard({ status, isLoading }: { status: SetupStatus | undefined; isLoading: boolean }) {
  const attached = status?.ai?.enabled ?? false
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[7px] text-[13px] font-semibold text-text-primary">
          <BrainCircuit size={15} className="text-text-muted" />
          Brain
        </div>
        {isLoading
          ? <Sk h={13} style={{ width: 120 }} />
          : <StatusBadge ok={attached} label={attached ? 'Attached' : 'Not attached'} />
        }
      </div>
      <p className="text-[13px] text-text-muted m-0">
        FlowForge runs fully without AI. Optional AI diagnostics come from a separate Brain service;
        until one is attached, no AI features appear anywhere in the UI. Pipelines, reports, schedules
        and alerts are unaffected.
      </p>
      <div className="flex flex-col gap-1.5">
        <CodeBlock>FLOWFORGE_BRAIN_URL=   # optional — base URL of the Brain service</CodeBlock>
      </div>
    </div>
  )
}
