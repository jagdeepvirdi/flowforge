/**
 * pipeline-canvas.spec.ts — the canvas view of the pipeline editor (Phase 14.1).
 *
 * Covers what's safe to automate reliably: view toggling, adding a step
 * from the shared toolbar while in canvas view, editing a step via the
 * side panel and confirming it persists after Save + reload, and
 * duplicate/delete from a node's hover actions. Actual pointer-drag-to-
 * reorder / drag-to-group is NOT exercised here — react-flow's drag math
 * depends on real layout/viewport transforms that are flaky under
 * automation; that logic is covered by unit tests for
 * `resolveDropTarget`/`assignParallelGroup` instead, and verified manually.
 */
import { test, expect, type Page } from '@playwright/test'

let PIPELINE_NAME: string
let DAG_PIPELINE_NAME: string

/** Reads the JWT out of localStorage (zustand persist key `flowforge-auth`) for direct API calls. */
async function getAuthToken(page: Page): Promise<string> {
  return page.evaluate(() => JSON.parse(localStorage.getItem('flowforge-auth') ?? '{}')?.state?.token)
}

async function createPipeline(page: Page, name: string): Promise<void> {
  await page.goto('/pipelines')
  await page.getByRole('link', { name: /New Pipeline/i }).click()
  await expect(page).toHaveURL(/\/pipelines\/new/)

  await page.locator('[data-testid="pipeline-name"]').fill(name)
  await page.getByRole('button', { name: /Save/i }).click()
  await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })
}

async function openPipelineEditor(page: Page, name: string): Promise<void> {
  await page.goto('/pipelines')
  const row = page.locator('tr').filter({ hasText: name })
  await expect(row).toBeVisible()
  await row.locator('a[title="Edit"], button[title="Edit"], a').first().click()
  await expect(page).toHaveURL(/\/pipelines\/.+\/edit/)
}

async function deletePipeline(page: Page, name: string): Promise<void> {
  await page.goto('/pipelines')
  const row = page.locator('tr').filter({ hasText: name })
  await Promise.all([
    page.waitForEvent('dialog').then(d => d.accept()),
    row.locator('button[title="Delete"]').click(),
  ])
  await expect(row).not.toBeVisible({ timeout: 10_000 })
}

test.describe('Pipeline canvas view', () => {
  test.beforeAll(async () => {
    PIPELINE_NAME = `E2E Canvas ${Date.now()}`
  })

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: 'e2e/.auth.json' })
    const page = await ctx.newPage()
    try { await deletePipeline(page, PIPELINE_NAME) } catch { /* already deleted */ }
    await ctx.close()
  })

  test('toggling to canvas view shows the empty state, and back to list works', async ({ page }) => {
    await createPipeline(page, PIPELINE_NAME)
    await openPipelineEditor(page, PIPELINE_NAME)

    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.getByText('Add steps using the buttons above.')).toBeVisible()

    await page.locator('[data-testid="view-toggle-list"]').click()
    await expect(page.getByText('Add steps using the buttons above.')).toBeVisible()
  })

  test('adding a step from the toolbar while in canvas view renders a node, and persists after save', async ({ page }) => {
    await openPipelineEditor(page, PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()

    await page.getByRole('button', { name: /db query/i }).click()
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(1)

    // Save always redirects back to the pipeline list (PipelineEdit.tsx's
    // handleSave), not back to the edit page.
    await page.getByRole('button', { name: /Save/i }).click()
    await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })

    await openPipelineEditor(page, PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(1)
  })

  test('editing a step name via the side panel persists after save + reload', async ({ page }) => {
    await openPipelineEditor(page, PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(1)

    const node = page.locator('[data-testid^="canvas-node-"]').first()
    await node.click()

    const dialog = page.getByLabel('Edit step')
    await expect(dialog).toBeVisible()
    await dialog.getByLabel('Name').fill('Extract customers')
    await dialog.getByTitle('Close').click()

    await page.getByRole('button', { name: /Save/i }).click()
    await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })

    await openPipelineEditor(page, PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.locator('[data-testid^="canvas-node-"]').filter({ hasText: 'Extract customers' })).toBeVisible()
  })

  test('duplicate and delete from a node change the node count', async ({ page }) => {
    await openPipelineEditor(page, PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()

    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(1)

    const node = page.locator('[data-testid^="canvas-node-"]').first()
    await node.getByTitle('Duplicate step').click({ force: true })
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(2)

    const firstNode = page.locator('[data-testid^="canvas-node-"]').first()
    await firstNode.getByTitle('Delete step').click({ force: true })
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(1)
  })
})

/**
 * Real step-dependency edges (Phase 14 Option B, Milestone 3). Drawing a connection is a
 * handle-to-handle pointer drag inside an SVG canvas — the same class of gesture already
 * documented above as too flaky to automate reliably in headless CI (worse, even, than the
 * node-repositioning drag: it requires landing precisely on a 6px handle). That interaction is
 * covered instead by PipelineCanvas.test.tsx's mocked-ReactFlow component tests, which exercise
 * the actual onConnect/onEdgesDelete handlers directly. What *is* reliably automatable here —
 * and still real, end-to-end coverage — is that once a step-dependency exists (created via a
 * direct API call, mirroring what a successful connect gesture would have done), the canvas
 * fetches and renders it correctly, exclusively (not alongside the synthetic wave edge), and
 * that it survives a reload.
 */
test.describe('Pipeline canvas — real step-dependency edges', () => {
  test.beforeAll(async () => {
    DAG_PIPELINE_NAME = `E2E Canvas DAG ${Date.now()}`
  })

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: 'e2e/.auth.json' })
    const page = await ctx.newPage()
    try { await deletePipeline(page, DAG_PIPELINE_NAME) } catch { /* already deleted */ }
    await ctx.close()
  })

  test('a step dependency created via the API renders as a real edge and survives reload', async ({ page, request }) => {
    await createPipeline(page, DAG_PIPELINE_NAME)
    await openPipelineEditor(page, DAG_PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()

    await page.getByRole('button', { name: /db query/i }).click()
    await page.getByRole('button', { name: /db query/i }).click()
    await expect(page.locator('[data-testid^="canvas-node-"]')).toHaveCount(2)

    await page.getByRole('button', { name: /Save/i }).click()
    await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })

    const token = await getAuthToken(page)
    const pipelines = await request.get('/api/pipelines', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
    const pipeline = pipelines.find((p: { name: string }) => p.name === DAG_PIPELINE_NAME)
    const steps = await request.get(`/api/pipelines/${pipeline.id}/steps`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
    expect(steps).toHaveLength(2)

    const depRes = await request.post(`/api/pipelines/${pipeline.id}/step-dependencies`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { upstream_step_id: steps[0].id, downstream_step_id: steps[1].id },
    })
    expect(depRes.ok()).toBe(true)

    await openPipelineEditor(page, DAG_PIPELINE_NAME)
    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.locator('.react-flow__edge')).toHaveCount(1)

    // Reload — the edge must still be fetched and rendered, not just a leftover from this session.
    await page.reload()
    await page.locator('[data-testid="view-toggle-canvas"]').click()
    await expect(page.locator('.react-flow__edge')).toHaveCount(1)
  })
})
