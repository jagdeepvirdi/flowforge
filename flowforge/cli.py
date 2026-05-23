import logging
import os
import sys

import click


@click.group()
@click.version_option(package_name='flowforge')
@click.option('--debug', is_flag=True, help='Enable debug logging (overrides LOG_LEVEL).')
def cli(debug: bool):
    """FlowForge — database-driven pipeline orchestrator."""
    if debug:
        level = logging.DEBUG
    else:
        level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
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
        steps, pipeline_vars, secret_keys = load_pipeline(pipeline.id)
        pipeline_vars.update(overrides)

        result = run_pipeline(
            pipeline_name=pipeline.name,
            steps=steps,
            pipeline_vars=pipeline_vars,
            triggered_by='cli',
            pipeline_id=pipeline.id,
            secret_var_keys=secret_keys,
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
    from flowforge.engine import shutdown
    shutdown.install_handler(app)
    click.echo(f"Starting FlowForge on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
    shutdown.graceful_exit(app)


@cli.command()
def schedule():
    """Start the FlowForge scheduler daemon."""
    app = _create_app()
    from flowforge.engine import shutdown
    from flowforge.engine.scheduler import start_scheduler
    shutdown.install_handler(app)
    click.echo('Starting scheduler...')
    start_scheduler(app)
    # Reached here after Ctrl+C or SIGTERM (APScheduler absorbs SystemExit internally).
    # Drain any still-running jobs; no-op if SIGTERM handler already cleaned up.
    shutdown.graceful_exit(app)


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
            steps, _, _sk = load_pipeline(pipeline.id)
            click.echo(f"✓ Pipeline '{pipeline_name}' loaded: {len(steps)} steps")
        except Exception as e:
            click.echo(f"✗ Validation failed: {e}", err=True)
            sys.exit(1)


@cli.group()
def setup():
    """Run provider OAuth2 setup flows."""


@setup.command('gmail')
def setup_gmail():
    """Print Gmail OAuth2 setup instructions."""
    click.echo("")
    click.echo("Gmail OAuth2 Setup")
    click.echo("──────────────────")
    click.echo("Full step-by-step guide: docs/gmail-oauth2-setup.md")
    click.echo("")
    click.echo("Quick summary:")
    click.echo("  1. Go to https://console.cloud.google.com")
    click.echo("  2. Create a project → Enable Gmail API and Google Drive API")
    click.echo("  3. OAuth consent screen → Desktop app credentials")
    click.echo("  4. Run the token script from docs/gmail-oauth2-setup.md to get GMAIL_REFRESH_TOKEN")
    click.echo("  5. Set in .env:")
    click.echo("       GMAIL_CLIENT_ID=")
    click.echo("       GMAIL_CLIENT_SECRET=")
    click.echo("       GMAIL_REFRESH_TOKEN=")
    click.echo("       GMAIL_SENDER=you@gmail.com")
    click.echo("")


@setup.command('microsoft365')
def setup_microsoft365():
    """Print Microsoft 365 OAuth2 setup instructions."""
    click.echo("")
    click.echo("Microsoft 365 Setup")
    click.echo("───────────────────")
    click.echo("  1. Register an app in Azure AD: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps")
    click.echo("  2. Add permission: Microsoft Graph → Mail.Send (application permission)")
    click.echo("  3. Grant admin consent")
    click.echo("  4. Create a client secret under 'Certificates & secrets'")
    click.echo("  5. Set in .env:")
    click.echo("       MICROSOFT_TENANT_ID=")
    click.echo("       MICROSOFT_CLIENT_ID=")
    click.echo("       MICROSOFT_CLIENT_SECRET=")
    click.echo("       MICROSOFT_SENDER_EMAIL=reports@yourcompany.com")
    click.echo("")


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


@cli.command()
@click.option('--days', default=None, type=int,
              help='Delete files older than this many days (default: FLOWFORGE_OUTPUT_TTL_DAYS or 7).')
@click.option('--dir', 'output_dir', default=None,
              help='Output directory to clean (default: FLOWFORGE_OUTPUT_DIR or ./output).')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting.')
def cleanup(days: int | None, output_dir: str | None, dry_run: bool):
    """Delete generated output files older than the TTL."""
    import os
    from pathlib import Path
    from datetime import datetime, timezone

    directory = Path(output_dir or os.environ.get('FLOWFORGE_OUTPUT_DIR', 'output'))
    ttl = days if days is not None else int(os.environ.get('FLOWFORGE_OUTPUT_TTL_DAYS', 7))

    if not directory.exists():
        click.echo(f"Output directory does not exist: {directory}")
        return

    cutoff = datetime.now(timezone.utc).timestamp() - ttl * 86_400
    to_delete = [
        p for p in directory.iterdir()
        if p.is_file() and p.stat().st_mtime < cutoff
    ]

    if not to_delete:
        click.echo(f"No files older than {ttl} days in {directory}.")
        return

    total_bytes = sum(p.stat().st_size for p in to_delete)
    click.echo(f"{'Would delete' if dry_run else 'Deleting'} {len(to_delete)} file(s) "
               f"({total_bytes / 1_048_576:.2f} MB) from {directory} [TTL={ttl}d]:")
    for p in sorted(to_delete):
        click.echo(f"  {p.name}")

    if not dry_run:
        errors = 0
        for p in to_delete:
            try:
                p.unlink()
            except Exception as e:
                click.echo(f"  ERROR deleting {p.name}: {e}", err=True)
                errors += 1
        deleted = len(to_delete) - errors
        click.echo(f"Done. {deleted} file(s) deleted.")


@cli.group('db')
def db_group():
    """Database migration commands (wraps Alembic)."""


def _alembic_cfg():
    """Return an Alembic Config pointed at the bundled migrations directory."""
    from pathlib import Path
    from alembic.config import Config
    migrations_dir = Path(__file__).parent / 'db' / 'migrations'
    cfg = Config()
    cfg.set_main_option('script_location', str(migrations_dir))
    return cfg


@db_group.command('upgrade')
@click.argument('revision', default='head')
def db_upgrade(revision: str):
    """Apply pending migrations (default: head)."""
    from alembic import command as alembic_cmd
    alembic_cmd.upgrade(_alembic_cfg(), revision)
    click.echo('Database is up to date.')


@db_group.command('downgrade')
@click.argument('revision')
def db_downgrade(revision: str):
    """Revert to REVISION (use -1 for one step back)."""
    from alembic import command as alembic_cmd
    alembic_cmd.downgrade(_alembic_cfg(), revision)


@db_group.command('revision')
@click.option('--message', '-m', required=True, help='Short description of the change.')
@click.option('--autogenerate', is_flag=True, help='Detect schema changes from models.')
def db_revision(message: str, autogenerate: bool):
    """Generate a new migration script."""
    from alembic import command as alembic_cmd
    alembic_cmd.revision(_alembic_cfg(), message=message, autogenerate=autogenerate)


@db_group.command('current')
def db_current():
    """Show the currently applied migration revision."""
    from alembic import command as alembic_cmd
    alembic_cmd.current(_alembic_cfg())


@db_group.command('stamp')
@click.argument('revision')
def db_stamp(revision: str):
    """Mark the database as being at REVISION without running migrations.
    Use 'head' to mark an existing database as up to date after a fresh install.
    """
    from alembic import command as alembic_cmd
    alembic_cmd.stamp(_alembic_cfg(), revision)
    click.echo(f'Database stamped at revision: {revision}')


@db_group.command('seed')
def db_seed():
    """Create the initial admin user from FLOWFORGE_USERNAME / FLOWFORGE_PASSWORD env vars.

    Run once after applying migrations on a fresh installation:

        flowforge db upgrade
        flowforge db seed
    """
    username = os.environ.get('FLOWFORGE_USERNAME', '').strip()
    password_hash = os.environ.get('FLOWFORGE_PASSWORD', '').strip()
    if not username or not password_hash:
        click.echo(
            'ERROR: Set FLOWFORGE_USERNAME and FLOWFORGE_PASSWORD env vars before seeding.',
            err=True,
        )
        sys.exit(1)

    app = _create_app()
    with app.app_context():
        try:
            from flowforge.db.models import User, db
            if db.session.query(User).first():
                click.echo('Admin user already exists — skipping.')
                return
            db.session.add(User(username=username, password_hash=password_hash))
            db.session.commit()
            click.echo(f'Admin user "{username}" created.')
        except Exception as e:
            click.echo(f'ERROR: {e}', err=True)
            sys.exit(1)


@cli.command('import')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--overwrite', is_flag=True,
              help='Replace the existing pipeline if one with the same name already exists.')
def import_pipeline(file_path: str, overwrite: bool):
    """Import a pipeline definition from a YAML file."""
    app = _create_app()
    with app.app_context():
        import yaml
        from flowforge.db.models import Pipeline, PipelineStep, PipelineVariable, db

        with open(file_path) as f:
            data = yaml.safe_load(f)

        name = data.get('name')
        if not name:
            click.echo("ERROR: YAML is missing 'name' field.", err=True)
            sys.exit(1)

        existing = db.session.query(Pipeline).filter_by(name=name).first()
        if existing:
            if not overwrite:
                click.echo(
                    f"ERROR: Pipeline '{name}' already exists. Use --overwrite to replace.",
                    err=True,
                )
                sys.exit(1)
            db.session.delete(existing)
            db.session.flush()

        pipeline = Pipeline(
            name=name,
            description=data.get('description'),
            schedule=data.get('schedule'),
            enabled=data.get('enabled', True),
            timeout_minutes=data.get('timeout_minutes', 60),
        )
        db.session.add(pipeline)
        db.session.flush()

        for step_data in data.get('steps', []):
            db.session.add(PipelineStep(
                pipeline_id=pipeline.id,
                step_order=step_data['step_order'],
                name=step_data['name'],
                step_type=step_data['step_type'],
                config=step_data.get('config', {}),
                on_error=step_data.get('on_error', 'stop'),
            ))

        skipped_secrets = 0
        for var_data in data.get('variables', []):
            if var_data.get('is_secret') and var_data.get('var_value') == '***':
                skipped_secrets += 1
                continue
            db.session.add(PipelineVariable(
                pipeline_id=pipeline.id,
                var_key=var_data['var_key'],
                var_value=var_data['var_value'],
                is_secret=var_data.get('is_secret', False),
            ))

        db.session.commit()
        step_count = len(data.get('steps', []))
        click.echo(f"Imported pipeline '{name}' ({step_count} step(s)).")
        if skipped_secrets:
            click.echo(
                f"  Note: {skipped_secrets} secret variable(s) skipped (exported as '***') — set them manually."
            )


def _create_app():
    from flowforge.api.app import create_app
    return create_app()


if __name__ == '__main__':
    cli()
