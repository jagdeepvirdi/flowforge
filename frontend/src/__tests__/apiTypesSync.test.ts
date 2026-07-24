// MAINT-02: guards against docs/openapi/pipelines.yaml and the committed generated
// types (src/lib/generated/pipelines.ts) drifting apart. Regenerates the types from
// the spec (the exact command `npm run generate:api-types` runs) and diffs the
// result against what's committed — fails if someone edited the spec (or the
// generated file) without running the generator and committing the result.
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = path.resolve(__dirname, '..', '..')
const SPEC_PATH = path.resolve(FRONTEND_ROOT, '..', 'docs', 'openapi', 'pipelines.yaml')
const GENERATED_PATH = path.resolve(FRONTEND_ROOT, 'src', 'lib', 'generated', 'pipelines.ts')
// Invoke the CLI's JS entry point directly via `node` rather than `npx` — avoids
// `shell: true` (a command-injection footgun even with static, developer-controlled
// args) while still working identically on Windows/macOS/Linux/CI.
const CLI_ENTRY = path.resolve(FRONTEND_ROOT, 'node_modules', 'openapi-typescript', 'bin', 'cli.js')

describe('generated API types stay in sync with docs/openapi/pipelines.yaml', () => {
  it('regenerating from the spec produces the exact committed file', () => {
    const freshlyGenerated = execFileSync(
      process.execPath,
      [CLI_ENTRY, SPEC_PATH],
      { cwd: FRONTEND_ROOT, encoding: 'utf-8' },
    )
    const committed = readFileSync(GENERATED_PATH, 'utf-8')

    expect(freshlyGenerated.trim()).toBe(committed.trim())
  })
})
