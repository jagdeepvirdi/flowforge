import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react'
import { INTRO_CARDS } from '../../lib/helpContent'

interface Props {
  page: string
}

export default function PageIntro({ page }: Props) {
  const key = `ff_help_dismissed_${page}`
  const card = INTRO_CARDS[page]

  const [visible, setVisible] = useState(() => {
    try { return localStorage.getItem(key) !== '1' } catch { return true }
  })
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (!visible) {
      try { localStorage.setItem(key, '1') } catch {}
    }
  }, [visible, key])

  if (!card || !visible) return null

  return (
    <div style={{
      background: 'linear-gradient(135deg, var(--surface-hover) 0%, var(--surface) 100%)',
      border: '1px solid var(--border)',
      borderLeft: '3px solid var(--accent)',
      borderRadius: 8,
      marginBottom: 16,
      overflow: 'hidden',
    }}>
      <button
        style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 14px', cursor: 'pointer',
          width: '100%', background: 'transparent', border: 'none', textAlign: 'left',
        }}
        aria-expanded={!collapsed}
        onClick={() => setCollapsed(c => !c)}
      >
        <HelpCircle size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', flex: 1 }}>{card.title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {collapsed && (
            <button
              onClick={e => { e.stopPropagation(); setVisible(false) }}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--text-muted)', padding: '2px 6px' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-3)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              Dismiss
            </button>
          )}
          {collapsed ? <ChevronDown size={13} style={{ color: 'var(--text-muted)' }} /> : <ChevronUp size={13} style={{ color: 'var(--text-muted)' }} />}
        </div>
      </button>

      {!collapsed && (
        <div style={{ padding: '0 14px 12px 38px' }}>
          <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '0 0 10px', lineHeight: 1.6 }}>{card.body}</p>
          <button
            onClick={() => setVisible(false)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11.5, color: 'var(--text-muted)', padding: 0 }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-3)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            Got it, dismiss
          </button>
        </div>
      )}
    </div>
  )
}
