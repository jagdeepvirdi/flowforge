# Writing a Plugin Step Type

FlowForge ships with a fixed set of built-in step types (`db_procedure`,
`db_query`, `report`, `email`, `ssh_command`, `notification`, ...). For
anything else — a custom integration, an internal-only step — you can drop
a Python file into a plugin directory instead of forking FlowForge.

---

## How it works

At startup (and once per process, lazily, the first time a pipeline is
loaded), FlowForge scans `FLOWFORGE_PLUGIN_DIR` (default `./plugins`) for
`*.py` files. Any file not starting with `_` is imported, and every class
in it that subclasses `flowforge.steps.base.BaseStep` and sets a `step_type`
is registered under that type string.

If the directory doesn't exist, plugin loading is a no-op — nothing changes
for installs that don't use it.

Registered plugin types then behave exactly like built-in ones:

- Selectable as a step type via `GET /api/step-types` (and in the Pipeline
  Builder's "Add step" list).
- Configurable in the UI via a generic JSON config editor (plugin types have
  no dedicated form — see the "Frontend" section below).
- Executed the same way as any other step: `run(context)` is called by the
  pipeline runner, with the same retry/`on_error`/parallel-group support.

A plugin file that fails to import, or defines no usable `BaseStep`
subclass, is logged and skipped — it never blocks startup or other plugins.

---

## Minimal example

```python
# plugins/my_step.py
from typing import Any
from flowforge.steps.base import BaseStep, StepResult

class MyStep(BaseStep):
    step_type = 'my_step'   # must be unique — lowercase, letters/digits/underscore, 2-49 chars

    def run(self, context: dict[str, Any]) -> StepResult:
        # self.config is the step's `config` JSON from the pipeline builder
        # context has: current_date, run_id, pipeline_name, steps.<name>.*, env.*, ...
        try:
            do_the_work(self.config)
        except Exception as e:
            return StepResult(success=False, error=str(e))
        return StepResult(success=True, logs='did the work')
```

Copy this (or the fuller `examples/plugins/http_webhook_step.py`, which
POSTs a Jinja2-rendered JSON payload to an arbitrary URL) into your
`FLOWFORGE_PLUGIN_DIR` and restart FlowForge. The new step type appears
immediately in the Pipeline Builder.

---

## The `BaseStep` contract

```python
class BaseStep(ABC):
    step_type: str = ''   # class attribute — the string stored in pipeline_steps.step_type

    def __init__(self, name: str, config: dict[str, Any]):
        self.name, self.config = name, config
        # on_error, parallel_group, db_step_order are also set for you

    @abstractmethod
    def run(self, context: dict[str, Any]) -> StepResult: ...
```

`StepResult` (`flowforge.steps.base.StepResult`) fields you'll typically use:

| Field | Meaning |
|---|---|
| `success` | Required. `False` marks the step (and, per `on_error`, the pipeline) as failed. |
| `logs` | Free text shown in Run History for this step. |
| `error` | Shown in Run History when `success=False`. |
| `output_path` | Set if the step produced a file — downstream steps can reference it via `{{ steps.<name>.output_path }}`. |
| `output_variables` | dict merged into the pipeline context — downstream steps see these as `{{ variable_name }}`. |

You don't need to catch every exception yourself — an uncaught exception in
`run()` is caught by the runner and converted into `StepResult(success=False, error=str(e))` automatically. Returning a `StepResult` explicitly just gives
you control over the message and any partial output.

To render Jinja2 templates (variables, `{{ pipeline_name }}`, etc.) inside
your config values, call `flowforge.engine.context.render(template_str, context)` — see `examples/plugins/http_webhook_step.py` for a working example.

---

## Configuration

```env
# .env
FLOWFORGE_PLUGIN_DIR=./plugins
```

Leave unset (or point it at a directory that doesn't exist) to disable
plugin loading entirely — the default in `.env.example` is `./plugins`,
which most installs will never populate.

---

## Frontend

Plugin step types have no dedicated configuration form. The Pipeline
Builder's step editor falls back to a raw JSON textarea for any step type
it doesn't specifically recognize, bound directly to the step's `config`.
This is intentionally minimal — if a plugin becomes popular enough to
deserve a first-class form, that's a good candidate for a PR against
`frontend/src/components/pipeline/StepEditor.tsx`.

---

## Security note

Plugin files run with the same privileges as the rest of FlowForge (DB
access, decrypted connection/email credentials via the pipeline context,
filesystem access). Only load plugins you've reviewed and trust — there is
no sandboxing.
