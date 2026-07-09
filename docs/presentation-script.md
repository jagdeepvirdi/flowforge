# FlowForge — Presentation & Demo Script

This is **not** the QA checklist. See [`manual-testing-guide.md`](manual-testing-guide.md) for
exhaustive feature verification before a release. This document is optimized for narrative
flow and audience engagement — it deliberately skips anything that isn't visually compelling
or doesn't reinforce the core pitch, even if it's a real, tested feature.

Use this for: the README/social demo GIF, live investor or stakeholder calls, conference/meetup
demos, and ProductHunt launch day.

---

## The pitch, in one breath

> "Teams automate reporting with 50 brittle cron scripts nobody wants to touch. FlowForge
> replaces that with a web UI: point-and-click pipelines that pull from your database, build a
> report, and email or Slack it out — with local AI for summaries, at zero marginal cost, and no
> YAML or Airflow complexity."

Memorize the shape of this, not the exact words: **pain (cron scripts) → solution (UI-driven
pipelines) → proof point (AI, $0 cost) → no-complexity promise (no YAML/Airflow)**.

---

## Format A — 60–90s Hero Demo (recorded GIF/MP4)

This is the asset referenced in `docs/TASKS.md` Phase 10 (Go-To-Market 5.1) — README hero,
LinkedIn Featured, ProductHunt gallery. Record at 1280×800 or higher, no narration needed (most
viewers watch muted), but keep the on-screen action self-explanatory.

**Pre-recording checklist**
- [ ] Seed data ready: a DB connection already exists and is named something readable (e.g. "Production DB"), so you don't type credentials on camera
- [ ] Browser zoom at 100%, window sized to avoid horizontal scroll
- [ ] Dashboard has at least 2–3 prior successful runs so it doesn't look empty
- [ ] Close the Help panel and any "Got it, dismiss" banners before recording
- [ ] Clear browser console (no red errors visible if you screen-record dev tools by accident)

**Shot list (timestamped beats)**

| Time | Screen | Action |
|---|---|---|
| 0:00–0:08 | Dashboard | Land on Dashboard — pipeline cards with status badges (Success/Running), stats row (runs today, success rate) visible |
| 0:08–0:20 | Pipelines → New Pipeline | Click **New Pipeline**, type a name ("Monthly Revenue Report"), set a schedule via the visual Cron Builder (pick "Daily" so the UI shows the plain-English + next-run-times preview — more visual than typing raw cron) |
| 0:20–0:40 | Pipeline Builder | Click **+ db query**, pick the connection, paste a short SQL query. Click **+ report**, pick a report config. Click **+ email**, pick an email config — use the quick-attach chip to attach the report step's output in one click (visually shows the "no manual Jinja2" story) |
| 0:40–0:50 | Pipeline Builder | Click **Save**, then **Run Now** on the pipeline card |
| 0:50–1:10 | Run History | Show the run appear with a pulsing "Running" badge, then flip to "Success" — expand the step timeline to show each step's duration and row count |
| 1:10–1:20 | Run Detail | Show the email step's log line (recipients, subject) as the closing beat — proof the whole thing actually sent |

**Caption/description text (paste under the GIF in the README and ProductHunt gallery)**
> Configure a full SQL → Report → Email pipeline entirely from the browser. No YAML, no Airflow
> DAGs — just point at your database and go.

---

## Format B — 5–8 min Live Walkthrough (investor calls, conference demos, stakeholder review)

Live demos get questions — leave room to pause and answer without losing the thread. Each
section below is a self-contained beat you can skip if time runs short; do them in order.

### 1. Open on the Dashboard (30s)
Talking point: *"This is what a team sees every morning — every pipeline's last run, next
scheduled run, and a Run Now button. No log-diving required."*
Point out: status badges, the live stats row, the pulse animation on any currently-running
pipeline (trigger one beforehand if nothing is running naturally).

### 2. Build a pipeline live (2 min)
Don't build from scratch under time pressure — clone an existing one (**Pipelines → Clone**) and
edit it, or have a half-built one ready to finish. Narrate as you go:
- *"Every step type — database call, report, email, Slack notification — is a form, not code."*
- Show the **step type registry** (the row of `+ db_query`, `+ report`, `+ email`, `+ notification`
  buttons) — *"and this list is extensible — plugin step types show up here too, side by side with
  the built-ins."*
- Show the quick-attach chip in the email step (auto-fills `{{ steps.report.output_path }}`) —
  *"the UI writes the Jinja2 for you."*

### 3. Differentiators tour (2–3 min) — pick 2–3 based on the audience
Don't do all of these — read the room and pick what lands:

- **Multi-database, one interface**: open **Connections** — show PostgreSQL, Oracle, Snowflake,
  BigQuery side by side. *"Same pipeline engine, any data source — including warehouses, not
  just OLTP databases."*
- **Local AI, zero marginal cost**: in Report Designer, click **Visualize** or **Explain** on a
  query — *"this calls a local Ollama model, not an API — so AI features don't show up on
  anyone's cloud bill."*
- **Smart attachments**: in an Email config, point out the attachment-size threshold — *"large
  reports auto-upload to Drive/OneDrive and the email gets a link instead — nobody's inbox chokes
  on a 40MB spreadsheet."*
- **Enterprise-ready, still self-hosted**: Settings → show MFA enrollment QR flow, or Login page
  SSO buttons — *"MFA, SSO, SAML, full audit logging — the compliance checkboxes are there, but
  it's still one Docker container you run yourself."*
- **Notification fan-out**: a Notification step config — *"Slack, Teams, Telegram — same pipeline,
  pick your channel."*

### 4. Run it and show the receipts (1 min)
Trigger a run, flip to Run History mid-run so the audience sees the pulsing "Running" state
update live, then open Run Detail — step timeline, durations, row counts, and (if relevant) the
Audit Log entry for the run.

### 5. Close (30s)
Talking point: *"Free to run — Postgres, Redis, the app container. AI is local by default. Pay
only if you opt into Claude (or use Gemini's free tier) for analysis, or if you're pushing files
to S3/Drive at scale."*
Land on the GitHub URL / call to action.

---

## Format C — 2-minute safety-net version (no screen share, bad wifi, or a live outage)

Talking points only, no live app required — use this if the demo environment breaks mid-call:

1. The problem: teams run reporting automation as brittle, undocumented cron scripts.
2. The fix: a web UI over a pipeline engine — DB call → report → email/Slack, configured, not coded.
3. Three proof points: (a) database-agnostic (Postgres/Oracle/MySQL/Snowflake/BigQuery/Redshift),
   (b) local AI for summaries and chart suggestions — no per-seat AI cost, (c) enterprise auth
   (MFA/SSO/SAML) and full audit logging, but still self-hosted and free.
4. Point to the README demo GIF or screenshots as the visual proof, and offer a follow-up live demo.

---

## Pre-demo checklist (do this the night before, not 5 minutes before)

- [ ] `docker compose up` from a clean pull — confirm nothing broke since the last demo
- [ ] At least one pipeline has 3+ successful runs in history (empty Run History looks unfinished)
- [ ] At least one connection per major DB type you plan to show is pre-configured and passes **Test**
- [ ] Ollama is running locally if showing AI features (`ollama serve`) — test the button once beforehand
- [ ] Log in as a non-admin test user once if you plan to show role-based restrictions, so you're not fumbling credentials live
- [ ] Close any browser tabs with unrelated errors, other client work, or sensitive data
- [ ] Mute Slack/Teams/Telegram notification volume if you're about to trigger a real webhook send live — a notification popping up mid-sentence is a distraction, not a feature demo

## Common failure modes and how to route around them live

| If this happens | Do this |
|---|---|
| A live query is slow / times out | Have a pre-run pipeline's Run History ready as a fallback — narrate over it instead of waiting |
| Ollama isn't responding | If Claude/Gemini is configured it silently falls back; otherwise the AI buttons degrade gracefully ("AI unavailable") — acknowledge it in one sentence and move on, don't debug live |
| An email doesn't arrive in time | Show the step log's "sent" confirmation instead of waiting for the inbox — narrate that delivery is provider-side |
| Someone asks a QA-level "what happens if X fails" question | Answer at a high level, then say "happy to show that in detail after" rather than derailing into an error-handling deep dive |
