import type { PipelineStep } from './types'

/**
 * Mirrors `flowforge/engine/runner.py::_build_execution_waves` exactly. A wave
 * is either one step with no `parallel_group`, or a maximal run of
 * consecutive-by-`step_order` steps sharing the same non-null
 * `parallel_group` value. A different (or absent) group interleaved by
 * `step_order` splits the group into separate waves — this is NOT a global
 * groupby. If the backend algorithm ever changes, this function and its
 * tests must change too.
 */
export function computeWaves(steps: PipelineStep[]): PipelineStep[][] {
  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order)
  const waves: PipelineStep[][] = []
  let i = 0
  while (i < sorted.length) {
    const step = sorted[i]
    const pg = step.parallel_group
    if (!pg) {
      waves.push([step])
      i += 1
    } else {
      const group: PipelineStep[] = [step]
      i += 1
      while (i < sorted.length && sorted[i].parallel_group === pg) {
        group.push(sorted[i])
        i += 1
      }
      waves.push(group)
    }
  }
  return waves
}
