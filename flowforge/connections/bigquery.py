import json
import logging
import time
from typing import Any

from flowforge.connections.base import BaseConnection

logger = logging.getLogger(__name__)


def _bq_param_type(value: Any) -> str:
    if isinstance(value, bool):
        return 'BOOL'
    if isinstance(value, int):
        return 'INT64'
    if isinstance(value, float):
        return 'FLOAT64'
    return 'STRING'


class BigQueryConnection(BaseConnection):
    """Google BigQuery. Unlike DBAPI connectors, queries run as async jobs and
    parameters are bound by name (@p0, @p1, ...) rather than positional '%s' —
    make_placeholders()/execute_* translate the tuple-based BaseConnection
    interface into BigQuery's named-parameter QueryJobConfig.
    """

    db_type = 'bigquery'

    def __init__(self, project_id: str, dataset: str = '', credentials_json: str = ''):
        try:
            from google.cloud import bigquery
        except ImportError:
            raise ImportError(
                "google-cloud-bigquery is required for BigQuery connections. "
                "Install with: pip install flowforge[bigquery]"
            )
        self._bigquery = bigquery
        self.dataset = dataset

        if credentials_json:
            from google.oauth2 import service_account
            info = json.loads(credentials_json)
            creds = service_account.Credentials.from_service_account_info(info)
            self._client = bigquery.Client(project=project_id, credentials=creds)
        else:
            self._client = bigquery.Client(project=project_id)
        logger.debug("BigQuery client created for project %s", project_id)

    def _job_config(self, params: tuple):
        if not params:
            return None
        query_params = [
            self._bigquery.ScalarQueryParameter(f'p{i}', _bq_param_type(v), v)
            for i, v in enumerate(params)
        ]
        return self._bigquery.QueryJobConfig(query_parameters=query_params)

    def execute_procedure(self, name: str, params: dict[str, Any]) -> None:
        placeholders = self.make_placeholders(len(params))
        sql = f"CALL {name}({placeholders})"
        job = self._client.query(sql, job_config=self._job_config(tuple(params.values())))
        job.result()
        logger.debug("Called BigQuery procedure %s", name)

    def execute_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        job = self._client.query(sql, job_config=self._job_config(params))
        return [tuple(row.values()) for row in job.result()]

    def execute_query_with_columns(self, sql: str, params: tuple = ()) -> tuple[list[tuple], list[str]]:
        job = self._client.query(sql, job_config=self._job_config(params))
        result = job.result()
        columns = [field.name for field in result.schema]
        return [tuple(row.values()) for row in result], columns

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        job = self._client.query(sql, job_config=self._job_config(params))
        job.result()
        return job.num_dml_affected_rows or 0

    def execute_many(self, sql: str, rows: list[tuple]) -> int:
        # BigQuery has no DBAPI-style executemany; each row runs as its own query job.
        total = 0
        for row in rows:
            job = self._client.query(sql, job_config=self._job_config(row))
            job.result()
            total += job.num_dml_affected_rows or 0
        return total

    def make_placeholders(self, n: int) -> str:
        return ', '.join(f'@p{i}' for i in range(n))

    def test(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            self.execute_query("SELECT 1")
            return True, int((time.monotonic() - start) * 1000)
        except Exception:
            logger.exception("BigQuery connection test failed")
            return False, 0

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass
