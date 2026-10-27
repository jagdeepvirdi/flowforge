"""Reusable input-length and type validators for API routes.

Column widths mirror the SQLAlchemy models (String(N) → N chars).
All functions return (value, error_string | None).  A non-None error string
should be returned as a 400 response.
"""
from __future__ import annotations

from flowforge.net_guard import UnsafeUrlError, check_url_syntax


def _check_len(value: str | None, field: str, max_len: int) -> str | None:
    if value and len(value) > max_len:
        return f"'{field}' must be {max_len} characters or fewer (got {len(value)})"
    return None


def validate_webhook_url(url: str | None, field: str = 'on_failure_webhook_url') -> str | None:
    """Reject obviously-unsafe outbound URLs at save time (scheme, hostname, literal private IPs).

    DNS-based checks happen at send time in net_guard.safe_urlopen — they must, since a name can
    resolve differently later — so this only gives the editor an early, clear 400.
    """
    if not url:
        return None
    try:
        check_url_syntax(str(url))
    except UnsafeUrlError:
        # Fixed message on purpose: never echo exception text (or the submitted URL) back to the client.
        return (f"'{field}' must be a public http(s) URL — internal, loopback, link-local and "
                "non-http(s) targets are not allowed")
    return _check_len(str(url), field, 2000)


def validate_pipeline(data: dict) -> str | None:
    for err in (
        _check_len(data.get('name'),        'name',        255),
        _check_len(data.get('description'), 'description', 2000),
        _check_len(data.get('schedule'),    'schedule',    100),
        validate_webhook_url(data.get('on_failure_webhook_url')),
    ):
        if err:
            return err
    return None


def validate_pipeline_step(data: dict) -> str | None:
    return _check_len(data.get('name'), 'name', 255)


def validate_pipeline_variable(data: dict) -> str | None:
    return _check_len(data.get('var_key'), 'var_key', 100)


def validate_report(data: dict) -> str | None:
    for err in (
        _check_len(data.get('name'),            'name',            255),
        _check_len(data.get('output_filename'), 'output_filename', 500),
        _check_len(data.get('title'),           'title',           255),
        _check_len(data.get('sheet_name'),      'sheet_name',      100),
        _check_len(data.get('template_path'),   'template_path',   500),
    ):
        if err:
            return err
    return None


def validate_email_config(data: dict) -> str | None:
    for err in (
        _check_len(data.get('name'),        'name',        255),
        _check_len(data.get('subject'),     'subject',     500),
        _check_len(data.get('header_text'), 'header_text', 500),
        _check_len(data.get('from_name'),   'from_name',   255),
    ):
        if err:
            return err
    return None


def validate_recipient_group(data: dict) -> str | None:
    return _check_len(data.get('name'), 'name', 100)


def validate_connection(data: dict) -> str | None:
    return _check_len(data.get('name'), 'name', 100)


def validate_provider(data: dict) -> str | None:
    return _check_len(data.get('name'), 'name', 100)


def validate_project(data: dict) -> str | None:
    return _check_len(data.get('name'), 'name', 100)
