import { describe, it, expect } from 'vitest'
import { renumberSteps, reorderSteps, duplicateStep, assignParallelGroup } from '../lib/pipelineReorder'
import type { PipelineStep } from '../lib/types'

function makeStep(overrides: Partial<PipelineStep> & { id: string; step_order: number }): PipelineStep {
  return {
    pipeline_id: 'p1',
    name: overrides.id,
    step_type: 'db_query',
    config: {},
    on_error: 'stop',
    enabled: true,
    parallel_group: null,
    ...overrides,
  }
}

describe('renumberSteps', () => {
  it('renumbers step_order sequentially from 1, preserving array order', () => {
    const steps = [makeStep({ id: 'a', step_order: 9 }), makeStep({ id: 'b', step_order: 4 })]
    const result = renumberSteps(steps)
    expect(result.map(s => s.step_order)).toEqual([1, 2])
    expect(result.map(s => s.id)).toEqual(['a', 'b'])
  })
})

describe('reorderSteps', () => {
  it('moves a step from one index to another and renumbers everything', () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1 }),
      makeStep({ id: 'b', step_order: 2 }),
      makeStep({ id: 'c', step_order: 3 }),
    ]
    const result = reorderSteps(steps, 2, 0)
    expect(result.map(s => s.id)).toEqual(['c', 'a', 'b'])
    expect(result.map(s => s.step_order)).toEqual([1, 2, 3])
  })

  it('is a no-op when from equals to', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
    expect(reorderSteps(steps, 1, 1)).toBe(steps)
  })

  it('is a no-op for out-of-range indices', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 })]
    expect(reorderSteps(steps, 0, 5)).toBe(steps)
    expect(reorderSteps(steps, -1, 0)).toBe(steps)
  })
})

describe('duplicateStep', () => {
  it('inserts a clone directly after the original with a fresh id and renumbered order', () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1 }),
      makeStep({ id: 'b', step_order: 2 }),
    ]
    const result = duplicateStep(steps, 'a')
    expect(result).toHaveLength(3)
    expect(result[0].id).toBe('a')
    expect(result[1].id).not.toBe('a')
    expect(result[1].id).not.toBe('b')
    expect(result[1].name).toBe('a (copy)')
    expect(result[1].config).toEqual(steps[0].config)
    expect(result.map(s => s.step_order)).toEqual([1, 2, 3])
  })

  it('is a no-op when the step id is not found', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 })]
    expect(duplicateStep(steps, 'missing')).toBe(steps)
  })
})

describe('assignParallelGroup', () => {
  it('moves the step to the target index and sets its parallel_group', () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1 }),
      makeStep({ id: 'b', step_order: 2, parallel_group: 'g1' }),
      makeStep({ id: 'c', step_order: 3, parallel_group: 'g1' }),
    ]
    const result = assignParallelGroup(steps, 'a', 'g1', 1)
    expect(result.map(s => s.id)).toEqual(['b', 'a', 'c'])
    expect(result.find(s => s.id === 'a')?.parallel_group).toBe('g1')
    expect(result.map(s => s.step_order)).toEqual([1, 2, 3])
  })

  it('clears parallel_group when passed null (dropping near an ungrouped node)', () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1, parallel_group: 'g1' }),
      makeStep({ id: 'b', step_order: 2 }),
    ]
    const result = assignParallelGroup(steps, 'a', null, 1)
    expect(result.find(s => s.id === 'a')?.parallel_group).toBeNull()
  })

  it('clamps out-of-range target indices', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
    const result = assignParallelGroup(steps, 'a', null, 99)
    expect(result.map(s => s.id)).toEqual(['b', 'a'])
  })

  it('is a no-op when the step id is not found', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 })]
    expect(assignParallelGroup(steps, 'missing', 'g1', 0)).toBe(steps)
  })
})
