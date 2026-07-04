import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import Settings from '../pages/Settings'

vi.mock('../lib/api', () => ({
  getSetupStatus: vi.fn(() => Promise.resolve({
    gmail:        { configured: false, sender: '' },
    drive:        { configured: false, folder_id: '' },
    microsoft365: { configured: false, sender: '' },
    ai:           { enabled: true, ollama_url: 'http://localhost:11434', model: 'llama3.2:3b' },
    retention:    { run_days: 90, audit_days: 90 },
  })),
  getMfaStatus:   vi.fn(() => Promise.resolve({ mfa_enabled: false, sso_provider: null })),
  mfaEnroll:      vi.fn(() => Promise.resolve({ provisioning_uri: '', secret: '' })),
  mfaConfirm:     vi.fn(() => Promise.resolve({ backup_codes: [] })),
  mfaDisable:     vi.fn(() => Promise.resolve({ message: 'ok' })),
  changePassword: vi.fn(() => Promise.resolve({})),
  getProjects:    vi.fn(() => Promise.resolve([])),
}))

describe('Settings', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()
    })
  })

  it('shows Change Password section title', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      // "Change Password" appears in section title and button — use getAllByText
      expect(screen.getAllByText('Change Password').length).toBeGreaterThan(0)
    })
  })

  it('shows Google OAuth2 section', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'Email & AI' }))
    await waitFor(() => {
      expect(screen.getByText('Google OAuth2 (Gmail + Drive)')).toBeInTheDocument()
    })
  })

  it('shows Microsoft 365 section', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'Email & AI' }))
    await waitFor(() => {
      expect(screen.getByText('Microsoft 365 OAuth2')).toBeInTheDocument()
    })
  })

  it('shows AI section title', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'Email & AI' }))
    await waitFor(() => {
      expect(screen.getByText('AI Features (Ollama)')).toBeInTheDocument()
    })
  })

  it('shows retention policy section title', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'System' }))
    await waitFor(() => {
      expect(screen.getByText('Data Retention Policies')).toBeInTheDocument()
    })
  })

  it('shows password form fields', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByLabelText('Current Password')).toBeInTheDocument()
      expect(screen.getByLabelText('New Password')).toBeInTheDocument()
    })
  })
})
