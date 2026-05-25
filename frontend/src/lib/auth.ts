import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { CurrentUser } from './types'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  setToken: (token: string) => void
  setUser: (user: CurrentUser) => void
  clearToken: () => void
  isAuthenticated: () => boolean
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      clearToken: () => set({ token: null, user: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: 'flowforge-auth' },
  ),
)

export function useCurrentUser(): CurrentUser | null {
  return useAuth((state) => state.user)
}
