"""SQLite connector."""

from __future__ import annotations

import os
from pathlib import Path

from duckguard.connectors.base import ConnectionConfig, Connector
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine


class SQLiteConnector(Connector):
    """
    Connector for SQLite databases.

    DuckDB has native SQLite support, making this connector very efficient.

    Examples:
        # Connect to SQLite file
        data = connect("sqlite:///path/to/database.db", table="users")

        # Or directly with .db/.sqlite extension
        data = connect("database.sqlite", table="orders")
    """

    def __init__(self, engine: DuckGuardEngine | None = None):
        super().__init__(engine)
        self._setup_extension()

    def _setup_extension(self) -> None:
        """Install and load the SQLite extension."""
        try:
            self.engine.execute("INSTALL sqlite")
            self.engine.execute("LOAD sqlite")
        except Exception:
            # Extension might already be loaded
            pass

    def connect(self, config: ConnectionConfig) -> Dataset:
        """
        Connect to SQLite database and return a Dataset.

        Args:
            config: Connection configuration

        Returns:
            Dataset object
        """
        if not config.table:
            raise ValueError("Table name is required for SQLite connections")

        # Parse the path
        path = self._parse_path(config.source)

        # Validate file exists
        if not os.path.exists(path):
            raise FileNotFoundError(f"SQLite database not found: {path}")

        table = config.table

        # Create a unique alias for this connection
        alias = f"sqlite_{Path(path).stem}"

        # Attach the SQLite database
        attach_sql = f"ATTACH '{path}' AS {alias} (TYPE sqlite)"

        try:
            self.engine.execute(attach_sql)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # The source reference for DuckDB
        source_ref = f"{alias}.{table}"

        # Register as a view for easier access
        view_name = f"_duckguard_sqlite_{table}"
        try:
            self.engine.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM {source_ref}")
        except Exception:
            pass

        return Dataset(source=view_name, engine=self.engine, name=table)

    def _parse_path(self, source: str) -> str:
        """Parse SQLite connection string to get file path."""
        if source.lower().startswith("sqlite:///"):
            return source[10:]  # Remove 'sqlite:///'
        if source.lower().startswith("sqlite://"):
            return source[9:]  # Remove 'sqlite://'
        return source

    @classmethod
    def can_handle(cls, source: str) -> bool:
        """Check if this is a SQLite database."""
        source_lower = source.lower()

        # Check for sqlite:// protocol
        if source_lower.startswith("sqlite://"):
            return True

        # Check for common SQLite file extensions
        if source_lower.endswith((".db", ".sqlite", ".sqlite3")):
            return True

        return False

    @classmethod
    def get_priority(cls) -> int:
        """SQLite connector has medium-high priority."""
        return 40
