"""Connections to FlowForge's own database are refused unless explicitly allowed."""
import uuid
from unittest.mock import patch

import pytest

from flowforge.connections import internal_guard
from flowforge.connections.internal_guard import (
    ALLOW_ENV,
    InternalDatabaseConnectionError,
    check_allowed,
    check_config,
    targets_internal_db,
)

INTERNAL_URL = 'postgresql://ffuser:s3cretpw@meta.example.internal:5432/flowforge_meta'


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_DB_URL', INTERNAL_URL)
    monkeypatch.delenv(ALLOW_ENV, raising=False)   # the suite's conftest allows it globally


# -- matching -----------------------------------------------------------------------------

def test_exact_match_is_internal():
    assert targets_internal_db('meta.example.internal', 5432, 'flowforge_meta')


def test_host_comparison_is_case_insensitive_and_port_may_be_a_string_or_missing():
    assert targets_internal_db('META.Example.Internal', '5432', 'flowforge_meta')
    assert targets_internal_db('meta.example.internal', None, 'flowforge_meta')   # defaults to 5432


@pytest.mark.parametrize('host,port,db', [
    ('meta.example.internal', 5432, 'billing'),          # other database on the same server
    ('meta.example.internal', 5433, 'flowforge_meta'),   # other port
    ('other.example.com', 5432, 'flowforge_meta'),       # other host
    ('meta.example.internal', 'abc', 'flowforge_meta'),  # junk port: do not crash, do not match
])
def test_other_targets_are_not_internal(host, port, db):
    with patch.object(internal_guard.socket, 'getaddrinfo', side_effect=OSError):
        assert not targets_internal_db(host, port, db)


def test_loopback_aliases_match_each_other(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_DB_URL', 'postgresql://u:p@localhost:5432/flowforge')
    for alias in ('localhost', '127.0.0.1', '::1', '', 'LOCALHOST'):
        assert targets_internal_db(alias, 5432, 'flowforge'), alias


def test_different_names_resolving_to_the_same_address_match():
    def fake(host, port, *a, **k):
        ip = {'meta.example.internal': '10.1.2.3', 'alias.example.com': '10.1.2.3'}.get(host, '10.9.9.9')
        return [(2, 1, 6, '', (ip, 0))]
    with patch.object(internal_guard.socket, 'getaddrinfo', fake):
        assert targets_internal_db('alias.example.com', 5432, 'flowforge_meta')
        assert not targets_internal_db('elsewhere.example.com', 5432, 'flowforge_meta')


def test_driver_suffix_in_url_is_understood(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_DB_URL', 'postgresql+psycopg2://u:p@meta.example.internal/flowforge_meta')
    assert targets_internal_db('meta.example.internal', 5432, 'flowforge_meta')


def test_non_postgres_or_missing_url_never_matches(monkeypatch):
    monkeypatch.setenv('FLOWFORGE_DB_URL', 'sqlite:///x.db')
    assert not targets_internal_db('localhost', 5432, 'x.db')
    monkeypatch.delenv('FLOWFORGE_DB_URL')
    assert not targets_internal_db('localhost', 5432, 'flowforge')


# -- enforcement --------------------------------------------------------------------------

def test_check_allowed_raises_without_leaking_the_url():
    with pytest.raises(InternalDatabaseConnectionError) as e:
        check_allowed('meta.example.internal', 5432, 'flowforge_meta')
    msg = str(e.value)
    assert 's3cretpw' not in msg and 'ffuser' not in msg and 'meta.example.internal' not in msg
    assert ALLOW_ENV in msg                                    # tells the operator how to opt out


@pytest.mark.parametrize('value', ['true', 'TRUE', '1', 'yes'])
def test_opt_out_allows_it(monkeypatch, value):
    monkeypatch.setenv(ALLOW_ENV, value)
    check_allowed('meta.example.internal', 5432, 'flowforge_meta')


@pytest.mark.parametrize('value', ['', 'false', '0', 'no', 'maybe'])
def test_anything_but_an_explicit_yes_does_not_opt_out(monkeypatch, value):
    monkeypatch.setenv(ALLOW_ENV, value)
    with pytest.raises(InternalDatabaseConnectionError):
        check_allowed('meta.example.internal', 5432, 'flowforge_meta')


def test_unrelated_connections_pass():
    check_allowed('warehouse.example.com', 5432, 'billing')


def test_check_config_applies_to_postgresql_only():
    cfg = {'host': 'meta.example.internal', 'port': 5432, 'database': 'flowforge_meta'}
    with pytest.raises(InternalDatabaseConnectionError):
        check_config('postgresql', cfg)
    check_config('oracle', cfg)          # a different server type cannot be FlowForge's PostgreSQL
    check_config('postgresql', None)     # malformed config is validated elsewhere


def test_postgres_constructor_refuses_before_opening_any_pool():
    from flowforge.connections import postgres
    with patch.object(postgres.pool, 'ThreadedConnectionPool') as pool_cls:
        with pytest.raises(InternalDatabaseConnectionError):
            postgres.PostgreSQLConnection('meta.example.internal', 'flowforge_meta', 'u', 'p', 5432)
        pool_cls.assert_not_called()


def test_env_fallback_path_in_a_step_is_covered_too(monkeypatch):
    """db_query falls back to DB_HOST/DB_NAME when no connection_id is set; it must hit the guard."""
    from flowforge.connections import postgres
    from flowforge.steps.db_query import DbQueryStep
    monkeypatch.setenv('DB_HOST', 'meta.example.internal')
    monkeypatch.setenv('DB_NAME', 'flowforge_meta')
    step = DbQueryStep('q', {'query': 'SELECT 1'})
    with patch.object(postgres.pool, 'ThreadedConnectionPool') as pool_cls:
        with pytest.raises(InternalDatabaseConnectionError):
            step._get_connection()
        pool_cls.assert_not_called()


# -- REST routes (need the app fixtures / test database) -------------------------------------

def _internal_cfg(live_db_config):
    return {'host': live_db_config['host'], 'port': live_db_config['port'],
            'database': live_db_config['database'], 'username': live_db_config['username'],
            'password': live_db_config['password']}


def test_route_create_refuses_internal_db(client, headers, live_db_config):
    name = f'internal-{uuid.uuid4().hex[:8]}'
    r = client.post('/api/db-connections', headers=headers,
                    json={'name': name, 'db_type': 'postgresql', 'config': _internal_cfg(live_db_config)})
    assert r.status_code == 400, r.get_json()
    assert 'own database' in r.get_json()['error']
    names = [c['name'] for c in client.get('/api/db-connections', headers=headers).get_json()]
    assert name not in names


def test_route_create_allows_internal_db_with_opt_out(client, headers, live_db_config, monkeypatch):
    monkeypatch.setenv(ALLOW_ENV, 'true')
    r = client.post('/api/db-connections', headers=headers,
                    json={'name': f'internal-{uuid.uuid4().hex[:8]}', 'db_type': 'postgresql',
                          'config': _internal_cfg(live_db_config)})
    assert r.status_code == 201, r.get_json()
    client.delete(f"/api/db-connections/{r.get_json()['id']}", headers=headers)


def test_route_update_cannot_repoint_a_connection_at_the_internal_db(client, headers, live_db_config, monkeypatch):
    ext = {'host': 'warehouse.example.com', 'port': 5432, 'database': 'billing', 'username': 'u', 'password': 'p'}
    created = client.post('/api/db-connections', headers=headers,
                          json={'name': f'ext-{uuid.uuid4().hex[:8]}', 'db_type': 'postgresql', 'config': ext})
    assert created.status_code == 201, created.get_json()
    cid = created.get_json()['id']
    try:
        monkeypatch.delenv(ALLOW_ENV, raising=False)
        r = client.put(f'/api/db-connections/{cid}', headers=headers,
                       json={'config': {'host': live_db_config['host'], 'port': live_db_config['port'],
                                        'database': live_db_config['database']}})
        assert r.status_code == 400, r.get_json()
        cfg = client.get(f'/api/db-connections/{cid}', headers=headers).get_json()['config']
        assert cfg['host'] == 'warehouse.example.com'            # unchanged
    finally:
        client.delete(f'/api/db-connections/{cid}', headers=headers)


def test_route_test_raw_refuses_internal_db_without_connecting(client, headers, live_db_config):
    with patch('psycopg2.connect') as connect:
        r = client.post('/api/db-connections/test-raw', headers=headers,
                        json={'db_type': 'postgresql', 'config': _internal_cfg(live_db_config)})
        connect.assert_not_called()
    assert r.status_code == 400 and r.get_json()['success'] is False
