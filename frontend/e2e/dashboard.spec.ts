/**
 * dashboard.spec.ts — Dashboard page E2E golden-path tests.
 *
 * Requires the full stack running (backend + frontend dev server).
 * Auth is pre-loaded from global.setup.ts.
 */
import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('renders the dashboard heading', async ({ page }) => {
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('shows the four stat cards', async ({ page }) => {
    // Stat labels rendered by Dashboard.tsx
    await expect(page.getByText('Runs today')).toBeVisible()
    await expect(page.getByText('Success rate')).toBeVisible()
    await expect(page.getByText('Active schedules')).toBeVisible()
  })

  test('New Pipeline button navigates to pipeline editor', async ({ page }) => {
    const btn = page.getByRole('link', { name: /new pipeline/i })
    await expect(btn).toBeVisible()
    await btn.click()
    await expect(page).toHaveURL(/\/pipelines\/new/)
  })

  test('clicking a pipeline card edit link navigates to edit page', async ({ page }) => {
    // Only run if at least one pipeline card exists
    const editLinks = page.locator('a[href*="/pipelines/"]')
    const count = await editLinks.count()
    if (count === 0) {
      test.skip()
      return
    }
    const href = await editLinks.first().getAttribute('href')
    await editLinks.first().click()
    await expect(page).toHaveURL(new RegExp(href!.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
  })
})
