/**
 * global.teardown.ts — runs once after all E2E tests complete.
 *
 * Deletes every pipeline whose name starts with "E2E " so the dashboard
 * stays clean. Cascade delete in the DB removes the associated run history.
 * Runs via API (no browser needed) using the stored auth token from .auth.json.
 */
import { test as teardown } from '@playwright/test'
import fs from 'fs'

const API = process.env.E2E_API_URL ?? 'http://localhost:5000/api'
const AUTH_FILE = 'e2e/.auth.json'
const E2E_PREFIX = 'E2E '

teardown('delete E2E test pipelines', async () => {
  // Read the JWT token from the Zustand state saved by global.setup.ts.
  // localStorage key: "flowforge-auth", value: '{"state":{"token":"..."},"version":0}'
  if (!fs.existsSync(AUTH_FILE)) return
  const state = JSON.parse(fs.readFileSync(AUTH_FILE, 'utf8'))
  const rawEntry = state?.origins
    ?.flatMap((o: { localStorage: { name: string; value: string }[] }) => o.localStorage)
    ?.find((e: { name: string }) => e.name === 'flowforge-auth')
    ?.value
  const token: string | undefined = rawEntry ? JSON.parse(rawEntry)?.state?.token : undefined

  if (!token) {
    console.warn('[teardown] No auth token found — skipping cleanup')
    return
  }

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  // Fetch all pipelines
  const listRes = await fetch(`${API}/pipelines`, { headers })
  if (!listRes.ok) {
    console.warn(`[teardown] Could not list pipelines (${listRes.status}) — skipping cleanup`)
    return
  }
  const pipelines: { id: string; name: string }[] = await listRes.json()
  const e2ePipelines = pipelines.filter(p => p.name.startsWith(E2E_PREFIX))

  if (e2ePipelines.length === 0) {
    console.log('[teardown] No E2E pipelines to clean up')
    return
  }

  let deleted = 0
  for (const p of e2ePipelines) {
    const res = await fetch(`${API}/pipelines/${p.id}`, { method: 'DELETE', headers })
    if (res.ok) {
      deleted++
    } else {
      console.warn(`[teardown] Failed to delete "${p.name}" (${res.status})`)
    }
  }
  console.log(`[teardown] Deleted ${deleted}/${e2ePipelines.length} E2E pipelines`)
})
