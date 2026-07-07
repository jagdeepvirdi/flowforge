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
    <div ref={ref} className="relative inline-flex">
      <button
        type="button"
        onClick={handleToggle}
        className={`bg-transparent border-none cursor-pointer flex items-center p-0.5 transition-colors duration-150 ${open ? 'text-accent' : 'text-text-dim hover:text-text-3'}`}
        aria-label={`Help for ${field}`}
      >
        <HelpCircle size={13} />
      </button>

      {open && (
        <div className={`absolute left-1/2 -translate-x-1/2 z-[300] w-[280px] bg-surface2 border border-border-strong rounded-r py-2.5 px-3 shadow-[0_8px_24px_rgba(0,0,0,0.5)] ${popDown ? 'top-[calc(100%+8px)]' : 'bottom-[calc(100%+8px)]'}`}>
          {/* Arrow */}
          <div className={`absolute left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent ${popDown ? 'bottom-full border-b-[6px] border-b-border-strong' : 'top-full border-t-[6px] border-t-border-strong'}`} />

          <p className={`text-[12.5px] text-text-3 leading-[1.55] m-0${tip.example ? ' mb-2' : ''}`}>
            {tip.text}
          </p>
          {tip.example && (
            <pre className="text-[11px] text-text-2 bg-bg-code rounded-[5px] py-1.5 px-2 m-0 mt-1.5 overflow-x-auto whitespace-pre-wrap font-mono leading-normal">
              {tip.example}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
