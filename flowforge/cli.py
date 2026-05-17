import click


@click.group()
@click.version_option(package_name='flowforge')
def cli():
    """FlowForge — database-driven pipeline orchestrator."""


@cli.command()
@click.argument('pipeline_name')
@click.option('--var', '-v', multiple=True, metavar='KEY=VALUE', help='Pipeline variable override.')
def run(pipeline_name, var):
    """Run a pipeline by name."""
    click.echo(f"Running pipeline: {pipeline_name}")
    click.echo("(Database-driven execution not yet wired — coming in Phase 2.)")


@cli.command()
def web():
    """Start the FlowForge web server."""
    click.echo("Starting FlowForge web server...")
    click.echo("(Web server not yet implemented — coming in Phase 2.)")


@cli.command()
def schedule():
    """Start the FlowForge scheduler."""
    click.echo("Starting FlowForge scheduler...")
    click.echo("(Scheduler not yet implemented — coming in Phase 2.)")


@cli.command()
@click.argument('provider', type=click.Choice(['gmail', 'microsoft365', 'drive']))
def setup(provider):
    """Run the OAuth2 setup flow for a provider."""
    click.echo(f"Setting up {provider}...")
    click.echo("(OAuth2 setup flow not yet implemented — coming in Phase 2.)")


if __name__ == '__main__':
    cli()
