"""Shared helper for sending transactional emails through the configured default
email provider — used outside the pipeline engine (password reset, user invites)."""
from flowforge.db.models import EmailProvider, db
from flowforge.email_providers.factory import get_provider


def send_via_default_provider(to: list[str], subject: str, html_body: str) -> None:
    """Send an email using the default (or first available) email provider.

    Raises RuntimeError if no provider is configured or the send fails —
    callers decide how to handle/log that.
    """
    provider_row = db.session.query(EmailProvider).filter_by(is_default=True).first()
    if not provider_row:
        provider_row = db.session.query(EmailProvider).first()
    if not provider_row:
        raise RuntimeError("No email provider configured")

    provider = get_provider(provider_row)
    result = provider.send(to=to, cc=[], bcc=[], subject=subject, html_body=html_body, attachments=[])
    if not result.success:
        raise RuntimeError(result.error or "Send failed")
