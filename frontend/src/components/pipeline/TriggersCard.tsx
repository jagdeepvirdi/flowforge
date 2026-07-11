import { useState } from 'react'
import { CalendarClock, GitBranch, Link as LinkIcon } from 'lucide-react'
import CronBuilder from './CronBuilder'
import DependenciesCard from './DependenciesCard'
import WebhookCard from './WebhookCard'
import FieldTooltip from '../shared/FieldTooltip'
import CollapsibleCard from '../shared/CollapsibleCard'
import type { Pipeline, PipelineDep } from '../../lib/types'

type Tab = 'schedule' | 'dependencies' | 'webhook'

const TABS: Array<{ key: Tab; label: string; icon: typeof CalendarClock }> = [
  { key: 'schedule',     label: 'Schedule',     icon: CalendarClock },
  { key: 'dependencies', label: 'Dependencies', icon: GitBranch },
  { key: 'webhook',      label: 'Webhook',      icon: LinkIcon },
]

/**
 * Everything that can start this pipeline running — schedule, upstream pipeline
 * dependencies, and webhook/API tokens — grouped into one card instead of three,
 * since they're alternative (and combinable) answers to the same question.
 */
export default function TriggersCard({
  id, existing, schedule, onScheduleChange,
  upstreamDeps, setUpstreamDeps, allPipelines,
}: {
  id?: string
  existing?: Pipeline
  schedule: string
  onScheduleChange: (v: string) => void
  upstreamDeps: PipelineDep[]
  setUpstreamDeps: React.Dispatch<React.SetStateAction<PipelineDep[]>>
  allPipelines: Pipeline[]
}) {
  const [tab, setTab] = useState<Tab>('schedule')

  return (
    <CollapsibleCard title="Triggers">
      <div className="flex gap-px p-px bg-surface2 rounded-[7px] border border-border w-fit mb-3.5">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            className={`btn btn-sm ${tab === key ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setTab(key)}
            data-testid={`triggers-tab-${key}`}
          >
            <Icon size={12} /> {label}
            {key === 'dependencies' && upstreamDeps.length > 0 && (
              <span className="ml-1 font-mono opacity-80">({upstreamDeps.length})</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'schedule' && (
        <div className="field">
          <label className="flex items-center gap-1">
            Schedule{' '}
            <FieldTooltip field="cron" />
          </label>
          {(!id || existing) && (
            <CronBuilder key={id ?? 'new'} defaultValue={schedule} onChange={onScheduleChange} />
          )}
        </div>
      )}

      {tab === 'dependencies' && (
        <DependenciesCard
          bare
          upstreamDeps={upstreamDeps}
          setUpstreamDeps={setUpstreamDeps}
          allPipelines={allPipelines}
          thisPipelineId={id}
        />
      )}

      {tab === 'webhook' && (
        id ? (
          <WebhookCard bare pipelineId={id} />
        ) : (
          <p className="text-xs text-[var(--text-muted)] m-0">
            Save this pipeline first to generate a webhook token.
          </p>
        )
      )}
    </CollapsibleCard>
  )
}
