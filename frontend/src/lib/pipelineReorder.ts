import type { PipelineStep } from './types'

/** Renumbers `step_order` sequentially as 1..N, preserving array order. */
export function renumberSteps(steps: PipelineStep[]): PipelineStep[] {
  return steps.map((s, i) => ({ ...s, step_order: i + 1 }))
}

/** Moves the step at `from` to `to` and renumbers `step_order` for all steps. */
export function reorderSteps(steps: PipelineStep[], from: number, to: number): PipelineStep[] {
  if (from === to || from < 0 || to < 0 || from >= steps.length || to >= steps.length) return steps
  const next = [...steps]
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return renumberSteps(next)
}

let dupeCounter = 0

/** Clones a step (fresh synthetic id, same config) and inserts it directly after the original. */
export function duplicateStep(steps: PipelineStep[], stepId: string): PipelineStep[] {
  const idx = steps.findIndex(s => s.id === stepId)
  if (idx === -1) return steps
  dupeCounter += 1
  const clone: PipelineStep = {
    ...steps[idx],
    id: `_new_${Date.now()}_${dupeCounter}`,
    name: `${steps[idx].name} (copy)`,
  }
  const next = [...steps]
  next.splice(idx + 1, 0, clone)
  return renumberSteps(next)
}

/**
 * Moves `stepId` to `targetIndex` and assigns it `parallel_group` (null to
 * clear it). Used by canvas drag-to-group: dropping a node into an existing
 * wave's column adopts that wave's group; dropping near an ungrouped node
 * clears the group instead of inventing one.
 */
export function assignParallelGroup(
  steps: PipelineStep[],
  stepId: string,
  group: string | null,
  targetIndex: number,
): PipelineStep[] {
  const fromIdx = steps.findIndex(s => s.id === stepId)
  if (fromIdx === -1) return steps
  const withoutMoved = steps.filter(s => s.id !== stepId)
  const clampedIndex = Math.max(0, Math.min(targetIndex, withoutMoved.length))
  const moved: PipelineStep = { ...steps[fromIdx], parallel_group: group }
  const next = [...withoutMoved]
  next.splice(clampedIndex, 0, moved)
  return renumberSteps(next)
}
