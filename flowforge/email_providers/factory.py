"""Load an email provider from the FlowForge config DB."""
from flowforge.email_providers.base import EmailProvider


def get_provider(row) -> EmailProvider:
    """Return the appropriate EmailProvider subclass for an EmailProvider model row.

    Accepts the ORM row directly (used by password_reset and email_step).
    """
    from flowforge.crypto import decrypt_config
    cfg = decrypt_config(row.config)
    return _build_provider(row.provider_type, cfg)


def get_email_provider(provider_id: str) -> EmailProvider:
    """Return the appropriate EmailProvider subclass for an email_providers row ID."""
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import EmailProvider as EmailProviderRow
    from flowforge.db.models import db

    row = db.session.get(EmailProviderRow, provider_id)
    if not row:
        raise ValueError(f"Email provider not found: {provider_id}")

    cfg = decrypt_config(row.config)
    return _build_provider(row.provider_type, cfg)


def _build_provider(provider_type: str, cfg: dict) -> EmailProvider:
    if provider_type == 'gmail':
        from flowforge.email_providers.gmail import GmailProvider
        return GmailProvider(
            client_id=cfg['client_id'],
            client_secret=cfg['client_secret'],
            refresh_token=cfg['refresh_token'],
            sender=cfg['sender'],
        )

    if provider_type == 'microsoft365':
        from flowforge.email_providers.microsoft365 import Microsoft365Provider
        sender = cfg.get('sender_email') or cfg.get('sender', '')
        if not sender:
            raise ValueError(
                "Microsoft 365 provider config is missing 'sender' (the licensed M365 sender email address)"
            )
        return Microsoft365Provider(
            tenant_id=cfg.get('tenant_id', ''),
            client_id=cfg.get('client_id', ''),
            client_secret=cfg.get('client_secret', ''),
            sender_email=sender,
        )

    if provider_type == 'smtp':
        from flowforge.email_providers.smtp import SMTPProvider
        return SMTPProvider(
            host=cfg['host'],
            port=int(cfg.get('port', 587)),
            username=cfg.get('username', ''),
            password=cfg.get('password', ''),
            use_ssl=cfg.get('use_ssl', False),
            use_tls=cfg.get('use_tls', True),
        )

    if provider_type == 'sendgrid':
        from flowforge.email_providers.sendgrid import SendGridProvider
        return SendGridProvider(
            api_key=cfg['api_key'],
            from_email=cfg['from_email'],
            from_name=cfg.get('from_name', ''),
        )

    if provider_type == 'ses':
        from flowforge.email_providers.ses import SESProvider
        return SESProvider(
            aws_access_key_id=cfg['aws_access_key_id'],
            aws_secret_access_key=cfg['aws_secret_access_key'],
            aws_region=cfg.get('aws_region', 'us-east-1'),
            from_email=cfg['from_email'],
            from_name=cfg.get('from_name', ''),
        )

    if provider_type == 'mailgun':
        from flowforge.email_providers.mailgun import MailgunProvider
        return MailgunProvider(
            api_key=cfg['api_key'],
            domain=cfg['domain'],
            from_email=cfg['from_email'],
            from_name=cfg.get('from_name', ''),
            region=cfg.get('region', 'us'),
        )

    raise ValueError(f"Unsupported provider_type: {provider_type}")
