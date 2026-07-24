"""Business logic for pipeline CRUD, cloning/promotion, dependencies, and webhook tokens.

Extracted from flowforge/api/routes/pipelines.py so routes stay thin HTTP glue (parse
request -> authz -> call service -> jsonify). Follows the same convention as
project_access.py / validators.py: a flat module owning its own db.session queries,
imported directly by routes rather than a separate repository/ORM abstraction.
"""
import hashlib
import secrets
from datetime import UTC

from flowforge import audit
from flowforge.crypto import encrypt_value
from flowforge.db.models import (
    DEFAULT_PROJECT_ID,
    Pipeline,
    PipelineDependency,
    PipelineStep,
    PipelineVariable,
    Project,
    WebhookToken,
    db,
)

_REFERENCE_KEYS = ('connection_id', 'report_config_id', 'email_config_id',
                   'provider_id', 'recipient_group_id')


def validate_cron(expr: str) -> str | None:
    """Return an error string if expr is not a valid 5-field cron expression, else None."""
    if not expr:
        return None
    try:
        from apscheduler.triggers.cron import CronTrigger
        CronTrigger.from_crontab(expr)
        return None
    except Exception as e:
        return str(e)


def next_run_iso(schedule: str | None) -> str | None:
    if not schedule:
        return None
    try:
        from datetime import datetime

        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(schedule, timezone='UTC')
        now = datetime.now(UTC)
        t = trigger.get_next_fire_time(now, now)
        return t.isoformat() if t else None
    except Exception:
        return None


def cron_next_runs(expr: str, n: int) -> list[str]:
    """Return up to n upcoming fire times (ISO strings) for a cron expression."""
    from datetime import datetime

    from apscheduler.triggers.cron import CronTrigger
    trigger = CronTrigger.from_crontab(expr, timezone='UTC')
    times, t = [], datetime.now(UTC)
    for _ in range(n):
        t = trigger.get_next_fire_time(t, t)
        if t is None:
            break
        times.append(t.isoformat())
    return times


def default_project_id() -> str:
    p = db.session.query(Project).filter_by(is_default=True).first()
    return p.id if p else DEFAULT_PROJECT_ID


def unique_pipeline_name(base_name: str, fmt: str = '{base} ({n})') -> str:
    candidate = base_name
    n = 1
    while db.session.query(Pipeline).filter_by(name=candidate).first():
        n += 1
        candidate = fmt.format(base=base_name, n=n)
    return candidate


def replace_pipeline_variables(pipeline: Pipeline, variables_data: list) -> None:
    for v in pipeline.variables:
        db.session.delete(v)
    db.session.flush()
    for var in variables_data:
        is_secret = var.get('is_secret', False)
        raw_value = var.get('var_value', '')
        db.session.add(PipelineVariable(
            pipeline_id=pipeline.id,
            var_key=var['var_key'],
            var_value=encrypt_value(raw_value) if is_secret else raw_value,
            is_secret=is_secret,
        ))


def add_pipeline_steps(pipeline_id: str, steps_data: list) -> None:
    for s in steps_data:
        db.session.add(PipelineStep(
            pipeline_id=pipeline_id,
            step_order=int(s.get('step_order', 1)),
            name=str(s['name']),
            step_type=str(s['step_type']),
            config=s.get('config') or {},
            on_error=s.get('on_error', 'stop'),
            enabled=s.get('enabled', True),
            parallel_group=s.get('parallel_group') or None,
        ))


def add_pipeline_vars(pipeline_id: str, vars_data: list) -> None:
    for v in vars_data:
        if v.get('is_secret') and v.get('var_value') == '***':
            continue
        db.session.add(PipelineVariable(
            pipeline_id=pipeline_id,
            var_key=str(v['var_key']),
            var_value=str(v.get('var_value', '')),
            is_secret=bool(v.get('is_secret', False)),
        ))


def create_pipeline(data: dict, project_id: str) -> Pipeline:
    pipeline = Pipeline(
        name=data['name'],
        description=data.get('description', ''),
        schedule=data.get('schedule'),
        enabled=data.get('enabled', True),
        timeout_minutes=data.get('timeout_minutes', 60),
        on_failure_webhook_url=data.get('on_failure_webhook_url'),
        project_id=project_id,
    )
    db.session.add(pipeline)
    db.session.flush()

    for var in data.get('variables', []):
        is_secret = var.get('is_secret', False)
        raw_value = var['var_value']
        db.session.add(PipelineVariable(
            pipeline_id=pipeline.id,
            var_key=var['var_key'],
            var_value=encrypt_value(raw_value) if is_secret else raw_value,
            is_secret=is_secret,
        ))

    db.session.commit()
    audit.log_pipeline_change('CREATED', pipeline.name, pipeline.id)
    return pipeline


def update_pipeline(pipeline: Pipeline, data: dict) -> Pipeline:
    for field in ('name', 'description', 'schedule', 'enabled', 'timeout_minutes',
                  'on_failure_webhook_url', 'project_id'):
        if field in data:
            setattr(pipeline, field, data[field])

    if 'variables' in data:
        replace_pipeline_variables(pipeline, data['variables'])

    db.session.commit()
    return pipeline


def promote_pipeline(src: Pipeline, target_project: Project, suffix: str) -> tuple[Pipeline, list[str]]:
    """Copy a pipeline to a different project (environment promotion: dev -> staging -> prod).

    `suffix` is appended to the source name to build the clone's name (already resolved/
    stripped by the caller, since the default depends on target_project.name). Step configs
    that reference IDs (connection_id, report_config_id, etc.) are copied as-is; warnings are
    returned for anything that may not resolve in the target project.
    """
    new_name = unique_pipeline_name(src.name + suffix)

    clone = Pipeline(
        name=new_name,
        description=src.description,
        schedule=src.schedule,
        enabled=False,           # promoted pipelines start disabled for safety
        timeout_minutes=src.timeout_minutes,
        on_failure_webhook_url=src.on_failure_webhook_url,
        send_only_on_failure=src.send_only_on_failure,
        project_id=target_project.id,
    )
    db.session.add(clone)
    db.session.flush()

    # Copy steps including parallel_group
    for s in src.steps:
        db.session.add(PipelineStep(
            pipeline_id=clone.id,
            step_order=s.step_order,
            name=s.name,
            step_type=s.step_type,
            config=dict(s.config),
            on_error=s.on_error,
            enabled=s.enabled,
            parallel_group=s.parallel_group,
        ))

    # Copy non-secret variables only (secrets are environment-specific)
    warnings: list[str] = []
    for v in src.variables:
        if v.is_secret:
            warnings.append(f"Secret variable '{v.var_key}' was not copied — set it manually in the target project.")
            continue
        db.session.add(PipelineVariable(
            pipeline_id=clone.id,
            var_key=v.var_key,
            var_value=v.var_value,
            is_secret=False,
        ))

    # Warn about step configs that reference external IDs
    for s in src.steps:
        for key in _REFERENCE_KEYS:
            if s.config.get(key):
                warnings.append(
                    f"Step '{s.name}': {key} references an ID from the source project — "
                    f"update it to the equivalent resource in '{target_project.name}'."
                )

    db.session.commit()
    audit.log_pipeline_change('PROMOTED', clone.name, clone.id)
    return clone, warnings


def clone_pipeline(src: Pipeline) -> Pipeline:
    candidate = unique_pipeline_name(f"{src.name} (Copy)", fmt='{base} {n}')

    clone = Pipeline(
        name=candidate,
        description=src.description,
        schedule=None,           # clones start disabled with no schedule
        enabled=False,
        timeout_minutes=src.timeout_minutes,
        on_failure_webhook_url=src.on_failure_webhook_url,
        project_id=src.project_id,
    )
    db.session.add(clone)
    db.session.flush()

    for s in src.steps:
        db.session.add(PipelineStep(
            pipeline_id=clone.id,
            step_order=s.step_order,
            name=s.name,
            step_type=s.step_type,
            config=dict(s.config),
            on_error=s.on_error,
            enabled=s.enabled,
            parallel_group=s.parallel_group,
        ))

    for v in src.variables:
        db.session.add(PipelineVariable(
            pipeline_id=clone.id,
            var_key=v.var_key,
            var_value=v.var_value,
            is_secret=v.is_secret,
        ))

    db.session.commit()
    audit.log_pipeline_change('CLONED', clone.name, clone.id)
    return clone


def import_pipeline_from_yaml(doc: dict, project_id: str) -> Pipeline:
    pipeline = Pipeline(
        name=unique_pipeline_name(str(doc['name'])),
        description=doc.get('description', ''),
        schedule=doc.get('schedule'),
        enabled=doc.get('enabled', True),
        timeout_minutes=doc.get('timeout_minutes', 60),
        on_failure_webhook_url=doc.get('on_failure_webhook_url'),
        project_id=project_id,
    )
    db.session.add(pipeline)
    db.session.flush()

    add_pipeline_steps(pipeline.id, doc.get('steps', []))
    add_pipeline_vars(pipeline.id, doc.get('variables', []))

    db.session.commit()
    return pipeline


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_webhook_token(pipeline_id: str, label: str) -> tuple[WebhookToken, str]:
    raw = 'flwf_' + secrets.token_urlsafe(32)
    wt = WebhookToken(
        pipeline_id=pipeline_id,
        label=label,
        token_hash=token_hash(raw),
    )
    db.session.add(wt)
    db.session.commit()
    return wt, raw


def has_path(start_id: str, target_id: str) -> bool:
    """Return True if there is a dependency path from start_id to target_id (cycle detection)."""
    visited: set[str] = set()
    queue = [start_id]
    while queue:
        current = queue.pop()
        if current == target_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        deps = db.session.query(PipelineDependency).filter_by(upstream_id=current).all()
        queue.extend(d.downstream_id for d in deps)
    return False


def add_dependency(downstream_id: str, upstream_id: str) -> tuple[PipelineDependency | None, str | None, int]:
    """Validate and create a dependency edge. Returns (dependency, error_message, status_code)."""
    if upstream_id == downstream_id:
        return None, 'A pipeline cannot depend on itself', 400
    if not db.session.get(Pipeline, upstream_id):
        return None, 'upstream pipeline not found', 404

    # Cycle detection: would adding this create a cycle?
    if has_path(downstream_id, upstream_id):
        return None, 'Adding this dependency would create a circular dependency', 409

    # Duplicate check
    existing = db.session.query(PipelineDependency).filter_by(
        upstream_id=upstream_id, downstream_id=downstream_id
    ).first()
    if existing:
        return None, 'Dependency already exists', 409

    dep = PipelineDependency(upstream_id=upstream_id, downstream_id=downstream_id)
    db.session.add(dep)
    db.session.commit()
    return dep, None, 201
