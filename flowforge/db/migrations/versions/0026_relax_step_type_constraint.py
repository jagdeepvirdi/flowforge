"""Relax ck_step_type from a fixed enum to a format check (plugin step types)

Revision ID: 0026_relax_step_type_constraint
Revises: 0025_new_providers_notification
Create Date: 2026-07-01

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0026_relax_step_type_constraint'
down_revision: str | None = '0025_new_providers_notification'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STEP_TYPES = (
    "'db_procedure','db_query','report','email','drive_upload',"
    "'data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer',"
    "'ssh_command','db_health_check','data_report','ssh_health_check','notification'"
)


def upgrade() -> None:
    # Community plugin step types (loaded from FLOWFORGE_PLUGIN_DIR) aren't known
    # at migration-authoring time, so the enum list is replaced with a format check.
    # Actual valid-type enforcement moves to the application layer
    # (flowforge.engine.loader.get_step_types()).
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type', 'ff_pipeline_steps',
        "step_type ~ '^[a-z][a-z0-9_]{1,48}$'",
    )


def downgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type', 'ff_pipeline_steps',
        f'step_type IN ({_OLD_STEP_TYPES})',
    )
