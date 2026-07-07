import { useEffect, useRef, useState } from 'react'
import { X, BookOpen, List, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react'
import { useHelp } from '../../lib/useHelp'
import { INTRO_CARDS, GLOSSARY, STEP_HINTS, PROVIDER_SETUP_GUIDES, type ProviderSetupGuide } from '../../lib/helpContent'

const STEP_TYPES = ['db_procedure', 'db_query', 'report', 'email', 'drive_upload'] as const

function GlossaryTab() {
  return (
    <div className="flex flex-col gap-px">
      {GLOSSARY.map(entry => (
        <div key={entry.term} className="py-2.5 border-b border-border">
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <span className="text-[13px] font-semibold text-text-primary">{entry.term}</span>
            <span className="text-[10px] text-text-dim shrink-0 italic">{entry.where}</span>
          </div>
          <p className="text-[12.5px] text-text-3 m-0 leading-[1.55]">{entry.def}</p>
        </div>
      ))}
    </div>
  )
}

function ProviderGuide({ guide }: { guide: ProviderSetupGuide }) {
  const [openStep, setOpenStep] = useState<number | null>(null)
  const [showTrouble, setShowTrouble] = useState(false)

  return (
    <div className="flex flex-col gap-2.5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-semibold text-text-primary">{guide.title}</span>
        <a
          href={`/api/docs/${guide.docPath}`}
          target="_blank" rel="noreferrer"
          className="text-[11px] text-accent-text no-underline inline-flex items-center gap-1"
        >
          Full guide <ExternalLink size={10} />
        </a>
      </div>

      {/* Intro */}
      <p className="text-[12.5px] text-text-3 m-0 leading-[1.55]">{guide.intro}</p>

      {/* Steps */}
      <div className="flex flex-col gap-1">
        {guide.steps.map((step, i) => (
          <div key={step.label} className="border border-border rounded-r-sm overflow-hidden">
            <button
              onClick={() => setOpenStep(openStep === i ? null : i)}
              className={`w-full border-none cursor-pointer py-2 px-2.5 flex items-center gap-1.5 text-left ${openStep === i ? 'bg-surface2' : 'bg-transparent'}`}
            >
              {openStep === i
                ? <ChevronDown size={12} className="text-accent shrink-0" />
                : <ChevronRight size={12} className="text-text-muted shrink-0" />
              }
              <span className="text-xs font-medium text-text-primary">{step.label}</span>
            </button>
            {openStep === i && (
              <div className="pt-2 pr-2.5 pb-2.5 pl-[28px] bg-surface2 border-t border-border">
                <p className={`text-xs text-text-3 m-0 leading-[1.6] whitespace-pre-wrap ${step.detail.includes('\n') ? 'font-mono' : ''}`}>
                  {step.detail}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Troubleshooting */}
      <button
        onClick={() => setShowTrouble(t => !t)}
        className="bg-transparent border-none cursor-pointer p-0 flex items-center gap-[5px] text-text-muted"
      >
        {showTrouble ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        <span className="text-[11px] font-medium">Troubleshooting</span>
      </button>
      {showTrouble && (
        <div className="flex flex-col gap-1.5">
          {guide.troubleshooting.map((t) => (
            <div key={t.error} className="bg-surface2 border border-border rounded-r-sm py-2 px-2.5">
              <div className="text-[11px] font-mono text-failure mb-[3px]">{t.error}</div>
              <div className="text-xs text-text-3">{t.fix}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function HelpTab({ topic }: { topic: string }) {
  const card = INTRO_CARDS[topic]
  const stepHint = STEP_HINTS[topic as (typeof STEP_TYPES)[number]]

  return (
    <div className="flex flex-col gap-[18px]">
      {card && (
        <div className="bg-surface2 border border-border rounded-r py-3.5 px-4">
          <div className="text-[13px] font-semibold text-accent mb-1.5">{card.title}</div>
          <p className="text-[13px] text-text-3 m-0 leading-[1.6]">{card.body}</p>
        </div>
      )}

      {stepHint && (
        <div>
          <div className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.05em] mb-2.5">Step Tips</div>
          <p className="text-[13px] text-text-3 m-0 mb-2.5 leading-[1.6]">{stepHint.summary}</p>
          <ul className="m-0 pt-0 pr-0 pb-0 pl-4 flex flex-col gap-1.5">
            {stepHint.tips.map((tip) => (
              <li key={tip} className="text-[12.5px] text-text-3 leading-normal">{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step reference */}
      {topic === 'pipeline_builder' && (
        <div>
          <div className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.05em] mb-2.5">Step Types</div>
          <div className="flex flex-col gap-2.5">
            {STEP_TYPES.map(type => {
              const hint = STEP_HINTS[type]
              return (
                <div key={type} className="bg-surface2 border border-border rounded-[7px] py-2.5 px-3">
                  <div className="text-xs font-semibold text-text-primary font-mono mb-1">{type}</div>
                  <p className="text-xs text-text-muted m-0">{hint.summary}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Provider setup guides — shown on the Settings page */}
      {topic === 'settings' && (
        <div className="flex flex-col gap-5">
          <div className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.05em]">
            Email Provider Setup
          </div>
          <ProviderGuide guide={PROVIDER_SETUP_GUIDES.gmail} />
          <div className="border-t border-border" />
          <ProviderGuide guide={PROVIDER_SETUP_GUIDES.microsoft365} />
        </div>
      )}

      {!card && !stepHint && topic !== 'settings' && (
        <p className="text-[13px] text-text-muted m-0">Select a page to see contextual help.</p>
      )}
    </div>
  )
}

export default function HelpDrawer() {
  const { open, topic, closeHelp } = useHelp()
  const [tab, setTab] = useState<'help' | 'glossary'>('help')
  const drawerRef = useRef<HTMLDialogElement>(null)

  /* Keyboard: Escape closes */
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') closeHelp() }
    globalThis.addEventListener('keydown', handler)
    return () => globalThis.removeEventListener('keydown', handler)
  }, [open, closeHelp])

  /* Sync dialog state with 'open' prop */
  useEffect(() => {
    const dialog = drawerRef.current
    if (!dialog) return
    if (open) {
      if (!dialog.open) dialog.showModal()
    } else {
      if (dialog.open) dialog.close()
    }
  }, [open])

  return (
    <>
      {/* Drawer panel */}
      <dialog
        ref={drawerRef}
        onClose={closeHelp}
        aria-label="Help"
        className="m-0 p-0 top-0 right-0 bottom-0 left-auto h-screen w-[400px] bg-surface border-none border-l border-border flex-col shadow-[-8px_0_32px_rgba(0,0,0,0.4)]"
        style={{ display: open ? 'flex' : 'none' }}
      >
        {/* Header */}
        <div className="flex items-center gap-2.5 py-3.5 px-4 border-b border-border shrink-0">
          <BookOpen size={15} className="text-accent" />
          <span className="text-sm font-semibold text-text-primary flex-1">Help</span>
          <button
            onClick={closeHelp}
            className="bg-transparent border-none cursor-pointer text-text-muted hover:text-text-primary flex p-1 rounded"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          {(['help', 'glossary'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 bg-transparent border-none cursor-pointer py-2.5 text-[12.5px] font-medium transition-colors duration-150 flex items-center justify-center gap-1.5 border-b-2 ${tab === t ? 'text-accent border-b-accent' : 'text-text-muted border-b-transparent'}`}
            >
              {t === 'help' ? <BookOpen size={13} /> : <List size={13} />}
              {t === 'help' ? 'Help' : 'Glossary'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {tab === 'help'     && <HelpTab topic={topic} />}
          {tab === 'glossary' && <GlossaryTab />}
        </div>
      </dialog>
    </>
  )
}
