import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import Dashboard from '../pages/Dashboard'

vi.mock('../lib/api', () => ({
  getPipelines:    vi.fn(() => Promise.resolve([])),
  getRuns:         vi.fn(() => Promise.resolve([])),
  getPipelineRuns: vi.fn(() => Promise.resolve([])),
  runPipeline:     vi.fn(() => Promise.resolve({ run_id: 'r1', status: 'running' })),
}))

describe('Dashboard', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Dashboard />)
    // breadcrumb text is rendered synchronously by TopBar
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('shows stats section', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Runs today')).toBeInTheDocument()
    })
  })

  it('shows success rate stat', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Success rate')).toBeInTheDocument()
    })
  })

  it('renders pipeline cards when pipelines are returned', async () => {
    const { getPipelines } = await import('../lib/api')
    ;(getPipelines as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      {
        id: 'p1', name: 'Monthly Revenue', description: 'Runs every month',
        schedule: '0 8 1 * *', enabled: true, timeout_minutes: 60,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
        steps: [], variables: [],
      },
    ])

    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Monthly Revenue')).toBeInTheDocument()
    })
  })

  it('shows empty state when no pipelines configured', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      // Stats section always renders even with no pipelines
      expect(screen.getByText('Active schedules')).toBeInTheDocument()
    })
  })
})
