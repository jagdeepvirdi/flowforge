import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import Login from '../pages/Login'

// vi.hoisted ensures mocks are defined before vi.mock's factory runs
const mockLogin   = vi.hoisted(() => vi.fn())
const mockGetMe   = vi.hoisted(() => vi.fn())
const mockSetToken = vi.hoisted(() => vi.fn())
const mockSetUser  = vi.hoisted(() => vi.fn())

vi.mock('../lib/api', () => ({
  login: mockLogin,
  getMe: mockGetMe,
  getSsoProviders: vi.fn(() => Promise.resolve({ google: false, microsoft: false })),
}))

vi.mock('../lib/auth', () => ({
  useAuth: () => ({ setToken: mockSetToken, setUser: mockSetUser, token: null, clearToken: vi.fn() }),
}))

describe('Login page', () => {
  beforeEach(() => {
    mockLogin.mockReset()
    mockSetToken.mockReset()
    mockSetUser.mockReset()
    mockGetMe.mockResolvedValue({ id: 'u1', username: 'admin', role: 'admin' })
  })

  it('renders username and password fields', () => {
    renderWithProviders(<Login />)
    expect(screen.getByTestId('username')).toBeInTheDocument()
    expect(screen.getByTestId('password')).toBeInTheDocument()
  })

  it('renders the Sign in button', () => {
    renderWithProviders(<Login />)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('calls login API with entered credentials', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValueOnce({ token: 'tok-abc' })
    renderWithProviders(<Login />)

    await user.type(screen.getByTestId('username'), 'admin')
    await user.type(screen.getByTestId('password'), 'secret')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin', 'secret')
    })
  })

  it('shows error message when login fails', async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))
    renderWithProviders(<Login />)

    await user.type(screen.getByTestId('username'), 'admin')
    await user.type(screen.getByTestId('password'), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('disables button while login is in progress', async () => {
    const user = userEvent.setup()
    // Never resolves — keeps the button in loading state
    mockLogin.mockReturnValueOnce(new Promise(() => {}))
    renderWithProviders(<Login />)

    await user.type(screen.getByTestId('username'), 'admin')
    await user.type(screen.getByTestId('password'), 'secret')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
    })
  })
})
