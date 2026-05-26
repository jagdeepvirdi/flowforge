# Security & Quality Issues — FlowForge
*SonarCloud snapshot: 2026-05-26. GitHub Scorecard: 2026-05-26 (27 open alerts, 10 distinct rules).*
*Only OPEN issues listed. CLOSED = already fixed.*

---

# GitHub Scorecard — Open Alerts

*Scorecard runs on every push to `master` and weekly Saturday cron. Results publish to GitHub → Security → Code scanning.*
*Total: 28 alerts scanned, 27 open, 1 dismissed.*

## Alert Summary

| Rule | Severity | Count | Status |
|---|---|---|---|
| PinnedDependencies | ERROR | 18 | Partial — see breakdown below |
| TokenPermissions | ERROR | 1 | ✅ Already fixed — stale alert (test.yml line 9 has `permissions: read-all`) |
| BranchProtection | ERROR | 1 | ⬜ Fix — GitHub UI |
| CodeReview | ERROR | 1 | ⬜ Fix — tied to BranchProtection |
| DependencyUpdateTool | ERROR | 1 | ✅ Already fixed — stale alert (dependabot.yml covers pip + npm + github-actions) |
| SAST | ERROR | 1 | ⬜ Fix — add CodeQL workflow |
| Vulnerabilities | ERROR | 1 | ⬜ Fix — run pip-audit in CI |
| CIIBestPractices | ERROR | 1 | ⬜ Tracked in TASKS.md §2.3 (OpenSSF self-cert) |
| Fuzzing | ERROR | 1 | 🚫 Accept — OSS-Fuzz registration not practical for v1 |
| Maintained | ERROR | 1 | 🚫 Auto-resolves with commit activity |

---

## SC-1 — PinnedDependencies (18 alerts)

Scorecard flags any dependency reference not locked to an immutable hash.

### SC-1a — Docker base images not pinned to digest (2 alerts) ⬜ Fix
**Files:** `Dockerfile:2`, `Dockerfile:10`
```dockerfile
# Current (unfixed):
FROM node:20-alpine
FROM python:3.11-slim

# Fix — pin to SHA digest:
FROM node:20-alpine@sha256:<digest>
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0
```
Scorecard provided the python digest in the alert. Run `docker pull node:20-alpine --quiet` to get node digest.

---

### SC-1b — pip install without hash verification (4 alerts) 🚫 Accept
**Files:** `test.yml:47,79`, `Dockerfile:15,20`

Scorecard wants `pip install --require-hashes` (hash-checked mode). This requires a `pip-compile --generate-hashes`-produced lockfile and is incompatible with editable installs (`-e ".[dev]"`). Too complex to maintain without dedicated tooling. Accept this score penalty.

---

### SC-1c — GitHub Actions in test.yml not SHA-pinned (10 alerts) ✅ Stale alerts
**Files:** `test.yml:36,40,47,52,59,70,72,89,91`

All actions in `test.yml` and `scorecard.yml` are already SHA-pinned in commits `c633837` and `04efa8e`. These alerts were generated before those commits and will clear on the next Scorecard weekly run.

---

## SC-2 — TokenPermissions (1 alert) ✅ Stale — already fixed
**File:** `test.yml:1`

`permissions: read-all` already exists at the workflow top level (line 9). Alert will clear on next run.

---

## SC-3 — BranchProtection + SC-4 CodeReview (2 alerts) ⬜ Fix
**Action:** GitHub UI → Settings → Branches → Add rule for `master`:
- [x] Require a pull request before merging
- [x] Require at least 1 approval
- [x] Require status checks to pass before merging (select: `test`, `sast`, `frontend`)
- [x] Require branches to be up to date before merging

Fixes both `BranchProtection` and `CodeReview` in a single step. No code change required.

---

## SC-5 — DependencyUpdateTool (1 alert) ✅ Stale — already fixed
`.github/dependabot.yml` is present and covers three ecosystems: `pip`, `npm`, `github-actions`. Alert will clear on next Scorecard run.

---

## SC-6 — SAST (1 alert) ⬜ Fix
**Problem:** Scorecard doesn't recognise bandit or SonarCloud as a SAST tool. It looks for CodeQL or Semgrep with a SARIF upload to the GitHub Security tab.

**Fix:** Add a `codeql.yml` workflow (Python + JavaScript/TypeScript analysis):
```yaml
# .github/workflows/codeql.yml
name: CodeQL
on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]
  schedule:
    - cron: '0 3 * * 1'   # Weekly Monday 03:00 UTC

permissions: read-all

jobs:
  analyze:
    name: CodeQL analysis
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
      actions: read
    strategy:
      matrix:
        language: [python, javascript]
    steps:
      - uses: actions/checkout@<SHA>
      - uses: github/codeql-action/init@<SHA>
        with:
          languages: ${{ matrix.language }}
      - uses: github/codeql-action/autobuild@<SHA>
      - uses: github/codeql-action/analyze@<SHA>
```
SHAs to fill in from `github/codeql-action` latest release at time of implementation.

---

## SC-7 — Vulnerabilities (1 alert) ⬜ Fix
**Fix:** Add `pip-audit` step to CI so known CVEs fail the build:
```yaml
- name: Python vulnerability audit
  run: pip install pip-audit && pip-audit
```
Also confirm `npm audit --audit-level=high` in the `frontend` job is correctly failing the build on HIGH+ CVEs (currently present in `test.yml:115`).

---

## SC-8 — CIIBestPractices (1 alert) ⬜ Tracked in TASKS.md §2.3
Complete the self-certification at [bestpractices.dev](https://bestpractices.dev). Earning the Passing tier adds this badge and clears the Scorecard alert automatically.

---

## SC-9 — Fuzzing (1 alert) 🚫 Accept for v1
Scorecard expects integration with OSS-Fuzz or a project-registered fuzzer. Not practical for v1. Revisit for v2.

---

## SC-10 — Maintained (1 alert) 🚫 Auto-resolves
Scorecard marks a project as not maintained if there are no commits in the past 90 days. Will auto-clear as the repo becomes active.

---

---

# SonarCloud Issues

*Exported 2026-05-26. Only OPEN issues listed. CLOSED = already fixed.*
*540 total rows in export; ~200 were CLOSED before this snapshot.*

---

## Summary

| Priority | Count | Action |
|---|---|---|
| 🔴 Bugs | 9 | Fix — real defects |
| 🟠 Security | 2 | Fix or accept |
| 🔴 Critical code smells | 28 | Refactor |
| 🟡 Major code smells | ~90 | Fix in batches |
| 🟢 Minor code smells | ~60 | Fix opportunistically |

---

## 🔴 Bugs (fix first)

### React Hooks called conditionally — `Users.tsx` (4 instances)
**Rule:** typescript:S6440 — **Real bug.** React will throw at runtime if hook call order changes.
| Line | Hook |
|---|---|
| 51 | `useQuery` |
| 56 | `useMutation` |
| 67 | `useMutation` |
| 72 | `useMutation` |
**Fix:** Move all hook calls above any early-return conditions.

---

### Conditional always returns same value
**Rule:** typescript:S3923
| File | Line | Note |
|---|---|---|
| `frontend/src/pages/Dashboard.tsx` | 100 | Both branches of ternary produce same result |
| `frontend/src/pages/Connections.tsx` | 466 | Same — dead branch |
**Fix:** Remove the condition, use the value directly.

---

### Click handlers without keyboard listener
**Rule:** typescript:S1082 — Accessibility + functional bug (keyboard-only users can't trigger).
| File | Line |
|---|---|
| `frontend/src/components/shared/Layout.tsx` | 68 |
| `frontend/src/components/shared/HelpDrawer.tsx` | 185 |
| `frontend/src/components/shared/PageIntro.tsx` | 35 |
| `frontend/src/pages/EmailEdit.tsx` | 380 |
| `frontend/src/pages/Projects.tsx` | 149 |
**Fix:** Add `onKeyDown`/`onKeyUp` handler or replace `<div onClick>` with `<button>`.

---

## 🟠 Security (OPEN)

### `SECRET_KEY` false positive — `app.py:40`
**Rule:** python:S2068 — SonarCloud flags `jwt_secret = app.config['SECRET_KEY']`.
**Reality:** Value comes from `FLOWFORGE_JWT_SECRET` env var, not hardcoded.
**Action:** Accept as false positive in SonarCloud UI ("Won't Fix" + justification), or rename the variable to avoid the `SECRET_KEY` pattern.

### NOSONAR comment syntax — 2 files
**Rule:** python:S7632 — SonarCloud complains about malformed suppression comment syntax.
| File | Line | Current comment |
|---|---|---|
| `flowforge/api/app.py` | 34 | `# NOSONAR: value from env, not hardcoded` |
| `flowforge/api/routes/emails.py` | 140 | In PR #22 (fix already in flight) |
**Fix:** Change to exactly `# NOSONAR` with no trailing text, or use `# noqa` style per SonarCloud docs for Python.

---

## 🔴 Critical Code Smells

### Cognitive complexity too high — Python
**Rule:** python:S3776 — threshold is 15.
| File | Function line | Complexity | Excess |
|---|---|---|---|
| `flowforge/engine/runner.py` | 53 | 42 | +27 |
| `flowforge/steps/bulk_load.py` | 26 | 34 | +19 |
| `flowforge/steps/data_load.py` | 19 | 32 | +17 |
| `flowforge/steps/bulk_load.py` | 369 | 30 | +15 |
| `flowforge/api/routes/ai.py` | 166 | 19 | +4 |
| `flowforge/steps/db_query.py` | 47 | 18 | +3 |
| `flowforge/api/routes/pipelines.py` | 177 | 17 | +2 |
| `flowforge/api/routes/pipelines.py` | 328 | 17 | +2 |
**Fix:** Extract sub-functions. `runner.py:53` is the worst — split the main execution loop into helper methods.

---

### Cognitive complexity too high — TypeScript/Frontend
**Rule:** typescript:S3776 — threshold is 15.
| File | Line | Complexity |
|---|---|---|
| `frontend/src/pages/RunDetail.tsx` | 71 | 32 |
| `frontend/src/pages/Connections.tsx` | 74 | 26 |
| `frontend/src/pages/Settings.tsx` | 108 | 17 |
**Fix:** Extract render helpers or sub-components.

---

### Deeply nested functions — `PipelineEdit.tsx`
**Rule:** typescript:S2004 — max nesting depth is 4.
| Lines | Note |
|---|---|
| 299, 306, 312, 318 | Functions nested >4 levels deep |
**Fix:** Extract inner callbacks to named functions at module/component level.

---

### Duplicated string literals — Python routes
**Rule:** python:S1192 — define a constant instead.
| File | Literal | Count |
|---|---|---|
| `flowforge/api/routes/pipelines.py:171` | `'Pipeline not found'` | 9x |
| `flowforge/api/routes/emails.py:89` | `'Email config not found'` | 4x |
| `flowforge/api/routes/users.py:58` | `'User not found'` | 3x |
| `flowforge/api/routes/runs.py:108` | `'Run not found'` | 3x |
| `flowforge/api/routes/projects.py:72` | `'Project not found'` | 3x |
| `flowforge/api/routes/bulk_loads.py:77` | `'Bulk load config not found'` | 3x |
| `flowforge/api/app.py:143` | `'Not found'` | 3x |
| `flowforge/db/models.py:62` | `'SET NULL'` | 9x |
| `flowforge/db/models.py:62` | `'ff_projects.id'` | 4x |
| `flowforge/db/models.py:196` | `'all, delete-orphan'` | 4x |
| `flowforge/db/models.py:217` | `'ff_pipelines.id'` | 4x |
**Fix:** Define module-level constants e.g. `_NOT_FOUND = 'Pipeline not found'`.

---

## 🟡 Major Code Smells

### Use `logging.exception()` instead of `logger.error()` in except blocks
**Rule:** python:S8572 — `logging.exception()` automatically includes the traceback.
| File | Lines |
|---|---|
| `flowforge/engine/runner.py` | 219, 248, 268 |
| `flowforge/engine/scheduler.py` | 96, 153, 164 |
| `flowforge/engine/launcher.py` | 67, 96 |
| `flowforge/engine/shutdown.py` | 153, 155 |
| `flowforge/steps/bulk_load.py` | 143 |
| `flowforge/steps/data_load.py` | 138, 159 |
| `flowforge/steps/ai_analyze.py` | 116, 147 |
| `flowforge/steps/sftp_transfer.py` | 195, 285 |
| `flowforge/steps/onedrive_upload.py` | 34 |
| `flowforge/connections/mysql.py` | 88 |
| `flowforge/email_providers/gmail.py` | 95 |
| `flowforge/email_providers/microsoft365.py` | 102 |
| `flowforge/email_providers/smtp.py` | 92 |
**Fix:** In each `except` block, change `logger.error("...: %s", e)` → `logger.exception("...")`. One-liner per occurrence, ~20 min total.

---

### Flask routes missing explicit HTTP methods — `app.py:149,150`
**Rule:** python:S6965
```python
# Current (flags both routes):
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
# Fix:
@app.get('/', defaults={'path': ''})
@app.get('/<path:path>')
```

---

### Do not use Array index as React key
**Rule:** typescript:S6479 — causes rendering bugs when list order changes.
| File | Lines |
|---|---|
| `frontend/src/components/shared/Layout.tsx` | 186 |
| `frontend/src/components/shared/HelpDrawer.tsx` | 51, 91, 126 |
| `frontend/src/components/report/ChartPreview.tsx` | 101 |
| `frontend/src/pages/Dashboard.tsx` | 94, 218, 253 |
| `frontend/src/pages/PipelineEdit.tsx` | 294, 616, 640 |
| `frontend/src/pages/BulkLoads.tsx` | 44 |
| `frontend/src/pages/EmailEdit.tsx` | 176 |
| `frontend/src/pages/ReportEdit.tsx` | 216 |
| `frontend/src/pages/RunHistory.tsx` | 94 |
**Fix:** Use a stable unique field from the data as key (e.g. `item.id`). Only use index when list is static and never reordered.

---

### Form labels not associated with controls — Accessibility
**Rule:** typescript:S6853 — screen readers can't link label to input.
| File | Lines |
|---|---|
| `frontend/src/pages/Settings.tsx` | 74, 79, 84 |
| `frontend/src/pages/Users.tsx` | 118, 128, 138 |
| `frontend/src/pages/Projects.tsx` | 87, 97, 106 |
| `frontend/src/pages/BulkLoadEdit.tsx` | 150, 155, 164, 171, 178, 203, 212, 217, 225, 233, 237, 247, 251, 262, 278 |
| `frontend/src/pages/EmailEdit.tsx` | 274, 282 |
**Fix:** Add `htmlFor="field-id"` on `<label>` and matching `id="field-id"` on `<input>`, or wrap input inside the label element.

---

### Non-native interactive elements without ARIA role
**Rule:** typescript:S6848
| File | Line |
|---|---|
| `frontend/src/components/shared/Layout.tsx` | 68 |
| `frontend/src/components/shared/HelpDrawer.tsx` | 185 |
| `frontend/src/components/shared/PageIntro.tsx` | 35 |
| `frontend/src/components/shared/TopBar.tsx` | 154 |
| `frontend/src/pages/EmailEdit.tsx` | 380 |
| `frontend/src/pages/Projects.tsx` | 149 |
**Fix:** Replace `<div onClick>` with `<button>` where possible. If a div must be used, add `role="button"` + `tabIndex={0}` + keyboard handler.

---

### Nested ternary operations — extract to variable
**Rule:** typescript:S3358
| File | Lines |
|---|---|
| `frontend/src/pages/Connections.tsx` | 133, 456, 466, 495, 503 |
| `frontend/src/pages/Dashboard.tsx` | 67 |
| `frontend/src/pages/RunDetail.tsx` | 163, 242, 404, 405 |
| `frontend/src/pages/ReportEdit.tsx` | 324 |
| `frontend/src/pages/PipelineEdit.tsx` | 468, 562 |
| `frontend/src/pages/Settings.tsx` | 144 |
| `frontend/src/pages/Projects.tsx` | 124 |
| `frontend/src/pages/Users.tsx` | 169 |
**Fix:** Extract to a named `const` before the JSX return.

---

### CSS contrast ratio below WCAG minimum — `index.css`
**Rule:** css:S7924 — affects accessibility/readability.
| Lines | Note |
|---|---|
| 305, 306 | Text colour does not meet minimum contrast ratio against its background |
**Fix:** Increase foreground/background contrast to at least 4.5:1 (AA standard).

---

### Use `<dialog>` element — `HelpDrawer.tsx:197`
**Rule:** typescript:S6819
**Fix:** Replace `<div role="dialog">` with native `<dialog>` element for proper accessibility semantics.

---

### Ambiguous spacing after element — JSX
**Rule:** typescript:S6772
| File | Lines |
|---|---|
| `frontend/src/components/shared/Layout.tsx` | 103, 148 |
| `frontend/src/pages/Projects.tsx` | 232 |
| `frontend/src/pages/PipelineEdit.tsx` | 313 |
| `frontend/src/pages/BulkLoadEdit.tsx` | 186 |
**Fix:** Add explicit space character `{' '}` between inline elements instead of relying on whitespace collapsing.

---

## 🟢 Minor Code Smells (fix opportunistically)

### Mark React props as `Readonly<Props>` — TypeScript
**Rule:** typescript:S6759 — prevents accidental mutation.
Affects: `App.tsx`, `Skeleton.tsx`, `Recipients.tsx`, `Users.tsx`, `Dashboard.tsx`, `Settings.tsx`, `Connections.tsx`, `HelpDrawer.tsx`, `RunDetail.tsx`, `ChartPreview.tsx`, `PipelineEdit.tsx`, `Pipelines.tsx`, `PageIntro.tsx`, `Projects.tsx`, `ProjectSwitcher.tsx`, `StepEditor.tsx`, `FieldTooltip.tsx`, `TopBar.tsx`.
**Fix:** Change `interface Props` → `type Props = Readonly<{...}>` or `React.FC<Readonly<Props>>`.

---

### Prefer `globalThis` over `window`
**Rule:** typescript:S7764 — `window` is not available in non-browser environments.
Affects: `api.ts:26,205`, `TopBar.tsx:44,45`, `HelpDrawer.tsx:178,179`, `PipelineEdit.tsx:394`, `BulkLoads.tsx:142`, `Projects.tsx:194`, `RouteErrorBoundary.tsx:50`, `Users.tsx:86`.
**Fix:** Replace `window.location`, `window.open` etc. with `globalThis.location`, `globalThis.open`.

---

### Unnecessary type assertions — TypeScript
**Rule:** typescript:S4325
Affects: `PipelineEdit.tsx:128`, `Pipelines.tsx:92`, `ReportEdit.tsx:196`, `RunDetail.tsx:331`, `ProjectSwitcher.tsx:39`, `BulkLoadEdit.tsx:22,99`, `StepEditor.tsx:223,267`, `FieldTooltip.tsx:18`.
**Fix:** Remove `as SomeType` casts where TypeScript already infers the correct type.

---

### Prefer `Number.parseInt` over `parseInt`
**Rule:** typescript:S7773
Affects: `StepEditor.tsx:186,627`, `BulkLoadEdit.tsx:248,252`, `Pipelines.tsx:17,18,23,36,40`, `PipelineEdit.tsx:537–541`.
**Fix:** `parseInt(x, 10)` → `Number.parseInt(x, 10)`.

---

### Unexpected negated condition
**Rule:** typescript:S7735
Affects: `Layout.tsx:182`, `RunDetail.tsx:225`, `BulkLoads.tsx:78`.
**Fix:** Invert condition and swap branches to remove the `!`.

---

### Shell: use `[[` instead of `[`
**Rule:** shelldre:S7688
Affects: `tests/run_tests.sh:27,29,35`.
**Fix:** Replace `if [ ... ]` with `if [[ ... ]]`.

---

### Shell: add default case to switch — `tests/run_tests.sh:17`
**Rule:** shelldre:S131
**Fix:** Add `*) echo "Unknown option" ; exit 1 ;;` to the case statement.

---

### Prefer `Blob#text()` over `FileReader` — `Pipelines.tsx:93`
**Rule:** typescript:S7756
**Fix:** Replace `FileReader.readAsText(blob)` with `await blob.text()`.

---

### Replace constructor call with literal — `sftp_transfer.py:56`
**Rule:** python:S7498 — e.g. `dict()` → `{}`, `list()` → `[]`.

---

## Already Fixed / In Flight

| Issue | Status |
|---|---|
| SSL cert validation + hostname verification (`smtp.py`) | ✅ Fixed in commit `b9f61c2` |
| Hardcoded PostgreSQL passwords (`docker-compose.yml`) | ✅ Fixed in commit `7dfbdab` |
| Hardcoded NOSONAR (`verify_celery.py`) | ✅ Fixed in commit `b9f61c2` |
| `/tmp` in `emails.py` (S5443) | 🔄 PR #22 in review |
| `ssl.SSLContext(ssl.PROTOCOL_TLS)` weak protocol | ✅ Fixed in commit `b9f61c2` |
| PL/SQL false positives (`*.sql` exclusion) | ✅ Fixed in commit `5dcb468` |
