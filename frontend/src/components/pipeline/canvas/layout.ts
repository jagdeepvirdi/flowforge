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
 * Auto-layout: waves become left-to-right columns (dagre rankdir LR), with
 * multiple steps in one wave stacked vertically in the same column. Node
 * x/y are never persisted — this is recomputed from `step_order`/
 * `parallel_group` on every render.
 */
export function layoutWaves(waves: PipelineStep[][]): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 28, ranksep: 96 })
  g.setDefaultEdgeLabel(() => ({}))

  for (const wave of waves) {
    for (const step of wave) {
      g.setNode(step.id, { width: CANVAS_NODE_WIDTH, height: CANVAS_NODE_HEIGHT })
    }
  }
  for (const edge of buildWaveEdges(waves)) {
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
