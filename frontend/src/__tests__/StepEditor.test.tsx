import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DndContext } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import StepEditor from '../components/pipeline/StepEditor'
import type { PipelineStep } from '../lib/types'

function makeStep(overrides: Partial<PipelineStep> = {}): PipelineStep {
  return {
    id: 's1',
    pipeline_id: 'p1',
    step_order: 1,
    name: 'Extract customers',
    step_type: 'db_query',
    config: {},
    on_error: 'stop',
    enabled: true,
    parallel_group: null,
    ...overrides,
  }
}

function renderStepEditor(step: PipelineStep, overrides: Partial<React.ComponentProps<typeof StepEditor>> = {}) {
  const onChange = vi.fn()
  const onDelete = vi.fn()
  const onDuplicate = vi.fn()
  render(
    <DndContext onDragEnd={() => {}}>
      <SortableContext items={[step.id]} strategy={verticalListSortingStrategy}>
        <StepEditor
          step={step}
          onChange={onChange}
          onDelete={onDelete}
          onDuplicate={onDuplicate}
          allSteps={[step]}
          dbConnections={[]}
          reportConfigs={[]}
          emailConfigs={[]}
          bulkLoadConfigs={[]}
          {...overrides}
        />
      </SortableContext>
    </DndContext>,
  )
  return { onChange, onDelete, onDuplicate }
}

describe('StepEditor', () => {
  it('renders the step name and type badge', () => {
    renderStepEditor(makeStep())
    expect(screen.getByDisplayValue('Extract customers')).toBeInTheDocument()
    expect(screen.getByText('Query')).toBeInTheDocument()
  })

  it('shows the parallel-group pill when set', () => {
    renderStepEditor(makeStep({ parallel_group: 'g1' }))
    expect(screen.getByText('∥ g1')).toBeInTheDocument()
  })

  it('calls onChange when the name is edited', () => {
    const { onChange } = renderStepEditor(makeStep())
    fireEvent.change(screen.getByDisplayValue('Extract customers'), { target: { value: 'New name' } })
    expect(onChange).toHaveBeenCalledWith('s1', { name: 'New name' })
  })

  it('calls onDuplicate when the duplicate button is clicked', () => {
    const { onDuplicate } = renderStepEditor(makeStep())
    fireEvent.click(screen.getByTitle('Duplicate step'))
    expect(onDuplicate).toHaveBeenCalledWith('s1')
  })

  it('calls onDelete when the delete button is clicked', () => {
    const { onDelete } = renderStepEditor(makeStep())
    const buttons = screen.getAllByRole('button')
    const deleteBtn = buttons[buttons.length - 1]
    fireEvent.click(deleteBtn)
    expect(onDelete).toHaveBeenCalledWith('s1')
  })

  it('falls back to a JSON config textarea for step types without a dedicated form', () => {
    renderStepEditor(makeStep({ step_type: 'some_plugin_type', config: { foo: 'bar' } }))
    expect(screen.getByText(/Config \(JSON\)/)).toBeInTheDocument()
    expect(screen.getByDisplayValue(/"foo":\s*"bar"/)).toBeInTheDocument()
  })
})
