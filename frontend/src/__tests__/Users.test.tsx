import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders, createTestQueryClient } from './helpers'
import Users from '../pages/Users'

const MOCK_USERS = [
  { id: 'u1', username: 'admin',    role: 'admin',  created_at: new Date().toISOString() },
  { id: 'u2', username: 'editor1',  role: 'editor', created_at: new Date().toISOString() },
  { id: 'u3', username: 'viewer1',  role: 'viewer', created_at: new Date().toISOString() },
]

vi.mock('../lib/api', () => ({
  getUsers:    vi.fn(() => Promise.resolve(MOCK_USERS)),
  createUser:  vi.fn(() => Promise.resolve({ id: 'u-new', username: 'newuser', role: 'editor', created_at: new Date().toISOString() })),
  updateUser:  vi.fn(() => Promise.resolve(MOCK_USERS[1])),
  deleteUser:  vi.fn(() => Promise.resolve({})),
  getProjects: vi.fn(() => Promise.resolve([])),
}))

vi.mock('../lib/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/auth')>()
  return {
    ...actual,
    useCurrentUser: vi.fn(() => ({ id: 'u1', username: 'admin', role: 'admin' })),
  }
})

describe('Users', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Users' })).toBeInTheDocument()
    })
  })

  it('lists all users', async () => {
    renderWithProviders(<Users />)
    await waitFor(() => {
      // admin appears multiple times (breadcrumb + table) — use getAllByText
      expect(screen.getAllByText('admin').length).toBeGreaterThan(0)
      expect(screen.getByText('editor1')).toBeInTheDocument()
      expect(screen.getByText('viewer1')).toBeInTheDocument()
    })
  })

  it('shows Add User button', async () => {
    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getByText('Add User')).toBeInTheDocument()
    })
  })

  it('shows role badges', async () => {
    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getAllByText(/admin|editor|viewer/i).length).toBeGreaterThan(0)
    })
  })

  it('marks current user with (you)', async () => {
    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getByText('(you)')).toBeInTheDocument()
    })
  })
})
