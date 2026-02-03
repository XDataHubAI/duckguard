"""Schema tracking implementation.

Provides functionality to capture and store schema snapshots over time.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from duckguard.history.schema import QUERIES
from duckguard.history.storage import HistoryStorage

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset


@dataclass
class ColumnSchema:
    """Represents the schema of a single column.

    Attributes:
        name: Column name
        dtype: Data type as string
        nullable: Whether the column allows nulls
        position: Position in the table (0-indexed)
    """

    name: str
    dtype: str
    nullable: bool
    position: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "dtype": self.dtype,
            "nullable": self.nullable,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnSchema:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            dtype=data["dtype"],
            nullable=data.get("nullable", True),
            position=data.get("position", 0),
        )


@dataclass
class SchemaSnapshot:
    """Represents a captured schema at a point in time.

    Attributes:
        source: Data source path
        snapshot_id: Unique identifier for this snapshot
        captured_at: When the snapshot was captured
        columns: List of column schemas
        row_count: Optional row count at capture time
    """

    source: str
    snapshot_id: str
    captured_at: datetime
    columns: list[ColumnSchema]
    row_count: int | None = None

    @property
    def column_count(self) -> int:
        """Get the number of columns."""
        return len(self.columns)

    @property
    def column_names(self) -> list[str]:
        """Get list of column names."""
        return [c.name for c in self.columns]

    def get_column(self, name: str) -> ColumnSchema | None:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at.isoformat(),
            "columns": [c.to_dict() for c in self.columns],
            "row_count": self.row_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaSnapshot:
        """Create from dictionary."""
        return cls(
            source=data["source"],
            snapshot_id=data["snapshot_id"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
            columns=[ColumnSchema.from_dict(c) for c in data["columns"]],
            row_count=data.get("row_count"),
        )

    def __eq__(self, other: object) -> bool:
        """Check schema equality (ignores snapshot_id and captured_at)."""
        if not isinstance(other, SchemaSnapshot):
            return False
        return (
            self.source == other.source
            and len(self.columns) == len(other.columns)
            and all(
                c1.name == c2.name and c1.dtype == c2.dtype and c1.nullable == c2.nullable
                for c1, c2 in zip(self.columns, other.columns)
            )
        )


class SchemaTracker:
    """Track schema changes over time.

    Usage:
        from duckguard import connect
        from duckguard.schema_history import SchemaTracker

        tracker = SchemaTracker()
        data = connect("data.csv")

        # Capture current schema
        snapshot = tracker.capture(data)

        # Get history
        history = tracker.get_history(data.source)

        # Get latest snapshot
        latest = tracker.get_latest(data.source)
    """

    def __init__(self, storage: HistoryStorage | None = None):
        """Initialize schema tracker.

        Args:
            storage: Optional HistoryStorage instance. Uses default if not provided.
        """
        self._storage = storage or HistoryStorage()

    @property
    def storage(self) -> HistoryStorage:
        """Get the underlying storage."""
        return self._storage

    def capture(self, dataset: Dataset) -> SchemaSnapshot:
        """Capture current schema as a snapshot.

        Args:
            dataset: Dataset to capture schema from

        Returns:
            SchemaSnapshot representing current state
        """
        # Get schema information from the engine
        columns = self._get_column_schemas(dataset)

        snapshot = SchemaSnapshot(
            source=dataset.source,
            snapshot_id=str(uuid.uuid4()),
            captured_at=datetime.now(),
            columns=columns,
            row_count=dataset.row_count,
        )

        # Store in database
        self._store_snapshot(snapshot)

        return snapshot

    def get_history(
        self,
        source: str,
        limit: int = 50,
    ) -> list[SchemaSnapshot]:
        """Get schema snapshot history for a source.

        Args:
            source: Data source path
            limit: Maximum snapshots to return

        Returns:
            List of SchemaSnapshot objects, most recent first
        """
        conn = self._storage._get_connection()
        cursor = conn.execute(QUERIES["get_schema_snapshots"], (source, limit))

        return [self._row_to_snapshot(row) for row in cursor.fetchall()]

    def get_latest(self, source: str) -> SchemaSnapshot | None:
        """Get the most recent schema snapshot for a source.

        Args:
            source: Data source path

        Returns:
            SchemaSnapshot or None if no snapshots exist
        """
        conn = self._storage._get_connection()
        cursor = conn.execute(QUERIES["get_latest_schema_snapshot"], (source,))
        row = cursor.fetchone()

        return self._row_to_snapshot(row) if row else None

    def get_snapshot(self, snapshot_id: str) -> SchemaSnapshot | None:
        """Get a specific snapshot by ID.

        Args:
            snapshot_id: Snapshot ID

        Returns:
            SchemaSnapshot or None if not found
        """
        conn = self._storage._get_connection()
        cursor = conn.execute(QUERIES["get_schema_snapshot_by_id"], (snapshot_id,))
        row = cursor.fetchone()

        return self._row_to_snapshot(row) if row else None

    def _get_column_schemas(self, dataset: Dataset) -> list[ColumnSchema]:
        """Get column schemas from dataset."""
        columns = []

        # Get column info from DuckDB
        ref = dataset.engine.get_source_reference(dataset.source)
        result = dataset.engine.execute(f"DESCRIBE {ref}")

        for i, row in enumerate(result.fetchall()):
            col_name = row[0]
            col_type = row[1]
            nullable = row[2] == "YES" if len(row) > 2 else True

            columns.append(ColumnSchema(
                name=col_name,
                dtype=col_type,
                nullable=nullable,
                position=i,
            ))

        return columns

    def _store_snapshot(self, snapshot: SchemaSnapshot) -> None:
        """Store a snapshot in the database."""
        conn = self._storage._get_connection()

        schema_json = json.dumps({
            "columns": [c.to_dict() for c in snapshot.columns]
        })

        conn.execute(
            QUERIES["insert_schema_snapshot"],
            (
                snapshot.source,
                snapshot.snapshot_id,
                snapshot.captured_at.isoformat(),
                schema_json,
                snapshot.column_count,
                snapshot.row_count,
            ),
        )
        conn.commit()

    def _row_to_snapshot(self, row) -> SchemaSnapshot:
        """Convert database row to SchemaSnapshot."""
        schema_data = json.loads(row["schema_json"])
        columns = [ColumnSchema.from_dict(c) for c in schema_data["columns"]]

        return SchemaSnapshot(
            source=row["source"],
            snapshot_id=row["snapshot_id"],
            captured_at=datetime.fromisoformat(row["captured_at"]),
            columns=columns,
            row_count=row["row_count"],
        )
