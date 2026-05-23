/**
 * global.setup.ts — runs once before all E2E tests.
 *
 * Logs in via the UI and saves the resulting browser storage state
 * (localStorage auth token) to e2e/.auth.json.  Every subsequent
 * test file that sets storageState: 'e2e/.auth.json' starts already
 * authenticated without repeating the login flow.
 */
import { test as setup, expect } from '@playwright/test'

const AUTH_FILE = 'e2e/.auth.json'

setup('authenticate', async ({ page }) => {
  const username = process.env.E2E_USERNAME ?? 'admin'
  const password = process.env.E2E_PASSWORD ?? 'testpass'

  await page.goto('/login')

  await page.locator('[data-testid="username"]').fill(username)
  await page.locator('[data-testid="password"]').fill(password)
  await page.locator('button[type="submit"]').click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })

  await page.context().storageState({ path: AUTH_FILE })
})
