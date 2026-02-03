"""Microsoft SQL Server connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class SQLServerConnector(Connector):
    """
    Connector for Microsoft SQL Server.

    Uses pyodbc or pymssql to connect to SQL Server.

    Examples:
        # Using connection string
        data = connect(
            "mssql://user:pass@server/database",
            table="orders"
        )

        # Using options
        data = connect(
            "sqlserver://server/database",
            table="orders",
            user="myuser",
            password="mypass",
            schema="dbo"
        )

        # Using trusted connection (Windows auth)
        data = connect(
            "mssql://server/database",
            table="orders",
            trusted_connection=True
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._connection = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to SQL Server and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        # Try pyodbc first, then pymssql
        import importlib.util

        if importlib.util.find_spec("pyodbc") is not None:
            driver_module = "pyodbc"
        elif importlib.util.find_spec("pymssql") is not None:
            driver_module = "pymssql"
        else:
            raise ImportError(
                "SQL Server support requires pyodbc or pymssql. "
                "Install with: pip install duckguard[sqlserver]"
            )

        if not config.table:
            raise ValueError("Table name is required for SQL Server connections")

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Connect using the available driver
        if driver_module == "pyodbc":
            self._connection = self._connect_pyodbc(conn_params)
        else:
            self._connection = self._connect_pymssql(conn_params)

        table = config.table
        schema = config.schema or conn_params.get("schema", "dbo")

        # Build fully qualified table name
        fq_table = f"[{schema}].[{table}]"

        return SQLServerDataset(
            source=fq_table,
            engine=self.engine,
            name=table,
            connection=self._connection,
        )

    def _connect_pyodbc(self, params: dict) -> Any:
        """Connect using pyodbc."""
        import pyodbc

        # Build connection string
        conn_str_parts = []

        driver = params.get("driver", "ODBC Driver 17 for SQL Server")
        conn_str_parts.append(f"DRIVER={{{driver}}}")

        conn_str_parts.append(f"SERVER={params.get('host', 'localhost')}")

        if params.get("port"):
            conn_str_parts[-1] += f",{params['port']}"

        conn_str_parts.append(f"DATABASE={params.get('database', '')}")

        if params.get("trusted_connection"):
            conn_str_parts.append("Trusted_Connection=yes")
        else:
            conn_str_parts.append(f"UID={params.get('user', '')}")
            conn_str_parts.append(f"PWD={params.get('password', '')}")

        conn_str = ";".join(conn_str_parts)
        return pyodbc.connect(conn_str)

    def _connect_pymssql(self, params: dict) -> Any:
        """Connect using pymssql."""
        import pymssql

        return pymssql.connect(
            server=params.get("host", "localhost"),
            port=params.get("port", "1433"),
            user=params.get("user", ""),
            password=params.get("password", ""),
            database=params.get("database", ""),
        )

    def _parse_connection_string(self, conn_string: str, config: ConnectionConfig) -> dict:
        """Parse SQL Server connection string."""
        params: dict[str, Any] = {}

        # Normalize prefixes
        conn_string_lower = conn_string.lower()
        if conn_string_lower.startswith(("mssql://", "sqlserver://")):
            # Convert to standard URL format for parsing
            if conn_string_lower.startswith("mssql://"):
                conn_string = "mssql://" + conn_string[8:]
            else:
                conn_string = "mssql://" + conn_string[12:]

            parsed = urlparse(conn_string)

            params["host"] = parsed.hostname or "localhost"
            params["port"] = str(parsed.port) if parsed.port else "1433"
            params["database"] = parsed.path.lstrip("/") if parsed.path else ""
            params["user"] = parsed.username or ""
            params["password"] = parsed.password or ""

            # Parse query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    params[key] = values[0] if len(values) == 1 else values

        # Override with config options
        options = config.options or {}
        for key in [
            "user",
            "password",
            "host",
            "port",
            "database",
            "schema",
            "driver",
            "trusted_connection",
        ]:
            if key in options:
                params[key] = options[key]

        if config.database:
            params["database"] = config.database
        if config.schema:
            params["schema"] = config.schema

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a SQL Server connection string."""
        source_lower = source.lower()
        return source_lower.startswith(("mssql://", "sqlserver://", "mssql+pyodbc://"))

    @classmethod
    def get_priority(cls) -> int:
        """SQL Server connector has high priority."""
        return 55


class SQLServerDataset(Dataset):
    """Dataset that queries SQL Server directly."""

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        connection: Any,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._mssql_connection = connection

    def _execute_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a query on SQL Server."""
        cursor = self._mssql_connection.cursor()
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
        """Get row count from SQL Server."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from SQL Server."""
        if self._columns_cache is None:
            cursor = self._mssql_connection.cursor()
            try:
                cursor.execute(f"SELECT TOP 0 * FROM {self._source}")
                self._columns_cache = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return self._columns_cache
