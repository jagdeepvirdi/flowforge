# TASKS.md — FlowForge

*Open work only. Completed work lives in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) (newest-first; the
2026-10-27 entries hold the V2.0 audit, Phase 13 fixes, the SSRF/dependency fixes and the Dependabot triage).*
*Direction: [TELECOM_PIVOT_ROADMAP.md](TELECOM_PIVOT_ROADMAP.md) (with `[claude]` review comments) · architecture: [../ARCHITECTURE.md](../ARCHITECTURE.md) · AI removal plan: [BRAIN_DECOUPLING_PLAN.md](BRAIN_DECOUPLING_PLAN.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*
*Last reorganized: 2026-10-27 (second pass: re-ranked around the Telecom Revenue Assurance direction).*

---

## Where we are

| Release | Goal | Status |
|---|---|---|
| **v1.0** | Public GitHub release — stable, tested, `docker compose up` works | Shipped (tagged); **GTM partial** — see §D |
| **v2.0** | Production-hardening — scaling docs, metrics, audit UI, retention, dependency audit in CI | Code complete; V2.0 audit items all closed |
| **v2.x Compliance** | MFA, SSO, GDPR, encryption at rest | Shipped |
| **v3.0** | New connectors/providers, pipeline DAGs, plugin system, visual canvas | Shipped |
| **Telecom RA MVP** | Orphaned-subscription audit on a design partner's data; Muscle/Brain split | **Muscle side of the split done (v2.0.0, AI removed from Core); Brain not built; nothing telecom-specific shipped** — see §B–§C |

CI is green on `master` (backend, frontend, bandit, CodeQL, TruffleHog) after #129 (msgpack CVE-2026-114613 had turned it red on 2026-10-27). Core is at **v2.0.0** (2026-10-28): all AI/LLM code removed from Core (#130); the Brain service itself is not built.
Latest code-review score table: **7.8 / 10 (2026-05-25)** — stale; the 2026-07-24 architect/VC audit scored 6/10
(Security 3/10 at the time; all its Critical items are fixed, and the 2026-10-27 re-audit closed the remaining SSRF
and dependency gaps — Claude's estimate ≈ 6.5–7/10, a judgment, not a rubric). Re-score after §A and §B land.

**Open items: 56** — §A Now (7) · §B Telecom MVP track (12) · §C Gating decisions (5) · §D Go-to-market (8) · §E Product polish (5) · §F Engineering quality (7) · §G Dev environment (4) · §H Parked (8)

**Priority rule:** §A and §B come first; §C runs in parallel (the design partner is the longest lead time, so start it now);
§D keeps moving but is ordered behind the Brain scrub so nothing is published that the scrub makes untrue; §E–§G are
done opportunistically; §H is parked deliberately — do not pick from it without a reason.

Items tagged *(derived)* were not open checkboxes before: they come from "explicitly out of scope" notes
in archived completed items, promoted here so they aren't lost.

---

## A. Now — scrub, conditional execution, security leftovers *(≈ weeks 1–2)*

### A1. AI decoupling — remove all AI/LLM from Core *(decided 2026-10-27)*

**Full plan: [BRAIN_DECOUPLING_PLAN.md](BRAIN_DECOUPLING_PLAN.md)** (read its 2026-10-27 (b) amendment: no `/ai/*` shells — the UI calls Brain directly) and the target architecture in [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Read both before touching any AI code.
FlowForge becomes a deterministic ETL/SQL orchestrator; all LLM logic moves to a separate FastAPI "Brain" service.
**Rule:** the small AI features (SQL explain/optimize, failure diagnosis, anomaly narrative, data profile, chart suggestion,
`ai_analyze` step) stay in the UI code paths but are **dark unless a Brain is attached** (`FLOWFORGE_BRAIN_URL`). No fake/stub AI
output; disabled routes return `503 brain_not_attached`; the `ai_analyze` step fails with a clear message. **Do this before the §D
launch assets are recorded or published** (published posts advertise "local AI"). Effort ≈ 3–4 days. Runs in parallel with A2.

- [x] **A0 Prep** — tag `pre-brain-split`; branch/worktree `scrub/brain-decoupling`; record baseline test counts. *(The uncommitted auth/users work was committed in PR #123.)*
- [x] **A1 Extract** — write `extracted_ai_logic.md` (prompts, provider code, endpoint contracts, step spec, UX contract, test behavior) **before deleting anything**; decide commit vs gitignore (public repo). *Keep it as a record only: the legacy prompts are generic and will not drive the telecom RCA design.*
- [x] **A2 Gate module** — `flowforge/brain.py`: `brain_enabled()` (Phase A: always False, TODO comment) + `brain_unavailable_response()`.
- [x] **A3 Backend** — gut `routes/ai.py` to 503 shells, `ai_analyze` to a failing step, `setup.py` ai block → `{enabled, brain_url_configured}`; keep secret blocklist + historic migrations.
- [x] **A4 Backend tests** — replace `test_ai.py`/`test_ai_analyze.py` with `test_brain_gate.py`; fix 4 other test files; check coverage gate.
- [x] **A5 Frontend** *(done 2026-10-28)* — code shipped in #130; the manual pass is automated as `frontend/e2e/brain-absent.spec.ts` (Brain tab "Not attached", no `ai_analyze` in the picker, no Explain/Optimize in the report designer, `/api/ai/*` → 503); Run Detail and anomaly UI verified in source. Remaining browser checks live in `docs/manual-testing-guide.md` §14–15.
- [x] **A6 Dependencies & config** — add a CI deny-list test (no LLM SDK imports/deps in `flowforge/`); remove `claude` extra (`anthropic`) from `pyproject.toml`; replace `.env.example` AI block with `FLOWFORGE_BRAIN_URL`/`_API_KEY`.
- [x] **A7 Docs & positioning** *(done; historical review/briefing docs such as `CODEBASE_REVIEW.md`, `GEMINI_*.md` and `TELECOM_PIVOT_ROADMAP.md` intentionally left as records)* — CLAUDE.md, README, ARCHITECTURE, getting-started, step-types, data-flow, USE_CASE, manual-testing-guide, health-monitoring scenario, presentation-script, LAUNCH_STRATEGY, new `docs/brain.md`, CHANGELOG breaking entry. The published Reddit/LinkedIn posts are tracked in §D.
- [x] **A8 Ship** — v2.0.0 chosen; merged as #130 (CI green) and #129 (msgpack CVE bump) on 2026-10-28, both with admin override.
- [x] **Tag `v2.0.0` and cut the GitHub release** *(done 2026-10-28; live on GitHub and PyPI)* *(≈ 0.5 h)* — version is bumped and the changelog section exists, but no tag/release has been created.
- [ ] **Decide before A3:** check your DB for saved `ai_analyze` steps (they will fail after the scrub) — query in the plan §7.3.

### A2. Conditional / branching step execution *(≈ 1 week; moved up from product polish — needed for threshold alerting)*

- [x] **Conditional execution** *(done 2026-10-28: `run_if` on any step, both engines, UI + save-time validation, docs in step-types.md)* — gate a step on a prior step's result (e.g. "alert only if `mismatch_count > threshold`", "only send email if row count > 0"). Today only DAG failure propagation (`on_error: stop`/`continue`) exists. Touches the runner and the DAG engine, so it has the highest blast radius of anything on this list: add it to both the sequential/parallel-wave engine and the DAG engine, with tests in both. Basic threshold gating belongs in the MIT core (general-purpose); do not make it a proprietary feature. *(Phase 12)*

### A3. Security leftovers *(from the 2026-10-27 re-audit; the July Critical items and the SSRF/dependency gaps are fixed — see archive)*

- [ ] **react-router 6 → 7** *(≈ 1–2 days; 19 files in `frontend/src/`; manual click-through needed)* — `npm audit` flags `react-router` `6.0.0-7.17.0` for two moderate advisories: open redirect via backslash in `<Link>`/`useNavigate` ([GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6)) and constructor injection via `deserializeErrors()` in SSR hydration ([GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg)). 6.30.6 is still inside the advisory range, so only the v7 migration clears it. Read the [v7 upgrade guide](https://reactrouter.com/upgrading/v6), migrate, re-run `npm audit`. The vitest/@vitest/mocker moderate chain also remains (needs a vitest bump). Neither gates CI (`--audit-level=high`).
- [ ] **Resolve SonarCloud `pythonsecurity:S5496`** (issue key `AZ82Oyzt-6VzRaR01a4L`, `flowforge/engine/context.py`) as Won't Fix / False Positive in the SonarCloud UI — the rule flags the `render()` call-site pattern itself regardless of mitigations already shipped (`_jinja` is a `SandboxedEnvironment`, the blocklist covers credential names, rendered values are not reflected). **Requires SonarCloud login (not available to Claude).** *(~15 min, you)*
- [ ] **Resolve SonarCloud `pythonsecurity:S3649`** (SQL injection, issue key `AZ83ITEjNp5vzm4zlnz0`, `flowforge/steps/bulk_load.py:614` in `_dry_run_insert_rows()`) as Won't Fix / False Positive — both `target_table` and `columns` are validated with `validate_identifier()` (regex allowlist) by the caller **and** re-validated inside the function; SonarCloud doesn't recognise a project-local validator as a sanitizer boundary. **Requires SonarCloud login.** *(~15 min, you)*
- [ ] **Make bandit fail on unjustified `# nosec`** *(≈ 0.5 day)* — 40 findings are hidden by `# nosec` (`--ignore-nosec`: 7× B608 SQL string-building, rest low). The SQL ones in `data_load`, `db_query`, `bulk_load` were spot-checked (identifiers validated first); `urlopen` suppressions are down to 4 (three in the legacy AI code being removed in A1, one DevBrain notify hook). Require a reason comment so this can't recur silently.
- [ ] **Local credential hygiene + one-time full-history secrets scan** *(≈ 0.5 day)* — a dev login is stored in plaintext in the assistant memory index; `docs/credentials.local.md` is correctly gitignored and untracked. Rotate/remove the stored login if it was ever reused, and run TruffleHog over **full git history** once (the CI gate is `--only-verified`).
- [ ] **Re-verify the 2026-07-01 audit findings with regression tests** *(≈ 0.5–1 day; do early)* — memory records a verified SQL injection in `data_load.py`, a secrets leak and an SSRF from that audit; the code looks fixed, but confirm each has a regression test rather than assuming.

---

## B. Telecom RA MVP track *(≈ weeks 3–11, one developer full-time; estimates are unvalidated)*

**First proof-of-concept: orphaned subscriptions** (HLR/HSS vs. billing vs. CRM), audited **in place** in the operator's
databases; FlowForge schedules and monitors the SQL and collects aggregates (no terabyte ingestion; raw-file streaming
stays deferred — §E). Sequence: §A1 ∥ §A2 → reconciliation → tokenization → audit template + benchmark → compliance
evidence → Brain scaffold (last; it only adds value once detection is trustworthy). Reasoning, and the points where
Claude disagrees with the roadmap, are in the roadmap document. Design-partner discovery (§C) runs throughout.

- [ ] **Reconciliation step** *(≈ 1–2 weeks; the missing telecom primitive)* — compare keyed aggregates or key sets across **two connections** with tolerances and a capped sample of offending keys. A single `db_query` cannot join CRM, billing and HLR because they live in different systems, and `data_load` reads whole files into memory, so staging a full subscriber base is not safe. Define "orphaned" precisely first (active-unbilled, billed-unprovisioned, status mismatch, in-flight provisioning windows). Uses conditional execution (§A2) for threshold alerting.
- [ ] **Synthetic telecom dataset generator** *(≈ 2–3 days)* — seed CRM / billing / HLR tables with a controllable fraction of planted orphans, so the demo, the benchmark and the tests don't wait on a partner's data.
- [ ] **PII tokenization/masking step** *(≈ 1 week)* — keyed HMAC with a per-deployment secret, **or** tokenization with a local lookup table (so Core can map findings back to subscribers). A plain/shared-salt hash of MSISDN/IMSI is brute-forceable and must not be called "irreversible". Also scrub free-text fields and cap the payload. Must exist and be reviewed before any data is sent to a Brain.
- [ ] **Orphaned-subscription audit template** *(≈ 1 week)* — scheduled pipeline built from the reconciliation step, with the synthetic dataset as the demo; run end to end on the partner's data when available. This is the PoC evidence.
- [ ] **Volume benchmark** *(≈ 2–3 days)* — run the reconciliation on a realistic multi-million-row table on PostgreSQL **and Oracle** (telco billing/mediation commonly runs on Oracle; confirm that path at scale, not just that it works). Publish real numbers; until then docs say "designed for", not "optimized for extreme volume".
- [ ] **Verify audit-log immutability** *(≈ 0.5 day)* — the roadmap lists "immutable audit logs" as built. It is append-only in application code only; confirm whether the DB blocks UPDATE/DELETE (the retention job deletes old rows) and add revoked privileges / trigger / hash chain if not. Until then do not use the word "immutable" in docs or sales material.
- [ ] **Editor trust boundary controls** *(by design today; a prerequisite for the telecom pitch)* — users with the `editor` role can author arbitrary SQL (`db_query`, `db_procedure`, report SQL) against every connected database and arbitrary shell commands over SSH (`ssh_command`); `docs/threat-model.md` documents this. Decide and implement: read-only DB accounts per connection, per-connection allowlists, an approval/review step for SQL and SSH changes, and an `author`/`approver` role split.
- [ ] **Compliance-floor evidence** *(≈ 1–2 weeks, parallelizable)* — data-flow diagram (what leaves the network, over which path), retention and data-residency statement, key-management description, pen-test plan. A telco security review asks for these before it looks at features.
- [ ] **Signed releases + SBOM** *(≈ 1 day)* — add a cosign step to `release.yml` (`cosign sign-blob` on the wheel, attach `.sig`/`.pem`) and publish an SBOM; telco security reviews ask for both.
- [ ] **On-premises install and upgrade docs** *(≈ 2–3 days)* — air-gapped install (offline wheel/image bundle), network requirements (including Core→Brain egress and UI→Brain reachability), upgrade/rollback, backup and restore. A Kubernetes/Helm option once the install is documented. Replaces "one-click cloud deploy" as the deployment priority.
- [ ] **Brain API contract, service credential and token endpoint** *(blocked on a design partner's requirements)* — freeze the contract in `ARCHITECTURE.md` §6.3 (auth, TLS, size caps, redaction, errors, versioning); Core→Brain service credential; `POST /api/brain/token` (short-lived, audience-scoped, asymmetrically signed — not the shared HS256 secret); `brain_enabled()` health check and async forwarding with circuit breaker. Not scheduled.
- [ ] **Scaffold `flowforge-brain`** *(≈ 2–3 weeks; last)* — separate repo: FastAPI, model-agnostic provider interface (Vertex AI Gemini and a customer-hosted open-weight option; the latter needs an evaluation set before it is promised to anyone), structured-JSON RCA, async `202 + case_id` contract. Not started.

---

## C. Gating decisions *(run in parallel; none is buildable by Claude alone)*

- [ ] **Find one design partner** *(longest lead time — weeks to months)* — ideally an RA analyst at one operator, with a sample schema for CRM, billing and HLR/HSS. The PoC and the Brain both depend on this; zero external users exist today, so SSO/SAML/MFA/GDPR tooling currently serves no one but the author. Do not add more enterprise-checkbox features before this.
- [ ] **Decide repo naming and the licensing/delivery model** — this repo is `flowforge`; the roadmap says `flowforge-core`. An MIT core plus a proprietary Telecom RA Pack + Brain needs a delivery mechanism (private repo / package index) and a contributor policy (CLA); the MIT core also means anyone can build the pack, so the moat is audit templates proven on real data and the partner relationship. Hold until a partner has seen reconciliation output.
- [ ] **Decide the Brain network path for telco deployments** — a cloud Brain requires operator browsers and Core to reach it, which many telco networks forbid. Proxy UI→Brain traffic through Core (contradicts the direct-UI decision in `ARCHITECTURE.md`) or require direct reachability; also decide the on-premises open-weight mode. "Air-gapped" is not an accurate description of Core's relationship to the Brain; use "no LLM code or keys in Core, only sanitized evidence leaves".
- [ ] **Decide who runs the Brain (hosted tier)** — running it for customers is a hosted tier and conflicts with the stated "No cloud SaaS" non-goal (`CLAUDE.md`; "Self-hosted only" below). If operators run it themselves there is no conflict. Decide explicitly before any hosted work.
- [ ] **Reconcile positioning and roadmap documents** — `ROADMAP.md`, `CLAUDE.md` ("Target users" still says solo developers/small teams), `README.md` and this file have disagreed before about what is shipped vs. deferred and who the product is for; do one pass so all tell the same story, and add the telecom roadmap to the picture.

---

## D. Go-to-market *(keep moving — ordered behind the Brain scrub)*

*Detail/copy for each item is in the reference section at the bottom. Copy that advertises "local AI" is wrong after the scrub; the demo GIF must show the post-scrub UI. Positioning tension: the existing launch material targets solo developers/small teams while the product direction is telecom — settle the headline in §C ("Reconcile positioning") before spending ProductHunt's one launch.*

- [ ] **Correct the already-published posts** *(do first, right after A1 ships)* — the 2026-07-08 Reddit (r/Python, r/selfhosted) and LinkedIn launch posts advertise "local AI"; edit or add a clarifying comment so they match the product.
- [ ] **Rewrite GTM copy and the README hero** without "local AI" and with the agreed positioning (part of A7).
- [ ] **Record a 60–90s demo GIF/MP4** (dashboard → create pipeline with report+email step → run → Run History) and add it to the README *(5.1 — blocks the rest; record after A1)*. Add the telecom demo (synthetic orphans → reconciliation → alert) once §B has it.
- [ ] **High-quality Dashboard screenshot** for the README hero / LinkedIn Featured *(5.1)*; this also covers the "update pre-multi-user screenshots" docs item.
- [ ] **Reddit** — r/Python and r/selfhosted posted 2026-07-08; r/opensource and the r/dataengineering cross-post still pending *(5.3)*.
- [ ] **Awesome lists** — PRs to awesome-selfhosted ("Automation") and awesome-python ("Task Queues"/"Data Pipeline") *(5.4)*. Review waits are external.
- [ ] **LinkedIn** — launch post published 2026-07-08; confirm it's pinned to Featured and carries the suggested hashtags *(5.5)*.
- [ ] **ProductHunt** — maker profile, listing (name/tagline/description/gallery), schedule a Tue/Wed launch *(5.2)*. **Last**: needs the final positioning and the demo assets.

---

## E. Product polish — generic product

*Useful, but secondary to §A–§B. Pick up opportunistically.*

- [ ] **Close the "no YAML required" first-run gap** *(≈ 3–4 days; the biggest hobbyist-adoption lever)* — a first real pipeline with email needs 5+ manual steps in Google Cloud Console or Azure AD before the no-code promise is true end-to-end. Candidates: a guided first-run wizard, a zero-config "send me a test email" via plain SMTP, a sample pipeline that needs no external account.
- [ ] **One-click deploy** (Railway/Render/Fly.io) *(≈ 1 day per platform)* — lowers hobbyist adoption friction; irrelevant to telco on-premises installs (see the on-prem docs in §B).
- [ ] **Decide Jinja undefined-variable behavior in DAG-mode pipelines** *(≈ 0.5 day; optional)* — a typo'd `{{ steps.X.* }}` silently renders blank. Keep Jinja's default `Undefined` or add a DAG-build-time lint. *(Phase 14.2 M2 stretch.)*
- [ ] **Stream Excel/PDF/JSON reports and `bulk_load`/`data_load` source files** *(derived; ≈ 3–5 days; deferred)* — only CSV streams end-to-end today. The telecom plan audits in place and does not ingest raw volume, so do this only when a real large-file case appears. Excel needs `openpyxl` `write_only=True`, which interacts with the shipped column-formatting feature (`docs/manual-testing-guide.md` §36); footer-row stripping needs a bounded sliding-window buffer across 3 load paths (Python fallback, Postgres COPY, SQL*Loader).
- [ ] **Extend OpenAPI-generated frontend types to the other 21 route files** *(derived; ≈ 0.5 day each, 8–10 days total)* — only `pipelines.py` + `runs.py` are generated; `connections`, `reports`, `emails`, `users`, `steps`, … are hand-typed in `types.ts`/`api.ts`, which is where drift bugs hide. Do incrementally, worst-drift files first.

---

## F. Engineering quality

- [ ] **True unit tests with mocking** for `engine/runner.py`, `engine/dag.py`, `engine/context.py` *(≈ 3–4 days)* — the suite is ~2,200 tests but 100% integration-style against a real Postgres with zero `@patch`/`MagicMock` in the files checked; safe for refactors but slow, and can't isolate business logic. **Consider doing this right before or alongside §A2** — conditional execution touches the runner and DAG engine, and this is the safety net.
- [ ] **Production error tracking** (Sentry or equivalent) *(≈ 0.5 day)* — logging is solid (113 call sites) but there is no error-tracking SDK anywhere.
- [ ] **Dependency/license audit in CI** (e.g. `pip-licenses`) plus a `NOTICE` file *(≈ 0.5 day)* — the MIT-compatibility check was a one-time manual grep. Do before any relicensing/commercial conversation (§C).
- [ ] **Extend the service/repository layer beyond `pipelines.py`** *(derived; ≈ 4–6 days)* — `runs.py`, `reports.py`, `connections.py`, etc. still hold business logic inline in route bodies.
- [ ] **Extend the N+1 review to other list endpoints** *(≈ 1 day)* — PERF-01 fixed `/api/pipelines` only; `/runs`, `/reports`, `/emails` list serializers weren't audited.
- [ ] **Dependabot hygiene** *(≈ 0.5 day)* — the pip group keeps bundling SQLAlchemy 2.1 and ruff 0.17 with patch bumps. Configure ignore rules for those majors and a weekly lock refresh so the audit gates don't silently rot again. SQLAlchemy 2.1 and ruff 0.16+ each need their own decision.
- [ ] **Refresh the review score table** *(≈ 1 day)* — re-run the codebase review and update `CODEBASE_REVIEW.md` after §A–§B.

---

## G. Dev environment *(local only — does not affect the product)*

*Gmail sending is broken on the author's machine. SMTP is fixed.*

- [ ] **AVG Web Shield is intercepting `oauth2.googleapis.com`** — `SSLCertVerificationError: unable to get local issuer certificate`. Fix: AVG → Settings → Protection → Web & Email → disable **Web Shield** or add a domain exception for `googleapis.com`. (The same interception breaks host `pip-audit`.) *(~1 hr)*
- [ ] **Re-authorize Gmail — refresh token expired** — `RefreshError: invalid_grant`. The OAuth consent screen is in **Testing** status, where refresh tokens hard-expire after 7 days. Re-run Step 5 in `docs/gmail-oauth2-setup.md`, then update the "Personal Gmail" provider in **Connections → Email Providers**.
- [ ] **Stop it recurring every ~7 days** — publish the consent screen to "In production". Caveat: the app requests the full `drive` scope (Google-*restricted*, needs a verification review). Either go through verification (1–4 weeks) or narrow to `drive.file` (not restricted; ≈ 0.5 day plus re-consent) if full-Drive access isn't required.
- [ ] **Doc gap**: `docs/gmail-oauth2-setup.md` "Keeping the App in Testing vs Publishing" (line ~158) says Testing mode is fine "indefinitely" but omits the 7-day refresh-token expiry — add a warning.

---

## H. Parked *(deliberately not now — revisit after a design partner or when §A–§B are done)*

*Badge and speculative work. None of it helps win a first partner or ship the MVP.*

- [ ] **OpenSSF Scorecard: re-run and Code-Review deadlock** — Code-Review is 0/10 and structurally stuck for a solo maintainer (GitHub blocks self-approval; admin-override merges count as unreviewed). Recruit a co-maintainer/approver or explicitly drop the ≥ 8.0 target. Re-run Scorecard once to confirm Pinned-Dependencies improved after the hash-pinning.
- [ ] **PR discipline** — never push directly to `master`; open a PR. Self-approval is blocked, so use a second account/collaborator or prefer bot-authored PRs.
- [ ] **CII Silver** — needs a co-maintainer (`bus_factor`), DCO sign-off in the PR template, the Silver questionnaire at bestpractices.dev, and the README badge URL.
- [ ] **Fuzzing** — register with [OSS-Fuzz](https://google.github.io/oss-fuzz/getting-started/accepting-new-projects/) or add an `atheris` target + `project.yaml`.
- [ ] **Code Climate maintainability badge** — add to the README badge row if grade is A or B (explicitly optional).
- [ ] **Airflow/cron migration tooling** *(2–4 weeks)* — nothing exists beyond FlowForge's own YAML export/import; a plausible differentiator for the generic product, not for telecom RA.
- [ ] **Plugin marketplace/discovery layer** *(2–3 weeks)* on the existing plugin system (`docs/plugins.md`) — the load mechanism exists; no registry/discovery UX.
- [ ] **Managed/hosted tier build** *(4+ weeks)* — blocked on the §C decision.

*Removed as obsolete or done: "ensure ≥ 1 commit/week" (window passed); "push the dependency fixes and triage Dependabot PRs" (done — PR #123 and the Dependabot triage, see archive); "confirm the blocking secrets-scan gate" (TruffleHog ran and passed on the merged PRs); "run the remaining security checks" (full backend suite 2,195 passed, `flowforge-db` on port 5434 is the test DB).*

---

## Timeline & effort *(estimates, rebuilt 2026-10-27 for the telecom direction)*

**Assumptions:** one developer working with Claude doing most of the code; focused working days (~6 productive hrs).
Part-time (~15 hrs/week): multiply calendar time by ~2.5. External waits (partner replies, reviews, awesome-list PRs)
are shown separately because effort doesn't shrink them. These are judgment-based, not measured — re-baseline after Week 2.

| Week | Focus | Exit criteria |
|---|---|---|
| **1** | §A1 Brain scrub (branch + tag first); SonarCloud ×2 (you, 30 min); nosec policy; full-history secrets scan; **start design-partner outreach** | Suite green without AI code; CI deny-list in place; Quality Gate green |
| **2** | §A2 conditional execution (consider the mocked runner/dag tests first); §D wave 1: correct published posts, README rewrite, demo GIF + screenshot, Reddit remainder, LinkedIn pin | Gated step works in both engines, tested; README and posts no longer say "local AI" |
| **3–4** | §B reconciliation step; synthetic dataset generator; react-router 7 (1–2 days, in a gap) | Two-connection reconcile with tolerances and capped sample; `npm audit` clean |
| **5** | §B PII tokenization step | Keyed HMAC / tokenization with local lookup, reviewed |
| **6** | §B orphaned-subscription audit template; volume benchmark (PostgreSQL + Oracle) | End-to-end demo on synthetic data; real benchmark numbers |
| **7–8** | §B audit-log immutability; editor-boundary controls; compliance evidence; cosign + SBOM; on-prem install docs; awesome-list PRs | Data-flow diagram and install docs exist; "immutable" claim verified or removed |
| **9** | §D telecom demo asset; ProductHunt prep (only if positioning settled in §C) | Demo shows the telecom flow |
| **10–12** | §B Brain contract + scaffold `flowforge-brain` (only once a partner exists or the PoC is validated) | Async RCA over tokenized evidence, Core fully functional with Brain absent |
| **Ongoing** | §C design partner, licensing, network path; §E/§F opportunistically; §H parked | Revisit after the first partner has seen reconciliation output |

**Totals (full-time, to Brain scaffold):** ≈ 10–12 weeks, or ~6–7 months part-time. §E and §F add roughly 3–4 weeks if all done.
The design partner is the real critical path: without one, weeks 10–12 (Brain) should wait.

**Why this order:** the scrub is cheap, makes the positioning true and unblocks honest GTM copy; conditional execution is the
one engine change every telecom use case needs, so it runs alongside the scrub rather than after it; the reconciliation
step is the missing primitive and tokenization must be reviewed before any data can reach a Brain; the Brain comes last
because it only adds value once the detection layer produces trustworthy findings.

---

# Reference material

## Phase 5 detail — Go-To-Market copy (§D reference)

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
