"""Databricks connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class DatabricksConnector(Connector):
    """
    Connector for Databricks SQL Warehouse and Unity Catalog.

    Uses the databricks-sql-connector package for efficient querying.

    Examples:
        # Using connection string
        data = connect(
            "databricks://workspace.cloud.databricks.com/catalog/schema",
            table="orders",
            token="dapi..."
        )

        # Using options
        data = connect(
            "databricks://workspace.cloud.databricks.com",
            table="orders",
            catalog="main",
            schema="default",
            http_path="/sql/1.0/warehouses/abc123",
            token="dapi..."
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._connection = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to Databricks and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            from databricks import sql as databricks_sql
        except ImportError:
            raise ImportError(
                "Databricks support requires databricks-sql-connector. "
                "Install with: pip install duckguard[databricks]"
            )

        if not config.table:
            raise ValueError("Table name is required for Databricks connections")

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Validate required parameters
        if not conn_params.get("server_hostname"):
            raise ValueError("Databricks server hostname is required")
        if not conn_params.get("http_path"):
            raise ValueError("Databricks http_path is required (SQL Warehouse path)")
        if not conn_params.get("access_token"):
            raise ValueError("Databricks access token is required")

        # Connect to Databricks
        self._connection = databricks_sql.connect(
            server_hostname=conn_params["server_hostname"],
            http_path=conn_params["http_path"],
            access_token=conn_params["access_token"],
        )

        table = config.table
        catalog = conn_params.get("catalog", "main")
        schema = config.schema or conn_params.get("schema", "default")

        # Build fully qualified table name
        fq_table = f"`{catalog}`.`{schema}`.`{table}`"

        return DatabricksDataset(
            source=fq_table,
            engine=self.engine,
            name=table,
            connection=self._connection,
        )

    def _parse_connection_string(
        self, conn_string: str, config: ConnectionConfig
    ) -> dict[str, Any]:
        """Parse Databricks connection string and merge with config options."""
        params: dict[str, Any] = {}

        # Parse URL format: databricks://workspace.cloud.databricks.com/catalog/schema
        if conn_string.lower().startswith("databricks://"):
            parsed = urlparse(conn_string)

            params["server_hostname"] = parsed.hostname or ""

            # Parse path for catalog/schema
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 1:
                params["catalog"] = path_parts[0]
            if len(path_parts) >= 2:
                params["schema"] = path_parts[1]

            # Parse query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    params[key] = values[0] if len(values) == 1 else values

        # Override with config options
        options = config.options or {}
        for key in [
            "server_hostname",
            "http_path",
            "access_token",
            "token",
            "catalog",
            "schema",
        ]:
            if key in options:
                # Handle token alias
                if key == "token":
                    params["access_token"] = options[key]
                else:
                    params[key] = options[key]

        if config.database:
            params["catalog"] = config.database
        if config.schema:
            params["schema"] = config.schema

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a Databricks connection string."""
        source_lower = source.lower()
        return source_lower.startswith("databricks://") or ".databricks.com" in source_lower

    @classmethod
    def get_priority(cls) -> int:
        """Databricks connector has high priority."""
        return 60


class DatabricksDataset(Dataset):
    """Dataset that queries Databricks directly."""

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        connection: Any,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._db_connection = connection

    def _execute_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a query on Databricks."""
        cursor = self._db_connection.cursor()
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
        """Get row count from Databricks."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from Databricks."""
        if self._columns_cache is None:
            cursor = self._db_connection.cursor()
            try:
                cursor.execute(f"SELECT * FROM {self._source} LIMIT 0")
                self._columns_cache = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return self._columns_cache
