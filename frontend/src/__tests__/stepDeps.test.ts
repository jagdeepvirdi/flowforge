import { describe, it, expect } from 'vitest'
import { toRealFlowEdges, canConnectSteps } from '../components/pipeline/canvas/stepDeps'
import type { StepDep } from '../lib/types'

describe('toRealFlowEdges', () => {
  it('maps upstream/downstream step ids to source/target', () => {
    const deps: StepDep[] = [
      { dep_id: 'd1', upstream_step_id: 'a', downstream_step_id: 'b' },
      { dep_id: 'd2', upstream_step_id: 'b', downstream_step_id: 'c' },
    ]
    const edges = toRealFlowEdges(deps)
    expect(edges).toHaveLength(2)
    expect(edges[0]).toMatchObject({ id: 'd1', source: 'a', target: 'b', deletable: true })
    expect(edges[1]).toMatchObject({ id: 'd2', source: 'b', target: 'c', deletable: true })
  })

  it('carries the dep_id in edge.data for delete-time lookup', () => {
    const edges = toRealFlowEdges([{ dep_id: 'd1', upstream_step_id: 'a', downstream_step_id: 'b' }])
    expect(edges[0].data).toEqual({ depId: 'd1' })
  })

  it('returns an empty array for no dependencies', () => {
    expect(toRealFlowEdges([])).toEqual([])
  })
})

describe('canConnectSteps', () => {
  it('allows a normal connection between two saved steps on a saved pipeline', () => {
    expect(canConnectSteps({ pipelineId: 'p1', source: 'a', target: 'b' })).toEqual({ allowed: true })
  })

  it('rejects when the pipeline is unsaved (no pipelineId)', () => {
    const result = canConnectSteps({ pipelineId: undefined, source: 'a', target: 'b' })
    expect(result.allowed).toBe(false)
    expect(result.reason).toMatch(/save this pipeline/i)
  })

  it('rejects when the source step is unsaved', () => {
    const result = canConnectSteps({ pipelineId: 'p1', source: '_new_123', target: 'b' })
    expect(result.allowed).toBe(false)
    expect(result.reason).toMatch(/save this pipeline/i)
  })

  it('rejects when the target step is unsaved', () => {
    const result = canConnectSteps({ pipelineId: 'p1', source: 'a', target: '_new_456' })
    expect(result.allowed).toBe(false)
  })

  it('rejects a self-connection', () => {
    const result = canConnectSteps({ pipelineId: 'p1', source: 'a', target: 'a' })
    expect(result.allowed).toBe(false)
    expect(result.reason).toMatch(/cannot depend on itself/i)
  })
})
