import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import Reports from '../pages/Reports'

const MOCK_REPORTS = [
  {
    id: 'r1', name: 'Monthly Revenue', description: 'Finance report',
    connection_id: 'c1', query: 'SELECT * FROM revenue', format: 'excel',
    output_filename: 'revenue_{{ current_month }}.xlsx',
    title: null, sheet_name: 'Revenue', columns: [],
    project_id: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
  {
    id: 'r2', name: 'Daily Subscribers', description: '',
    connection_id: null, query: 'SELECT * FROM subs', format: 'csv',
    output_filename: 'subs_{{ current_date }}.csv',
    title: null, sheet_name: null, columns: [],
    project_id: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
]

vi.mock('../lib/api', () => ({
  getReportConfigs:  vi.fn(() => Promise.resolve(MOCK_REPORTS)),
  deleteReportConfig: vi.fn(() => Promise.resolve({})),
  getProjects:       vi.fn(() => Promise.resolve([])),
}))

describe('Reports', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeInTheDocument()
    })
  })

  it('lists report names', async () => {
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText('Monthly Revenue')).toBeInTheDocument()
      expect(screen.getByText('Daily Subscribers')).toBeInTheDocument()
    })
  })

  it('shows report count', async () => {
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText(/2 report/i)).toBeInTheDocument()
    })
  })

  it('shows New Report button', async () => {
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText('New Report')).toBeInTheDocument()
    })
  })

  it('shows empty state when no reports', async () => {
    const { getReportConfigs } = await import('../lib/api')
    ;(getReportConfigs as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText(/no report/i)).toBeInTheDocument()
    })
  })

  it('shows output filenames', async () => {
    renderWithProviders(<Reports />)
    await waitFor(() => {
      expect(screen.getByText(/revenue_/i)).toBeInTheDocument()
    })
  })
})
