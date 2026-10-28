/**
 * brain-absent.spec.ts — with no Brain attached, every AI surface stays dark.
 *
 * Covers the manual A5 checklist (docs/manual-testing-guide.md §14–15).
 * Requires the full stack running with FLOWFORGE_BRAIN_URL unset.
 */
import { test, expect } from '@playwright/test'

test.describe('Brain not attached', () => {
  test('Settings → Brain tab shows "Not attached" and no provider fields', async ({ page }) => {
    await page.goto('/settings')
    await page.getByRole('button', { name: 'Brain', exact: true }).click()
    await expect(page.getByText('Not attached')).toBeVisible()
    await expect(page.getByText(/ollama|anthropic|gemini/i)).toHaveCount(0)
  })

  test('step picker offers no ai_analyze', async ({ page }) => {
    await page.goto('/pipelines/new')
    await expect(page.getByRole('button', { name: /db query/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /ai analyze/i })).toHaveCount(0)
  })

  test('report designer has no AI Explain / Optimize buttons', async ({ page }) => {
    await page.goto('/reports/new')
    await expect(page.getByRole('heading').first()).toBeVisible()
    await expect(page.getByRole('button', { name: /explain|optimi[sz]e/i })).toHaveCount(0)
    await expect(page.getByText(/AI unavailable|via Ollama/i)).toHaveCount(0)
  })

  test('/api/ai/* returns 503 brain_not_attached', async ({ request }) => {
    const login = await request.post('/api/auth/login', {
      data: {
        username: process.env.E2E_USERNAME ?? 'admin',
        password: process.env.E2E_PASSWORD ?? 'testpass',
      },
    })
    const { token } = await login.json()
    const res = await request.post('/api/ai/query', {
      headers: { Authorization: `Bearer ${token}` },
      data: {},
    })
    expect(res.status()).toBe(503)
    expect((await res.json()).error).toBe('brain_not_attached')
  })
})
