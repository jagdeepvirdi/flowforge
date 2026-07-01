"""Unit tests for flowforge/connections/bigquery.py — mocks google.cloud.bigquery."""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch


def _make_row(values):
    row = MagicMock()
    row.values.return_value = values
    return row


def _make_bigquery_mock(query_result_rows=None, schema_fields=('col1', 'col2'), num_dml_affected_rows=1):
    query_result_rows = query_result_rows or [(1, 'a'), (2, 'b')]

    result_rows = [_make_row(list(v)) for v in query_result_rows]
    result = MagicMock()
    result.__iter__ = MagicMock(return_value=iter(result_rows))
    result.schema = [MagicMock(name=f) for f in schema_fields]
    for field_mock, name in zip(result.schema, schema_fields, strict=False):
        field_mock.name = name

    job = MagicMock()
    job.result.return_value = result
    job.num_dml_affected_rows = num_dml_affected_rows

    client = MagicMock()
    client.query.return_value = job

    bigquery_mod = ModuleType('google.cloud.bigquery')
    bigquery_mod.Client = MagicMock(return_value=client)
    bigquery_mod.ScalarQueryParameter = MagicMock(side_effect=lambda name, type_, value: (name, type_, value))
    bigquery_mod.QueryJobConfig = MagicMock(side_effect=lambda query_parameters=None: {'query_parameters': query_parameters})

    google_pkg = ModuleType('google')
    google_cloud_pkg = ModuleType('google.cloud')
    google_cloud_pkg.bigquery = bigquery_mod
    google_pkg.cloud = google_cloud_pkg

    return google_pkg, google_cloud_pkg, bigquery_mod, client, job


def _build(google_pkg, google_cloud_pkg, bigquery_mod, **kwargs):
    with patch.dict(sys.modules, {
        'google': google_pkg,
        'google.cloud': google_cloud_pkg,
        'google.cloud.bigquery': bigquery_mod,
    }):
        from flowforge.connections.bigquery import BigQueryConnection
        return BigQueryConnection(
            project_id=kwargs.get('project_id', 'my-project'),
            dataset=kwargs.get('dataset', 'my_dataset'),
        )


def test_import_error_when_driver_missing():
    with patch.dict(sys.modules, {'google.cloud.bigquery': None}):
        from flowforge.connections.bigquery import BigQueryConnection
        try:
            BigQueryConnection(project_id='p')
            raise AssertionError("expected ImportError")
        except ImportError as e:
            assert 'google-cloud-bigquery' in str(e)


def test_db_type():
    from flowforge.connections.bigquery import BigQueryConnection
    assert BigQueryConnection.db_type == 'bigquery'


def test_client_created_with_project():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    _build(google_pkg, google_cloud_pkg, bigquery_mod, project_id='proj-123')
    _, kwargs = bigquery_mod.Client.call_args
    assert kwargs['project'] == 'proj-123'


def test_execute_query_returns_row_tuples():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock(query_result_rows=[(1, 'a'), (2, 'b')])
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    rows = conn.execute_query("SELECT * FROM t")
    assert rows == [(1, 'a'), (2, 'b')]


def test_execute_query_with_columns():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock(schema_fields=('a', 'b'))
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    rows, columns = conn.execute_query_with_columns("SELECT * FROM t")
    assert columns == ['a', 'b']


def test_execute_write_returns_affected_rows():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock(num_dml_affected_rows=7)
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    affected = conn.execute_write("UPDATE t SET x=1")
    assert affected == 7


def test_make_placeholders_uses_named_params():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    assert conn.make_placeholders(3) == '@p0, @p1, @p2'


def test_execute_query_with_params_builds_scalar_query_parameters():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    conn.execute_query("SELECT * FROM t WHERE x=@p0", params=(42,))
    bigquery_mod.ScalarQueryParameter.assert_called_with('p0', 'INT64', 42)


def test_execute_procedure_builds_call_statement():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    conn.execute_procedure('my_proc', {'a': 1, 'b': 'x'})
    sql = client.query.call_args[0][0]
    assert sql == 'CALL my_proc(@p0, @p1)'


def test_execute_many_runs_one_job_per_row():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock(num_dml_affected_rows=1)
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    total = conn.execute_many("INSERT INTO t VALUES (@p0)", [(1,), (2,), (3,)])
    assert total == 3
    assert client.query.call_count == 3


def test_test_success():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    ok, latency = conn.test()
    assert ok is True


def test_test_failure_returns_false():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    client.query.side_effect = Exception('boom')
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    ok, latency = conn.test()
    assert ok is False
    assert latency == 0


def test_close_swallows_exceptions():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    conn = _build(google_pkg, google_cloud_pkg, bigquery_mod)
    client.close.side_effect = Exception('already closed')
    conn.close()  # must not raise


def test_credentials_json_uses_service_account():
    google_pkg, google_cloud_pkg, bigquery_mod, client, job = _make_bigquery_mock()
    service_account_mod = ModuleType('google.oauth2.service_account')
    mock_creds = MagicMock()
    service_account_mod.Credentials = MagicMock()
    service_account_mod.Credentials.from_service_account_info = MagicMock(return_value=mock_creds)
    oauth2_pkg = ModuleType('google.oauth2')
    oauth2_pkg.service_account = service_account_mod

    with patch.dict(sys.modules, {
        'google': google_pkg,
        'google.cloud': google_cloud_pkg,
        'google.cloud.bigquery': bigquery_mod,
        'google.oauth2': oauth2_pkg,
        'google.oauth2.service_account': service_account_mod,
    }):
        from flowforge.connections.bigquery import BigQueryConnection
        BigQueryConnection(project_id='p', credentials_json='{"type": "service_account"}')

    service_account_mod.Credentials.from_service_account_info.assert_called_once()
    _, kwargs = bigquery_mod.Client.call_args
    assert kwargs['credentials'] is mock_creds
