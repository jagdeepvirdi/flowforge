import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / '.env')

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so SQLAlchemy metadata is populated for autogenerate
from flowforge.db.models import db  # noqa: E402
target_metadata = db.metadata

# Tables managed outside of Alembic — APScheduler creates apscheduler_jobs itself.
_EXCLUDE_TABLES = frozenset({'apscheduler_jobs'})


def _include_object(obj, name, type_, reflected, compare_to):
    if type_ == 'table' and name in _EXCLUDE_TABLES:
        return False
    return True


def _db_url() -> str:
    url = os.environ.get('FLOWFORGE_DB_URL')
    if not url:
        raise RuntimeError(
            'FLOWFORGE_DB_URL is not set. '
            'Copy .env.example to .env and set FLOWFORGE_DB_URL before running migrations.'
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg['sqlalchemy.url'] = _db_url()
    connectable = engine_from_config(cfg, prefix='sqlalchemy.', poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
