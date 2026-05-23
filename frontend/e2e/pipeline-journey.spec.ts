/**
 * pipeline-journey.spec.ts — the golden-path E2E journey:
 *
 *   login (via stored auth) → create pipeline → verify in list
 *   → run pipeline → verify run appears in history → delete pipeline
 *
 * The pipeline created here has no steps, so it completes immediately
 * with status "success" — no real DB or email configuration needed.
 */
import { test, expect, type Page } from '@playwright/test'

// Names are initialised in beforeAll so Date.now() is called at execution time,
// not at collection time (Playwright evaluates module code twice).
let PIPELINE_NAME: string

// ── Helpers ────────────────────────────────────────────────────────────────────

async function createPipeline(page: Page, name: string): Promise<void> {
  await page.goto('/pipelines')
  await page.getByRole('link', { name: /New Pipeline/i }).click()
  await expect(page).toHaveURL(/\/pipelines\/new/)

  await page.locator('[data-testid="pipeline-name"]').fill(name)
  await page.getByRole('button', { name: /Save/i }).click()

  // After save, the page redirects back to /pipelines
  await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })
}

async function deletePipeline(page: Page, name: string): Promise<void> {
  await page.goto('/pipelines')
  const row = page.locator('tr').filter({ hasText: name })

  // Accept the window.confirm() dialog triggered by the delete button
  page.once('dialog', dialog => dialog.accept())
  await row.locator('button[title="Delete"]').click()

  await expect(row).not.toBeVisible({ timeout: 10_000 })
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe('Pipeline golden-path journey', () => {
  test.beforeAll(async () => {
    PIPELINE_NAME = `E2E Journey ${Date.now()}`
  })

  // Ensure the test pipeline is removed even if a step below fails
  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext({
      storageState: 'e2e/.auth.json',
    })
    const page = await ctx.newPage()
    try {
      await deletePipeline(page, PIPELINE_NAME)
    } catch {
      // Pipeline may already have been deleted by the test itself — ignore
    }
    await ctx.close()
  })

  test('create pipeline and verify it appears in the pipeline list', async ({ page }) => {
    await createPipeline(page, PIPELINE_NAME)

    // The pipeline name must be visible in the table
    await expect(page.locator('tr').filter({ hasText: PIPELINE_NAME })).toBeVisible()
  })

  test('run pipeline from the pipeline list', async ({ page }) => {
    await page.goto('/pipelines')

    const row = page.locator('tr').filter({ hasText: PIPELINE_NAME })
    await expect(row).toBeVisible()

    // Click the Run Now button (title="Run now") for this specific pipeline
    await row.locator('button[title="Run now"]').click()

    // The button triggers an API call; wait for it to settle
    // (the run is queued/started — we don't wait for completion here)
    await page.waitForTimeout(1_500)
  })

  test('pipeline run appears in run history', async ({ page }) => {
    // Empty pipelines complete in milliseconds; give the backend a moment
    await page.waitForTimeout(2_000)

    await page.goto('/runs')
    await expect(page).toHaveURL(/\/runs/)

    // At least one row for our pipeline name should be visible
    await expect(
      page.locator('tr').filter({ hasText: PIPELINE_NAME }).first()
    ).toBeVisible({ timeout: 15_000 })
  })

  test('run history shows the correct status badge for the pipeline run', async ({ page }) => {
    await page.goto('/runs')

    const runRow = page.locator('tr').filter({ hasText: PIPELINE_NAME }).first()
    await expect(runRow).toBeVisible({ timeout: 15_000 })

    // An empty pipeline completes immediately — status should be success or running
    const badge = runRow.locator('td').nth(0)   // Status column (first td in row)
    await expect(badge).toContainText(/success|running/i)
  })

  test('run detail page is reachable from history', async ({ page }) => {
    await page.goto('/runs')

    const runRow = page.locator('tr').filter({ hasText: PIPELINE_NAME }).first()
    await expect(runRow).toBeVisible({ timeout: 15_000 })

    // The last td contains the ChevronRight anchor link to /runs/:id
    await runRow.locator('td').last().locator('a').click()
    await expect(page).toHaveURL(/\/runs\//)
  })

  test('delete pipeline cleans up', async ({ page }) => {
    await deletePipeline(page, PIPELINE_NAME)

    // After deletion the row should be gone
    await expect(
      page.locator('tr').filter({ hasText: PIPELINE_NAME })
    ).not.toBeVisible()
  })
})

// ── Additional pipeline CRUD tests ────────────────────────────────────────────

test.describe('Pipeline CRUD (independent)', () => {
  let CRUD_NAME: string

  test.beforeAll(async () => {
    CRUD_NAME = `E2E CRUD ${Date.now()}`
  })

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: 'e2e/.auth.json' })
    const page = await ctx.newPage()
    try { await deletePipeline(page, CRUD_NAME) } catch { /* already deleted */ }
    await ctx.close()
  })

  test('create → edit name → verify updated', async ({ page }) => {
    await createPipeline(page, CRUD_NAME)

    // Click into the pipeline to edit it
    await page.locator('tr').filter({ hasText: CRUD_NAME }).locator('a[title="Edit"], button[title="Edit"], a').first().click()
    await expect(page).toHaveURL(/\/pipelines\/.+\/edit/)

    const updated = `${CRUD_NAME} (updated)`
    await page.locator('[data-testid="pipeline-name"]').fill(updated)
    await page.getByRole('button', { name: /Save/i }).click()
    await expect(page).toHaveURL(/\/pipelines$/, { timeout: 15_000 })

    await expect(page.locator('tr').filter({ hasText: updated })).toBeVisible()

    // Clean up the updated name
    page.once('dialog', dialog => dialog.accept())
    await page.locator('tr').filter({ hasText: updated }).locator('button[title="Delete"]').click()
  })
})
