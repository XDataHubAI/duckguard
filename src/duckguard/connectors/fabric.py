"""Microsoft Fabric connector.

Supports two access patterns:
1. OneLake direct access (Parquet/Delta files on ADLS Gen2)
2. SQL endpoint (T-SQL compatible, via pyodbc)

Examples:
    # OneLake — Parquet files in a Lakehouse
    data = connect(
        "fabric://workspace/lakehouse/Tables/orders",
        token="eyJ..."
    )

    # OneLake — shorthand for ADLS Gen2 path
    data = connect(
        "onelake://workspace/lakehouse.Lakehouse/Files/orders.parquet",
        token="eyJ..."
    )

    # SQL endpoint
    data = connect(
        "fabric+sql://workspace-guid.datawarehouse.fabric.microsoft.com",
        table="orders",
        database="my_lakehouse",
        token="eyJ..."
    )
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class FabricConnector(Connector):
    """
    Connector for Microsoft Fabric (OneLake + SQL endpoints).

    Uses OneLake (ADLS Gen2) for direct file access or pyodbc for SQL endpoints.
    Authentication via Azure AD token (pass as `token` option).
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._connection = None

    def connect(self, config: ConnectionConfig) -> Dataset:
        """Connect to Microsoft Fabric and return a Dataset."""
        source_lower = config.source.lower()

        if source_lower.startswith("fabric+sql://"):
            return self._connect_sql(config)
        else:
            return self._connect_onelake(config)

    def _connect_onelake(self, config: ConnectionConfig) -> Dataset:
        """Connect via OneLake (ADLS Gen2 path)."""
        options = config.options or {}
        token = options.get("token", "")

        # Convert fabric:// or onelake:// to abfss:// path
        parsed = urlparse(config.source)
        path_parts = [p for p in parsed.path.split("/") if p]

        if len(path_parts) < 2:
            raise ValueError(
                "OneLake path must include workspace and lakehouse. "
                "Format: fabric://workspace/lakehouse/Tables/table_name"
            )

        workspace = parsed.hostname or path_parts[0]
        remaining = "/".join(path_parts)

        # Build ADLS Gen2 path
        # OneLake uses: https://onelake.dfs.fabric.microsoft.com/{workspace}/{item}/{path}
        onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace}/{remaining}"

        # If it looks like a Delta table or directory, try DuckDB's httpfs
        # DuckDB can read Parquet directly from HTTP(S) URLs
        try:
            self.engine.execute("INSTALL httpfs; LOAD httpfs;")
        except Exception:
            pass  # Already loaded

        # Set auth token if provided
        if token:
            try:
                self.engine.execute("SET azure_transport_option_type = 'curl'")
                self.engine.execute(f"SET azure_access_token = '{token}'")
            except Exception:
                pass

        # Determine table name
        table_name = path_parts[-1] if path_parts else "fabric_data"
        if "." in table_name:
            table_name = table_name.rsplit(".", 1)[0]

        return Dataset(
            source=onelake_url,
            engine=self.engine,
            name=table_name,
        )

    def _connect_sql(self, config: ConnectionConfig) -> Dataset:
        """Connect via Fabric SQL endpoint."""
        try:
            import pyodbc
        except ImportError:
            raise ImportError(
                "Microsoft Fabric SQL support requires pyodbc. "
                "Install with: pip install duckguard[fabric]"
            )

        if not config.table:
            raise ValueError("Table name is required for Fabric SQL connections")

        options = config.options or {}
        parsed = urlparse(config.source.replace("fabric+sql://", "https://"))
        server = parsed.hostname or ""

        token = options.get("token", "")
        database = config.database or options.get("database", "")

        # Build connection string for Fabric SQL endpoint
        # Fabric uses Azure AD token auth
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Authentication=ActiveDirectoryAccessToken;"
            f"AccessToken={token};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )

        self._connection = pyodbc.connect(conn_str)

        table = config.table
        schema = config.schema or "dbo"

        return FabricSQLDataset(
            source=f"{schema}.{table}",
            engine=self.engine,
            name=table,
            connection=self._connection,
        )

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a Fabric connection string."""
        source_lower = source.lower()
        return (
            source_lower.startswith("fabric://")
            or source_lower.startswith("fabric+sql://")
            or source_lower.startswith("onelake://")
            or ".datawarehouse.fabric.microsoft.com" in source_lower
            or "onelake.dfs.fabric.microsoft.com" in source_lower
        )

    @classmethod
    def get_priority(cls) -> int:
        """Fabric connector has high priority."""
        return 65


class FabricSQLDataset(Dataset):
    """Dataset that queries Fabric SQL endpoint directly."""

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine,
        name: str,
        connection: Any,
    ):
        super().__init__(source=source, engine=engine, name=name)
        self._fabric_connection = connection

    def _execute_query(self, sql: str) -> list[tuple[Any, ...]]:
        """Execute a query on Fabric SQL endpoint."""
        cursor = self._fabric_connection.cursor()
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
        """Get row count from Fabric."""
        if self._row_count_cache is None:
            sql = f"SELECT COUNT(*) FROM {self._source}"
            self._row_count_cache = self._fetch_value(sql) or 0
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """Get column names from Fabric."""
        if self._columns_cache is None:
            cursor = self._fabric_connection.cursor()
            try:
                cursor.execute(f"SELECT TOP 0 * FROM {self._source}")
                self._columns_cache = [desc[0] for desc in cursor.description]
            finally:
                cursor.close()
        return self._columns_cache
