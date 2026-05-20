import { useEffect, useRef, useState } from 'react'
import { X, BookOpen, List } from 'lucide-react'
import { useHelp } from '../../lib/useHelp'
import { INTRO_CARDS, GLOSSARY, STEP_HINTS } from '../../lib/helpContent'

const STEP_TYPES = ['db_procedure', 'db_query', 'report', 'email', 'drive_upload'] as const

function GlossaryTab() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {GLOSSARY.map(entry => (
        <div key={entry.term} style={{
          padding: '10px 0',
          borderBottom: '1px solid #2D3143',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#F1F5F9' }}>{entry.term}</span>
            <span style={{ fontSize: 10, color: '#475569', flexShrink: 0, fontStyle: 'italic' }}>{entry.where}</span>
          </div>
          <p style={{ fontSize: 12.5, color: '#94A3B8', margin: 0, lineHeight: 1.55 }}>{entry.def}</p>
        </div>
      ))}
    </div>
  )
}

function HelpTab({ topic }: { topic: string }) {
  const card = INTRO_CARDS[topic]
  const stepHint = STEP_HINTS[topic as (typeof STEP_TYPES)[number]]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {card && (
        <div style={{
          background: '#21252F',
          border: '1px solid #2D3143',
          borderRadius: 8,
          padding: '14px 16px',
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#F97316', marginBottom: 6 }}>{card.title}</div>
          <p style={{ fontSize: 13, color: '#94A3B8', margin: 0, lineHeight: 1.6 }}>{card.body}</p>
        </div>
      )}

      {stepHint && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Step Tips</div>
          <p style={{ fontSize: 13, color: '#94A3B8', margin: '0 0 10px', lineHeight: 1.6 }}>{stepHint.summary}</p>
          <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {stepHint.tips.map((tip, i) => (
              <li key={i} style={{ fontSize: 12.5, color: '#94A3B8', lineHeight: 1.5 }}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step reference */}
      {topic === 'pipeline_builder' && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Step Types</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {STEP_TYPES.map(type => {
              const hint = STEP_HINTS[type]
              return (
                <div key={type} style={{ background: '#21252F', border: '1px solid #2D3143', borderRadius: 7, padding: '10px 12px' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#F1F5F9', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4 }}>{type}</div>
                  <p style={{ fontSize: 12, color: '#64748B', margin: 0 }}>{hint.summary}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!card && !stepHint && (
        <p style={{ fontSize: 13, color: '#64748B', margin: 0 }}>Select a page to see contextual help.</p>
      )}
    </div>
  )
}

export default function HelpDrawer() {
  const { open, topic, closeHelp } = useHelp()
  const [tab, setTab] = useState<'help' | 'glossary'>('help')
  const drawerRef = useRef<HTMLDivElement>(null)

  /* Keyboard: Escape closes */
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') closeHelp() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, closeHelp])

  return (
    <>
      {/* Overlay */}
      <div
        onClick={closeHelp}
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(0,0,0,0.4)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 200ms ease',
        }}
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-label="Help"
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 201,
          width: 400,
          background: '#1A1D27',
          borderLeft: '1px solid #2D3143',
          display: 'flex', flexDirection: 'column',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 220ms cubic-bezier(0.4,0,0.2,1)',
          boxShadow: open ? '-8px 0 32px rgba(0,0,0,0.4)' : 'none',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '14px 16px',
          borderBottom: '1px solid #2D3143',
          flexShrink: 0,
        }}>
          <BookOpen size={15} style={{ color: '#F97316' }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9', flex: 1 }}>Help</span>
          <button
            onClick={closeHelp}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748B', display: 'flex', padding: 4, borderRadius: 4 }}
            onMouseEnter={e => (e.currentTarget.style.color = '#F1F5F9')}
            onMouseLeave={e => (e.currentTarget.style.color = '#64748B')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid #2D3143',
          flexShrink: 0,
        }}>
          {(['help', 'glossary'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                flex: 1, background: 'transparent', border: 'none', cursor: 'pointer',
                padding: '10px 0',
                fontSize: 12.5, fontWeight: 500,
                color: tab === t ? '#F97316' : '#64748B',
                borderBottom: tab === t ? '2px solid #F97316' : '2px solid transparent',
                transition: 'color 150ms',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              {t === 'help' ? <BookOpen size={13} /> : <List size={13} />}
              {t === 'help' ? 'Help' : 'Glossary'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px' }}>
          {tab === 'help'     && <HelpTab topic={topic} />}
          {tab === 'glossary' && <GlossaryTab />}
        </div>
      </div>
    </>
  )
}
