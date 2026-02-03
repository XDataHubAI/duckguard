"""MySQL connector."""

from __future__ import annotations

from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class MySQLConnector(Connector):
    """
    Connector for MySQL databases.

    Uses DuckDB's mysql extension for efficient query pushdown.
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._setup_extension()

    def _setup_extension(self) -> None:
        """Install and load the mysql extension."""
        try:
            self.engine.execute("INSTALL mysql")
            self.engine.execute("LOAD mysql")
        except Exception:
            # Extension might already be loaded
            pass

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to MySQL and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        if not config.table:
            raise ValueError("Table name is required for MySQL connections")

        # Parse connection string
        conn_info = self._parse_connection_string(config.source)

        table = config.table
        database = config.database or conn_info.get("database", "")

        # Create a unique alias for this connection
        alias = f"mysql_{table}"

        # Build MySQL connection string for DuckDB
        mysql_conn = self._build_duckdb_connection(conn_info)

        # Attach the database
        attach_sql = f"ATTACH '{mysql_conn}' AS {alias} (TYPE mysql)"

        try:
            self.engine.execute(attach_sql)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # The source reference for DuckDB
        if database:
            source_ref = f"{alias}.{database}.{table}"
        else:
            source_ref = f"{alias}.{table}"

        # Register as a view for easier access
        view_name = f"_duckguard_{table}"
        try:
            self.engine.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {source_ref}")
        except Exception:
            pass

        return Dataset(source=view_name, engine=self.engine, name=table)

    def _parse_connection_string(self, conn_string: str) -> dict[str, str]:
        """Parse MySQL connection string."""
        # Handle mysql+pymysql:// format
        conn_string = conn_string.replace("mysql+pymysql://", "mysql://")

        parsed = urlparse(conn_string)

        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 3306),
            "database": parsed.path.lstrip("/") if parsed.path else "",
            "user": parsed.username or "",
            "password": parsed.password or "",
        }

    def _build_duckdb_connection(self, conn_info: dict[str, str]) -> str:
        """Build connection string for DuckDB MySQL extension."""
        parts = []

        if conn_info.get("host"):
            parts.append(f"host={conn_info['host']}")
        if conn_info.get("port"):
            parts.append(f"port={conn_info['port']}")
        if conn_info.get("user"):
            parts.append(f"user={conn_info['user']}")
        if conn_info.get("password"):
            parts.append(f"password={conn_info['password']}")
        if conn_info.get("database"):
            parts.append(f"database={conn_info['database']}")

        return " ".join(parts)

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a MySQL connection string."""
        return source.lower().startswith(("mysql://", "mysql+pymysql://"))

    @classmethod
    def get_priority(cls) -> int:
        """Database connectors have high priority."""
        return 50
