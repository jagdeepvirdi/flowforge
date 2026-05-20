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
      background: 'linear-gradient(135deg, #1E2130 0%, #1A1D27 100%)',
      border: '1px solid #2D3143',
      borderLeft: '3px solid #F97316',
      borderRadius: 8,
      marginBottom: 16,
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 14px', cursor: 'pointer',
      }} onClick={() => setCollapsed(c => !c)}>
        <HelpCircle size={14} style={{ color: '#F97316', flexShrink: 0 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9', flex: 1 }}>{card.title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {collapsed && (
            <button
              onClick={e => { e.stopPropagation(); setVisible(false) }}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11, color: '#64748B', padding: '2px 6px' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#94A3B8')}
              onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
            >
              Dismiss
            </button>
          )}
          {collapsed ? <ChevronDown size={13} style={{ color: '#64748B' }} /> : <ChevronUp size={13} style={{ color: '#64748B' }} />}
        </div>
      </div>

      {!collapsed && (
        <div style={{ padding: '0 14px 12px 38px' }}>
          <p style={{ fontSize: 13, color: '#94A3B8', margin: '0 0 10px', lineHeight: 1.6 }}>{card.body}</p>
          <button
            onClick={() => setVisible(false)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 11.5, color: '#64748B', padding: 0 }}
            onMouseEnter={e => (e.currentTarget.style.color = '#94A3B8')}
            onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
          >
            Got it, dismiss
          </button>
        </div>
      )}
    </div>
  )
}
