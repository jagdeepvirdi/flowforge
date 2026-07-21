import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import Connections from '../pages/Connections'

vi.mock('../lib/auth', () => ({
  useAuth: vi.fn(() => ({ token: 'tok', setToken: vi.fn(), setUser: vi.fn(), clearToken: vi.fn(), isAuthenticated: () => true })),
  useCurrentUser: vi.fn(() => ({ id: 'u1', username: 'admin', role: 'admin' })),
}))

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

const MOCK_CONNECTION_REGISTRY = [
  { key: 'postgresql', display_name: 'PostgreSQL', description: '', requires: null, tier: null, plugin: false, installed: true },
  { key: 'my_custom_db', display_name: 'My Custom DB', description: '', requires: null, tier: null, plugin: true, installed: true },
]
const MOCK_PROVIDER_REGISTRY = [
  { key: 'smtp', display_name: 'SMTP', description: '', requires: null, tier: null, plugin: false, installed: true },
  { key: 'my_custom_provider', display_name: 'My Custom Provider', description: '', requires: null, tier: null, plugin: true, installed: true },
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
  getRegistryCategory: vi.fn((category: string) =>
    Promise.resolve(category === 'connections' ? MOCK_CONNECTION_REGISTRY : MOCK_PROVIDER_REGISTRY)),
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

  // ── ARCH-10: plugin db_type/provider_type JSON fallback ────────────────────

  it('lists a plugin db_type as an extra option and shows the JSON fallback when selected', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Connections />)

    await user.click(await screen.findByText('Add Connection'))
    const typeSelect = await screen.findByDisplayValue('PostgreSQL')
    await waitFor(() => {
      expect(screen.getByText('My Custom DB (plugin)')).toBeInTheDocument()
    })

    await user.selectOptions(typeSelect, 'my_custom_db')
    expect(screen.getByText(/No dedicated form for this plugin db_type/)).toBeInTheDocument()
  })

  it('lists a plugin provider_type as an extra option and shows the JSON fallback when selected', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Connections />)

    await user.click(await screen.findByText('Add Connection'))
    await user.click(screen.getByText('Email Provider'))
    const typeSelect = await screen.findByDisplayValue('SMTP (Generic)')
    await waitFor(() => {
      expect(screen.getByText('My Custom Provider (plugin)')).toBeInTheDocument()
    })

    await user.selectOptions(typeSelect, 'my_custom_provider')
    expect(screen.getByText(/No dedicated form for this plugin provider_type/)).toBeInTheDocument()
    // Sender Email is part of the dedicated forms, not shown for plugin types
    expect(screen.queryByText('Sender Email')).not.toBeInTheDocument()
  })

  it('shows a form error when saving a plugin connection with invalid JSON config', async () => {
    const user = userEvent.setup()
    const { container } = renderWithProviders(<Connections />)

    await user.click(await screen.findByText('Add Connection'))
    const typeSelect = await screen.findByDisplayValue('PostgreSQL')
    await waitFor(() => expect(screen.getByText('My Custom DB (plugin)')).toBeInTheDocument())
    await user.selectOptions(typeSelect, 'my_custom_db')

    await user.type(screen.getByPlaceholderText('Production DB'), 'My Plugin Conn')
    const textarea = container.querySelector('textarea') as HTMLTextAreaElement
    expect(textarea).toBeTruthy()
    await user.clear(textarea)
    await user.type(textarea, 'not valid json')

    await user.click(screen.getByText('Save Connection'))
    expect(await screen.findByText(/not valid JSON/)).toBeInTheDocument()
  })
})
