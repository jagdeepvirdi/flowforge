import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import Settings from '../pages/Settings'
import { useCurrentUser } from '../lib/auth'
import { updateRetentionSettings } from '../lib/api'

const RETENTION_DEFAULTS = {
  run_retention_days: 90,
  audit_retention_days: 90,
  output_ttl_days: 7,
  is_custom: { run_retention_days: false, audit_retention_days: false, output_ttl_days: false },
}

vi.mock('../lib/api', () => ({
  getSetupStatus: vi.fn(() => Promise.resolve({
    gmail:        { configured: false, sender: '' },
    drive:        { configured: false, folder_id: '' },
    microsoft365: { configured: false, sender: '' },
    ai: {
      enabled: true, ollama_url: 'http://localhost:11434', model: 'llama3.2:3b',
      claude: { configured: false },
      gemini: { configured: false, model: 'gemini-2.5-flash' },
    },
    retention:    { run_days: 90, audit_days: 90 },
  })),
  getMfaStatus:   vi.fn(() => Promise.resolve({ mfa_enabled: false, sso_provider: null })),
  mfaEnroll:      vi.fn(() => Promise.resolve({ provisioning_uri: '', secret: '' })),
  mfaConfirm:     vi.fn(() => Promise.resolve({ backup_codes: [] })),
  mfaDisable:     vi.fn(() => Promise.resolve({ message: 'ok' })),
  changePassword: vi.fn(() => Promise.resolve({})),
  getProjects:    vi.fn(() => Promise.resolve([])),
  getRetentionSettings:    vi.fn(() => Promise.resolve(RETENTION_DEFAULTS)),
  updateRetentionSettings: vi.fn(() => Promise.resolve({
    run_retention_days: 90, audit_retention_days: 90, output_ttl_days: 7,
  })),
}))

vi.mock('../lib/auth', () => ({
  useCurrentUser: vi.fn(() => ({ id: 'u1', username: 'viewer', role: 'viewer' })),
}))

describe('Settings', () => {
  beforeEach(() => {
    vi.mocked(useCurrentUser).mockReturnValue({ id: 'u1', username: 'viewer', role: 'viewer' })
  })

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
    await user.click(await screen.findByRole('button', { name: 'Email' }))
    await waitFor(() => {
      expect(screen.getByText('Google OAuth2 (Gmail + Drive)')).toBeInTheDocument()
    })
  })

  it('shows Microsoft 365 section', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'Email' }))
    await waitFor(() => {
      expect(screen.getByText('Microsoft 365 OAuth2')).toBeInTheDocument()
    })
  })

  it('shows AI section title', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'AI' }))
    await waitFor(() => {
      expect(screen.getByText('AI Features')).toBeInTheDocument()
    })
  })

  it('shows Claude and Gemini provider status for ai_analyze', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'AI' }))
    await waitFor(() => {
      expect(screen.getByText('Claude API (Anthropic)')).toBeInTheDocument()
      expect(screen.getByText('Gemini API (Google, free tier)')).toBeInTheDocument()
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

  it('shows the Documentation links under the Docs tab', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Settings />)
    await user.click(await screen.findByRole('button', { name: 'Docs' }))
    await waitFor(() => {
      expect(screen.getByText('Documentation')).toBeInTheDocument()
      expect(screen.getByText('Getting Started')).toBeInTheDocument()
    })
  })

  it('does not show Email, AI, or System content on the default Account tab', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getAllByText('Change Password').length).toBeGreaterThan(0)
    })
    expect(screen.queryByText('Google OAuth2 (Gmail + Drive)')).not.toBeInTheDocument()
    expect(screen.queryByText('AI Features')).not.toBeInTheDocument()
    expect(screen.queryByText('Data Retention Policies')).not.toBeInTheDocument()
  })

  describe('Data Retention Policies card', () => {
    it('shows read-only badges for all three values to a non-admin', async () => {
      vi.mocked(useCurrentUser).mockReturnValue({ id: 'u1', username: 'viewer', role: 'viewer' })
      const user = userEvent.setup()
      renderWithProviders(<Settings />)
      await user.click(await screen.findByRole('button', { name: 'System' }))
      await waitFor(() => {
        expect(screen.getByText('Runs: 90 days')).toBeInTheDocument()
        expect(screen.getByText('Audit: 90 days')).toBeInTheDocument()
        expect(screen.getByText('Output files: 7 days')).toBeInTheDocument()
      })
      expect(screen.queryByLabelText('Output files (days)')).not.toBeInTheDocument()
    })

    it('shows an editable form with a Save button to an admin', async () => {
      vi.mocked(useCurrentUser).mockReturnValue({ id: 'u1', username: 'admin', role: 'admin' })
      const user = userEvent.setup()
      renderWithProviders(<Settings />)
      await user.click(await screen.findByRole('button', { name: 'System' }))
      await waitFor(() => {
        expect(screen.getByLabelText('Pipeline runs (days)')).toBeInTheDocument()
        expect(screen.getByLabelText('Audit log (days)')).toBeInTheDocument()
        expect(screen.getByLabelText('Output files (days)')).toBeInTheDocument()
      })
      expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    })

    it('blocks saving when Output files is set to 0', async () => {
      vi.mocked(useCurrentUser).mockReturnValue({ id: 'u1', username: 'admin', role: 'admin' })
      const user = userEvent.setup()
      renderWithProviders(<Settings />)
      await user.click(await screen.findByRole('button', { name: 'System' }))
      const outputInput = await screen.findByLabelText('Output files (days)')
      await user.clear(outputInput)
      await user.type(outputInput, '0')
      expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled()
      expect(updateRetentionSettings).not.toHaveBeenCalled()
    })

    it('saves updated values for an admin', async () => {
      vi.mocked(useCurrentUser).mockReturnValue({ id: 'u1', username: 'admin', role: 'admin' })
      const user = userEvent.setup()
      renderWithProviders(<Settings />)
      await user.click(await screen.findByRole('button', { name: 'System' }))
      const runInput = await screen.findByLabelText('Pipeline runs (days)')
      await user.clear(runInput)
      await user.type(runInput, '45')
      await user.click(screen.getByRole('button', { name: 'Save' }))
      await waitFor(() => {
        expect(updateRetentionSettings).toHaveBeenCalledWith(
          expect.objectContaining({ run_retention_days: 45 }),
          expect.anything(),
        )
      })
    })
  })
})
