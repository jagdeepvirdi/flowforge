import { describe, it, expect } from 'vitest'
import { computeWaves } from '../lib/pipelineWaves'
import type { PipelineStep } from '../lib/types'

function makeStep(overrides: Partial<PipelineStep> & { name: string; step_order: number }): PipelineStep {
  return {
    id: overrides.name,
    pipeline_id: 'p1',
    step_type: 'db_query',
    config: {},
    on_error: 'stop',
    enabled: true,
    parallel_group: null,
    ...overrides,
  }
}

describe('computeWaves', () => {
  it('sequential_steps: each step without parallel_group becomes a separate single-step wave', () => {
    const steps = [
      makeStep({ name: 'a', step_order: 1 }),
      makeStep({ name: 'b', step_order: 2 }),
      makeStep({ name: 'c', step_order: 3 }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(3)
    expect(waves.every(w => w.length === 1)).toBe(true)
  })

  it('empty_steps: no steps produces no waves', () => {
    expect(computeWaves([])).toEqual([])
  })

  it('same_parallel_group_grouped: steps sharing one parallel_group become a single wave', () => {
    const steps = [
      makeStep({ name: 'a', step_order: 1, parallel_group: 'g1' }),
      makeStep({ name: 'b', step_order: 2, parallel_group: 'g1' }),
      makeStep({ name: 'c', step_order: 3, parallel_group: 'g1' }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(1)
    expect(waves[0]).toHaveLength(3)
  })

  it('mixed_parallel_and_sequential: seq1 -> [p1, p2] -> seq2', () => {
    const steps = [
      makeStep({ name: 'seq1', step_order: 1 }),
      makeStep({ name: 'p1', step_order: 2, parallel_group: 'g1' }),
      makeStep({ name: 'p2', step_order: 3, parallel_group: 'g1' }),
      makeStep({ name: 'seq2', step_order: 4 }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(3)
    expect(waves[0]).toHaveLength(1)
    expect(waves[1]).toHaveLength(2)
    expect(waves[2]).toHaveLength(1)
    expect(waves[0][0].name).toBe('seq1')
    expect(waves[2][0].name).toBe('seq2')
  })

  it('different_parallel_groups: distinct group values stay in separate waves', () => {
    const steps = [
      makeStep({ name: 'a', step_order: 1, parallel_group: 'g1' }),
      makeStep({ name: 'b', step_order: 2, parallel_group: 'g2' }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(2)
    expect(waves[0][0].name).toBe('a')
    expect(waves[1][0].name).toBe('b')
  })

  it('parallel_group_none_breaks_group: an interleaved ungrouped step splits a group into two waves', () => {
    const steps = [
      makeStep({ name: 'a', step_order: 1, parallel_group: 'g1' }),
      makeStep({ name: 'b', step_order: 2 }),
      makeStep({ name: 'c', step_order: 3, parallel_group: 'g1' }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(3)
    expect(waves[0].map(s => s.name)).toEqual(['a'])
    expect(waves[1].map(s => s.name)).toEqual(['b'])
    expect(waves[2].map(s => s.name)).toEqual(['c'])
  })

  it('sorts by step_order first, regardless of input array order', () => {
    // Unsorted input; after sorting by step_order, a(1) and b(2) are adjacent
    // and share a group, so they must merge into one wave despite arriving
    // out of order.
    const steps = [
      makeStep({ name: 'c', step_order: 3 }),
      makeStep({ name: 'b', step_order: 2, parallel_group: 'g1' }),
      makeStep({ name: 'a', step_order: 1, parallel_group: 'g1' }),
    ]
    const waves = computeWaves(steps)
    expect(waves).toHaveLength(2)
    expect(waves[0].map(s => s.name)).toEqual(['a', 'b'])
    expect(waves[1].map(s => s.name)).toEqual(['c'])
  })
})
