import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react'
import { INTRO_CARDS } from '../../lib/helpContent'

type Props = Readonly<{
  page: string
}>

export default function PageIntro({ page }: Props) {
  const key = `ff_help_dismissed_${page}`
  const card = INTRO_CARDS[page]

  const [visible, setVisible] = useState(() => {
    try { return localStorage.getItem(key) !== '1' } catch { return true }
  })
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (!visible) {
      try { localStorage.setItem(key, '1') } catch { /* localStorage unavailable (private mode, quota) — ignore */ }
    }
  }, [visible, key])

  if (!card || !visible) return null

  return (
    <div className="bg-[linear-gradient(135deg,var(--surface-hover)_0%,var(--surface)_100%)] border border-border border-l-[3px] border-l-accent rounded-r mb-4 overflow-hidden">
      <div className="flex items-center py-2.5 px-3.5 gap-2.5">
        <button
          className="flex items-center gap-2.5 flex-1 bg-transparent border-none cursor-pointer text-left"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed(c => !c)}
        >
          <HelpCircle size={14} className="text-accent shrink-0" />
          <span className="text-[13px] font-semibold text-text-primary flex-1">{card.title}</span>
          {collapsed ? <ChevronDown size={13} className="text-text-muted" /> : <ChevronUp size={13} className="text-text-muted" />}
        </button>
        {collapsed && (
          <button
            onClick={() => setVisible(false)}
            className="bg-transparent border-none cursor-pointer text-[11px] text-text-muted hover:text-text-3 py-0.5 px-1.5 shrink-0"
          >
            Dismiss
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="pt-0 pr-3.5 pb-3 pl-[38px]">
          <p className="text-[13px] text-text-3 m-0 mb-2.5 leading-[1.6]">{card.body}</p>
          <button
            onClick={() => setVisible(false)}
            className="bg-transparent border-none cursor-pointer text-[11.5px] text-text-muted hover:text-text-3 p-0"
          >
            Got it, dismiss
          </button>
        </div>
      )}
    </div>
  )
}
