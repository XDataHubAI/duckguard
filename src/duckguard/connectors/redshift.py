"""Amazon Redshift connector."""

from __future__ import annotations

from urllib.parse import urlparse

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class RedshiftConnector(Connector):
    """
    Connector for Amazon Redshift.

    Redshift is PostgreSQL-compatible, so we can use the PostgreSQL
    extension in DuckDB or the redshift_connector package.

    Examples:
        # Using connection string
        data = connect(
            "redshift://user:pass@cluster.region.redshift.amazonaws.com:5439/database",
            table="orders"
        )

        # Using options
        data = connect(
            "redshift://cluster.region.redshift.amazonaws.com:5439/database",
            table="orders",
            user="myuser",
            password="mypass",
            schema="public"
        )
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._setup_extension()

    def _setup_extension(self) -> None:
        """Install and load the postgres extension (Redshift compatible)."""
        try:
            self.engine.execute("INSTALL postgres")
            self.engine.execute("LOAD postgres")
        except Exception:
            pass

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to Redshift and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        if not config.table:
            raise ValueError("Table name is required for Redshift connections")

        # Parse connection string
        conn_info = self._parse_connection_string(config.source, config)

        table = config.table
        schema = config.schema or conn_info.get("schema", "public")

        # Create a unique alias
        alias = f"redshift_{table}"

        # Build PostgreSQL-compatible connection string for DuckDB
        pg_conn = self._build_connection_string(conn_info)

        # Attach using PostgreSQL extension (Redshift is PG-compatible)
        attach_sql = f"ATTACH '{pg_conn}' AS {alias} (TYPE postgres)"

        try:
            self.engine.execute(attach_sql)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # Build source reference
        source_ref = f"{alias}.{schema}.{table}"

        # Register as a view
        view_name = f"_duckguard_redshift_{table}"
        try:
            self.engine.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {source_ref}")
        except Exception:
            pass

        return Dataset(source=view_name, engine=self.engine, name=table)

    def _parse_connection_string(self, conn_string: str, config: ConnectionConfig) -> dict:
        """Parse Redshift connection string."""
        # Handle redshift:// prefix
        if conn_string.lower().startswith("redshift://"):
            conn_string = "postgresql://" + conn_string[11:]

        parsed = urlparse(conn_string)

        params = {
            "host": parsed.hostname or "",
            "port": str(parsed.port or 5439),
            "database": parsed.path.lstrip("/") if parsed.path else "",
            "user": parsed.username or "",
            "password": parsed.password or "",
        }

        # Override with config options
        options = config.options or {}
        for key in ["user", "password", "host", "port", "database", "schema", "sslmode"]:
            if key in options:
                params[key] = options[key]

        if config.database:
            params["database"] = config.database
        if config.schema:
            params["schema"] = config.schema

        return params

    def _build_connection_string(self, conn_info: dict) -> str:
        """Build connection string for DuckDB PostgreSQL extension."""
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
            parts.append(f"dbname={conn_info['database']}")

        # Redshift requires SSL
        parts.append("sslmode=require")

        return " ".join(parts)

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a Redshift connection string."""
        source_lower = source.lower()
        return source_lower.startswith("redshift://") or (
            "redshift.amazonaws.com" in source_lower
        )

    @classmethod
    def get_priority(cls) -> int:
        """Redshift connector has high priority."""
        return 55
