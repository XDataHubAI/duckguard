"""Snowflake connector."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class SnowflakeConnector(Connector):
    """
    Connector for Snowflake data warehouse.

    Uses the snowflake-connector-python package to connect and query,
    then processes results with DuckDB for validation.

    Examples:
        # Using connection string
        data = connect(
            "snowflake://user:pass@account/database/schema",
            table="orders"
        )

        # Using options
        data = connect(
            "snowflake://account",
            table="orders",
            user="myuser",
            password="mypass",
            database="mydb",
            schema="public",
            warehouse="compute_wh"
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._connection = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to Snowflake and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        try:
            import snowflake.connector
        except ImportError:
            raise ImportError(
                "Snowflake support requires snowflake-connector-python. "
                "Install with: pip install duckguard[snowflake]"
            )

        if not config.table:
            raise ValueError("Table name is required for Snowflake connections")

        # Parse connection parameters
        conn_params = self._parse_connection_string(config.source, config)

        # Connect to Snowflake
        self._connection = snowflake.connector.connect(**conn_params)

        table = config.table
        schema = config.schema or conn_params.get("schema", "PUBLIC")
        database = config.database or conn_params.get("database", "")

        # Build fully qualified table name
        if database and schema:
            fq_table = f"{database}.{schema}.{table}"
        elif schema:
            fq_table = f"{schema}.{table}"
        else:
            fq_table = table

        # Create a wrapper dataset that uses Snowflake for queries
        return SnowflakeDataset(
            source=fq_table,
            engine=self.engine,
            name=table,
            connection=self._connection,
            conn_params=conn_params,
        )

    def _parse_connection_string(
        self, conn_string: str, config: ConnectionConfig
    ) -> dict[str, Any]:
        """Parse Snowflake connection string and merge with config options."""
        params: dict[str, Any] = {}

        # Parse URL format: snowflake://user:pass@account/database/schema
        if conn_string.lower().startswith("snowflake://"):
            parsed = urlparse(conn_string)

            params["account"] = parsed.hostname or ""
            if parsed.username:
                params["user"] = parsed.username
            if parsed.password:
                params["password"] = parsed.password

            # Parse path for database/schema
            path_parts = [p for p in parsed.path.split("/") if p]
            if len(path_parts) >= 1:
                params["database"] = path_parts[0]
            if len(path_parts) >= 2:
                params["schema"] = path_parts[1]

            # Parse query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    params[key] = values[0] if len(values) == 1 else values

        # Override with config options
        options = config.options or {}
        for key in ["user", "password", "account", "warehouse", "role", "database", "schema"]:
            if key in options:
                params[key] = options[key]

        if config.database:
            params["database"] = config.database
        if config.schema:
            params["schema"] = config.schema

        return params

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a Snowflake connection string."""
        return source.lower().startswith("snowflake://")

    @classmethod
    def get_priority(cls) -> int:
        """Snowflake connector has high priority."""
        return 60


class SnowflakeDataset(Dataset):
    """
    Dataset that queries Snowflake directly for statistics.

    Uses query pushdown to compute aggregations in Snowflake,
    minimizing data transfer.
    """

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        connection: Any,
        conn_params: dict[str, Any],
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._sf_connection = connection
        self._sf_params = conn_params

    def _execute_sf_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a query on Snowflake."""
        cursor = self._sf_connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _fetch_sf_value(self, sql: str) -> Any:
        """Execute query and return single value."""
        rows = self._execute_sf_query(sql)
        return rows[0][0] if rows else None

    @property
    def row_count(self) -> int:
        """Get row count from Snowflake."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_sf_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from Snowflake."""
        if self._columns_cache is None:
            sql = f"SELECT * FROM {self._source} LIMIT 0"
            cursor = self._sf_connection.cursor()
            try:
                cursor.execute(sql)
                self._columns_cache = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return self._columns_cache


class SnowflakeColumn:
    """Column that queries Snowflake directly."""

    def __init__(self, name: str, dataset: SnowflakeDataset):
        self._name = name
        self._dataset = dataset

    @property
    def null_percent(self) -> float:
        """Get null percentage from Snowflake."""
        sql = f"""
        SELECT
            ROUND(100.0 * SUM(CASE WHEN "{self._name}" IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2)
        FROM {self._dataset._source}
        """
        return self._dataset._fetch_sf_value(sql) or 0.0

    @property
    def unique_percent(self) -> float:
        """Get unique percentage from Snowflake."""
        sql = f"""
        SELECT
            ROUND(100.0 * COUNT(DISTINCT "{self._name}") / COUNT(*), 2)
        FROM {self._dataset._source}
        """
        return self._dataset._fetch_sf_value(sql) or 0.0
