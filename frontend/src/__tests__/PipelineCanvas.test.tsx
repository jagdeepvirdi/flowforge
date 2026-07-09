import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import PipelineCanvas from '../components/pipeline/canvas/PipelineCanvas'
import type { PipelineStep } from '../lib/types'

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

function renderCanvas(steps: PipelineStep[]) {
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
    />,
  )
  return { ...utils, onStepsChange, onDuplicate, onDelete }
}

describe('PipelineCanvas', () => {
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
})
