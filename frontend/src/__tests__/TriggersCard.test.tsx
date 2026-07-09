import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './helpers'
import TriggersCard from '../components/pipeline/TriggersCard'
import type { Pipeline, PipelineDep } from '../lib/types'

vi.mock('../lib/api', () => ({
  getCronNext:        vi.fn(() => Promise.resolve({ next_runs: [] })),
  getWebhookTokens:    vi.fn(() => Promise.resolve([])),
  createWebhookToken:  vi.fn(),
  revokeWebhookToken:  vi.fn(),
}))

function makePipeline(overrides: Partial<Pipeline> = {}): Pipeline {
  return {
    id: 'p0', name: 'Pipeline', description: '', schedule: null, next_run: null,
    enabled: true, timeout_minutes: 60, on_failure_webhook_url: null, project_id: null,
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    steps: [], variables: [], upstream_deps: [], downstream_deps: [],
    ...overrides,
  }
}

const OTHER_PIPELINE = makePipeline({ id: 'p2', name: 'Upstream Extract' })

// CronBuilder only renders once `existing` has loaded for an edit page (id set) —
// mirrors PipelineEdit.tsx's `(!id || existing)` gate against a stale pre-load flash.
const EXISTING_PIPELINE = makePipeline({ id: 'p1', name: 'This Pipeline' })

function setup(overrides: Partial<React.ComponentProps<typeof TriggersCard>> = {}) {
  const onScheduleChange = vi.fn()
  const setUpstreamDeps = vi.fn()
  renderWithProviders(
    <TriggersCard
      id="p1"
      existing={EXISTING_PIPELINE}
      schedule=""
      onScheduleChange={onScheduleChange}
      upstreamDeps={[]}
      setUpstreamDeps={setUpstreamDeps}
      allPipelines={[OTHER_PIPELINE]}
      {...overrides}
    />,
  )
  return { onScheduleChange, setUpstreamDeps }
}

describe('TriggersCard', () => {
  it('shows the Schedule tab (cron builder) by default', () => {
    setup()
    expect(screen.getByText('No schedule')).toBeInTheDocument()
  })

  it('switches to the Dependencies tab and lists other pipelines to add', async () => {
    const user = userEvent.setup()
    setup()
    await user.click(screen.getByTestId('triggers-tab-dependencies'))
    expect(screen.getByText('No dependencies. This pipeline runs on its own schedule or when triggered manually.')).toBeInTheDocument()
    expect(screen.getByText('Upstream Extract')).toBeInTheDocument()
  })

  it('shows a dependency count badge on the tab once deps are added', () => {
    const deps: PipelineDep[] = [{ dep_id: 'd1', pipeline_id: 'p2', pipeline_name: 'Upstream Extract' }]
    setup({ upstreamDeps: deps })
    expect(screen.getByTestId('triggers-tab-dependencies')).toHaveTextContent('(1)')
  })

  it('switches to the Webhook tab and loads tokens for an existing pipeline', async () => {
    const user = userEvent.setup()
    setup({ id: 'p1' })
    await user.click(screen.getByTestId('triggers-tab-webhook'))
    await waitFor(() => {
      expect(screen.getByText('No tokens yet. Generate one below to enable API triggers.')).toBeInTheDocument()
    })
  })

  it('prompts to save first when the pipeline has no id yet', async () => {
    const user = userEvent.setup()
    setup({ id: undefined })
    await user.click(screen.getByTestId('triggers-tab-webhook'))
    expect(screen.getByText('Save this pipeline first to generate a webhook token.')).toBeInTheDocument()
  })
})
