import { defineConfig, devices } from '@playwright/test'

/**
 * E2E tests require the full stack running before you invoke playwright:
 *
 *   # Terminal 1 — backend
 *   source .env && python -m flask --app flowforge.api.app:create_app run -p 5000
 *   # or: flowforge web
 *
 *   # Terminal 2 — frontend dev server
 *   cd frontend && npm run dev
 *
 *   # Terminal 3 — run tests
 *   cd frontend && npm run test:e2e
 *
 * Environment variables (all optional, shown with defaults):
 *   E2E_BASE_URL   http://localhost:5173
 *   E2E_USERNAME   admin
 *   E2E_PASSWORD   testpass
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['html', { open: 'never', outputFolder: 'e2e/playwright-report' }],
    ['line'],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
  },
  projects: [
    // Login once and persist storage state for all other tests
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth.json',
      },
      dependencies: ['setup'],
    },
  ],
})
