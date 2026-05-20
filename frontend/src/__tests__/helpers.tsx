import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity },
      mutations: { retry: false },
    },
  })
}

interface WrapperProps {
  queryClient?: QueryClient
  initialPath?: string
}

export function renderWithProviders(
  ui: React.ReactElement,
  { queryClient, initialPath = '/', ...renderOptions }: WrapperProps & RenderOptions = {},
) {
  const qc = queryClient ?? createTestQueryClient()
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialPath]}>
        <QueryClientProvider client={qc}>
          {children}
        </QueryClientProvider>
      </MemoryRouter>
    )
  }
  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }), queryClient: qc }
}
