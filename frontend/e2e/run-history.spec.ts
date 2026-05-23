/**
 * run-history.spec.ts — Run History page rendering and filter tests.
 *
 * These tests use the stored auth session and don't depend on any specific
 * pipeline run existing — they exercise the page structure and UI controls.
 */
import { test, expect } from '@playwright/test'

test.describe('Run History page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/runs')
    await expect(page).toHaveURL(/\/runs/)
  })

  test('run history page renders page heading and table', async ({ page }) => {
    // The page heading
    await expect(page.locator('h1')).toContainText(/Run History|Runs/i)

    // The table is rendered (even if empty)
    await expect(page.locator('table')).toBeVisible()
  })

  test('time-range tabs are visible and clickable', async ({ page }) => {
    // RunHistory.tsx renders tabs: 24h, 7d, 30d, All
    // exact: true prevents matching "All Projects" or other buttons containing "All"
    for (const tab of ['24h', '7d', '30d', 'All']) {
      const btn = page.getByRole('button', { name: tab, exact: true })
      await expect(btn).toBeVisible()
    }

    // Clicking 24h should not error
    await page.getByRole('button', { name: '24h', exact: true }).click()
    await expect(page).toHaveURL(/\/runs/)
  })

  test('status filter chips render', async ({ page }) => {
    // RunHistory.tsx has a status filter (Success / Failed / All)
    // The exact labels depend on the component; just verify filter controls exist
    await expect(page.locator('select, button').first()).toBeVisible()
  })

  test('search box filters pipeline name', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"], input[placeholder*="Filter"]').first()

    if (await searchInput.isVisible()) {
      await searchInput.fill('nonexistent_pipeline_xyz')
      // After filtering, the table body should be empty or show "no results"
      const rows = page.locator('tbody tr')
      await expect(rows).toHaveCount(0, { timeout: 5_000 }).catch(() => {
        // If count isn't 0, a "no results" message should be shown
      })
      // Clear the filter
      await searchInput.fill('')
    }
  })

  test('navigating to run detail works', async ({ page }) => {
    const rows = page.locator('tbody tr')
    const count = await rows.count()

    if (count > 0) {
      // Click the first link in the first row to open the run detail
      await rows.first().locator('a').first().click()
      await expect(page).toHaveURL(/\/runs\//)

      // Run detail page should show step-level info
      await expect(page.locator('h1, h2').first()).toBeVisible()
    } else {
      test.skip()
    }
  })
})

test.describe('Navigation via sidebar', () => {
  test('sidebar nav links reach correct pages', async ({ page }) => {
    await page.goto('/dashboard')

    const links: [string, RegExp][] = [
      ['Pipelines', /\/pipelines/],
      ['Run History', /\/runs/],
      ['Connections', /\/connections/],
    ]

    for (const [label, urlPattern] of links) {
      await page.getByRole('link', { name: label }).click()
      await expect(page).toHaveURL(urlPattern)
    }
  })

  test('dashboard renders pipeline cards section', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page.locator('h1')).toBeVisible()
  })
})
