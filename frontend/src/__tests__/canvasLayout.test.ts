import { describe, it, expect } from 'vitest'
import { buildWaveEdges, layoutWaves } from '../components/pipeline/canvas/layout'
import type { PipelineStep } from '../lib/types'

function makeStep(id: string, step_order: number, parallel_group: string | null = null): PipelineStep {
  return {
    id, pipeline_id: 'p1', step_order, name: id, step_type: 'db_query',
    config: {}, on_error: 'stop', enabled: true, parallel_group,
  }
}

describe('buildWaveEdges', () => {
  it('connects every node in wave N to every node in wave N+1', () => {
    const waves = [
      [makeStep('a', 1)],
      [makeStep('b', 2, 'g1'), makeStep('c', 3, 'g1')],
      [makeStep('d', 4)],
    ]
    const edges = buildWaveEdges(waves)
    expect(edges).toHaveLength(2 + 2) // a->b, a->c, b->d, c->d
    expect(edges.map(e => `${e.source}->${e.target}`).sort()).toEqual(
      ['a->b', 'a->c', 'b->d', 'c->d'].sort(),
    )
  })

  it('produces no edges for a single wave', () => {
    expect(buildWaveEdges([[makeStep('a', 1)]])).toEqual([])
  })

  it('produces no edges for zero waves', () => {
    expect(buildWaveEdges([])).toEqual([])
  })
})

describe('layoutWaves', () => {
  it('assigns exactly one position per step', () => {
    const waves = [[makeStep('a', 1)], [makeStep('b', 2), makeStep('c', 3)]]
    const positions = layoutWaves(waves)
    expect(positions.size).toBe(3)
    expect(positions.has('a')).toBe(true)
    expect(positions.has('b')).toBe(true)
    expect(positions.has('c')).toBe(true)
  })

  it('increases x monotonically from wave to wave (left-to-right execution order)', () => {
    const waves = [[makeStep('a', 1)], [makeStep('b', 2)], [makeStep('c', 3)]]
    const positions = layoutWaves(waves)
    const xa = positions.get('a')!.x
    const xb = positions.get('b')!.x
    const xc = positions.get('c')!.x
    expect(xa).toBeLessThan(xb)
    expect(xb).toBeLessThan(xc)
  })

  it('places same-wave steps at the same x (one column)', () => {
    const waves = [[makeStep('a', 1, 'g1'), makeStep('b', 2, 'g1')]]
    const positions = layoutWaves(waves)
    expect(positions.get('a')!.x).toBe(positions.get('b')!.x)
    expect(positions.get('a')!.y).not.toBe(positions.get('b')!.y)
  })

  it('handles an empty wave list', () => {
    expect(layoutWaves([]).size).toBe(0)
  })
})
