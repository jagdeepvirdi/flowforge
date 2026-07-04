import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from './helpers'
import BulkLoads from '../pages/BulkLoads'

const MOCK_CONFIGS = [
  {
    id: 'bl1', name: 'Subscriber Daily Load', description: 'Loads subscriber CSV',
    connection_id: 'c1', source_directory: '/data/incoming/',
    file_prefix: 'SUBS_', file_prefix_exclude: '',
    file_type: 'csv', delimiter: ',', header_rows: 1, footer_rows: 0,
    target_table: 'public.bulk_test_subscribers', load_mode: 'replace',
    column_mapping: [], use_sqlloader: false, archive_directory: '',
    on_no_files: 'skip', created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
]

vi.mock('../lib/api', () => ({
  getBulkLoadConfigs:      vi.fn(() => Promise.resolve(MOCK_CONFIGS)),
  deleteBulkLoadConfig:    vi.fn(() => Promise.resolve({})),
  validateBulkLoadConfig:  vi.fn(() => Promise.resolve({ file_name: '', files_matched: 0, columns: [], sample_rows: [], row_count_sampled: 0, warnings: [] })),
  getProjects:             vi.fn(() => Promise.resolve([])),
}))

describe('BulkLoads', () => {
  it('renders without crashing', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText('Bulk Loads')).toBeInTheDocument()
    })
  })

  it('shows config names', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText('Subscriber Daily Load')).toBeInTheDocument()
    })
  })

  it('shows source directory', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText('/data/incoming/')).toBeInTheDocument()
    })
  })

  it('shows target table', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText('public.bulk_test_subscribers')).toBeInTheDocument()
    })
  })

  it('shows New Bulk Load button', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText('New Bulk Load')).toBeInTheDocument()
    })
  })

  it('shows count in subtitle', async () => {
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText(/1 bulk load config/i)).toBeInTheDocument()
    })
  })

  it('shows empty state when no configs', async () => {
    const { getBulkLoadConfigs } = await import('../lib/api')
    ;(getBulkLoadConfigs as ReturnType<typeof vi.fn>).mockResolvedValueOnce([])
    renderWithProviders(<BulkLoads />)
    await waitFor(() => {
      expect(screen.getByText(/no bulk load/i)).toBeInTheDocument()
    })
  })
})
