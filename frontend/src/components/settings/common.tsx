import { CheckCircle2, XCircle } from 'lucide-react'

export function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-[5px] text-xs font-medium ${ok ? 'text-success' : 'text-text-muted'}`}>
      {ok
        ? <CheckCircle2 size={13} />
        : <XCircle size={13} />
      }
      {label}
    </span>
  )
}

export function CodeBlock({ children }: { children: string }) {
  return (
    <code className="mono block text-xs bg-surface2 border border-border rounded-[7px] py-2.5 px-3 text-text-2">
      {children}
    </code>
  )
}

export function InlineCode({ children }: { children: string }) {
  return (
    <code className="mono text-[11px] bg-surface2 py-px px-[5px] rounded-[3px]">
      {children}
    </code>
  )
}
