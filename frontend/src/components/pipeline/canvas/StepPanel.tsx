import { useEffect, useRef } from 'react'
import { X, Copy, Trash2 } from 'lucide-react'
import type { PipelineStep } from '../../../lib/types'
import StepConfigBody from '../StepConfigBody'
import { stepMeta } from '../stepMeta'

type Props = Readonly<{
  step: PipelineStep | null
  onClose: () => void
  onChange: (id: string, updates: Partial<PipelineStep>) => void
  onDuplicate: (id: string) => void
  onDelete: (id: string) => void
  allSteps: PipelineStep[]
  dbConnections: { id: string; name: string }[]
  reportConfigs: { id: string; name: string; output_filename: string }[]
  emailConfigs: { id: string; name: string }[]
  bulkLoadConfigs: { id: string; name: string; source_directory: string; target_table: string }[]
}>

/**
 * Side panel for editing a step's config from the canvas, cloned from
 * HelpDrawer's <dialog>/showModal()/Escape pattern. State is local (the
 * `step` prop, driven by the canvas's own selection), not a global context.
 */
export default function StepPanel({
  step, onClose, onChange, onDuplicate, onDelete,
  allSteps, dbConnections, reportConfigs, emailConfigs, bulkLoadConfigs,
}: Props) {
  const panelRef = useRef<HTMLDialogElement>(null)
  const open = step !== null

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    globalThis.addEventListener('keydown', handler)
    return () => globalThis.removeEventListener('keydown', handler)
  }, [open, onClose])

  useEffect(() => {
    const dialog = panelRef.current
    if (!dialog) return
    if (open) {
      if (!dialog.open) dialog.showModal()
    } else {
      if (dialog.open) dialog.close()
    }
  }, [open])

  const meta = step ? stepMeta(step.step_type) : null

  return (
    <dialog
      ref={panelRef}
      onClose={onClose}
      aria-label="Edit step"
      className="m-0 p-0 top-0 right-0 bottom-0 left-auto h-screen w-[400px] bg-surface border-none border-l border-border flex-col shadow-[-8px_0_32px_rgba(0,0,0,0.4)]"
      style={{ display: open ? 'flex' : 'none' }}
    >
      {step && meta && (
        <>
          <div className="flex items-center gap-2.5 py-3.5 px-4 border-b border-border shrink-0">
            <span className={`tbadge ${meta.cls}`}>{meta.label}</span>
            <span className="text-sm font-semibold text-text-primary flex-1 truncate">{step.name}</span>
            <button
              onClick={() => onDuplicate(step.id)}
              className="bg-transparent border-none cursor-pointer text-text-muted hover:text-text-primary flex p-1 rounded"
              title="Duplicate step"
            >
              <Copy size={15} />
            </button>
            <button
              onClick={() => { onDelete(step.id); onClose() }}
              className="bg-transparent border-none cursor-pointer text-text-muted hover:text-failure-text flex p-1 rounded"
              title="Delete step"
            >
              <Trash2 size={15} />
            </button>
            <button
              onClick={onClose}
              className="bg-transparent border-none cursor-pointer text-text-muted hover:text-text-primary flex p-1 rounded"
              title="Close"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <StepConfigBody
              step={step}
              onChange={onChange}
              allSteps={allSteps}
              dbConnections={dbConnections}
              reportConfigs={reportConfigs}
              emailConfigs={emailConfigs}
              bulkLoadConfigs={bulkLoadConfigs}
            />
          </div>
        </>
      )}
    </dialog>
  )
}
