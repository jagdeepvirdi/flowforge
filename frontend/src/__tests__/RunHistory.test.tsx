import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import RunHistory from '../pages/RunHistory'

const MOCK_RUNS = [
  {
    id: 'run-1', pipeline_id: 'p1', pipeline_name: 'Daily Revenue Report',
    status: 'success', started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(), duration_ms: 4200,
    triggered_by: 'scheduler', error_step: null, error_message: null, step_runs: [],
  },
  {
    id: 'run-2', pipeline_id: 'p2', pipeline_name: 'Weekly Summary',
    status: 'failed', started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(), duration_ms: 1100,
    triggered_by: 'web_ui', error_step: 'Generate Report', error_message: 'Connection timeout',
    step_runs: [],
  },
]

vi.mock('../lib/api', () => ({
  getRuns:      vi.fn(() => Promise.resolve(MOCK_RUNS)),
  getPipelines: vi.fn(() => Promise.resolve([])),
  getProjects:  vi.fn(() => Promise.resolve([])),
}))

describe('RunHistory', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      expect(screen.getByText('Run History')).toBeInTheDocument()
    })
  })

  it('shows run pipeline names', async () => {
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      expect(screen.getByText('Daily Revenue Report')).toBeInTheDocument()
      expect(screen.getByText('Weekly Summary')).toBeInTheDocument()
    })
  })

  it('shows success count stat', async () => {
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      // The mini-stats bar renders "SUCCESS" (textTransform:uppercase) with label "Success"
      // Use getAllByText since StatusBadge also renders "Success" for each run row
      expect(screen.getAllByText('Success').length).toBeGreaterThan(0)
    })
  })

  it('shows failed count stat', async () => {
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      expect(screen.getAllByText('Failed').length).toBeGreaterThan(0)
    })
  })

  it('shows search input', async () => {
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search by run id/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no runs', async () => {
    const { getRuns } = await import('../lib/api')
    ;(getRuns as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])
    renderWithProviders(<RunHistory />)
    await waitFor(() => {
      expect(screen.getByText(/no runs/i)).toBeInTheDocument()
    })
  })
})
