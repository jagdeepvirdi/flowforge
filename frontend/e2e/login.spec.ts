/**
 * login.spec.ts — Authentication E2E tests.
 *
 * These tests do NOT use the global auth state so they can exercise the
 * login page itself (including wrong-credentials error path).
 */
import { test, expect } from '@playwright/test'

// Override storageState — run these tests unauthenticated
test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Login page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('renders the sign-in form', async ({ page }) => {
    await expect(page.getByTestId('username')).toBeVisible()
    await expect(page.getByTestId('password')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('shows error on wrong credentials', async ({ page }) => {
    await page.getByTestId('username').fill('admin')
    await page.getByTestId('password').fill('definitely-wrong-password')
    await page.getByRole('button', { name: /sign in/i }).click()

    // Backend returns 401; Login.tsx surfaces the error message
    await expect(page.locator('text=/invalid|unauthorized|credentials|incorrect/i')).toBeVisible({ timeout: 10_000 })

    // Must NOT navigate away from /login
    await expect(page).toHaveURL(/\/login/)
  })

  test('redirects to dashboard on correct credentials', async ({ page }) => {
    await page.getByTestId('username').fill(process.env.E2E_USERNAME ?? 'admin')
    await page.getByTestId('password').fill(process.env.E2E_PASSWORD ?? '')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })
    // FlowForge brand and breadcrumb should be visible
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('unauthenticated access to /dashboard redirects to /login', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })
})
