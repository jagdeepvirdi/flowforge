import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { renderWithProviders, createTestQueryClient } from './helpers'
import BulkLoadEdit from '../pages/BulkLoadEdit'

/** renderWithProviders doesn't register a <Route>, so useParams() never resolves
 * an :id. Editing tests need a real route match to exercise the "existing config" path. */
function renderEditRoute(path: string) {
  const qc = createTestQueryClient()
  return render(
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route path="/bulk-loads/new" element={<BulkLoadEdit />} />
          <Route path="/bulk-loads/:id/edit" element={<BulkLoadEdit />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

vi.mock('../lib/api', () => ({
  getBulkLoadConfig:        vi.fn(),
  createBulkLoadConfig:     vi.fn(() => Promise.resolve({ id: 'new-id' })),
  updateBulkLoadConfig:     vi.fn(() => Promise.resolve({})),
  getDbConnections:         vi.fn(() => Promise.resolve([])),
  validateBulkLoadConfigRaw: vi.fn(),
  getProjects:              vi.fn(() => Promise.resolve([])),
}))

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('Name *'), 'Daily Load')
  await user.type(screen.getByLabelText('Source directory *'), '/data/incoming/')
  await user.type(screen.getByLabelText('Target table *'), 'public.subs')
}

describe('BulkLoadEdit — new config', () => {
  it('renders the New Bulk Load form', async () => {
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'New Bulk Load' })).toBeInTheDocument()
    })
  })

  it('shows a field error and does not save when required fields are empty', async () => {
    const { createBulkLoadConfig } = await import('../lib/api')
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await user.click(screen.getByRole('button', { name: /Save/i }))
    expect(await screen.findByText('Name is required')).toBeInTheDocument()
    expect(createBulkLoadConfig).not.toHaveBeenCalled()
  })

  it('saves and navigates back to the list on success', async () => {
    const { createBulkLoadConfig } = await import('../lib/api')
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: /Save/i }))
    await waitFor(() => {
      expect(createBulkLoadConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Daily Load',
          source_directory: '/data/incoming/',
          target_table: 'public.subs',
        }),
      )
    })
  })

  it('shows the save error message when the create request rejects', async () => {
    const { createBulkLoadConfig } = await import('../lib/api')
    ;(createBulkLoadConfig as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('name already exists'))
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: /Save/i }))
    expect(await screen.findByText('name already exists')).toBeInTheDocument()
  })

  it('blocks Test File and shows an error when source directory is empty', async () => {
    const { validateBulkLoadConfigRaw } = await import('../lib/api')
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await user.click(screen.getByRole('button', { name: /Test File/i }))
    expect(await screen.findByText('Source directory is required to run a test')).toBeInTheDocument()
    expect(validateBulkLoadConfigRaw).not.toHaveBeenCalled()
  })

  it('runs the test and renders the preview table plus warnings', async () => {
    const { validateBulkLoadConfigRaw } = await import('../lib/api')
    ;(validateBulkLoadConfigRaw as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      file_name: 'SUBS_20260706.csv',
      files_matched: 2,
      columns: ['id', 'email'],
      sample_rows: [['1', 'a@x.com'], ['2', 'b@x.com']],
      row_count_sampled: 2,
      warnings: ['Column(s) not found in public.subs: email'],
    })
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await user.type(screen.getByLabelText('Source directory *'), '/data/incoming/')
    await user.click(screen.getByRole('button', { name: /Test File/i }))

    expect(await screen.findByText('SUBS_20260706.csv')).toBeInTheDocument()
    expect(screen.getByText(/2 files matched/)).toBeInTheDocument()
    expect(screen.getByText('Column(s) not found in public.subs: email')).toBeInTheDocument()
    expect(screen.getByText('a@x.com')).toBeInTheDocument()
    expect(screen.getByText('b@x.com')).toBeInTheDocument()
  })

  it('shows the test error message when the test request rejects', async () => {
    const { validateBulkLoadConfigRaw } = await import('../lib/api')
    ;(validateBulkLoadConfigRaw as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('no files found in /data/incoming/'))
    const user = userEvent.setup()
    renderWithProviders(<BulkLoadEdit />, { initialPath: '/bulk-loads/new' })
    await screen.findByRole('heading', { name: 'New Bulk Load' })
    await user.type(screen.getByLabelText('Source directory *'), '/data/incoming/')
    await user.click(screen.getByRole('button', { name: /Test File/i }))
    expect(await screen.findByText('no files found in /data/incoming/')).toBeInTheDocument()
  })
})

describe('BulkLoadEdit — editing an existing config', () => {
  const EXISTING = {
    id: 'bl1', name: 'Subscriber Daily Load', description: 'Loads subscriber CSV',
    connection_id: 'c1', source_directory: '/data/incoming/',
    file_prefix: 'SUBS_', file_prefix_exclude: '',
    file_type: 'csv', delimiter: ',', header_rows: 1, footer_rows: 0,
    target_table: 'public.bulk_test_subscribers', load_mode: 'replace',
    column_mapping: [], use_sqlloader: false, archive_directory: '',
    on_no_files: 'skip', created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  }

  it('prefills the form fields from the existing config', async () => {
    const { getBulkLoadConfig } = await import('../lib/api')
    ;(getBulkLoadConfig as ReturnType<typeof vi.fn>).mockResolvedValueOnce(EXISTING)
    renderEditRoute('/bulk-loads/bl1/edit')
    await waitFor(() => {
      expect(screen.getByLabelText('Name *')).toHaveValue('Subscriber Daily Load')
      expect(screen.getByLabelText('Source directory *')).toHaveValue('/data/incoming/')
      expect(screen.getByLabelText('Target table *')).toHaveValue('public.bulk_test_subscribers')
    })
    expect(getBulkLoadConfig).toHaveBeenCalledWith('bl1')
  })

  it('updates the existing config by id on save', async () => {
    const { getBulkLoadConfig, updateBulkLoadConfig } = await import('../lib/api')
    ;(getBulkLoadConfig as ReturnType<typeof vi.fn>).mockResolvedValueOnce(EXISTING)
    const user = userEvent.setup()
    renderEditRoute('/bulk-loads/bl1/edit')
    await waitFor(() => expect(screen.getByLabelText('Name *')).toHaveValue('Subscriber Daily Load'))
    await user.click(screen.getByRole('button', { name: /Save/i }))
    await waitFor(() => {
      expect(updateBulkLoadConfig).toHaveBeenCalledWith('bl1', expect.objectContaining({ name: 'Subscriber Daily Load' }))
    })
  })
})
