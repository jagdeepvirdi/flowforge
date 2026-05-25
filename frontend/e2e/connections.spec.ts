/**
 * connections.spec.ts — Connections page E2E golden-path tests.
 *
 * Exercises DB Connections and Email Providers tabs.
 * Does not create real connections (avoids side-effects on live DBs).
 */
import { test, expect } from '@playwright/test'

test.describe('Connections page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/connections')
    await expect(page).toHaveURL(/\/connections/)
  })

  test('renders the Connections heading', async ({ page }) => {
    await expect(page.getByText('Connections')).toBeVisible()
  })

  test('shows DB Connections and Email Providers tabs', async ({ page }) => {
    await expect(page.getByText('DB Connections')).toBeVisible()
    await expect(page.getByText('Email Providers')).toBeVisible()
  })

  test('Add Connection button is visible on DB tab', async ({ page }) => {
    await expect(page.getByText('Add Connection')).toBeVisible()
  })

  test('switching to Email Providers tab shows its content', async ({ page }) => {
    await page.getByText('Email Providers').click()

    // After switching, the Add Connection button updates contextually
    await expect(
      page.getByText('Add Connection').or(page.getByText('Add email provider'))
    ).toBeVisible()
  })

  test('opening Add Connection modal shows the connection form', async ({ page }) => {
    await page.getByText('Add Connection').click()

    // The modal / inline form should reveal a DB type selector or name field
    await expect(
      page.locator('select[name="db_type"], select, input[name="name"]').first()
    ).toBeVisible({ timeout: 5_000 })
  })
})
