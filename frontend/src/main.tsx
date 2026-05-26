import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import RouteErrorBoundary from './components/shared/RouteErrorBoundary'
import './index.css'
import { useProjectStore } from './lib/store'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function ThemeWrapper() {
  const { theme } = useProjectStore()

  document.body.className = theme === 'light' ? 'light' : ''

  return <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouteErrorBoundary label="The application">
      <QueryClientProvider client={queryClient}>
        <ThemeWrapper />
      </QueryClientProvider>
    </RouteErrorBoundary>
  </StrictMode>,
)