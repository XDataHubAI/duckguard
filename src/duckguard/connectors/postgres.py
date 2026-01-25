"""PostgreSQL connector."""

from __future__ import annotations

from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class PostgresConnector(Connector):
    """
    Connector for PostgreSQL databases.

    Uses DuckDB's postgres extension for efficient query pushdown.
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._setup_extension()

    def _setup_extension(self) -> None:
        """Install and load the postgres extension."""
        try:
            self.engine.execute("INSTALL postgres")
            self.engine.execute("LOAD postgres")
        except Exception:
            # Extension might already be loaded
            pass

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to PostgreSQL and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        if not config.table:
            raise ValueError("Table name is required for PostgreSQL connections")

        # Parse connection string
        conn_info = self._parse_connection_string(config.source)

        # Build the full table reference
        schema = config.schema or conn_info.get("schema", "public")
        table = config.table
        full_table = f"{schema}.{table}"

        # Create a unique alias for this connection
        alias = f"pg_{table}"

        # Attach the database
        attach_sql = f"ATTACH '{config.source}' AS {alias} (TYPE postgres)"

        try:
            self.engine.execute(attach_sql)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # The source reference for DuckDB
        source_ref = f"{alias}.{full_table}"

        # Register as a view for easier access
        view_name = f"_duckguard_{table}"
        try:
            self.engine.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {source_ref}")
        except Exception:
            pass

        return Dataset(source=view_name, engine=self.engine, name=table)

    def _parse_connection_string(self, conn_string: str) -> dict[str, str]:
        """Parse PostgreSQL connection string."""
        parsed = urlparse(conn_string)

        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "database": parsed.path.lstrip("/") if parsed.path else "",
            "user": parsed.username or "",
            "password": parsed.password or "",
            "schema": "public",
        }

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a PostgreSQL connection string."""
        return source.lower().startswith(("postgres://", "postgresql://"))

    @classmethod
    def get_priority(cls) -> int:
        """Database connectors have high priority."""
        return 50
