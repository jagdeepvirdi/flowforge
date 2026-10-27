# Brain Decoupling Plan — removing AI/LLM from FlowForge

*Written 2026-10-27. Status: **PLANNED — no code changed yet.** Tracker entry: [`TASKS.md`](TASKS.md) §0.
This document is the durable source of truth so the plan survives the session that wrote it.*

> **AMENDMENT 2026-10-27 (b) — supersedes parts of §3/§4 below.** The product direction is now Telecom Revenue
> Assurance with a "Muscle/Brain" split — see [`../ARCHITECTURE.md`](../ARCHITECTURE.md). Key change: the **UI calls
> Brain directly over HTTP**, so Core keeps **no `/ai/*` routes at all** (phase A3: delete `routes/ai.py` and its
> blueprint instead of leaving 503 shells; the frontend `aiQuery`/narrative calls move to a separate
> `lib/brainApi.ts` in Phase B). The attached/detached switch is a `brain: {enabled, url}` block in `/api/setup/status`
> (default **off**, including while loading/failed). `ai_analyze` stays a failing step shell only so saved pipelines
> still load. Add to A6: a **CI deny-list test** that fails if `flowforge/` imports an LLM SDK or `pyproject.toml`
> lists one. Add to Phase B: async evidence-job (Celery/thread, short timeouts, circuit breaker), Core-side
> anonymizer, `POST /api/brain/token` (asymmetric, audience-scoped), `brain_case_id` on runs/alerts. Everything else
> in this document (extraction spec, do-not-remove list, risks) still applies.

---

## 1. Decision

FlowForge returns to being a **deterministic data-pipeline / ETL / SQL orchestrator**. Every LLM capability moves
to a separate **FastAPI microservice, "Brain"** (separate repo, separate project).

**Product rule (decided 2026-10-27):** the small AI conveniences that remain visible in FlowForge — SQL
explain/optimize, run-failure diagnosis, anomaly narrative, data profile, AI chart suggestion, and the
`ai_analyze` step — are **dark by default and light up only when a Brain service is attached**
(`FLOWFORGE_BRAIN_URL` set and the service reachable). With no Brain: no AI buttons, no AI settings, no AI
network calls, no fake output. FlowForge contains **no LLM SDK, no prompts, no provider keys, and no Ollama
client**.

This resolves the earlier open question about stubs: we do **not** return hardcoded fake-AI JSON. Disabled
features are hidden by the UI and answered with `503 {"error": "brain_not_attached"}` by the API.

---

## 2. What exists today (verified 2026-10-27)

### Backend
| File | What it is |
|---|---|
| `flowforge/api/routes/ai.py` (344 lines) | 4 endpoints, each `@limiter.limit('20 per minute')` + `@require_auth`: `POST /ai/data-profile`, `/ai/chart-config`, `/ai/query` (task = `explain` \| `optimize` \| `diagnose`), `/ai/anomaly-narrative`. Prompt builders `_explain_prompt`, `_diagnose_prompt`, `_optimize_prompt`. Provider chain: Ollama → Claude (`claude-haiku-4-5-20251001`, hardcoded) → Gemini. Valid chart types `bar/line/area/pie/scatter`. |
| `flowforge/steps/ai_analyze.py` (222 lines) | The `ai_analyze` **pipeline step**: runs a SQL query, sends ≤100 rows (hard cap 500) to a provider (`ollama`/`claude`/`gemini`), stores the reply in `output_variable` (e.g. `{{ ai_summary }}`). Contains `_call_ollama`, `_call_claude`, `_call_gemini`, `_get_anthropic_client`, `_format_data`. |
| `flowforge/engine/loader.py:40` | Registers `'ai_analyze'` → `AiAnalyzeStep`. |
| `flowforge/api/app.py:217,240` | Imports and registers `ai_bp`. |
| `flowforge/api/routes/setup.py:70-81` | `GET /setup/status` returns the `ai` block (`enabled`, `ollama_url`, `model`, `claude.configured`, `gemini.configured/model`). |
| `flowforge/steps/base.py:38` | Comment on the `ai_analyze` output field; the `output_variables` mechanism itself is generic. |
| `flowforge/engine/context.py:92-93` | `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` in the template-secret blocklist. **Keep.** |
| `pyproject.toml:103-105` | `claude = ["anthropic>=0.25"]` extra — the **only** AI SDK. Ollama and Gemini are raw `urllib` calls. |
| `.env.example:257-277` | `FLOWFORGE_AI_ENABLED`, `OLLAMA_URL`, `OLLAMA_CHART_MODEL`, `OLLAMA_QUERY_MODEL`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GEMINI_QUERY_MODEL`. |
| Migrations `0013_ai_analyze_step` (+ `0001`, `0005`, `0011`, `0014`, `0019b`, `0019d`, `0025`, `0026` mention it in step-type constraints) | **Do not edit.** Historic Alembic migrations; editing breaks the chain. `0026` already relaxed the constraint. |

### Current gating (and why it must change)
- Server: `FLOWFORGE_AI_ENABLED` **defaults to `true`** (`ai.py:24`); a `before_request` hook returns 503 when false.
- Frontend: `setupStatus?.ai?.enabled ?? true` in `RunDetail.tsx:459` and `useReportConfigForm.ts:35` — **defaults to true**, so
  AI buttons show whenever the status call is pending or fails.
- New rule inverts both: default **off**, on only when Brain is attached.

### Frontend (~13 files)
`components/settings/AiOllamaCard.tsx` + Settings AI tab · `pages/RunDetail.tsx` (DiagnosisPanel, AnomalyRow narrative, "via Ollama" label, "Could not reach Ollama" messages) ·
`pages/ReportEdit.tsx` + `hooks/useReportPreviewTools.ts` + `hooks/useReportConfigForm.ts` (SQL explain/optimize buttons, data profile, "Visualize") ·
`components/report/ChartPreview.tsx` (**see §6 — do not delete**) · `lib/api.ts` (`aiQuery`, `getAnomalyNarrative`, data-profile/chart-config calls, `ai` status type) ·
`lib/types.ts` · `components/pipeline/stepMeta.ts:8` · `pages/PipelineEdit.tsx:38` · `__tests__/Settings.test.tsx` · `lib/generated/pipelines.ts` (string match only — check).

### Tests (~926 lines + edits)
`tests/test_ai.py` (488), `tests/test_ai_analyze.py` (438); references in `test_context.py`, `test_loader_unit.py`, `test_setup_extended.py`, `test_steps_extended.py`.

### Docs (~17 files)
`CLAUDE.md`, `README.md`, `ROADMAP.md`, `.env.example`, `docs/step-types.md`, `USE_CASE.md`, `getting-started.md`, `data-flow.md`, `testing.md`, `manual-testing-guide.md`, `INDEX.md`, `CODEBASE_REVIEW.md`, `GEMINI_REVIEW.md`, `SONAR_ISSUES.md`, `presentation-script.md`, `scenarios/health-monitoring.md` (+ `TASKS.md`/`TASKS_ARCHIVE.md` history, which stays as history).

---

## 3. Target design — "Brain attach" gate

### Configuration
| Variable | Meaning |
|---|---|
| `FLOWFORGE_BRAIN_URL` | Base URL of the Brain service. Empty/unset = no Brain = all AI features dark. |
| `FLOWFORGE_BRAIN_API_KEY` | Shared secret sent to Brain (add to the `context.py` secret blocklist). |
| *(removed)* | `FLOWFORGE_AI_ENABLED`, `OLLAMA_*`, `ANTHROPIC_API_KEY`, `GEMINI_*` — no longer read by FlowForge. Keep the two key names in the blocklist anyway. |

### New module `flowforge/brain.py` (small)
- `brain_enabled() -> bool` — **Phase A: always returns `False`** with `# TODO: Wire this to the new external Brain microservice API`.
  Phase B changes it to "URL configured and `/health` reachable (cached ~30 s)".
- `brain_unavailable_response()` — returns `503 {"error": "brain_not_attached", "message": "AI features require the Brain service. Set FLOWFORGE_BRAIN_URL."}`.

### Backend behavior after Phase A
| Surface | Behavior |
|---|---|
| `/ai/*` (4 endpoints) | Kept as thin shells: auth + rate limit retained, body replaced by `brain_unavailable_response()` + the TODO comment. No prompts, no provider calls. Phase B forwards to Brain. |
| `ai_analyze` step | Step type stays **registered** (so saved pipelines and run history still load), but `run()` returns `StepResult(success=False, error='ai_analyze requires the Brain service (FLOWFORGE_BRAIN_URL) — not attached')`. Honors the step's `on_error`. |
| `GET /setup/status` | `ai: {"enabled": brain_enabled(), "brain_url_configured": bool(url)}` — Ollama/Claude/Gemini fields removed. |
| Pipeline validation | Optional: warn when a pipeline contains an `ai_analyze` step and Brain is not attached. |

### Frontend behavior after Phase A
- Default `aiEnabled = false` everywhere (`?? false`); every AI button/panel renders only when `ai.enabled`.
- `AiOllamaCard` → replaced by a small **BrainCard** in Settings: "Brain: not attached" + one-paragraph explanation + docs link. (When attached, Phase B shows URL + status.)
- `ai_analyze` is **hidden from the "add step" picker** unless enabled, but `stepMeta.ts` keeps its badge so existing steps/history render.
- Remove "via Ollama" / "Could not reach Ollama" strings (provider-neutral wording: "Brain").

### Why not hardcoded stubs
The `ai_analyze` output feeds `{{ ai_summary }}` into emails, reports and notifications. A canned string would silently
ship fake analysis in a production pipeline. Hiding + failing loudly is the only safe behavior for an ETL tool.

---

## 4. Execution plan

**Rules:** do it on branch `scrub/brain-decoupling` in its own git worktree; tag `pre-brain-split` on the current
commit first; one commit per phase; never touch pipeline/engine/DB-query code beyond the lines listed. The working tree
currently has **uncommitted** auth/users changes (`flowforge/api/auth.py`, `routes/auth.py`, `password_reset.py`, `users.py`,
`db/models/auth.py`, `Login.tsx`, `Users.tsx`, `tests/test_users.py`, migration `0033`) — commit or stash those
separately **before** starting, so they never mix into the scrub.

Use `.venv\Scripts\python.exe` / `pip.exe` only; read `docs/credentials.local.md` for the test DB URL before running tests.

| Phase | Work | Verify |
|---|---|---|
| **A0 Prep** | Tag `pre-brain-split`; create worktree/branch; baseline: full pytest, `tsc --noEmit`, eslint, vitest, `vite build` — record counts (tests ≈ 2155 backend / 173 frontend at last report). | Baseline numbers saved in the PR description. |
| **A1 Extract** | Create `extracted_ai_logic.md` **before deleting anything** (spec in §5). | Checklist in §5 ticked; every function/prompt in `ai.py` + `ai_analyze.py` appears in the file. |
| **A2 Gate module** | Add `flowforge/brain.py` (`brain_enabled()` → False, `brain_unavailable_response()`); unit-test it. | New tests pass. |
| **A3 Backend** | Gut `routes/ai.py` to shells; gut `ai_analyze.py` to the failing step; update `setup.py` ai block; delete `_call_*`, prompts, `_get_anthropic_client`, provider chain, `urllib` Ollama code; keep blueprint/loader registrations. Add `FLOWFORGE_BRAIN_*` to the `context.py` blocklist. | `grep -rniE 'ollama|gemini|anthropic|generativelanguage' flowforge --include=*.py` returns only `context.py` blocklist names and historic migrations. App boots (`create_app()`). |
| **A4 Backend tests** | Delete `test_ai.py`/`test_ai_analyze.py`; replace with `tests/test_brain_gate.py` (endpoints → 503; `/setup/status` `ai.enabled == false`; `ai_analyze` step fails with the clear message and honors `on_error`; loader still resolves the type). Fix refs in the four other test files. | Full pytest green. Note coverage delta (see §7). |
| **A5 Frontend** | Per §2/§3: default-off gating, BrainCard, remove AI calls/types/strings, hide `ai_analyze` from picker, keep badge. Update `Settings.test.tsx`; add a test that AI buttons are absent when `ai.enabled=false` and when status fails. | `tsc --noEmit` 0 errors, eslint 0 errors, vitest green, `vite build` ok. Manual Playwright pass: login → Settings (no AI tab/card, BrainCard present) → Run Detail on a failed run (no "Explain" button) → Report editor (no AI buttons; preview still works) → Pipeline editor (no AI step option; existing `ai_analyze` step still renders). Zero console errors. |
| **A6 Dependencies & config** | Remove `claude` extra and its `all` mention from `pyproject.toml`; confirm `grep -rn "import anthropic"` empty; replace the `.env.example` AI block with the two `FLOWFORGE_BRAIN_*` vars (commented, "optional — attaches the Brain service"). Regenerate/verify `requirements.txt` has nothing AI. | `pip check`; fresh-venv install smoke test. |
| **A7 Docs & positioning** | Update every doc in §2; add a short `docs/brain.md` ("what Brain is, how to attach, contract status: not yet defined"); `CHANGELOG.md` breaking-change entry; rewrite GTM copy (TASKS §6) and review already-published posts. | `grep -rniE 'ollama|local ai|#LocalAI|gemini|anthropic' README.md CLAUDE.md docs/*.md .env.example` returns only intentional history (archive, changelog). |
| **A8 Ship** | Version decision (see §7), PR (not direct push), CI green incl. CodeQL/Sonar, then merge. | Master CI green. |
| **B (later)** | When Brain's API contract exists: implement `brain_enabled()` health check, forward `/ai/*` to Brain, implement `ai_analyze` call, BrainCard status, tests with a fake Brain (`responses`). Not scheduled here. | — |

**Effort:** A0–A8 ≈ 3–4 focused days. Phase B depends on Brain's contract and is a separate estimate.

**Rollback:** `git revert` the merge, or `git checkout pre-brain-split`. The extraction file means no logic is lost
even if the branch is abandoned.

---

## 5. `extracted_ai_logic.md` — required contents

Written **before any deletion**, at the repo root, in this order. Each section pastes the code/prompt **verbatim** in
fenced blocks; nothing paraphrased that Brain would need to reproduce behavior.

1. **Provider layer** — `_ollama_generate`, `_call_ollama`, `_call_claude`, `_call_gemini`, `_get_anthropic_client` (lazy singleton keyed by API key), `_fallback_candidates`, `_generate_text` (Ollama→Claude→Gemini fallback, timeouts: 30 s endpoints / 120 s step, temperature 0.1 endpoints / 0.2 step, `format: json` mode), model names and env defaults (`llama3.2:3b`, `claude-haiku-4-5-20251001`, `gemini-2.5-flash`).
2. **All prompts** verbatim: `_explain_prompt`, `_diagnose_prompt`, `_optimize_prompt`, the data-profile prompt, the chart-config prompt, the anomaly-narrative prompt, and the `ai_analyze` default prompt/format (`_format_data` pipe-table).
3. **Endpoint contracts**, one per route: URL, auth, rate limit (20/min), request JSON schema, validation rules (`_VALID_QUERY_TASKS`, `_VALID_CHART_TYPES`, size caps), response JSON shape, error codes/messages.
4. **`ai_analyze` step spec** — config schema (`connection_id`, `query`, `prompt`, `output_variable`, `provider`, `model`, `max_rows` default 100 / hard cap 500), Jinja rendering via `render_guarded(..., sink='ai_analyze query'|'ai_analyze prompt')`, how output lands in context, failure behavior.
5. **Frontend UX contract** — which screens call which endpoint, request payloads, how responses render, the exact error/empty strings, and the `ai.enabled` gating.
6. **Behavior specs from the tests** — a bullet list of what `test_ai.py` / `test_ai_analyze.py` assert (inputs → outputs, fallback order, error mapping), so Brain's own tests can be written from it.
7. **Env vars and security notes** — variables listed in §2; note that the secret blocklist and `render_guarded` exist because prompts interpolate user data.
8. **Provenance footer** — source commit hash (`pre-brain-split`) and date.

**Open decision — commit or not?** If Brain will be private/proprietary, add `extracted_ai_logic.md` to `.gitignore` or keep it on a
private branch/repo; this repo is public and git history keeps the old code regardless unless history is rewritten.

---

## 6. Do NOT remove (easy to over-scrub)

- **Anomaly detection** (`GET /runs/{id}/anomalies`, `getRunAnomalies`, `StepAnomaly` types, the "Anomaly Detected" panel) — statistical, not AI. Only the LLM *narrative* button is removed.
- **`components/report/ChartPreview.tsx`** — a Recharts renderer with `onConfigChange`; only the AI step that *suggests* a chart config (`handleVisualize` → `/ai/chart-config`) goes. Verify manual chart configuration still works. `StepTrendsPanel.tsx` mirrors its styles.
- **`ANTHROPIC_API_KEY` / `GEMINI_API_KEY` in `context.py`'s blocklist** — still a credential-leak guard if those env vars exist on a host.
- **Historic Alembic migrations** and the relaxed `step_type` constraint.
- **`output_variables` / generic context-injection mechanism** in `steps/base.py` — only the AI-specific comment changes.
- **`FLOWFORGE_DEVBRAIN_NOTIFY_URL` / `_notify_devbrain`** — see §7.1: unrelated to Brain.
- **Run history rows** for `ai_analyze` steps — keep the `stepMeta` badge so old runs display.

---

## 7. Things you need to know

1. **Name collision — "DevBrain" ≠ "Brain".** `FLOWFORGE_DEVBRAIN_NOTIFY_URL`, `engine/notifications.py:_notify_devbrain`, the DevBrain session hooks and
   `.env.example` lines 219-223 refer to your separate DevBrain notification tool. They stay untouched. Consider naming the new service
   something unambiguous in env vars (`FLOWFORGE_BRAIN_URL` is used here) and in docs.
2. **Defaults flip = behavior change.** Today AI is **on by default** (server env defaults `true`; frontend `?? true`). After this,
   anyone running Ollama who upgrades loses the AI features until Brain exists. Needs a breaking-change note. Version: the project is
   at 1.3.0; removing user-visible features suggests **v2.0.0** (or 1.4.0 with a loud BREAKING entry) — your call.
3. **Existing pipelines with `ai_analyze` steps will fail** at that step after the scrub (by design). Honor `on_error: continue` pipelines still finish. Check your own DB for saved `ai_analyze` steps before merging: `SELECT pipeline_id, name FROM ff_pipeline_steps WHERE step_type = 'ai_analyze';`.
4. **Data egress becomes a design question.** Today everything is local (Ollama). Brain will receive SQL, failure logs, and query result rows — i.e. customer data — over the network. The Brain contract needs auth, TLS, row/size caps, and redaction rules before Phase B. The `FLOWFORGE_BRAIN_URL` is admin-set; still validate the scheme and don't follow redirects blindly (SSRF hygiene).
5. **The Brain API contract does not exist yet.** Until it does, the AI features are dark; Phase B can't start. Defining the contract (endpoints, auth, timeouts, error shape, versioning) is the real gating item — and decides whether pipelines call Brain via the `ai_analyze` shell or a generic HTTP step.
6. **Marketing mismatch.** Published Reddit (r/Python, r/selfhosted) and LinkedIn posts, the README, `CLAUDE.md` cost table ("AI analysis (Ollama) $0 — local"), and planned ProductHunt copy advertise local AI. Rewrite before the launch push; the demo GIF must be recorded **after** this scrub. Do not edit already-published posts without deciding how.
7. **Test/coverage effect.** ~926 test lines are removed. If CI enforces a coverage threshold, check it before merging (new gate tests are small). The suite count will drop from ≈2155.
8. **Git history keeps the old code.** The extraction file is for rebuilding Brain, not for secrecy. If proprietary exposure matters, that needs a history rewrite, which is out of scope here.
9. **Sonar/Scorecard side effects:** none expected; `context.py` is untouched so the S5496 residual finding is unaffected. Removing `urllib`-based Ollama calls also removes `# nosec B310` suppressions — fine.
10. **Not verified yet:** I have read the gating code, signatures and file lists but have **not** read every prompt body or all frontend AI call sites in full — Phase A1 does that line-by-line, and may add items to this plan. Treat the file lists as a minimum.

---

## 8. Acceptance criteria (Phase A is done when…)

- [ ] `grep -rniE 'ollama|gemini|anthropic|openai|langchain|generativelanguage' flowforge frontend/src --include=*.py --include=*.ts --include=*.tsx` matches only: `context.py` blocklist names, historic migrations, and intentional TODO comments.
- [ ] `pip install .[all]` installs no AI SDK; `package.json` unchanged (no AI deps existed).
- [ ] With no `FLOWFORGE_BRAIN_URL`: no AI UI anywhere, `/ai/*` → 503 `brain_not_attached`, `/setup/status` → `ai.enabled=false`, `ai_analyze` step fails with the clear message.
- [ ] Core pipelines, DB queries, reports, email, scheduler, DAG engine: full backend suite green; frontend `tsc`/eslint/vitest/`vite build` green; manual Playwright pass clean (§4 A5).
- [ ] `extracted_ai_logic.md` exists with all §5 sections (and its commit/ignore decision is recorded).
- [ ] Docs, `.env.example`, `CHANGELOG.md` updated; GTM copy rewritten; version decision made.
- [ ] Merged via PR with CI green.
