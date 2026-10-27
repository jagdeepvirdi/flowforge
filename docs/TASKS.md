# TASKS.md — FlowForge

*Open work only. Completed work lives in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) (newest-first; the
2026-10-27 entry holds the V2.0 Audit Action Items and Phase 13 audit fixes).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*
*Last reorganized: 2026-10-27.*

---

## Where we are

| Release | Goal | Status |
|---|---|---|
| **v1.0** | Public GitHub release — stable, tested, `docker compose up` works, badges and docs polished, GTM done | Shipped (tagged); **GTM still partial** — see §6 |
| **v2.0** | Production-hardening — scaling docs, metrics, audit UI, retention, dependency audit in CI | Code complete; V2.0 audit items (ARCH/SEC/PERF/MAINT-01..02) all closed |
| **v2.x Compliance** | MFA, SSO, GDPR, encryption at rest | Shipped |
| **v3.0** | New connectors/providers, pipeline DAGs, plugin system, visual canvas | Shipped |

Latest code-review score table: **7.8 / 10 (2026-05-25)** — stale; the later 2026-07-24 architect/VC audit
scored 6/10 overall (Security 3/10 at the time; its Critical items have since all shipped). Re-score
after the §1–§3 items below land.

**Open items: 65** — §0 AI decoupling (11) · §0a Telecom RA MVP (5) · §1 Blockers (12) · §2 Product polish (7) · §3 Engineering quality (7) · §4 Supply chain & OSS health (7) · §5 Docs hygiene (2) · §6 Go-to-market (6) · §7 Strategic (8)

Items tagged *(derived)* were not open checkboxes before: they come from "explicitly out of scope" notes
in the now-archived completed items, promoted here so they aren't lost.

---

## 0. Architecture decision — decouple AI into the external "Brain" service *(decided 2026-10-27)*

**Full plan: [BRAIN_DECOUPLING_PLAN.md](BRAIN_DECOUPLING_PLAN.md)** (read its 2026-10-27 (b) amendment: no `/ai/*` shells — the UI calls Brain directly) and the target architecture in [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Read both before touching any AI code.
FlowForge becomes a deterministic ETL/SQL orchestrator; all LLM logic moves to a separate FastAPI "Brain" service.
**Rule:** the small AI features (SQL explain/optimize, failure diagnosis, anomaly narrative, data profile, chart suggestion,
`ai_analyze` step) stay in the UI code paths but are **dark unless a Brain is attached** (`FLOWFORGE_BRAIN_URL`). No fake/stub AI
output; disabled routes return `503 brain_not_attached`; the `ai_analyze` step fails with a clear message. **Do this before the §6
launch** (published posts and planned PH copy advertise "local AI"; record the demo GIF after the scrub). Effort ≈ 3–4 days.

- [ ] **A0 Prep** — commit/stash the uncommitted auth/users work first; tag `pre-brain-split`; branch/worktree `scrub/brain-decoupling`; record baseline test counts.
- [ ] **A1 Extract** — write `extracted_ai_logic.md` (prompts, provider code, endpoint contracts, step spec, UX contract, test behavior) **before deleting anything**; decide commit vs gitignore (public repo).
- [ ] **A2 Gate module** — `flowforge/brain.py`: `brain_enabled()` (Phase A: always False, TODO comment) + `brain_unavailable_response()`.
- [ ] **A3 Backend** — gut `routes/ai.py` to 503 shells, `ai_analyze` to a failing step, `setup.py` ai block → `{enabled, brain_url_configured}`; keep secret blocklist + historic migrations.
- [ ] **A4 Backend tests** — replace `test_ai.py`/`test_ai_analyze.py` with `test_brain_gate.py`; fix 4 other test files; check coverage gate.
- [ ] **A5 Frontend** — default-off gating (`?? false`), BrainCard replaces AiOllamaCard, remove AI calls/strings, hide `ai_analyze` from picker (keep badge), keep `ChartPreview` + anomaly detection; manual Playwright pass.
- [ ] **A6 Dependencies & config** — add a CI deny-list test (no LLM SDK imports/deps in `flowforge/`); remove `claude` extra (`anthropic`) from `pyproject.toml`; replace `.env.example` AI block with `FLOWFORGE_BRAIN_URL`/`_API_KEY`.
- [ ] **A7 Docs & positioning** — CLAUDE.md, README, ROADMAP, ~14 docs, new `docs/brain.md`, CHANGELOG breaking entry; rewrite GTM copy; check published Reddit/LinkedIn posts.
- [ ] **A8 Ship** — version decision (v2.0.0 vs 1.4.0 + BREAKING), PR with CI green.
- [ ] **Decide before A3:** check your DB for saved `ai_analyze` steps (they will fail after the scrub) — query in the plan §7.3.
- [ ] **Phase B (blocked)** — define Brain's API contract (auth, TLS, size caps, redaction, errors, versioning), then implement `brain_enabled()` health check and forwarding. Not scheduled.

---

## 0a. Telecom RA MVP — build order *(adopted 2026-10-27 from [TELECOM_PIVOT_ROADMAP.md](TELECOM_PIVOT_ROADMAP.md) with Claude's amendments)*

**First proof-of-concept: orphaned subscriptions** (HLR/HSS vs. billing vs. CRM), audited **in place** in the operator's
databases; FlowForge schedules and monitors the SQL and collects aggregates. Sequence: design-partner discovery
(§7, runs in parallel throughout) → §0 Brain scrub **∥** conditional execution (§2) → reconciliation step → PII
tokenization → audit template → compliance-claim verification → Brain scaffold (last; Phase B above). Reasoning and
the points where Claude disagrees with the roadmap are in the roadmap document. Effort figures are unvalidated estimates for one full-time developer.

- [ ] **Reconciliation step** *(≈ 1–2 weeks; the missing telecom primitive)* — compare keyed aggregates or key sets across **two connections** with tolerances and a capped sample of offending keys. A single `db_query` cannot join CRM, billing and HLR because they live in different systems, and `data_load` reads whole files into memory, so staging a full subscriber base is not safe. Define "orphaned" precisely first (active-unbilled, billed-unprovisioned, status mismatch, in-flight provisioning windows). Depends on conditional execution (§2) for threshold alerting.
- [ ] **PII tokenization/masking step** *(≈ 1 week)* — keyed HMAC with a per-deployment secret, **or** tokenization with a local lookup table (so Core can map findings back to subscribers). A plain/shared-salt hash of MSISDN/IMSI is brute-forceable and must not be called "irreversible". Also scrub free-text fields and cap the payload. Must exist and be reviewed before any data is sent to a Brain.
- [ ] **Orphaned-subscription audit template + seeded demo dataset** *(≈ 1 week)* — run end to end on the design partner's data or a synthetic equivalent; this is the PoC evidence.
- [ ] **Verify audit-log immutability** *(≈ 0.5 day)* — the roadmap lists "immutable audit logs" as already built. It is append-only in application code only; confirm whether the DB blocks UPDATE/DELETE (the retention job deletes old rows) and add revoked privileges / trigger / hash chain if not. Until then do not use the word "immutable" in docs or sales material.
- [ ] **Compliance-floor evidence** *(≈ 1–2 weeks, parallelizable)* — data-flow diagram (what leaves the network, over which path), retention and data-residency statement, key-management description, pen-test plan. Plus the existing items: react-router 7, the two SonarCloud findings. A telco security review asks for these before it looks at features.

---

## 1. Blockers — do first

*Failing quality gates or broken local dev. Nothing else is credible while these are red.*

### Security re-audit — 2026-10-27 *(do these before anything else; verified against code)*

*Re-check of the July 2026 audits (Security was scored 3/10 on 2026-07-24). The July Critical and punch-list items are confirmed fixed in code (see archive). Findings below are what the re-check turned up that is still open.*

- [ ] **react-router 6 → 7** (tracked in §2) — now the only frontend advisory pair left (2 moderate). Re-checked 2026-10-27: `npm audit fix` bumps 6.30.4 → 6.30.6 but the advisory range covers all of 6.x through 7.17.0, so it still needs the v7 migration. The vitest/@vitest/mocker moderate chain also remains (needs a vitest bump). Neither gates CI (`--audit-level=high`).
- [ ] **Push the dependency fixes and confirm CI is green; then triage the 12 open Dependabot PRs** — root cause of the failing CI found 2026-10-27: both audit gates were red on `master`'s own dependencies (backend `pip-audit`: 24 vulns in cryptography/PyJWT/tornado/urllib3; frontend `npm audit --audit-level=high`: 9 high), which is also why every Dependabot PR fails within ~45 s. Both are fixed locally (not yet committed or pushed). After merging: re-run CI, then rebase/close the Dependabot PRs; several are majors that need real review (typescript 7, recharts 3, jsdom 30, node 25-alpine, @types/node 26) and the actions bumps (checkout 7, setup-python 7, setup-node 7). Consider enabling Dependabot grouping for majors and a weekly lock refresh so the audit gates don't silently rot again.
- [ ] **Run the remaining security checks** *(partly done 2026-10-27: the full backend suite passed, 2,195 tests, once the test DB on port 5434 was up — the re-check had run while it was offline)*. Still to do: confirm the `flowforge-db` container is the intended test DB going forward, and run `npm test`/CI. Original item: **Test database was offline during the re-check** — nothing on port 5434 (only an unrelated `trove-postgres` container on 5440), so the security test files (`test_net_guard`, `test_rbac`, `test_auth*`, `test_context`, `test_plugin_loader`, `test_app_coverage`) were **not run**. Start the test DB and run the full suite to confirm the "fixed" claims empirically.
- [ ] **Residual `# nosec` review** — 40 findings are hidden by `# nosec` (bandit `--ignore-nosec`: 7× B608 SQL string-building, 8× B310 `urlopen`, rest low). I spot-checked the SQL ones in `data_load`, `db_query` and `bulk_load`: their table/column names are validated first. The `urlopen` suppressions are down from 8 to 4 after the 2026-10-27 SSRF fixes; the 4 left are admin-env URLs (three in the legacy AI code being removed, one DevBrain notify hook). Make `bandit` fail on **unjustified** `nosec` (require a reason comment) so this can't recur silently.
- [ ] **Decide the editor trust boundary** *(by design, but critical for a telecom pitch)* — users with the `editor` role can author arbitrary SQL (`db_query`, `db_procedure`, report SQL) against every connected database and arbitrary shell commands over SSH (`ssh_command`). `docs/threat-model.md` documents this. Before enterprise use, consider: read-only DB accounts per connection, per-connection allowlists, an approval/review step for SQL and SSH changes, and an `author`/`approver` role split.
- [ ] **Local credential hygiene** — a dev login is stored in plaintext in the assistant memory index; `docs/credentials.local.md` is correctly gitignored and untracked. Rotate/remove the stored login if it was ever reused anywhere, and run a TruffleHog scan over full git history once (the CI gate is `--only-verified`).

**Verified fixed (no action):** boot-time secret validation and no JWT→`SECRET_KEY` fallback outside tests; secret pipeline variables hard-blocked from SQL/email/notification sinks (`SecretLeakError`); `validate_identifier()` on `data_load`/`bulk_load`/`db_query` table and column names; `assert_public_url` on the `notification` step; `log_user_change()` for user-admin audit events; Docker runs as non-root `flowforge`; compose requires `POSTGRES_PASSWORD`; `.env`/`credentials.local.md` untracked; bandit (without `--ignore-nosec`) reports 0 medium/high.

### SonarCloud — needs manual resolution *(found 2026-07-06)*

- [ ] **Resolve SonarCloud `pythonsecurity:S5496`** (issue key `AZ82Oyzt-6VzRaR01a4L`, `flowforge/engine/context.py`) as Won't Fix / False Positive in the SonarCloud UI — the rule flags the `render()` call-site pattern itself (Jinja2 template from user-controlled input) regardless of the mitigations already shipped, and will keep failing `master`'s Quality Gate until manually resolved or aged out of the New Code period. Justification: `_jinja` is already a `SandboxedEnvironment` (blocks RCE-class gadgets), the blocklist/pattern covers known and future credential names, rendered values are no longer reflected, and this is the same `{{ current_date }}`-style templating used intentionally everywhere else. **Requires SonarCloud login (not available to Claude).**
- [ ] **Resolve SonarCloud `pythonsecurity:S3649`** (SQL injection, issue key `AZ83ITEjNp5vzm4zlnz0`, `flowforge/steps/bulk_load.py:614` in `_dry_run_insert_rows()`, introduced 2026-07-06) as Won't Fix / False Positive — taint tracker flags `target_table`/`columns` flowing into the f-string-built `INSERT`, but both are validated with `validate_identifier()` (regex allowlist: letters/digits/underscore/dot only) by the caller **and** redundantly re-validated inside `_dry_run_insert_rows()`. SonarCloud doesn't recognize a project-local validator as a sanitizer boundary, so the finding persists. Fails the Quality Gate (New Code Security Rating) like S5496. **Requires SonarCloud login.**

### Local environment — Gmail sending broken *(found 2026-07-03, blocks dev testing)*

*SMTP is fixed (port/`use_ssl` mismatch + AVG Email Shield). Gmail is still broken.*

- [ ] **AVG Web Shield is intercepting `oauth2.googleapis.com`** — `SSLCertVerificationError: unable to get local issuer certificate` on token refresh. Fix: AVG → Settings → Protection → Web & Email → disable **Web Shield**, or add a domain exception for `googleapis.com`.
- [ ] **Re-authorize Gmail — refresh token expired** — `RefreshError: invalid_grant: Bad Request`. Cause: Google OAuth consent screen is in **Testing** status, where refresh tokens hard-expire after 7 days. Fix: re-run Step 5 in `docs/gmail-oauth2-setup.md`, then update the "Personal Gmail" provider in **Connections → Email Providers**.
- [ ] **Stop it recurring every ~7 days** — publish the OAuth consent screen to "In production". Caveat: the app requests the full `drive` scope (Google-*restricted*, needs a verification review). Options: go through verification, or narrow to `drive.file` (not restricted) if full-Drive access isn't required — small code change plus re-consent.
- [ ] **Doc gap**: `docs/gmail-oauth2-setup.md` "Keeping the App in Testing vs Publishing" (line ~158) says Testing mode is fine "indefinitely" but omits the 7-day refresh-token expiry — add a warning.

---

## 2. Product polish — user-visible

*What a first-time user or evaluator actually sees. This is the "polish the product" track.*

- [ ] **Close the "no YAML required" first-run gap** — a bare dashboard is one `docker compose up` away, but a first real pipeline with email needs 5+ manual steps in Google Cloud Console or Azure AD (OAuth app registration, consent screens, client secrets) before the no-code promise is true end-to-end. Candidates: a guided first-run wizard, a zero-config "send me a test email" via plain SMTP, a sample pipeline that needs no external account.
- [ ] **Conditional / branching step execution** — can't gate a step on a prior step's output (e.g. "only send email if row count > 0") beyond DAG failure propagation (`on_error: stop`/`continue`). Current workaround: always run the step, filter in the query. Not a non-goal, just not built. *(Phase 12)*
- [ ] **One-click deploy** (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.
- [ ] **react-router-dom 6.x → 7.x migration** — `npm audit` flags `react-router` `6.0.0-7.17.0` (installed `^6.24.0`) for two moderate advisories: open redirect via backslash in `<Link>`/`useNavigate` ([GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6)) and constructor injection via `deserializeErrors()` in SSR hydration ([GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg)). No same-major patch clears it (6.30.6 is still in range); needs a real v6→v7 migration (19 files in `frontend/src/` use router APIs). Doesn't gate CI (`--audit-level=high`). Steps: read the [v7 upgrade guide](https://reactrouter.com/upgrading/v6), audit affected APIs, migrate, re-run `npm audit`.
- [ ] **Decide Jinja undefined-variable behavior in DAG-mode pipelines** — a typo'd `{{ steps.X.* }}` silently renders blank. Either keep Jinja's default `Undefined` or add a DAG-build-time lint. *(Phase 14.2 M2 stretch; genuinely optional.)*
- [ ] **Stream Excel/PDF/JSON reports and `bulk_load`/`data_load` source files** *(derived)* — only CSV streams end-to-end today. Excel needs `openpyxl` `write_only=True`, which interacts with the shipped column-formatting feature (`docs/manual-testing-guide.md` §36); footer-row stripping in `bulk_load`/`data_load` needs a bounded sliding-window buffer to preserve header/footer-trim behavior across 3 load paths (Python fallback, Postgres COPY, SQL*Loader). Do it only when a real large-file case appears.
- [ ] **Extend OpenAPI-generated frontend types to the other 21 route files** *(derived from MAINT-02)* — only `pipelines.py` + `runs.py` are generated; `connections`, `reports`, `emails`, `users`, `steps`, … are still hand-typed in `types.ts`/`api.ts`, which is where drift bugs hide (MAINT-02 found a real nullable-`started_at` bug this way). Per route file: write/verify the spec against the real route + serializer, regenerate, alias only response-only types, verify with `tsc`/vitest.

---

## 3. Engineering quality

- [ ] **True unit tests with mocking** for `engine/runner.py`, `engine/dag.py`, `engine/context.py` — the suite is ~2150 tests but 100% integration-style against a real Postgres with zero `@patch`/`MagicMock` in the files checked; safe for refactors but slow, and can't isolate business logic from the DB/HTTP layer.
- [ ] **Production error tracking** (Sentry or equivalent) — logging is solid (113 call sites) but there is no error-tracking SDK anywhere.
- [ ] **Dependency/license audit in CI** (e.g. `pip-licenses`) plus a `NOTICE` file — the MIT-compatibility check (no GPL-family packages) was a one-time manual grep. Do before any commercial relicensing conversation.
- [ ] **Extend the service/repository layer beyond `pipelines.py`** *(derived)* — `pipeline_service.py` shipped for the worst offender only; `runs.py`, `reports.py`, `connections.py`, etc. still hold business logic inline in route bodies.
- [ ] **Extend the N+1 review to other list endpoints** *(suggested, not from a prior note)* — PERF-01 fixed `/api/pipelines` only; `/runs`, `/reports`, `/emails` list serializers weren't audited. Add the same query-count assertion test where they walk relationships.
- [ ] **Confirm the blocking secrets-scan gate on the next PR** — `secrets-scan.yml` lost `continue-on-error`; it was only YAML-validated locally, never executed. Watch the next PR's checks to ensure nothing in history trips TruffleHog `--only-verified`.
- [ ] **Re-verify the audit's "Critical" claim against the older 2026-07-01 findings** *(derived from project memory)* — memory records a verified SQL injection in `data_load.py`, a secrets leak, and an SSRF from that earlier audit; confirm each is closed (with a regression test) rather than assuming the Phase 13 pass covered them.

---

## 4. Supply chain & OSS health

- [ ] **Resolve the Scorecard Code-Review deadlock** (0/10; structurally stuck for a solo maintainer since GitHub blocks self-approval) — recruit a co-maintainer/approver or explicitly drop the ≥ 8.0 target. Disabling `enforce_admins` (2026-07-06) unblocks the solo merge workflow but admin-override merges still count as unreviewed.
- [ ] **PR discipline** — never push directly to `master`; open a PR. Self-approval is blocked, so use a second account/collaborator, or prefer bot-authored PRs (Dependabot).
- [ ] **Re-run Scorecard** to confirm Pinned-Dependencies improved after the hash-pinning already done.
- [ ] **Fuzzing** — register with [OSS-Fuzz](https://google.github.io/oss-fuzz/getting-started/accepting-new-projects/), or add an `atheris` target + `project.yaml` *(Scorecard — Fuzzing)*.
- [ ] **Signed releases** — add a cosign step to `release.yml` (`cosign sign-blob` on the wheel, attach `.sig`/`.pem`) *(Scorecard — Signed-Releases)*.
- [ ] **CII Silver** — document/recruit a co-maintainer (`bus_factor`), add DCO sign-off to the PR template (`dco`), complete the [Silver questionnaire](https://bestpractices.dev), update the README badge URL.
- [ ] **Code Climate maintainability badge** — add to README badge row if grade is A or B *(explicitly optional)*.

---

## 5. Docs hygiene

- [ ] **Refresh the review score table** — the 7.8/10 table is from 2026-05-25; re-run the codebase review and update `CODEBASE_REVIEW.md` after §1–§3.
- [ ] **Update screenshots showing the pre-multi-user UI** *(deferred — no screenshots exist in docs yet; do this together with the §6 demo assets)*.

---

## 6. Go-to-market

*Detail/copy for each item is in the reference section at the bottom. The demo GIF blocks everything else here.*

- [ ] **Record a 60–90s demo GIF/MP4** (dashboard → create pipeline with report+email step → run → Run History) and add it to the README *(5.1 — blocks the rest)*.
- [ ] **High-quality Dashboard screenshot** for the README hero / LinkedIn Featured *(5.1)*.
- [ ] **ProductHunt** — maker profile, listing (name/tagline/description/gallery), schedule a Tue/Wed launch *(5.2)*.
- [ ] **Reddit** — **partially done 2026-07-08**: r/Python and r/selfhosted posted; r/opensource and the r/dataengineering cross-post still pending *(5.3)*.
- [ ] **Awesome lists** — PRs to awesome-selfhosted ("Automation") and awesome-python ("Task Queues"/"Data Pipeline") *(5.4)*.
- [ ] **LinkedIn** — **launch post published 2026-07-08**; confirm it's pinned to Featured and carries the suggested hashtags *(5.5)*.

---

## 7. Strategic — decide before building

*Product-direction questions from the architect/VC audits. Don't build these on autopilot.*

- [ ] **Telecom RA pivot: find the design partner** *(2026-10-27; MVP use case decided = orphaned subscriptions, see §0a)* — [`ARCHITECTURE.md` §7](../ARCHITECTURE.md#7-telecom-revenue-assurance-mapping) shows building blocks exist but no telecom feature does. Prerequisites already on this list: conditional steps (threshold alerting), streaming for large files (CDR volumes), cross-DB comparison. Decide which leakage type to prove first (dropped CDRs vs. orphaned subscriptions), whether MIT-open-source core + enterprise offering is the model, and revisit the "solo devs / small teams" positioning in `CLAUDE.md`.
- [ ] **Decide repo naming and the licensing/delivery model** *(2026-10-27)* — this repo is `flowforge`; the roadmap says `flowforge-core`. An MIT core plus a proprietary Telecom RA Pack + Brain needs a delivery mechanism (private repo / package index) and a contributor policy (CLA); the MIT core also means anyone can build the pack, so the moat is audit templates proven on real data and the partner relationship. Hold the decision until a partner has seen reconciliation output.
- [ ] **Decide the Brain network path for telco deployments** *(2026-10-27)* — a cloud Brain requires operator browsers and Core to reach it, which many telco networks forbid. Proxy UI→Brain traffic through Core (contradicts the direct-UI decision in `ARCHITECTURE.md`) or require direct reachability; also decide the on-premises open-weight mode and build an evaluation set before promising it. Note "air-gapped" is not an accurate description of Core's relationship to the Brain; use "no LLM code or keys in Core, only sanitized evidence leaves".
- [ ] **Get at least one real external user or design partner** before adding more enterprise-checkbox features (SSO/SAML/MFA/GDPR tooling currently serves zero non-author users).
- [ ] **Airflow/cron migration tooling** — nothing exists beyond FlowForge's own YAML export/import; the most plausible real differentiator given the "Oracle advantage" / migration-bridge positioning in `docs/USE_CASE.md`.
- [ ] **Plugin marketplace/discovery layer** on the existing plugin system (`docs/plugins.md`) — the load mechanism exists; no registry/discovery UX.
- [ ] **Managed/hosted tier** reusing the `docker-compose.yml` topology — **conflicts with the stated non-goal** ("No cloud SaaS version" in `CLAUDE.md`; "Self-hosted only" in the accepted tradeoffs below). Decide whether to change that non-goal before any work; the audit calls it the more realistic commercial moat.
- [ ] **Reconcile the roadmap contradictions** *(derived from project memory)* — `ROADMAP.md`, `CLAUDE.md` Non-Goals and this file have disagreed before about what's shipped vs deferred; do one pass so all three tell the same story.

---

*Removed as obsolete: "ensure ≥ 1 commit/week until the repo passes 90 days old (~2026-07)" — the window has passed; Scorecard's Maintained check resolves on its own.*

---

## Timeline & effort *(estimates, added 2026-10-27)*

**Assumptions:** one developer working with Claude doing most of the code; estimates are focused working days
(~6 productive hrs). Part-time (~15 hrs/week) multiply calendar time by ~2.5. External waits (verification
reviews, other people's replies) are shown separately because effort doesn't shrink them. These are
judgment-based estimates, not measured — re-baseline after Week 1.

### Effort per item

| § | Item | Effort | Notes |
|---|---|---|---|
| 0 | AI decoupling (extract, stub/disable, remove, tests, docs) | 3–4 days | Brain service itself is a separate project — not estimated here |
| 1 | SonarCloud S5496 + S3649 | 30 min | You only — needs SonarCloud login |
| 1 | AVG exception, Gmail re-auth, doc warning | 1 hr | You + Claude |
| 1 | Stop 7-day expiry | 0.5 day (narrow to `drive.file`) **or** 1–4 wk wait (Google verification) | Narrowing is the fast path |
| 2 | react-router 6→7 | 1–2 days | 19 files; manual click-through needed |
| 2 | First-run friction (wizard / SMTP test / sample pipeline) | 3–4 days | Biggest adoption lever |
| 2 | Conditional / branching steps | 2–3 days | Touches runner + DAG engine — highest blast radius |
| 2 | One-click deploy | 1 day per platform | Railway first |
| 2 | Jinja undefined lint | 0.5 day | Optional |
| 2 | Streaming Excel/PDF/bulk_load | 3–5 days | Defer until a real large-file case |
| 2 | OpenAPI for 21 route files | ~0.5 day each, 8–10 days total | Do incrementally, worst-drift files first |
| 3 | Mocked unit tests (runner/dag/context) | 3–4 days | |
| 3 | Sentry | 0.5 day | |
| 3 | License audit + NOTICE | 0.5 day | |
| 3 | Service layer for remaining routes | 4–6 days | Mechanical, tests already exist |
| 3 | N+1 review of other list endpoints | 1 day | |
| 3 | Re-verify 2026-07-01 audit findings | 0.5–1 day | Do early — it may reveal real bugs |
| 3 | Confirm secrets-scan gate | 10 min | Passive, on next PR |
| 4 | Scorecard re-run, Code Climate badge | 1 hr each | |
| 4 | Cosign signing | 0.5 day | |
| 4 | Fuzzing (atheris target) | 1–2 days | OSS-Fuzz acceptance: weeks of waiting |
| 4 | CII Silver | 1 day | Blocked on having a co-maintainer |
| 4 | Code-Review deadlock / PR discipline | Open-ended | Needs another person; or drop the 8.0 target (15 min decision) |
| 5 | Re-run review + score table, screenshots | 1 day + 2 hrs | Screenshots done alongside demo GIF |
| 6 | Demo GIF + screenshot | 0.5–1 day | Blocks the rest of §6 |
| 6 | ProductHunt | 1–2 days prep | Launch must be a Tue/Wed |
| 6 | Reddit, awesome lists, LinkedIn | ~0.5 day total | Awesome-list PR review waits are external |
| 7 | External user / design partner | Weeks–months | Not buildable; outreach |
| 7 | Airflow/cron migration tooling | 2–4 weeks | |
| 7 | Plugin marketplace | 2–3 weeks | |
| 7 | Hosted tier | 1 hr to decide; 4+ weeks to build | Conflicts with stated non-goal |
| 7 | Roadmap reconciliation | 0.5 day | |

**Totals (full-time):** §1 ≈ 1–2 days · §2 ≈ 19–26 days · §3 ≈ 10–14 days · §4 ≈ 4–6 days (+ people-dependent) ·
§5 ≈ 1.5 days · §6 ≈ 3–4 days. **§0–§6 ≈ 9–11 weeks full-time, or ~5–6 months part-time.** §7 is not scheduled.

### Suggested schedule

| Week | Focus | Exit criteria |
|---|---|---|
| **1** | §0 AI decoupling (branch + tag first); §1 blockers | Suite green without AI code; Quality Gate green; Gmail sending |
| **2** | §3 re-verify old audit; §6 demo GIF + screenshot + README (recorded *after* the scrub) | GIF shows the post-scrub UI |
| **3** | Launch (copy rewritten without "local AI"): Reddit remainder, awesome lists, LinkedIn pin, ProductHunt scheduled; Scorecard re-run | GTM items done or scheduled |
| **4** | react-router 7; Sentry; license audit + NOTICE; cosign | `npm audit` clean; supply-chain badges up |
| **5–6** | First-run friction (§2), one-click deploy (Railway) | A new user sends a first email with no cloud-console steps |
| **7–8** | Conditional steps; Jinja lint decision | Gated step works in both engines, tested |
| **9–10** | Mocked unit tests; service layer; N+1 review | Core engine logic testable without Postgres |
| **11+** | OpenAPI rollout, streaming, fuzzing; fresh code review + score refresh | Review score re-baselined |
| **Ongoing** | §4 people items, §7 strategic | Revisit after first external user |

**Why this order:** launch assets first because the demo GIF gates every GTM item and nothing is visible
without it; cheap security/supply-chain wins before the large features; the highest-risk engine change
(conditional steps) only after the old audit findings are re-verified and a safety net of mocked tests is
planned right behind it (consider moving §3 unit tests ahead of conditional steps if you want that net first).

---

# Reference material

## Phase 5 detail — Go-To-Market copy (§6 reference)

*These do not block the GitHub release tag but should happen within the first week of release.*
*Tracking checkboxes consolidated in Phase 10 — the detail below is reference material (exact copy/hashtags/etc.) for when you get to each one.*

### 5.1 Demo Assets
- Record a 60–90 second screen recording (GIF or MP4):
  - Open dashboard → create a pipeline with a report + email step → run it → show Run History with logs
- Capture a high-quality static screenshot of the Dashboard for the README hero and LinkedIn Featured section
- Add the demo GIF to the README (below the tagline, above the feature list)

### 5.2 ProductHunt Launch
- Create a ProductHunt account / maker profile
- Draft the listing:
  - Name: **FlowForge**
  - Tagline: `SQL-to-Email pipeline orchestrator. No YAML. No Airflow complexity.`
  - Description: Explain the problem (50+ cron scripts), the solution, highlight Celery scaling + local AI
  - Gallery: dashboard screenshot + report designer + run history
- Schedule launch for a Tuesday or Wednesday (highest ProductHunt traffic)

### 5.3 Reddit Posts
- Post in **r/selfhosted**: "I built an open-source database pipeline orchestrator — SQL → Report → Email, with local AI. No YAML required."
- Post in **r/Python**: focus on the Flask + Celery + APScheduler architecture choices
- Post in **r/opensource**: general project introduction with demo GIF
- Cross-post to **r/dataengineering** focusing on the Oracle + PostgreSQL + MySQL support

### 5.4 Awesome Lists Submission
- Submit PR to [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) — category: "Automation"
- Submit PR to [awesome-python](https://github.com/vinta/awesome-python) — category: "Task Queues" or "Data Pipeline"

### 5.5 LinkedIn
- Write the launch post:
  - Hook: "Stop writing boilerplate Python scripts for DB automation..."
  - Highlight: Celery/Redis scaling, local AI (Ollama), full audit logging, multi-user roles
  - Tech stack: React + Flask + PostgreSQL + Celery
  - Link to GitHub repo
  - Attach: demo GIF or dashboard screenshot
- Add FlowForge to LinkedIn "Featured" section with dashboard screenshot and 2-sentence value description
- Tag: `#OpenSource`, `#Python`, `#LocalAI`, `#DataEngineering`, `#Productivity`

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Migrated to `python-oracledb` (thin mode, pure Python) |
| M365 requires Azure AD app registration | Step-by-step guide in `docs/microsoft365-oauth2-setup.md`; `flowforge setup microsoft365` wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in Settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
| SonarCloud flags security hotspots | Review each hotspot; most will be acknowledged false positives with justification comments |

---

## Accepted design tradeoffs (not planned)

*From Phase 12 — deliberate decisions, not bugs; kept so `docs/USE_CASE.md` and this file stay honest about the same constraints.*

- No true multi-tenant isolation beyond project-level workspace scoping (`ff_project_members`) —
  by design; see [`docs/threat-model.md`](threat-model.md#out-of-scope)
- Self-hosted only, no managed/cloud SaaS offering — explicit non-goal, see `CLAUDE.md` Non-Goals
- No Airflow DAG import — explicit non-goal, see `CLAUDE.md` Non-Goals
- FlowForge does not terminate TLS itself — deploy behind Nginx/ALB by design, see
  [`docs/deployment.md`](deployment.md)
- PDF reports require the optional `weasyprint` extra (`pip install flowforge[pdf]`) rather than
  shipping in the default install — keeps the base install light for the Excel/CSV/JSON-only case
