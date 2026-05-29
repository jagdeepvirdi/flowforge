import { useState, useRef, useEffect } from 'react'
import { HelpCircle } from 'lucide-react'
import { TOOLTIPS } from '../../lib/helpContent'

type Props = Readonly<{
  field: string
}>

export default function FieldTooltip({ field }: Props) {
  const tip = TOOLTIPS[field]
  const [open, setOpen] = useState(false)
  const [popDown, setPopDown] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && e.target instanceof Node && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  if (!tip) return null

  const handleToggle = () => {
    if (!open && ref.current) {
      // Flip downward when the button is within 220px of the top (topbar + padding)
      setPopDown(ref.current.getBoundingClientRect().top < 220)
    }
    setOpen(o => !o)
  }

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        onClick={handleToggle}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: open ? 'var(--accent)' : 'var(--text-dim)',
          display: 'flex', alignItems: 'center', padding: 2,
          transition: 'color 150ms',
        }}
        onMouseEnter={e => { if (!open) e.currentTarget.style.color = 'var(--text-3)' }}
        onMouseLeave={e => { if (!open) e.currentTarget.style.color = 'var(--text-dim)' }}
        aria-label={`Help for ${field}`}
      >
        <HelpCircle size={13} />
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          ...(popDown
            ? { top: 'calc(100% + 8px)', bottom: undefined }
            : { bottom: 'calc(100% + 8px)', top: undefined }),
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 300,
          width: 280,
          background: 'var(--surface-2)',
          border: '1px solid var(--border-strong)',
          borderRadius: 8,
          padding: '10px 12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
        }}>
          {/* Arrow */}
          <div style={{
            position: 'absolute',
            ...(popDown
              ? { bottom: '100%', borderBottom: '6px solid var(--border-strong)', borderTop: undefined }
              : { top: '100%', borderTop: '6px solid var(--border-strong)', borderBottom: undefined }),
            left: '50%', transform: 'translateX(-50%)',
            width: 0, height: 0,
            borderLeft: '6px solid transparent',
            borderRight: '6px solid transparent',
          }} />

          <p style={{ fontSize: 12.5, color: 'var(--text-3)', margin: tip.example ? '0 0 8px' : 0, lineHeight: 1.55 }}>
            {tip.text}
          </p>
          {tip.example && (
            <pre style={{
              fontSize: 11, color: 'var(--text-2)',
              background: 'var(--bg-code)', borderRadius: 5,
              padding: '6px 8px', margin: '6px 0 0',
              overflowX: 'auto', whiteSpace: 'pre-wrap',
              fontFamily: 'JetBrains Mono, monospace',
              lineHeight: 1.5,
            }}>
              {tip.example}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
