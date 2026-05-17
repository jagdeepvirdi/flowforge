import type { PipelineStatus } from '../../lib/types'

interface Props { status: PipelineStatus | string; animate?: boolean }

export default function StatusBadge({ status, animate }: Props) {
  switch (status) {
    case 'success':
      return <span className="badge-success">Success</span>
    case 'failed':
      return <span className="badge-danger">Failed</span>
    case 'running':
      return (
        <span className="badge-running inline-flex items-center gap-1">
          {animate && <span className="w-1.5 h-1.5 rounded-full bg-running animate-pulse" />}
          Running
        </span>
      )
    case 'cancelled':
      return <span className="badge-muted">Cancelled</span>
    case 'skipped':
      return <span className="badge-muted">Skipped</span>
    default:
      return <span className="badge-muted">Never run</span>
  }
}
