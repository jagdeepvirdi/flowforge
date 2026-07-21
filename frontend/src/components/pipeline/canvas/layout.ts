import dagre from 'dagre'
import type { PipelineStep } from '../../../lib/types'

export const CANVAS_NODE_WIDTH = 220
export const CANVAS_NODE_HEIGHT = 76

export interface WaveEdge {
  id: string
  source: string
  target: string
}

/** Synthetic (non-persisted) edges connecting every node in wave N to every node in wave N+1. */
export function buildWaveEdges(waves: PipelineStep[][]): WaveEdge[] {
  const edges: WaveEdge[] = []
  for (let i = 0; i < waves.length - 1; i++) {
    for (const from of waves[i]) {
      for (const to of waves[i + 1]) {
        edges.push({ id: `${from.id}->${to.id}`, source: from.id, target: to.id })
      }
    }
  }
  return edges
}

/**
 * Auto-layout shared by both edge sources below: left-to-right columns (dagre
 * rankdir LR), multiple steps at the same rank stacked vertically. Node x/y
 * are never persisted — recomputed on every render.
 */
function layoutFromEdges(
  steps: PipelineStep[],
  edges: { source: string; target: string }[],
): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 28, ranksep: 96 })
  g.setDefaultEdgeLabel(() => ({}))

  for (const step of steps) {
    g.setNode(step.id, { width: CANVAS_NODE_WIDTH, height: CANVAS_NODE_HEIGHT })
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target)
  }

  dagre.layout(g)

  const positions = new Map<string, { x: number; y: number }>()
  for (const id of g.nodes()) {
    const n = g.node(id)
    // dagre positions are node centers; react-flow expects top-left corners.
    positions.set(id, { x: n.x - CANVAS_NODE_WIDTH / 2, y: n.y - CANVAS_NODE_HEIGHT / 2 })
  }
  return positions
}

/** Wave-derived layout — the original Option A model (step_order/parallel_group only). */
export function layoutWaves(waves: PipelineStep[][]): Map<string, { x: number; y: number }> {
  return layoutFromEdges(waves.flat(), buildWaveEdges(waves))
}

/**
 * Real-dependency-edge layout (Phase 14 Option B, Milestone 3) — used instead of
 * `layoutWaves` once a pipeline has persisted `StepDependency` edges, mirroring the
 * backend's dual-path gate: dagre lays the graph out from the actual edges, not the
 * synthetic wave-to-wave cartesian ones.
 */
export function layoutRealEdges(
  steps: PipelineStep[],
  edges: { source: string; target: string }[],
): Map<string, { x: number; y: number }> {
  return layoutFromEdges(steps, edges)
}
