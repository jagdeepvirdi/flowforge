"""Contract test (Phase 13.2 TEST-1): every registered connection/provider
class fully implements its ABC — catches "added a class but forgot an
abstract method" automatically, without needing live credentials to instantiate it.
"""
import importlib

import pytest

from flowforge.connections.base import BaseConnection
from flowforge.connections.factory import connections_registry
from flowforge.email_providers.base import EmailProvider
from flowforge.email_providers.factory import providers_registry


def _resolve(dotted_path: str):
    module_path, class_name = dotted_path.rsplit('.', 1)
    return getattr(importlib.import_module(module_path), class_name)


@pytest.mark.parametrize('db_type', connections_registry.list())
def test_connection_class_satisfies_base_connection(db_type):
    dotted_path, _kwargs_fn = connections_registry.get(db_type)
    cls = _resolve(dotted_path)
    assert issubclass(cls, BaseConnection)
    assert not cls.__abstractmethods__, (
        f"{cls.__name__} ({db_type}) is missing: {sorted(cls.__abstractmethods__)}"
    )


@pytest.mark.parametrize('provider_type', providers_registry.list())
def test_provider_class_satisfies_email_provider(provider_type):
    dotted_path, _kwargs_fn = providers_registry.get(provider_type)
    cls = _resolve(dotted_path)
    assert issubclass(cls, EmailProvider)
    assert not cls.__abstractmethods__, (
        f"{cls.__name__} ({provider_type}) is missing: {sorted(cls.__abstractmethods__)}"
    )


def test_registry_has_all_expected_connection_types():
    assert connections_registry.list() == [
        'bigquery', 'mssql', 'mysql', 'odbc', 'oracle', 'postgresql', 'redshift', 'snowflake',
    ]


def test_registry_has_all_expected_provider_types():
    assert providers_registry.list() == [
        'gmail', 'mailgun', 'microsoft365', 'sendgrid', 'ses', 'smtp',
    ]
