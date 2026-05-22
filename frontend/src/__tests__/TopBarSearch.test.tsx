import { describe, it, expect } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createTestQueryClient } from './helpers'
import TopBar from '../components/shared/TopBar'

describe('TopBar search', () => {
  it('renders the search input', () => {
    renderWithProviders(<TopBar crumbs={['Workspace', 'Dashboard']} />)
    expect(screen.getByPlaceholderText('Search…')).toBeInTheDocument()
  })

  it('shows results from seeded React Query cache', async () => {
    const user = userEvent.setup()
    const queryClient = createTestQueryClient()

    queryClient.setQueryData(['pipelines'], [
      {
        id: 'p1', name: 'Monthly Revenue Report', description: '',
        schedule: null, enabled: true, timeout_minutes: 60,
        created_at: '', updated_at: '', steps: [], variables: [],
      },
    ])
    queryClient.setQueryData(['report-configs'], [])
    queryClient.setQueryData(['email-configs'], [])

    renderWithProviders(<TopBar crumbs={['Dashboard']} />, { queryClient })

    const input = screen.getByPlaceholderText('Search…')
    await user.click(input)
    await user.type(input, 'revenue')

    await waitFor(() => {
      expect(screen.getByText('Monthly Revenue Report')).toBeInTheDocument()
    })
  })

  it('shows cache-empty hint when cache is empty and query is typed', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TopBar crumbs={['Dashboard']} />)

    const input = screen.getByPlaceholderText('Search…')
    await user.click(input)
    await user.type(input, 'anything')

    await waitFor(() => {
      expect(screen.getByText('Visit Pipelines and Reports pages first to populate search')).toBeInTheDocument()
    })
  })

  it('shows no results message when caches are populated but nothing matches', async () => {
    const user = userEvent.setup()
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(['pipelines'], [
      { id: 'p1', name: 'Unrelated Pipeline', description: '', schedule: null, enabled: true, timeout_minutes: 60, created_at: '', updated_at: '', steps: [], variables: [] },
    ])
    queryClient.setQueryData(['report-configs'], [])
    queryClient.setQueryData(['email-configs'], [])

    renderWithProviders(<TopBar crumbs={['Dashboard']} />, { queryClient })

    const input = screen.getByPlaceholderText('Search…')
    await user.click(input)
    await user.type(input, 'xyzzy_no_match')

    await waitFor(() => {
      expect(screen.getByText('No results')).toBeInTheDocument()
    })
  })

  it('clears results when Escape is pressed', async () => {
    const user = userEvent.setup()
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(['pipelines'], [
      {
        id: 'p1', name: 'Escape Test Pipeline', description: '',
        schedule: null, enabled: true, timeout_minutes: 60,
        created_at: '', updated_at: '', steps: [], variables: [],
      },
    ])

    renderWithProviders(<TopBar crumbs={['Dashboard']} />, { queryClient })

    const input = screen.getByPlaceholderText('Search…')
    await user.click(input)
    await user.type(input, 'escape')
    await waitFor(() => { expect(screen.getByText('Escape Test Pipeline')).toBeInTheDocument() })

    await user.keyboard('{Escape}')
    await waitFor(() => {
      expect(screen.queryByText('Escape Test Pipeline')).not.toBeInTheDocument()
    })
  })

  it('searches report configs from cache', async () => {
    const user = userEvent.setup()
    const queryClient = createTestQueryClient()
    queryClient.setQueryData(['pipelines'], [])
    queryClient.setQueryData(['report-configs'], [
      {
        id: 'r1', name: 'Finance Summary Report', description: '',
        format: 'excel', query: '', output_filename: '',
        connection_id: null, title: null, sheet_name: null, columns: [],
        created_at: '', updated_at: '',
      },
    ])
    queryClient.setQueryData(['email-configs'], [])

    renderWithProviders(<TopBar crumbs={['Reports']} />, { queryClient })

    const input = screen.getByPlaceholderText('Search…')
    await user.click(input)
    await user.type(input, 'finance')

    await waitFor(() => {
      expect(screen.getByText('Finance Summary Report')).toBeInTheDocument()
    })
  })
})
