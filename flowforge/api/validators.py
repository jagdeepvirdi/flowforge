"""Reusable input-length and type validators for API routes.

Column widths mirror the SQLAlchemy models (String(N) → N chars).
All functions return (value, error_string | None).  A non-None error string
should be returned as a 400 response.
"""
from __future__ import annotations


def _check_len(value: str | None, field: str, max_len: int) -> str | None:
    if value and len(value) > max_len:
        return f"'{field}' must be {max_len} characters or fewer (got {len(value)})"
    return None


def validate_pipeline(data: dict) -> str | None:
    for err in (
        _check_len(data.get('name'),        'name',        255),
        _check_len(data.get('description'), 'description', 2000),
        _check_len(data.get('schedule'),    'schedule',    100),
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
