import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

/** Card with a collapsible body, matching the expand/collapse affordance pipeline steps already use. */
export default function CollapsibleCard({
  title, headerExtra, actions, defaultExpanded = true, children,
}: {
  title: ReactNode
  headerExtra?: ReactNode
  actions?: ReactNode
  defaultExpanded?: boolean
  children: ReactNode
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="card mb-4">
      <div className={`flex items-center justify-between ${expanded ? 'mb-2.5' : ''}`}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text)]">{title}</span>
          {headerExtra}
        </div>
        <div className="flex items-center gap-1">
          {actions}
          <button
            type="button"
            onClick={() => setExpanded(x => !x)}
            className="btn btn-sm btn-ghost btn-icon"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div>
      {expanded && children}
    </div>
  )
}
