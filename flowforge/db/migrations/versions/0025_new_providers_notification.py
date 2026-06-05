"""Add sendgrid/ses/mailgun provider types and notification step type

Revision ID: 0025_new_providers_notification
Revises: 0024_report_column_formatting
Create Date: 2026-05-30

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0025_new_providers_notification'
down_revision: str | None = '0024_report_column_formatting'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_EMAIL_TYPES = "'gmail', 'microsoft365', 'smtp'"
_NEW_EMAIL_TYPES = "'gmail', 'microsoft365', 'smtp', 'sendgrid', 'ses', 'mailgun'"

_OLD_STEP_TYPES = (
    "'db_procedure','db_query','report','email','drive_upload',"
    "'data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer',"
    "'ssh_command','db_health_check','data_report','ssh_health_check'"
)
_NEW_STEP_TYPES = (
    "'db_procedure','db_query','report','email','drive_upload',"
    "'data_load','bulk_load','onedrive_upload','ai_analyze','sftp_transfer',"
    "'ssh_command','db_health_check','data_report','ssh_health_check','notification'"
)


def upgrade() -> None:
    op.drop_constraint('ck_email_provider_type', 'ff_email_providers')
    op.create_check_constraint(
        'ck_email_provider_type', 'ff_email_providers',
        f'provider_type IN ({_NEW_EMAIL_TYPES})',
    )

    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type', 'ff_pipeline_steps',
        f'step_type IN ({_NEW_STEP_TYPES})',
    )


def downgrade() -> None:
    op.drop_constraint('ck_step_type', 'ff_pipeline_steps')
    op.create_check_constraint(
        'ck_step_type', 'ff_pipeline_steps',
        f'step_type IN ({_OLD_STEP_TYPES})',
    )

    op.drop_constraint('ck_email_provider_type', 'ff_email_providers')
    op.create_check_constraint(
        'ck_email_provider_type', 'ff_email_providers',
        f'provider_type IN ({_OLD_EMAIL_TYPES})',
    )
