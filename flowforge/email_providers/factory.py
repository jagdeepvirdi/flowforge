"""Load an email provider from the FlowForge config DB.

Dispatch by `provider_type` goes through `providers_registry` (see
flowforge/registry.py) instead of an if/elif chain — see
connections/factory.py for the identical pattern (including the
plugin-vs-built-in dispatch split in _build_provider() below) and why the
class is resolved by dotted path rather than imported eagerly.
"""
import importlib
from collections.abc import Callable
from typing import Any

from flowforge.email_providers.base import EmailProvider
from flowforge.registry import IntegrationSpec, Registry

providers_registry = Registry('email_providers')


def _register(key: str, dotted_path: str, kwargs_fn: Callable[[dict], dict],
              display_name: str, requires: str | None = None) -> None:
    providers_registry.register_spec(
        IntegrationSpec(key=key, display_name=display_name, requires=requires),
        (dotted_path, kwargs_fn),
    )


def _m365_kwargs(cfg: dict) -> dict:
    sender = cfg.get('sender_email') or cfg.get('sender', '')
    if not sender:
        raise ValueError(
            "Microsoft 365 provider config is missing 'sender' (the licensed M365 sender email address)"
        )
    return dict(
        tenant_id=cfg.get('tenant_id', ''),
        client_id=cfg.get('client_id', ''),
        client_secret=cfg.get('client_secret', ''),
        sender_email=sender,
    )


_register(
    'gmail', 'flowforge.email_providers.gmail.GmailProvider',
    lambda cfg: dict(
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        refresh_token=cfg['refresh_token'],
        sender=cfg['sender'],
    ),
    display_name='Gmail',
)

_register(
    'microsoft365', 'flowforge.email_providers.microsoft365.Microsoft365Provider',
    _m365_kwargs,
    display_name='Microsoft 365',
)

_register(
    'smtp', 'flowforge.email_providers.smtp.SMTPProvider',
    lambda cfg: dict(
        host=cfg['host'],
        port=int(cfg.get('port', 587)),
        username=cfg.get('username', ''),
        password=cfg.get('password', ''),
        use_ssl=cfg.get('use_ssl', False),
        use_tls=cfg.get('use_tls', True),
    ),
    display_name='SMTP',
)

_register(
    'sendgrid', 'flowforge.email_providers.sendgrid.SendGridProvider',
    lambda cfg: dict(
        api_key=cfg['api_key'],
        from_email=cfg['from_email'],
        from_name=cfg.get('from_name', ''),
    ),
    display_name='SendGrid', requires='sendgrid',
)

_register(
    'ses', 'flowforge.email_providers.ses.SESProvider',
    lambda cfg: dict(
        aws_access_key_id=cfg['aws_access_key_id'],
        aws_secret_access_key=cfg['aws_secret_access_key'],
        aws_region=cfg.get('aws_region', 'us-east-1'),
        from_email=cfg['from_email'],
        from_name=cfg.get('from_name', ''),
    ),
    display_name='Amazon SES', requires='ses',
)

_register(
    'mailgun', 'flowforge.email_providers.mailgun.MailgunProvider',
    lambda cfg: dict(
        api_key=cfg['api_key'],
        domain=cfg['domain'],
        from_email=cfg['from_email'],
        from_name=cfg.get('from_name', ''),
        region=cfg.get('region', 'us'),
    ),
    display_name='Mailgun', requires='mailgun',
)

# Snapshot of built-in provider_types, taken right after registration above —
# lets the plugin loader's test-reset helper drop only plugin-added entries.
BUILTIN_PROVIDER_TYPES = frozenset(providers_registry.list())


def _build_provider(provider_type: str, cfg: dict) -> EmailProvider:
    if provider_type not in providers_registry:
        raise ValueError(f"Unsupported provider_type: {provider_type}")

    entry = providers_registry.get(provider_type)

    if isinstance(entry, tuple):
        dotted_path, kwargs_fn = entry
        module_path, class_name = dotted_path.rsplit('.', 1)
        cls: Any = getattr(importlib.import_module(module_path), class_name)
        return cls(**kwargs_fn(cfg))

    # Plugin-registered provider: `entry` is the class itself.
    if not hasattr(entry, 'from_config'):
        raise ValueError(
            f"Plugin email provider '{provider_type}' ({entry.__name__}) must define a "
            "from_config(cls, cfg) classmethod"
        )
    return entry.from_config(cfg)


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
