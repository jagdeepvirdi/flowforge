import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import Pipelines from '../pages/Pipelines'

const MOCK_PIPELINES = [
  {
    id: 'p1', name: 'Daily Billing Report', description: 'Finance export',
    schedule: '0 7 * * *', enabled: true, timeout_minutes: 30,
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    steps: [], variables: [],
  },
  {
    id: 'p2', name: 'Weekly Summary', description: '',
    schedule: null, enabled: false, timeout_minutes: 60,
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    steps: [], variables: [],
  },
]

vi.mock('../lib/api', () => ({
  getPipelines:  vi.fn(() => Promise.resolve(MOCK_PIPELINES)),
  deletePipeline: vi.fn(() => Promise.resolve({})),
  runPipeline:    vi.fn(() => Promise.resolve({ run_id: 'r1', status: 'running' })),
}))

describe('Pipelines list', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<Pipelines />)
    await waitFor(() => {
      expect(screen.getByText('Pipelines')).toBeInTheDocument()
    })
  })

  it('lists pipeline names from API', async () => {
    renderWithProviders(<Pipelines />)
    await waitFor(() => {
      expect(screen.getByText('Daily Billing Report')).toBeInTheDocument()
      expect(screen.getByText('Weekly Summary')).toBeInTheDocument()
    })
  })

  it('shows a New Pipeline button', async () => {
    renderWithProviders(<Pipelines />)
    await waitFor(() => {
      expect(screen.getByText('New Pipeline')).toBeInTheDocument()
    })
  })
})
