import logging
from pathlib import Path
from typing import Any

from flowforge.steps.base import BaseStep, StepResult

logger = logging.getLogger(__name__)


_DEFAULT_DRIVE_MESSAGE = (
    "The following report(s) were too large to attach directly and have been "
    "uploaded to Google Drive for your convenience:\n\n"
    "{% for link in drive_links %}"
    "• {{ link.filename }} ({{ link.size_mb }}MB) — {{ link.url }}\n"
    "{% endfor %}"
)


def _handle_attachments(
    attachments: list[Path],
    max_mb: int,
    drive_folder_id: str,
    drive_message_template: str,
    context: dict[str, Any],
) -> tuple[list[Path], str]:
    """Split attachments into direct and Drive-uploaded. Returns (direct_files, extra_body_text)."""
    from flowforge.engine.context import render
    from flowforge.storage.google_drive import upload_file

    max_bytes = max_mb * 1024 * 1024
    direct: list[Path] = []
    drive_links: list[dict] = []

    for path in attachments:
        if not path.exists():
            logger.warning("Attachment not found, skipping: %s", path)
            continue
        if path.stat().st_size > max_bytes:
            url = upload_file(path, drive_folder_id, make_shareable=True)
            drive_links.append({
                'filename': path.name,
                'url': url,
                'size_mb': round(path.stat().st_size / 1024 / 1024, 1),
            })
            logger.info("Large attachment uploaded to Drive: %s", path.name)
        else:
            direct.append(path)

    extra_text = ''
    if drive_links:
        tmpl = drive_message_template or _DEFAULT_DRIVE_MESSAGE
        extra_text = render(tmpl, {**context, 'drive_links': drive_links})

    return direct, extra_text


class EmailStep(BaseStep):
    """Sends an email with smart attachment handling (large files → Drive link)."""

    step_type = 'email'

    def run(self, context: dict[str, Any]) -> StepResult:
        from flowforge.engine.context import render

        email_cfg, provider = self._load_config_and_provider()

        raw_attachments = self.config.get('attachments', [])
        attachments = [Path(render(p, context)) for p in raw_attachments]

        max_mb = email_cfg.get('attachment_max_mb', 10)
        drive_folder_id = email_cfg.get('drive_folder_id', '')
        drive_message = email_cfg.get('drive_share_message', '')
        direct_attachments, extra_body = _handle_attachments(
            attachments, max_mb, drive_folder_id, drive_message, context
        )

        to = self._resolve_recipients(email_cfg)
        cc  = email_cfg.get('cc_addresses') or []
        bcc = email_cfg.get('bcc_addresses') or []

        subject = render(email_cfg.get('subject', ''), context)
        body    = render(email_cfg.get('body_template', ''), context) + extra_body

        try:
            result = provider.send(to, cc, bcc, subject, body, direct_attachments)
            if result.success:
                logger.info("Email sent: '%s' → %s", subject, to)
                import flowforge.audit as audit
                audit.log_email_sent(
                    pipeline_name=context.get('pipeline_name', ''),
                    step_name=self.name,
                    subject=subject,
                    recipients=result.recipients,
                    attachment_names=[p.name for p in direct_attachments],
                )
                return StepResult(success=True, extra={'email_sent_to': result.recipients})
            return StepResult(success=False, error=result.error)
        except Exception as e:
            logger.error("Email step failed: %s", e)
            return StepResult(success=False, error=str(e))

    def _load_config_and_provider(self) -> tuple[dict, Any]:
        email_config_id = self.config.get('email_config_id')
        if email_config_id:
            from flowforge.db.models import EmailConfig, db
            from flowforge.email_providers.factory import get_email_provider

            row = db.session.get(EmailConfig, email_config_id)
            if not row:
                raise ValueError(f"EmailConfig not found: {email_config_id}")

            cfg = {
                'subject':             row.subject,
                'body_template':       row.body_template,
                'to_addresses':        row.to_addresses or [],
                'cc_addresses':        row.cc_addresses or [],
                'bcc_addresses':       row.bcc_addresses or [],
                'recipient_group_id':  row.recipient_group_id,
                'attachment_max_mb':   row.attachment_max_mb,
                'drive_folder_id':     row.drive_folder_id or '',
                'drive_share_message': row.drive_share_message or '',
            }
            provider = get_email_provider(str(row.provider_id)) if row.provider_id else None
            if not provider:
                raise ValueError("Email config has no provider configured")
            return cfg, provider

        # Inline config (testing / YAML import)
        inline = self.config.get('inline_config', {})
        from flowforge.steps.email_step import _build_inline_provider
        return inline, _build_inline_provider(inline)

    def _resolve_recipients(self, email_cfg: dict) -> list[str]:
        group_id = email_cfg.get('recipient_group_id')
        if group_id:
            from flowforge.db.models import RecipientGroup, db
            group = db.session.get(RecipientGroup, group_id)
            if group:
                return list(group.addresses)
        return list(email_cfg.get('to_addresses') or [])


def _build_inline_provider(email_cfg: dict):
    """Instantiate a provider directly from inline config (no DB lookup)."""
    import os
    provider_type = email_cfg.get('provider_type', 'smtp').lower()

    if provider_type == 'gmail':
        from flowforge.email_providers.gmail import GmailProvider
        return GmailProvider(
            client_id=os.environ.get('GMAIL_CLIENT_ID', ''),
            client_secret=os.environ.get('GMAIL_CLIENT_SECRET', ''),
            refresh_token=os.environ.get('GMAIL_REFRESH_TOKEN', ''),
            sender=os.environ.get('GMAIL_SENDER', ''),
        )
    if provider_type == 'microsoft365':
        from flowforge.email_providers.microsoft365 import Microsoft365Provider
        return Microsoft365Provider(
            tenant_id=os.environ.get('MICROSOFT_TENANT_ID', ''),
            client_id=os.environ.get('MICROSOFT_CLIENT_ID', ''),
            client_secret=os.environ.get('MICROSOFT_CLIENT_SECRET', ''),
            sender_email=os.environ.get('MICROSOFT_SENDER_EMAIL', ''),
        )
    from flowforge.email_providers.smtp import SMTPProvider
    return SMTPProvider(
        host=email_cfg.get('host', ''),
        port=email_cfg.get('port', 587),
        username=email_cfg.get('username', ''),
        password=email_cfg.get('password', ''),
        use_ssl=email_cfg.get('use_ssl', False),
        use_tls=email_cfg.get('use_tls', True),
    )
