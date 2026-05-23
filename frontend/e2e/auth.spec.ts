/**
 * auth.spec.ts — login, redirect, and sign-out flows.
 *
 * These tests deliberately run WITHOUT a stored auth session so that
 * each test starts from a clean, unauthenticated state.
 */
import { test, expect } from '@playwright/test'

// Explicitly clear any stored session for all tests in this file.
test.use({ storageState: { cookies: [], origins: [] } })

test('login page renders the sign-in form', async ({ page }) => {
  await page.goto('/login')
  await expect(page.locator('[data-testid="username"]')).toBeVisible()
  await expect(page.locator('[data-testid="password"]')).toBeVisible()
  await expect(page.locator('button[type="submit"]')).toContainText('Sign in')
})

test('unauthenticated access to /dashboard redirects to /login', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login/)
})

test('unauthenticated access to / redirects to /login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/login/)
})

test('unauthenticated access to /pipelines redirects to /login', async ({ page }) => {
  await page.goto('/pipelines')
  await expect(page).toHaveURL(/\/login/)
})

test('login with valid credentials lands on dashboard', async ({ page }) => {
  const username = process.env.E2E_USERNAME ?? 'admin'
  const password = process.env.E2E_PASSWORD ?? 'testpass'

  await page.goto('/login')
  await page.locator('[data-testid="username"]').fill(username)
  await page.locator('[data-testid="password"]').fill(password)
  await page.locator('button[type="submit"]').click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })
  // Sidebar should render the nav
  await expect(page.getByRole('link', { name: 'Pipelines' })).toBeVisible()
})

test('login with wrong password shows error and stays on /login', async ({ page }) => {
  await page.goto('/login')
  await page.locator('[data-testid="username"]').fill('admin')
  await page.locator('[data-testid="password"]').fill('definitely-wrong-password')
  await page.locator('button[type="submit"]').click()

  await expect(page).toHaveURL(/\/login/)
  // Wait for the async API response — the form should display the error message
  await expect(page.locator('form')).toContainText(/unauthorized|invalid|error|incorrect/i, { timeout: 10_000 })
})

test('login with empty username/password stays on /login (HTML5 validation)', async ({ page }) => {
  await page.goto('/login')
  // Both inputs have required attribute — browser blocks submission
  await page.locator('button[type="submit"]').click()
  await expect(page).toHaveURL(/\/login/)
})

test('sign out clears session and redirects to /login', async ({ page }) => {
  const username = process.env.E2E_USERNAME ?? 'admin'
  const password = process.env.E2E_PASSWORD ?? 'testpass'

  await page.goto('/login')
  await page.locator('[data-testid="username"]').fill(username)
  await page.locator('[data-testid="password"]').fill(password)
  await page.locator('button[type="submit"]').click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })

  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login/)

  // Confirm the session is gone: navigating to a protected route redirects again
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login/)
})
