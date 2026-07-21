import type { Edge } from '@xyflow/react'
import type { StepDep } from '../../../lib/types'

/** Real, persisted step-dependency edges → react-flow Edge objects (distinct styling from
 *  the synthetic wave-to-wave edges, and individually deletable). */
export function toRealFlowEdges(stepDeps: StepDep[]): Edge[] {
  return stepDeps.map(d => ({
    id: d.dep_id,
    source: d.upstream_step_id,
    target: d.downstream_step_id,
    type: 'smoothstep',
    animated: false,
    deletable: true,
    data: { depId: d.dep_id },
    style: { stroke: 'var(--accent)', strokeWidth: 1.75 },
  }))
}

export interface ConnectGuardResult {
  allowed: boolean
  reason?: string
}

/**
 * Client-side guard for a canvas connect gesture, run before the API round-trip.
 * Cycle/duplicate detection stays server-side (the M1 endpoint already does it) — this
 * only rejects cases that are pointless to even send: no persisted pipeline yet, either
 * endpoint being an unsaved (`_new_...`-id) step, or a self-connection.
 */
export function canConnectSteps(params: {
  pipelineId: string | undefined
  source: string
  target: string
}): ConnectGuardResult {
  const { pipelineId, source, target } = params
  if (!pipelineId) {
    return { allowed: false, reason: 'Save this pipeline before drawing step dependencies.' }
  }
  if (source.startsWith('_new_') || target.startsWith('_new_')) {
    return { allowed: false, reason: 'Save this pipeline before connecting a newly added step.' }
  }
  if (source === target) {
    return { allowed: false, reason: 'A step cannot depend on itself.' }
  }
  return { allowed: true }
}
