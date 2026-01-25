"""Schema change analysis implementation.

Provides functionality to detect and analyze schema changes between snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from duckguard.history.schema import QUERIES
from duckguard.history.storage import HistoryStorage
from duckguard.schema_history.tracker import SchemaSnapshot, SchemaTracker

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset


class ChangeType(str, Enum):
    """Types of schema changes."""

    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    POSITION_CHANGED = "position_changed"


class ChangeSeverity(str, Enum):
    """Severity levels for schema changes."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SchemaChange:
    """Represents a single schema change.

    Attributes:
        change_type: Type of change
        column_name: Name of affected column (None for table-level changes)
        previous_value: Previous value (type, nullable, etc.)
        current_value: Current value
        is_breaking: Whether this is a breaking change
        severity: Change severity level
    """

    change_type: ChangeType
    column_name: str | None
    previous_value: str | None
    current_value: str | None
    is_breaking: bool
    severity: ChangeSeverity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "change_type": self.change_type.value,
            "column_name": self.column_name,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "is_breaking": self.is_breaking,
            "severity": self.severity.value,
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.change_type == ChangeType.COLUMN_ADDED:
            return f"Column '{self.column_name}' added (type: {self.current_value})"
        elif self.change_type == ChangeType.COLUMN_REMOVED:
            return f"Column '{self.column_name}' removed (was type: {self.previous_value})"
        elif self.change_type == ChangeType.TYPE_CHANGED:
            return f"Column '{self.column_name}' type changed: {self.previous_value} -> {self.current_value}"
        elif self.change_type == ChangeType.NULLABLE_CHANGED:
            return f"Column '{self.column_name}' nullable changed: {self.previous_value} -> {self.current_value}"
        elif self.change_type == ChangeType.POSITION_CHANGED:
            return f"Column '{self.column_name}' position changed: {self.previous_value} -> {self.current_value}"
        return f"{self.change_type.value}: {self.column_name}"


@dataclass
class SchemaEvolutionReport:
    """Report of schema changes between snapshots.

    Attributes:
        source: Data source path
        previous_snapshot: Previous schema snapshot (None if first)
        current_snapshot: Current schema snapshot
        changes: List of detected changes
        analyzed_at: When the analysis was performed
    """

    source: str
    previous_snapshot: SchemaSnapshot | None
    current_snapshot: SchemaSnapshot
    changes: list[SchemaChange] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=datetime.now)

    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return len(self.changes) > 0

    @property
    def has_breaking_changes(self) -> bool:
        """Check if any breaking changes were detected."""
        return any(c.is_breaking for c in self.changes)

    @property
    def breaking_changes(self) -> list[SchemaChange]:
        """Get only breaking changes."""
        return [c for c in self.changes if c.is_breaking]

    @property
    def non_breaking_changes(self) -> list[SchemaChange]:
        """Get only non-breaking changes."""
        return [c for c in self.changes if not c.is_breaking]

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [f"Schema Evolution Report for: {self.source}"]
        lines.append(f"Analyzed at: {self.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        if not self.has_changes:
            lines.append("No schema changes detected.")
            return "\n".join(lines)

        lines.append(f"Total changes: {len(self.changes)}")
        lines.append(f"Breaking changes: {len(self.breaking_changes)}")
        lines.append("")

        # Group by type
        by_type: dict[ChangeType, list[SchemaChange]] = {}
        for change in self.changes:
            by_type.setdefault(change.change_type, []).append(change)

        for change_type, type_changes in by_type.items():
            lines.append(f"{change_type.value.replace('_', ' ').title()}:")
            for change in type_changes:
                marker = "[BREAKING]" if change.is_breaking else ""
                lines.append(f"  - {change} {marker}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "previous_snapshot_id": self.previous_snapshot.snapshot_id if self.previous_snapshot else None,
            "current_snapshot_id": self.current_snapshot.snapshot_id,
            "has_changes": self.has_changes,
            "has_breaking_changes": self.has_breaking_changes,
            "total_changes": len(self.changes),
            "breaking_changes_count": len(self.breaking_changes),
            "changes": [c.to_dict() for c in self.changes],
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class SchemaChangeAnalyzer:
    """Analyze schema changes between snapshots.

    Usage:
        from duckguard import connect
        from duckguard.schema_history import SchemaChangeAnalyzer

        analyzer = SchemaChangeAnalyzer()
        data = connect("data.csv")

        # Detect changes (captures snapshot and compares to previous)
        report = analyzer.detect_changes(data)
        if report.has_breaking_changes:
            print("Breaking changes detected!")
            for change in report.breaking_changes:
                print(f"  - {change}")

        # Compare two specific snapshots
        changes = analyzer.compare(snapshot1, snapshot2)
    """

    # Type changes that are typically safe (widening)
    SAFE_TYPE_CHANGES = {
        ("INTEGER", "BIGINT"),
        ("FLOAT", "DOUBLE"),
        ("VARCHAR", "TEXT"),
        ("SMALLINT", "INTEGER"),
        ("SMALLINT", "BIGINT"),
        ("INTEGER", "DOUBLE"),
        ("FLOAT", "DECIMAL"),
    }

    def __init__(self, storage: HistoryStorage | None = None):
        """Initialize schema change analyzer.

        Args:
            storage: Optional HistoryStorage instance. Uses default if not provided.
        """
        self._storage = storage or HistoryStorage()
        self._tracker = SchemaTracker(self._storage)

    @property
    def storage(self) -> HistoryStorage:
        """Get the underlying storage."""
        return self._storage

    def compare(
        self,
        previous: SchemaSnapshot,
        current: SchemaSnapshot,
    ) -> list[SchemaChange]:
        """Compare two schema snapshots and return changes.

        Args:
            previous: Previous schema snapshot
            current: Current schema snapshot

        Returns:
            List of SchemaChange objects
        """
        changes: list[SchemaChange] = []

        prev_cols = {c.name: c for c in previous.columns}
        curr_cols = {c.name: c for c in current.columns}

        prev_names = set(prev_cols.keys())
        curr_names = set(curr_cols.keys())

        # Detect removed columns (breaking change)
        for name in prev_names - curr_names:
            col = prev_cols[name]
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                column_name=name,
                previous_value=col.dtype,
                current_value=None,
                is_breaking=True,
                severity=ChangeSeverity.CRITICAL,
            ))

        # Detect added columns (usually not breaking)
        for name in curr_names - prev_names:
            col = curr_cols[name]
            # Adding a non-nullable column without default is breaking
            is_breaking = not col.nullable
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                column_name=name,
                previous_value=None,
                current_value=col.dtype,
                is_breaking=is_breaking,
                severity=ChangeSeverity.WARNING if is_breaking else ChangeSeverity.INFO,
            ))

        # Detect changes to existing columns
        for name in prev_names & curr_names:
            prev_col = prev_cols[name]
            curr_col = curr_cols[name]

            # Type change
            if prev_col.dtype != curr_col.dtype:
                is_breaking = not self._is_safe_type_change(prev_col.dtype, curr_col.dtype)
                changes.append(SchemaChange(
                    change_type=ChangeType.TYPE_CHANGED,
                    column_name=name,
                    previous_value=prev_col.dtype,
                    current_value=curr_col.dtype,
                    is_breaking=is_breaking,
                    severity=ChangeSeverity.CRITICAL if is_breaking else ChangeSeverity.WARNING,
                ))

            # Nullable change
            if prev_col.nullable != curr_col.nullable:
                # Changing from nullable to non-nullable is breaking
                is_breaking = prev_col.nullable and not curr_col.nullable
                changes.append(SchemaChange(
                    change_type=ChangeType.NULLABLE_CHANGED,
                    column_name=name,
                    previous_value=str(prev_col.nullable),
                    current_value=str(curr_col.nullable),
                    is_breaking=is_breaking,
                    severity=ChangeSeverity.WARNING if is_breaking else ChangeSeverity.INFO,
                ))

            # Position change (usually not breaking, just informational)
            if prev_col.position != curr_col.position:
                changes.append(SchemaChange(
                    change_type=ChangeType.POSITION_CHANGED,
                    column_name=name,
                    previous_value=str(prev_col.position),
                    current_value=str(curr_col.position),
                    is_breaking=False,
                    severity=ChangeSeverity.INFO,
                ))

        return changes

    def detect_changes(self, dataset: Dataset) -> SchemaEvolutionReport:
        """Detect schema changes for a dataset.

        Captures current schema and compares to the most recent snapshot.

        Args:
            dataset: Dataset to analyze

        Returns:
            SchemaEvolutionReport with detected changes
        """
        # Get the latest snapshot before capturing new one
        previous = self._tracker.get_latest(dataset.source)

        # Capture current schema
        current = self._tracker.capture(dataset)

        # Compare if we have a previous snapshot
        changes: list[SchemaChange] = []
        if previous:
            changes = self.compare(previous, current)

            # Store detected changes
            self._store_changes(dataset.source, previous, current, changes)

        return SchemaEvolutionReport(
            source=dataset.source,
            previous_snapshot=previous,
            current_snapshot=current,
            changes=changes,
        )

    def analyze_evolution(
        self,
        source: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SchemaChange]:
        """Get all schema changes for a source.

        Args:
            source: Data source path
            since: Only get changes since this datetime
            limit: Maximum changes to return

        Returns:
            List of SchemaChange objects, most recent first
        """
        conn = self._storage._get_connection()

        if since:
            cursor = conn.execute(
                QUERIES["get_schema_changes_since"],
                (source, since.isoformat()),
            )
        else:
            cursor = conn.execute(
                QUERIES["get_schema_changes"],
                (source, limit),
            )

        changes = []
        for row in cursor.fetchall():
            changes.append(SchemaChange(
                change_type=ChangeType(row["change_type"]),
                column_name=row["column_name"],
                previous_value=row["previous_value"],
                current_value=row["current_value"],
                is_breaking=bool(row["is_breaking"]),
                severity=ChangeSeverity(row["severity"]),
            ))

        return changes

    def _is_safe_type_change(self, from_type: str, to_type: str) -> bool:
        """Check if a type change is safe (widening conversion)."""
        from_normalized = from_type.upper().split("(")[0].strip()
        to_normalized = to_type.upper().split("(")[0].strip()

        return (from_normalized, to_normalized) in self.SAFE_TYPE_CHANGES

    def _store_changes(
        self,
        source: str,
        previous: SchemaSnapshot,
        current: SchemaSnapshot,
        changes: list[SchemaChange],
    ) -> None:
        """Store detected changes in the database."""
        if not changes:
            return

        conn = self._storage._get_connection()
        now = datetime.now().isoformat()

        for change in changes:
            conn.execute(
                QUERIES["insert_schema_change"],
                (
                    source,
                    now,
                    previous.snapshot_id,
                    current.snapshot_id,
                    change.change_type.value,
                    change.column_name,
                    change.previous_value,
                    change.current_value,
                    1 if change.is_breaking else 0,
                    change.severity.value,
                ),
            )

        conn.commit()
