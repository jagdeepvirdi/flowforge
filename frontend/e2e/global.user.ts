/**
 * global.user.ts — Playwright `globalSetup`: gives the run its own throwaway admin account.
 *
 * Instead of keeping a real password in .env.test, this creates a user with a random
 * password through the FlowForge CLI (`flowforge user create --generate-password`), exposes it
 * to every test through E2E_USERNAME / E2E_PASSWORD (workers inherit this process's env), and
 * deletes the account again when the run ends. The password lives only in memory.
 *
 * Escape hatch: if E2E_USERNAME and E2E_PASSWORD are already set (e.g. you want to test a
 * specific account), they are used as-is and nothing is created or deleted.
 *
 * The CLI must reach the same database as the backend under test, so it runs with the server's
 * env file (../.env, or E2E_SERVER_ENV) layered over the current environment. That file wins
 * on purpose: playwright.config.ts has already loaded .env.test, whose FLOWFORGE_DB_URL points
 * at the pytest database, not the one the dev server is using.
 */
import { execFileSync } from 'child_process'
import { parse as parseEnv } from 'dotenv'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '../..')

function pythonBinary(): string {
  if (process.env.E2E_PYTHON) return process.env.E2E_PYTHON
  const candidates = [
    path.join(repoRoot, '.venv', 'Scripts', 'python.exe'),
    path.join(repoRoot, '.venv', 'bin', 'python'),
  ]
  return candidates.find(p => fs.existsSync(p)) ?? 'python'
}

function serverEnv(): NodeJS.ProcessEnv {
  const file = process.env.E2E_SERVER_ENV ?? path.join(repoRoot, '.env')
  const fromFile = fs.existsSync(file) ? parseEnv(fs.readFileSync(file)) : {}
  return { ...process.env, ...fromFile }
}

function flowforge(args: string[]): string {
  return execFileSync(pythonBinary(), ['-m', 'flowforge.cli', ...args], {
    cwd: repoRoot,
    env: serverEnv(),
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  })
}

export default async function globalSetup() {
  if (process.env.E2E_USERNAME && process.env.E2E_PASSWORD) return

  const username = `e2e_${Date.now().toString(36)}`
  const out = flowforge([
    'user', 'create', username,
    '--role', 'admin', '--generate-password', '--no-force-change', '--json',
  ])
  // Logging may precede the JSON; the credentials are on the last JSON line.
  const line = out.trim().split(/\r?\n/).reverse().find(l => l.startsWith('{'))
  if (!line) throw new Error('flowforge user create did not return credentials')
  const { password } = JSON.parse(line) as { password: string }

  process.env.E2E_USERNAME = username
  process.env.E2E_PASSWORD = password

  return async () => {
    try {
      flowforge(['user', 'delete', username, '--yes', '--purge'])
    } catch (err) {
      console.warn(`[e2e] could not delete throwaway user ${username}:`, (err as Error).message)
    }
  }
}
