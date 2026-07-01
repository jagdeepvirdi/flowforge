import logging

from flowforge.connections.postgres import PostgreSQLConnection

logger = logging.getLogger(__name__)


class RedshiftConnection(PostgreSQLConnection):
    """Amazon Redshift — wire-compatible with PostgreSQL, so this only overrides
    the type tag and default port; execute_*/make_placeholders/test/close are
    inherited unchanged from PostgreSQLConnection.
    """

    db_type = 'redshift'

    def __init__(self, host: str, database: str, user: str, password: str, port: int = 5439):
        super().__init__(host=host, database=database, user=user, password=password, port=port)
