"""Load an email provider from the FlowForge config DB."""
from flowforge.email_providers.base import EmailProvider


def get_email_provider(provider_id: str) -> EmailProvider:
    """Return the appropriate EmailProvider subclass for an email_providers row."""
    from flowforge.crypto import decrypt_config
    from flowforge.db.models import EmailProvider as EmailProviderRow, db

    row = db.session.get(EmailProviderRow, provider_id)
    if not row:
        raise ValueError(f"Email provider not found: {provider_id}")

    cfg = decrypt_config(row.config)

    if row.provider_type == 'gmail':
        from flowforge.email_providers.gmail import GmailProvider
        return GmailProvider(
            client_id=cfg['client_id'],
            client_secret=cfg['client_secret'],
            refresh_token=cfg['refresh_token'],
            sender=cfg['sender'],
        )

    if row.provider_type == 'microsoft365':
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

    if row.provider_type == 'smtp':
        from flowforge.email_providers.smtp import SMTPProvider
        return SMTPProvider(
            host=cfg['host'],
            port=int(cfg.get('port', 587)),
            username=cfg.get('username', ''),
            password=cfg.get('password', ''),
            use_ssl=cfg.get('use_ssl', False),
            use_tls=cfg.get('use_tls', True),
        )

    raise ValueError(f"Unsupported provider_type: {row.provider_type}")
