# Brain — optional AI diagnostics

FlowForge is split into two parts (see [`ARCHITECTURE.md`](../ARCHITECTURE.md)):

- **Core (this repository)** — deterministic ETL, SQL audits, scheduling, alerting. It contains **no** LLM SDKs,
  prompts, model names or AI-provider keys. A CI test (`tests/test_no_llm_in_core.py`) fails if one is added.
- **Brain (`flowforge-brain`)** — a separate FastAPI service that does non-deterministic root-cause analysis over
  anonymized evidence. It owns the prompts, model choice, provider keys and the diagnosis store.

## Current status

**Not shipped.** The Brain service and the Core→Brain contract do not exist yet, so `brain_enabled()` always returns
`False` and every AI surface is dark, whatever you set in the environment. Tracking: `docs/TASKS.md` §B
("Brain API contract…", "Scaffold `flowforge-brain`").

| Surface | Behaviour today |
|---|---|
| AI UI (explain/optimize SQL, failure diagnosis, chart suggestion, profiling) | Not rendered |
| `/api/ai/*` routes | `503 brain_not_attached` |
| `ai_analyze` step | Fails with "requires the Brain service"; hidden from the step picker. Saved pipelines still load. |
| Settings → Brain card | Shows attached / not attached and whether `FLOWFORGE_BRAIN_URL` is set |
| Run History anomaly alerts | **Unchanged** — statistical (>2σ), part of Core, no Brain needed |

Core is fully functional without a Brain; Brain output is advisory and never changes pipelines automatically.

## Configuration (reserved)

```env
FLOWFORGE_BRAIN_URL=          # base URL of the Brain service; unset = no AI anywhere
FLOWFORGE_BRAIN_API_KEY=      # service credential Core presents to the Brain (not a model-provider key)
```

`FLOWFORGE_BRAIN_API_KEY` is on the template-variable secret blocklist, like the legacy provider keys.

## Design rules for future Brain integration

1. Core→Brain traffic is asynchronous and off the critical path: short timeouts, bounded retries, circuit breaker.
   API workers, the scheduler, pipeline threads and Celery workers never wait on the Brain.
2. Evidence is anonymized and minimized in Core before it leaves: grouped signatures, counts and a capped sample,
   never raw row dumps.
3. The UI talks to the Brain directly over HTTP; with no Brain attached no AI UI renders.

## Upgrading from a version with built-in AI

- The `claude` extra (`anthropic`) is gone, and `OLLAMA_*`, `ANTHROPIC_API_KEY`, `GEMINI_*` and
  `FLOWFORGE_AI_ENABLED` are no longer read. Remove them from your environment.
- Any saved `ai_analyze` step now fails when run. Set `on_error: continue` on it or delete it.
- Downstream templates that use `{{ ai_summary }}` will render empty.
