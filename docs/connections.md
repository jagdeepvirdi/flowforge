# Database Connections

FlowForge talks to your data through a `db_connections` row (config UI: **Connections Manager**),
which any `db_procedure` / `db_query` step references by `connection_id`. All connection classes
implement the same `BaseConnection` interface (`flowforge/connections/base.py`) — `execute_procedure`,
`execute_query`, `execute_write`, `execute_many`, `make_placeholders`, `test`, `close` — so pipeline
steps don't know or care which database type they're talking to. `raw_connection` (a concrete
property, not abstract) exposes the underlying DB-API connection for the rare caller that needs
cursor-level control beyond those methods — see `flowforge/steps/bulk_load.py`'s Python-fallback and
PostgreSQL `COPY` paths.

## Supported Types

| `db_type` | Display Name | Extra Required | Config Fields |
|---|---|---|---|
| `postgresql` | PostgreSQL | — (built in) | `host`, `port` (5432), `database`, `user`, `password` |
| `oracle` | Oracle | `pip install -e .[oracle]` | `host`, `port` (1521), `service_name`, `user`, `password` |
| `mysql` | MySQL / MariaDB | `pip install -e .[mysql]` | `host`, `port` (3306), `database`, `user`, `password` |
| `mssql` | Microsoft SQL Server | `pip install -e .[mssql]` | `host`, `port` (1433), `database`, `user`, `password`, `driver` |
| `odbc` | Generic ODBC | `pip install -e .[mssql]` | `dsn` or `connection_string` |
| `redshift` | Amazon Redshift | — (uses the PostgreSQL wire protocol) | `host`, `port` (5439), `database`, `user`, `password` |
| `snowflake` | Snowflake | `pip install -e .[snowflake]` | `account`, `user`, `password`, `warehouse`, `database`, `schema`, `role` |
| `bigquery` | Google BigQuery | `pip install -e .[bigquery]` | `project_id`, `dataset`, `credentials_json` (service account JSON) |

This table is generated from `flowforge/connections/factory.py` — that file is the source of truth
if the two ever disagree. Oracle's `python-oracledb` driver runs in thin mode (no Oracle Instant
Client install required).

SSH is a separate connection type (`ff_ssh_connections` table, not `db_connections`) used by the
`ssh_command`, `ssh_health_check`, and `sftp_transfer` step types — see
[`step-types.md`](step-types.md) for those.

## Adding a Connection

**Connections Manager** → **Add Connection** → pick a type → fill in the type-specific form above →
**Test Connection** (calls `BaseConnection.test()`, which round-trips a trivial query and reports
latency) → **Save**.

## Credential Storage

`db_connections.config` is a JSONB column, encrypted at rest with AES-256-GCM
(`FLOWFORGE_SECRET_KEY`) — see [`security.md`](security.md#credential-encryption). Credentials are
decrypted only in-process, at the moment a connection is opened (`get_connection()` in
`factory.py`), and never logged or returned by the API after creation.

## Least Privilege

Scope each connection's DB user to only what its pipelines need:

- `db_query` steps only need `SELECT` on the tables/views their queries touch.
- `db_procedure` steps need `EXECUTE` on the specific procedure/package, not schema-wide DDL rights.
- `db_query` steps with `output_table` set need `INSERT`/`TRUNCATE` on that specific staging table
  only — not on the source tables the query reads from.
- Avoid reusing one admin-level credential across every connection in FlowForge; a compromised
  pipeline config (or a SQL injection bug in a downstream integration) has blast radius limited to
  what that one connection's DB user can do.

## Plugin Connections

Community-defined connection types can register themselves through the same `Registry` used for
built-ins (see [`plugins.md`](plugins.md)) — the only difference is a plugin class must implement a
`from_config(cls, cfg: dict)` classmethod itself, since the plugin loader passes the already-imported
class straight through instead of a lazy dotted-path + kwargs-builder pair.
