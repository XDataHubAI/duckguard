"""Oracle Database connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class OracleConnector(Connector):
    """
    Connector for Oracle Database.

    Uses the oracledb (python-oracledb) package for connectivity.

    Examples:
        # Using connection string
        data = connect(
            "oracle://user:pass@host:1521/service_name",
            table="orders"
        )

        # Using TNS alias
        data = connect(
            "oracle://user:pass@tns_alias",
            table="orders"
        )

        # Using options
        data = connect(
            "oracle://host:1521/service_name",
            table="orders",
            user="myuser",
            password="mypass",
            schema="HR"
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._connection = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to Oracle and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            import oracledb
        except ImportError:
            raise ImportError(
                "Oracle support requires oracledb. "
                "Install with: pip install duckguard[oracle]"
            )

        if not config.table:
            raise ValueError("Table name is required for Oracle connections")

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Build connection
        if conn_params.get("dsn"):
            # Using DSN/TNS
            self._connection = oracledb.connect(
                user=conn_params.get("user"),
                password=conn_params.get("password"),
                dsn=conn_params["dsn"],
            )
        else:
            # Using host/port/service
            self._connection = oracledb.connect(
                user=conn_params.get("user"),
                password=conn_params.get("password"),
                host=conn_params.get("host", "localhost"),
                port=int(conn_params.get("port", 1521)),
                service_name=conn_params.get("service_name"),
            )

        table = config.table
        schema = config.schema or conn_params.get("schema", conn_params.get("user", "").upper())

        # Build fully qualified table name
        if schema:
            fq_table = f'"{schema}"."{table.upper()}"'
        else:
            fq_table = f'"{table.upper()}"'

        return OracleDataset(
            source=fq_table,
            engine=self.engine,
            name=table,
            connection=self._connection,
        )

    def _parse_connection_string(self, conn_string: str, config: ConnectionConfig) -> dict:
        """Parse Oracle connection string."""
        params: dict[str, Any] = {}

        # Parse URL format: oracle://user:pass@host:port/service_name
        if conn_string.lower().startswith("oracle://"):
            parsed = urlparse(conn_string)

            params["user"] = parsed.username or ""
            params["password"] = parsed.password or ""
            params["host"] = parsed.hostname or "localhost"
            params["port"] = str(parsed.port) if parsed.port else "1521"

            # Path is service name or SID
            if parsed.path:
                service = parsed.path.lstrip("/")
                if service:
                    params["service_name"] = service

            # Check if it's a TNS alias (no port specified and no dots in hostname)
            if not parsed.port and parsed.hostname and "." not in parsed.hostname:
                params["dsn"] = parsed.hostname

        # Override with config options
        options = config.options or {}
        for key in ["user", "password", "host", "port", "service_name", "dsn", "schema"]:
            if key in options:
                params[key] = options[key]

        if config.database:
            params["service_name"] = config.database
        if config.schema:
            params["schema"] = config.schema

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is an Oracle connection string."""
        return source.lower().startswith("oracle://")

    @classmethod
    def get_priority(cls) -> int:
        """Oracle connector has high priority."""
        return 55


class OracleDataset(Dataset):
    """Dataset that queries Oracle directly."""

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        connection: Any,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._ora_connection = connection

    def _execute_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a query on Oracle."""
        cursor = self._ora_connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _fetch_value(self, sql: str) -> Any:
        """Execute query and return single value."""
        rows = self._execute_query(sql)
        return rows[0][0] if rows else None

    @property
    def row_count(self) -> int:
        """Get row count from Oracle."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from Oracle."""
        if self._columns_cache is None:
            cursor = self._ora_connection.cursor()
            try:
                cursor.execute(f"SELECT * FROM {self._source} WHERE ROWNUM = 0")
                self._columns_cache = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return self._columns_cache
