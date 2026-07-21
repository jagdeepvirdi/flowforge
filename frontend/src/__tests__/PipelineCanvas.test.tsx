import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react'
import PipelineCanvas from '../components/pipeline/canvas/PipelineCanvas'
import { addStepDep, removeStepDep } from '../lib/api'
import type { PipelineStep, StepDep } from '../lib/types'

// jsdom doesn't implement <dialog>.showModal()/close() — stub them so the
// side panel's imperative open-state sync doesn't throw in tests (same
// stub used by HelpDrawer.test.tsx for the same reason).
beforeAll(() => {
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.removeAttribute('open')
  }
})

vi.mock('../lib/api', () => ({
  addStepDep: vi.fn(() => Promise.resolve({ dep_id: 'new-dep', upstream_step_id: 'a', downstream_step_id: 'b' })),
  removeStepDep: vi.fn(() => Promise.resolve({ deleted: 'dep-1' })),
}))

// Simulating a real pointer-drag handle-to-handle connect (or a Delete-key edge removal) is
// the same class of flaky-under-automation gesture documented for drag-to-reorder in
// e2e/pipeline-canvas.spec.ts's header comment — so here `ReactFlow` itself is replaced with a
// minimal stand-in that still mounts real node components (via the real `nodeTypes`, so every
// pre-existing test below keeps exercising real StepNode/StepPanel DOM), but exposes
// `onConnect`/`onEdgesDelete` as plain buttons instead of a gesture, so the actual handler code
// in PipelineCanvas.tsx is what's under test — not a reimplementation of it.
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return {
    ...actual,
    ReactFlow: (props: {
      nodes: { id: string; type: string; data: unknown; selected: boolean }[]
      edges: { data?: { depId?: string } }[]
      nodeTypes: Record<string, React.ComponentType<{ data: unknown; selected: boolean }>>
      onNodeClick?: (e: unknown, node: unknown) => void
      onConnect?: (c: { source: string; target: string; sourceHandle: null; targetHandle: null }) => void
      onEdgesDelete?: (edges: { data?: { depId?: string } }[]) => void
    }) => (
      <div data-testid="mock-reactflow">
        {props.nodes.map(n => {
          const Comp = props.nodeTypes[n.type]
          return (
            <div key={n.id} onClick={e => props.onNodeClick?.(e, n)}>
              <Comp {...n} />
            </div>
          )
        })}
        <span data-testid="mock-edge-count">{props.edges.length}</span>
        <button
          data-testid="__trigger_connect"
          onClick={() => {
            const [n0, n1] = props.nodes
            if (n0 && n1) props.onConnect?.({ source: n0.id, target: n1.id, sourceHandle: null, targetHandle: null })
          }}
        />
        <button
          data-testid="__trigger_self_connect"
          onClick={() => {
            const [n0] = props.nodes
            if (n0) props.onConnect?.({ source: n0.id, target: n0.id, sourceHandle: null, targetHandle: null })
          }}
        />
        <button
          data-testid="__trigger_delete_edges"
          onClick={() => props.onEdgesDelete?.(props.edges)}
        />
      </div>
    ),
  }
})

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

function makeStepDep(overrides: Partial<StepDep> & { dep_id: string }): StepDep {
  return { upstream_step_id: 'a', downstream_step_id: 'b', ...overrides }
}

function renderCanvas(steps: PipelineStep[], extra: {
  pipelineId?: string
  stepDeps?: StepDep[]
  onStepDepsChanged?: () => void
} = {}) {
  const onStepsChange = vi.fn()
  const onDuplicate = vi.fn()
  const onDelete = vi.fn()
  const utils = render(
    <PipelineCanvas
      steps={steps}
      onStepsChange={onStepsChange}
      onDuplicate={onDuplicate}
      onDelete={onDelete}
      dbConnections={[]}
      reportConfigs={[]}
      emailConfigs={[]}
      bulkLoadConfigs={[]}
      {...extra}
    />,
  )
  return { ...utils, onStepsChange, onDuplicate, onDelete }
}

describe('PipelineCanvas', () => {
  beforeEach(() => {
    vi.mocked(addStepDep).mockClear()
    vi.mocked(removeStepDep).mockClear()
  })

  it('shows the empty state when there are no steps', () => {
    renderCanvas([])
    expect(screen.getByText('Add steps using the buttons above.')).toBeInTheDocument()
  })

  it('renders one node per step', () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1 }),
      makeStep({ id: 'b', step_order: 2 }),
      makeStep({ id: 'c', step_order: 3 }),
    ]
    renderCanvas(steps)
    expect(screen.getByTestId('canvas-node-a')).toBeInTheDocument()
    expect(screen.getByTestId('canvas-node-b')).toBeInTheDocument()
    expect(screen.getByTestId('canvas-node-c')).toBeInTheDocument()
  })

  it('opens the side panel with the correct step when a node is clicked', async () => {
    const steps = [
      makeStep({ id: 'a', step_order: 1, name: 'Extract customers' }),
      makeStep({ id: 'b', step_order: 2, name: 'Send report' }),
    ]
    renderCanvas(steps)
    fireEvent.click(screen.getByTestId('canvas-node-a'))
    const dialog = await screen.findByLabelText('Edit step', { selector: 'dialog' })
    expect(within(dialog).getByText('Extract customers')).toBeInTheDocument()
    expect(dialog).toHaveStyle({ display: 'flex' })
  })

  it('closes the panel when the close button is clicked', async () => {
    const steps = [makeStep({ id: 'a', step_order: 1, name: 'Extract customers' })]
    renderCanvas(steps)
    fireEvent.click(screen.getByTestId('canvas-node-a'))
    const dialog = await screen.findByLabelText('Edit step', { selector: 'dialog' })
    expect(dialog).toHaveStyle({ display: 'flex' })

    fireEvent.click(within(dialog).getByTitle('Close'))
    expect(dialog).toHaveStyle({ display: 'none' })
  })

  it('calls onDuplicate when a node hover-action duplicate button is clicked', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 })]
    const { onDuplicate } = renderCanvas(steps)
    const node = screen.getByTestId('canvas-node-a')
    fireEvent.click(within(node).getByTitle('Duplicate step'))
    expect(onDuplicate).toHaveBeenCalledWith('a')
  })

  it('calls onDelete when a node hover-action delete button is clicked', () => {
    const steps = [makeStep({ id: 'a', step_order: 1 })]
    const { onDelete } = renderCanvas(steps)
    const node = screen.getByTestId('canvas-node-a')
    fireEvent.click(within(node).getByTitle('Delete step'))
    expect(onDelete).toHaveBeenCalledWith('a')
  })

  describe('real step-dependency edges (Phase 14 Option B, Milestone 3)', () => {
    it('uses synthetic wave edges when no real step dependencies exist', () => {
      const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
      renderCanvas(steps)
      // a -> b synthetic wave edge
      expect(screen.getByTestId('mock-edge-count').textContent).toBe('1')
    })

    it('uses real edges exclusively (not synthetic ones) once step dependencies exist', () => {
      const steps = [
        makeStep({ id: 'a', step_order: 1 }),
        makeStep({ id: 'b', step_order: 2 }),
        makeStep({ id: 'c', step_order: 3 }),
      ]
      // Only one real edge (a->b), even though 3 sequential steps would synthesize 2 wave edges.
      const stepDeps = [makeStepDep({ dep_id: 'd1', upstream_step_id: 'a', downstream_step_id: 'b' })]
      renderCanvas(steps, { pipelineId: 'p1', stepDeps })
      expect(screen.getByTestId('mock-edge-count').textContent).toBe('1')
    })

    it('connecting two steps calls addStepDep and clears any prior error on success', async () => {
      const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
      const onStepDepsChanged = vi.fn()
      renderCanvas(steps, { pipelineId: 'p1', stepDeps: [], onStepDepsChanged })

      fireEvent.click(screen.getByTestId('__trigger_connect'))

      await waitFor(() => expect(onStepDepsChanged).toHaveBeenCalled())
      expect(addStepDep).toHaveBeenCalledWith('p1', 'a', 'b')
      expect(screen.queryByTestId('canvas-connect-error')).not.toBeInTheDocument()
    })

    it('shows an inline error and does not call the API when the pipeline is unsaved', () => {
      const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
      renderCanvas(steps, { pipelineId: undefined })

      fireEvent.click(screen.getByTestId('__trigger_connect'))

      expect(screen.getByTestId('canvas-connect-error')).toHaveTextContent(/save this pipeline/i)
      expect(addStepDep).not.toHaveBeenCalled()
    })

    it('shows an inline error and does not call the API for a self-connection', () => {
      const steps = [makeStep({ id: 'a', step_order: 1 })]
      renderCanvas(steps, { pipelineId: 'p1' })

      fireEvent.click(screen.getByTestId('__trigger_self_connect'))

      expect(screen.getByTestId('canvas-connect-error')).toHaveTextContent(/cannot depend on itself/i)
      expect(addStepDep).not.toHaveBeenCalled()
    })

    it('surfaces a 409 cycle error from the API as inline feedback, not a silent failure', async () => {
      vi.mocked(addStepDep).mockRejectedValueOnce(new Error('Adding this dependency would create a circular dependency'))
      const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
      renderCanvas(steps, { pipelineId: 'p1' })

      fireEvent.click(screen.getByTestId('__trigger_connect'))

      await waitFor(() =>
        expect(screen.getByTestId('canvas-connect-error')).toHaveTextContent(/circular dependency/i),
      )
    })

    it('deleting a real edge calls removeStepDep with its dep_id', async () => {
      const steps = [makeStep({ id: 'a', step_order: 1 }), makeStep({ id: 'b', step_order: 2 })]
      const stepDeps = [makeStepDep({ dep_id: 'd1', upstream_step_id: 'a', downstream_step_id: 'b' })]
      const onStepDepsChanged = vi.fn()
      renderCanvas(steps, { pipelineId: 'p1', stepDeps, onStepDepsChanged })

      fireEvent.click(screen.getByTestId('__trigger_delete_edges'))

      await waitFor(() => expect(onStepDepsChanged).toHaveBeenCalled())
      expect(removeStepDep).toHaveBeenCalledWith('p1', 'd1')
    })
  })
})
