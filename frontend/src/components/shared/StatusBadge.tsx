interface Props {
  status: string
  animate?: boolean
  label?: string
}

export default function StatusBadge({ status, label, animate: _animate }: Props) {
  const map: Record<string, { cls: string; text: string }> = {
    success:    { cls: 'pill-success', text: label ?? 'Success' },
    failed:     { cls: 'pill-failure', text: label ?? 'Failed' },
    failure:    { cls: 'pill-failure', text: label ?? 'Failed' },
    running:    { cls: 'pill-running', text: label ?? 'Running' },
    cancelled:  { cls: 'pill-idle',    text: label ?? 'Cancelled' },
    skipped:    { cls: 'pill-idle',    text: label ?? 'Skipped' },
    paused:     { cls: 'pill-paused',  text: label ?? 'Paused' },
    idle:       { cls: 'pill-idle',    text: label ?? 'Idle' },
    warn:       { cls: 'pill-warn',    text: label ?? 'Warning' },
  }
  const m = map[status] ?? { cls: 'pill-idle', text: label ?? status ?? 'Never run' }
  return (
    <span className={`pill ${m.cls}`}>
      <span className="dot" />
      {m.text}
    </span>
  )
}
