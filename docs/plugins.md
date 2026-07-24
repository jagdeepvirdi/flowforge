# Writing FlowForge Plugins

FlowForge ships with a fixed set of built-in step types (`db_procedure`,
`db_query`, `report`, `email`, `ssh_command`, `notification`, ...), database
connections (`postgresql`, `oracle`, `mysql`, ...), and email providers
(`gmail`, `smtp`, `sendgrid`, ...). For anything else — a custom integration,
an internal-only step, an unsupported database — you can drop a Python file
into a plugin directory instead of forking FlowForge, or ship a pip-installable
package that registers itself automatically.

Three categories are pluggable today: **steps**, **database connections**, and
**email providers**. Storage backends and report formats are not — see
"What's not pluggable yet" near the end.

---

## How it works

At startup (and once per process, lazily, the first time a pipeline is
loaded), FlowForge discovers plugins two ways:

1. **Directory scanning** — `FLOWFORGE_PLUGIN_DIR` (default `./plugins`) is
   scanned for `*.py` files. Any file not starting with `_` is imported.
2. **Entry points** — pip-installed packages can register a plugin without a
   file in `FLOWFORGE_PLUGIN_DIR` at all, via a `flowforge.plugins`
   entry-point group (see below).

Either way, every class found is checked against three pluggable categories:

| Category | Base class | Key attribute | Extra requirement |
|---|---|---|---|
| Step | `flowforge.steps.base.BaseStep` | `step_type` | none |
| Connection | `flowforge.connections.base.BaseConnection` | `db_type` | `from_config(cls, cfg)` classmethod |
| Email provider | `flowforge.email_providers.base.EmailProvider` | `provider_type` | `from_config(cls, cfg)` classmethod |

A single file (or a single package) can define classes from more than one
category — e.g. a plugin file with both a custom step and a custom
connection registers both. Each matching class is registered under its key
string, and behaves like a built-in of that category from then on (see
"Frontend" and "Registry introspection" below).

If the plugin directory doesn't exist, directory scanning is a no-op —
nothing changes for installs that don't use it.

A plugin file (or entry point) that fails to import/load, or that resolves
to no usable plugin class, is logged and skipped — it never blocks startup
or other plugins. A key that collides with an existing one (built-in or
another plugin) is also skipped and logged rather than overwriting it.

### Entry points (pip-installable plugins)

A plugin package registers itself in its own `pyproject.toml`:

```toml
[project.entry-points."flowforge.plugins"]
my_plugin = "my_package.plugin:MyStep"
```

Each entry point is expected to resolve to a class (not a module or
function); it's checked against the same three categories as a
directory-scanned class. `pip install`-ing the package is then enough — no
file needs to be copied into `FLOWFORGE_PLUGIN_DIR`. If enumerating entry
points fails, or one fails to load, or resolves to something that isn't a
class, it's logged and skipped the same way a broken directory-scanned file
would be.

---

## Step plugins

### Minimal example

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

### The `BaseStep` contract

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
`run()` is caught by the runner and converted into
`StepResult(success=False, error=str(e))` automatically. Returning a
`StepResult` explicitly just gives you control over the message and any
partial output.

To render Jinja2 templates (variables, `{{ pipeline_name }}`, etc.) inside
your config values, call
`flowforge.engine.context.render(template_str, context)` — see
`examples/plugins/http_webhook_step.py` for a working example.

---

## Connection plugins

Unlike steps — which the runner constructs directly from a pipeline step's
`(name, config)` — connections are built from a `db_connections` row's
*decrypted config dict*. A plugin connection class must therefore define a
`from_config` classmethod instead of relying on `__init__` alone:

```python
# plugins/my_connection.py
from flowforge.connections.base import BaseConnection

class MyConnection(BaseConnection):
    db_type = 'my_custom_db'   # must be unique — matches a db_connections.db_type value

    def __init__(self, host, api_key):
        self.host, self.api_key = host, api_key

    @classmethod
    def from_config(cls, cfg: dict) -> 'MyConnection':
        return cls(host=cfg['host'], api_key=cfg['api_key'])

    # ... implement the rest of BaseConnection's abstract methods:
    # execute_procedure, execute_query, execute_query_with_columns,
    # execute_write, execute_many, make_placeholders, test, close ...

    @staticmethod
    def make_placeholders(n: int) -> str:
        return ', '.join(['%s'] * n)   # or ':1, :2', '?, ?', etc. — your driver's bind syntax
```

`make_placeholders` must be a `@staticmethod` (matching every built-in connection
class) — some callers resolve it from the class itself, without an instance, to
get a connection type's placeholder syntax without opening a connection.

If the class is registered but has no `from_config` classmethod, building a
connection of that type raises a clear `ValueError` at the point of use (not
at plugin-load time — a plugin with a bug in `from_config` should still load
and register, so the error surfaces as close as possible to the actual
misuse rather than silently disabling the whole plugin file).

`BaseConnection` also provides a concrete `raw_connection` property for free —
if your `__init__` stores the underlying driver connection object as
`self._conn` (as every built-in connection class does), callers that need
cursor-level control beyond `execute_write`/`execute_many` (e.g. a bulk
`COPY`-style fast path) can reach it via `conn.raw_connection`. Connection types
with no traditional DB-API connection to expose (e.g. one built on a client SDK)
can leave `self._conn` unset — accessing `raw_connection` then raises a clear
`NotImplementedError` instead of `execute_*`-only callers ever needing it.

---

## Email provider plugins

Same shape as connection plugins, against
`flowforge.email_providers.base.EmailProvider`, keyed by `provider_type`
instead of `db_type`:

```python
# plugins/my_provider.py
from flowforge.email_providers.base import EmailProvider, EmailResult

class MyProvider(EmailProvider):
    provider_type = 'my_custom_provider'

    def __init__(self, api_key: str):
        self.api_key = api_key

    @classmethod
    def from_config(cls, cfg: dict) -> 'MyProvider':
        return cls(api_key=cfg['api_key'])

    def send(self, to, cc, bcc, subject, html_body, attachments) -> EmailResult:
        # ... call your provider's API ...
        return EmailResult(success=True, recipients=to)
```

`EmailProvider.test()` has a default implementation (returns `(True,
'Connected')`) — override it if your provider can verify credentials without
actually sending mail.

---

## Registry introspection

`GET /api/registry/<category>` (`category` is `steps`, `connections`, or
`email_providers`) lists every registered key in that category — built-in
and plugin — with `display_name`, `description`, `requires` (the pip extra
needed, if any), `tier` (unused today — see `docs/TASKS.md` Phase 13.5), and
two computed fields: `plugin` (registered by a plugin, not built in) and
`installed` (whether `requires`' underlying package is actually importable;
always `true` when `requires` is empty). `GET /api/registry` returns the same
shape flattened across all three categories, with a `category` field added
and an `entitled: true` stub on every row (there is no licensing/entitlement
system — this is a forward-looking placeholder, not an active gate).

This is what the frontend now uses to offer plugin connection/provider types
in the Connections page (see "Frontend" below) rather than hardcoding a
fixed list of them, and is generally useful for scripting/checking "what's
actually installed" without reading source.

---

## Frontend

All three categories get a generic fallback rather than a dedicated form,
since a plugin's config shape is unknown to the frontend ahead of time:

- **Steps**: the Pipeline Builder's step editor falls back to a raw JSON
  textarea for any step type it doesn't specifically recognize, bound
  directly to the step's `config`.
- **Connections / email providers**: the Connections page's "Add
  Connection"/"Add Email Provider" type dropdown lists plugin types
  (fetched from the registry endpoint above) alongside the built-in ones.
  Selecting a plugin type swaps the dedicated per-type form for a raw JSON
  textarea bound to the connection/provider's `config`.

This is intentionally minimal — if a plugin becomes popular enough to
deserve a first-class form, that's a good candidate for a PR against
`frontend/src/components/pipeline/StepEditor.tsx` (steps) or
`frontend/src/pages/Connections.tsx` (connections/providers).

---

## Configuration

```env
# .env
FLOWFORGE_PLUGIN_DIR=./plugins
```

Leave unset (or point it at a directory that doesn't exist) to disable
directory-scanned plugin loading entirely — the default in `.env.example` is
`./plugins`, which most installs will never populate. This has no effect on
entry-point-based plugins, which are discovered from whatever's `pip
install`-ed regardless of this setting.

---

## What's not pluggable yet

Storage backends (`s3_upload`/`azure_blob_upload`/`drive_upload`) and report
formats (`excel`/`pdf`/`csv`) aren't pluggable — there's no registry for
either yet. `report.py`'s format dispatch has the same if/elif shape as the
connections/providers dispatch this system replaced and could get the same
treatment later; storage is structurally different, since there's no shared
dispatch function to replace today (each upload step imports its own storage
module directly) — see `docs/TASKS.md` Phase 13 for the full reasoning and
current status.

---

## Security note

Plugin files run with the same privileges as the rest of FlowForge (DB
access, decrypted connection/email credentials via the pipeline context,
filesystem access). Only load plugins you've reviewed and trust — there is
no sandboxing.
