import logging
import os
import sys

import click


@click.group()
@click.version_option(package_name='flowforge')
@click.option('--debug', is_flag=True, help='Enable debug logging.')
def cli(debug: bool):
    """FlowForge — database-driven pipeline orchestrator."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s — %(message)s')


@cli.command('list')
def list_pipelines():
    """List all pipelines with their schedule and last run status."""
    app = _create_app()
    with app.app_context():
        from flowforge.db.models import Pipeline, PipelineRun, db
        pipelines = db.session.query(Pipeline).order_by(Pipeline.name).all()
        if not pipelines:
            click.echo('No pipelines configured.')
            return
        click.echo(f"{'Name':<40} {'Schedule':<20} {'Enabled':<8} {'Last Status'}")
        click.echo('-' * 80)
        for p in pipelines:
            last_run = (
                db.session.query(PipelineRun)
                .filter_by(pipeline_id=p.id)
                .order_by(PipelineRun.started_at.desc())
                .first()
            )
            status = last_run.status if last_run else 'never run'
            click.echo(f"{p.name:<40} {(p.schedule or '—'):<20} {str(p.enabled):<8} {status}")


@cli.command()
@click.argument('pipeline_name')
@click.option('--var', '-v', multiple=True, metavar='KEY=VALUE', help='Override pipeline variable.')
def run(pipeline_name: str, var: tuple[str, ...]):
    """Run a pipeline by name."""
    overrides = {}
    for item in var:
        if '=' not in item:
            click.echo(f"ERROR: --var must be KEY=VALUE, got: {item}", err=True)
            sys.exit(1)
        k, v = item.split('=', 1)
        overrides[k] = v

    app = _create_app()
    with app.app_context():
        from flowforge.db.models import Pipeline, db
        from flowforge.engine.loader import load_pipeline
        from flowforge.engine.runner import run_pipeline

        pipeline = db.session.query(Pipeline).filter_by(name=pipeline_name).first()
        if not pipeline:
            click.echo(f"ERROR: Pipeline not found: {pipeline_name}", err=True)
            sys.exit(1)

        click.echo(f"Running pipeline: {pipeline_name}")
        steps, pipeline_vars = load_pipeline(pipeline.id)
        pipeline_vars.update(overrides)

        result = run_pipeline(
            pipeline_name=pipeline.name,
            steps=steps,
            pipeline_vars=pipeline_vars,
            triggered_by='cli',
            pipeline_id=pipeline.id,
        )

        click.echo(f"\nStatus:       {'✓ SUCCESS' if result.success else '✗ FAILED'}")
        click.echo(f"Steps run:    {result.steps_run}")
        click.echo(f"Steps failed: {result.steps_failed}")
        if result.run_id:
            click.echo(f"Run ID:       {result.run_id}")
        if not result.success:
            click.echo(f"Error:        {result.error}", err=True)
            sys.exit(1)


@cli.command()
def web():
    """Start the FlowForge web server."""
    port = int(os.environ.get('FLOWFORGE_PORT', 5000))
    app = _create_app()
    click.echo(f"Starting FlowForge on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)


@cli.command()
def schedule():
    """Start the FlowForge scheduler daemon."""
    app = _create_app()
    with app.app_context():
        from flowforge.engine.scheduler import start_scheduler
        click.echo('Starting scheduler...')
        start_scheduler()


@cli.command()
@click.argument('pipeline_name')
def validate(pipeline_name: str):
    """Validate a pipeline — test connections and check step config."""
    app = _create_app()
    with app.app_context():
        from flowforge.db.models import Pipeline, db
        from flowforge.engine.loader import load_pipeline

        pipeline = db.session.query(Pipeline).filter_by(name=pipeline_name).first()
        if not pipeline:
            click.echo(f"ERROR: Pipeline not found: {pipeline_name}", err=True)
            sys.exit(1)

        try:
            steps, _ = load_pipeline(pipeline.id)
            click.echo(f"✓ Pipeline '{pipeline_name}' loaded: {len(steps)} steps")
        except Exception as e:
            click.echo(f"✗ Validation failed: {e}", err=True)
            sys.exit(1)


@cli.group()
def setup():
    """Run provider OAuth2 setup flows."""


@setup.command('gmail')
def setup_gmail():
    """OAuth2 setup for Gmail + Google Drive."""
    click.echo("Gmail OAuth2 setup — coming in Phase 3.")
    click.echo("For now, set these environment variables manually:")
    click.echo("  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_SENDER")


@setup.command('microsoft365')
def setup_microsoft365():
    """OAuth2 setup for Microsoft 365 via MSAL device code flow."""
    click.echo("Microsoft 365 setup — coming in Phase 3.")
    click.echo("For now, set these environment variables manually:")
    click.echo("  MICROSOFT_TENANT_ID, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_SENDER_EMAIL")


@cli.command()
@click.argument('pipeline_name')
@click.option('--output', '-o', default=None, help='Output file path (default: stdout).')
def export(pipeline_name: str, output: str | None):
    """Export a pipeline definition as YAML."""
    app = _create_app()
    with app.app_context():
        import yaml
        from flowforge.db.models import Pipeline, db

        pipeline = db.session.query(Pipeline).filter_by(name=pipeline_name).first()
        if not pipeline:
            click.echo(f"ERROR: Pipeline not found: {pipeline_name}", err=True)
            sys.exit(1)

        data = {
            'name': pipeline.name,
            'description': pipeline.description,
            'schedule': pipeline.schedule,
            'enabled': pipeline.enabled,
            'timeout_minutes': pipeline.timeout_minutes,
            'variables': [
                {'var_key': v.var_key, 'var_value': '***' if v.is_secret else v.var_value, 'is_secret': v.is_secret}
                for v in pipeline.variables
            ],
            'steps': [
                {'step_order': s.step_order, 'name': s.name, 'step_type': s.step_type,
                 'config': s.config, 'on_error': s.on_error}
                for s in pipeline.steps
            ],
        }
        text = yaml.dump(data, allow_unicode=True, sort_keys=False)
        if output:
            with open(output, 'w') as f:
                f.write(text)
            click.echo(f"Exported to {output}")
        else:
            click.echo(text)


def _create_app():
    from flowforge.api.app import create_app
    return create_app()


if __name__ == '__main__':
    cli()
