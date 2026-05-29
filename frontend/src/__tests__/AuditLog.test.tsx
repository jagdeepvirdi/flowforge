import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import AuditLog from '../pages/AuditLog'

const MOCK_AUDIT_DATA = {
  logs: [
    {
      id: 'log-1', timestamp: new Date().toISOString(),
      action: 'LOGIN_SUCCESS', username: 'admin',
      user_id: 'u1', ip_address: '127.0.0.1', details: {},
    },
    {
      id: 'log-2', timestamp: new Date().toISOString(),
      action: 'PIPELINE_RUN', username: 'admin',
      user_id: 'u1', ip_address: '192.168.1.1', details: { pipeline_name: 'Monthly Revenue' },
    },
  ],
  total: 2,
  page: 1,
  pages: 1,
}

vi.mock('../lib/api', () => ({
  getAuditLogs:   vi.fn(() => Promise.resolve(MOCK_AUDIT_DATA)),
  exportAuditLogs: vi.fn(() => Promise.resolve(new Blob(['csv data']))),
  getProjects:    vi.fn(() => Promise.resolve([])),
}))

describe('AuditLog', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Audit Log' })).toBeInTheDocument()
    })
  })

  it('shows log entries', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getByText('LOGIN_SUCCESS')).toBeInTheDocument()
      expect(screen.getByText('PIPELINE_RUN')).toBeInTheDocument()
    })
  })

  it('shows username column', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getAllByText('admin').length).toBeGreaterThan(0)
    })
  })

  it('shows action filter input', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/filter by action/i)).toBeInTheDocument()
    })
  })

  it('shows user filter input', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/filter by user/i)).toBeInTheDocument()
    })
  })

  it('shows export button', async () => {
    renderWithProviders(<AuditLog />)
    await waitFor(() => {
      expect(screen.getByText(/export/i)).toBeInTheDocument()
    })
  })
})
