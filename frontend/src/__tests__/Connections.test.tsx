import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import Connections from '../pages/Connections'

const MOCK_DB_CONNECTIONS = [
  {
    id: 'db1', name: 'Production Postgres', db_type: 'postgresql',
    config: { host: 'localhost', port: 5432, database: 'prod', username: 'app' },
    is_default: true, created_at: new Date().toISOString(),
  },
]

const MOCK_EMAIL_PROVIDERS = [
  {
    id: 'ep1', name: 'Company Gmail', provider_type: 'gmail',
    config: {}, is_default: false, created_at: new Date().toISOString(),
  },
]

vi.mock('../lib/api', () => ({
  getDbConnections:    vi.fn(() => Promise.resolve(MOCK_DB_CONNECTIONS)),
  getEmailProviders:   vi.fn(() => Promise.resolve(MOCK_EMAIL_PROVIDERS)),
  createDbConnection:  vi.fn(() => Promise.resolve({})),
  updateDbConnection:  vi.fn(() => Promise.resolve({})),
  deleteDbConnection:  vi.fn(() => Promise.resolve({})),
  testDbConnection:    vi.fn(() => Promise.resolve({ success: true, latency_ms: 12 })),
  testDbConnectionRaw: vi.fn(() => Promise.resolve({ success: true, latency_ms: 8 })),
  createEmailProvider: vi.fn(() => Promise.resolve({})),
  updateEmailProvider: vi.fn(() => Promise.resolve({})),
  deleteEmailProvider: vi.fn(() => Promise.resolve({})),
  testEmailProvider:   vi.fn(() => Promise.resolve({ success: true })),
  getDbConnection:     vi.fn(() => Promise.resolve(MOCK_DB_CONNECTIONS[0])),
  getEmailProvider:    vi.fn(() => Promise.resolve(MOCK_EMAIL_PROVIDERS[0])),
  getProjects:         vi.fn(() => Promise.resolve([])),
}))

describe('Connections page', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Connections />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Connections' })).toBeInTheDocument()
    })
  })

  it('shows DB Connections tab active by default', async () => {
    renderWithProviders(<Connections />)
    await waitFor(() => {
      expect(screen.getByText('Production Postgres')).toBeInTheDocument()
    })
  })

  it('shows an Add Connection button', async () => {
    renderWithProviders(<Connections />)
    await waitFor(() => {
      expect(screen.getByText('Add Connection')).toBeInTheDocument()
    })
  })

  it('switches to Email Providers tab', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Connections />)

    // Click the "Email Providers" tab button specifically
    await waitFor(() => {
      const tabs = screen.getAllByText('Email Providers')
      expect(tabs.length).toBeGreaterThan(0)
    })
    await user.click(screen.getAllByText('Email Providers')[0])

    await waitFor(() => {
      expect(screen.getByText('Company Gmail')).toBeInTheDocument()
    })
  })

  it('shows test button for each DB connection', async () => {
    renderWithProviders(<Connections />)
    await waitFor(() => {
      expect(screen.getByText('Production Postgres')).toBeInTheDocument()
    })
    expect(screen.getAllByText('Test').length).toBeGreaterThan(0)
  })
})
