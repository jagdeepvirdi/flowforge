import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import StepTrendsPanel from '../components/runs/StepTrendsPanel'

const MOCK_TRENDS = {
  window_days: 30,
  step_type: null,
  pipeline_id: null,
  available_step_types: ['bulk_load', 'report'],
  series: [
    { date: '2026-07-01', run_count: 4, success_count: 4, failure_count: 0, avg_duration_ms: 1200, p95_duration_ms: 2000, avg_rows_affected: 500 },
    { date: '2026-07-02', run_count: 3, success_count: 2, failure_count: 1, avg_duration_ms: 1500, p95_duration_ms: 2400, avg_rows_affected: 480 },
  ],
}

vi.mock('../lib/api', () => ({
  getStepRunTrends: vi.fn(() => Promise.resolve(MOCK_TRENDS)),
}))

describe('StepTrendsPanel', () => {
  it('renders collapsed by default without fetching', async () => {
    const { getStepRunTrends } = await import('../lib/api')
    renderWithProviders(<StepTrendsPanel />)
    expect(screen.getByText('Performance Trends')).toBeInTheDocument()
    expect(getStepRunTrends).not.toHaveBeenCalled()
  })

  it('fetches and renders the chart controls when expanded', async () => {
    const user = userEvent.setup()
    renderWithProviders(<StepTrendsPanel />)
    await user.click(screen.getByText('Performance Trends'))

    await waitFor(() => {
      expect(screen.getByText('Duration over time')).toBeInTheDocument()
    })
    expect(await screen.findByText('7 step runs')).toBeInTheDocument()
    expect(screen.getByText('1 failure')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'bulk_load' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'report' })).toBeInTheDocument()
  })

  it('shows an empty state when the series is empty', async () => {
    const { getStepRunTrends } = await import('../lib/api')
    ;(getStepRunTrends as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      window_days: 30, step_type: null, pipeline_id: null, available_step_types: [], series: [],
    })
    const user = userEvent.setup()
    renderWithProviders(<StepTrendsPanel />)
    await user.click(screen.getByText('Performance Trends'))
    expect(await screen.findByText(/No step runs in the last 30 days/)).toBeInTheDocument()
  })

  it('passes pipelineId through to the query', async () => {
    const { getStepRunTrends } = await import('../lib/api')
    const user = userEvent.setup()
    renderWithProviders(<StepTrendsPanel pipelineId="pipe-123" />)
    await user.click(screen.getByText('Performance Trends'))
    await waitFor(() => {
      expect(getStepRunTrends).toHaveBeenCalledWith(
        expect.objectContaining({ pipeline_id: 'pipe-123' }),
      )
    })
  })
})
