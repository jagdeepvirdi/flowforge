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
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{entry.term}</span>
            <span style={{ fontSize: 10, color: 'var(--text-dim)', flexShrink: 0, fontStyle: 'italic' }}>{entry.where}</span>
          </div>
          <p style={{ fontSize: 12.5, color: 'var(--text-3)', margin: 0, lineHeight: 1.55 }}>{entry.def}</p>
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
          background: 'var(--surface-2)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '14px 16px',
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', marginBottom: 6 }}>{card.title}</div>
          <p style={{ fontSize: 13, color: 'var(--text-3)', margin: 0, lineHeight: 1.6 }}>{card.body}</p>
        </div>
      )}

      {stepHint && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Step Tips</div>
          <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '0 0 10px', lineHeight: 1.6 }}>{stepHint.summary}</p>
          <ul style={{ margin: 0, padding: '0 0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {stepHint.tips.map((tip, i) => (
              <li key={i} style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.5 }}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step reference */}
      {topic === 'pipeline_builder' && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>Step Types</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {STEP_TYPES.map(type => {
              const hint = STEP_HINTS[type]
              return (
                <div key={type} style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 7, padding: '10px 12px' }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 4 }}>{type}</div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>{hint.summary}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!card && !stepHint && (
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Select a page to see contextual help.</p>
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
          background: 'var(--surface)',
          borderLeft: '1px solid var(--border)',
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
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}>
          <BookOpen size={15} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', flex: 1 }}>Help</span>
          <button
            onClick={closeHelp}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', padding: 4, borderRadius: 4 }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
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
                color: tab === t ? 'var(--accent)' : 'var(--text-muted)',
                borderBottom: tab === t ? '2px solid var(--accent)' : '2px solid transparent',
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
