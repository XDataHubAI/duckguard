"""Tests for schema evolution tracking."""

import tempfile
from datetime import datetime
from pathlib import Path

from duckguard.schema_history import (
    ColumnSchema,
    SchemaChange,
    SchemaChangeAnalyzer,
    SchemaEvolutionReport,
    SchemaSnapshot,
    SchemaTracker,
)
from duckguard.schema_history.analyzer import ChangeSeverity, ChangeType


class TestColumnSchema:
    """Tests for ColumnSchema dataclass."""

    def test_to_dict(self):
        """Test to_dict conversion."""
        col = ColumnSchema(
            name="amount",
            dtype="DOUBLE",
            nullable=True,
            position=0,
        )

        data = col.to_dict()
        assert data["name"] == "amount"
        assert data["dtype"] == "DOUBLE"
        assert data["nullable"] is True
        assert data["position"] == 0

    def test_from_dict(self):
        """Test from_dict creation."""
        data = {
            "name": "amount",
            "dtype": "DOUBLE",
            "nullable": True,
            "position": 0,
        }

        col = ColumnSchema.from_dict(data)
        assert col.name == "amount"
        assert col.dtype == "DOUBLE"


class TestSchemaSnapshot:
    """Tests for SchemaSnapshot class."""

    def test_column_count(self):
        """Test column count property."""
        snapshot = SchemaSnapshot(
            source="test.csv",
            snapshot_id="abc123",
            captured_at=datetime.now(),
            columns=[
                ColumnSchema("id", "INTEGER", False, 0),
                ColumnSchema("name", "VARCHAR", True, 1),
            ],
            row_count=100,
        )

        assert snapshot.column_count == 2

    def test_column_names(self):
        """Test column names property."""
        snapshot = SchemaSnapshot(
            source="test.csv",
            snapshot_id="abc123",
            captured_at=datetime.now(),
            columns=[
                ColumnSchema("id", "INTEGER", False, 0),
                ColumnSchema("name", "VARCHAR", True, 1),
            ],
        )

        assert snapshot.column_names == ["id", "name"]

    def test_get_column(self):
        """Test get_column method."""
        snapshot = SchemaSnapshot(
            source="test.csv",
            snapshot_id="abc123",
            captured_at=datetime.now(),
            columns=[
                ColumnSchema("id", "INTEGER", False, 0),
                ColumnSchema("name", "VARCHAR", True, 1),
            ],
        )

        col = snapshot.get_column("id")
        assert col is not None
        assert col.dtype == "INTEGER"

        assert snapshot.get_column("nonexistent") is None

    def test_to_dict(self):
        """Test to_dict conversion."""
        snapshot = SchemaSnapshot(
            source="test.csv",
            snapshot_id="abc123",
            captured_at=datetime(2024, 1, 15, 10, 30),
            columns=[
                ColumnSchema("id", "INTEGER", False, 0),
            ],
            row_count=100,
        )

        data = snapshot.to_dict()
        assert data["source"] == "test.csv"
        assert data["snapshot_id"] == "abc123"
        assert len(data["columns"]) == 1

    def test_equality(self):
        """Test snapshot equality."""
        cols = [ColumnSchema("id", "INTEGER", False, 0)]

        snap1 = SchemaSnapshot("test.csv", "abc", datetime.now(), cols)
        snap2 = SchemaSnapshot("test.csv", "xyz", datetime.now(), cols.copy())

        # Same schema structure should be equal
        assert snap1 == snap2

    def test_inequality_different_columns(self):
        """Test inequality with different columns."""
        snap1 = SchemaSnapshot(
            "test.csv", "abc", datetime.now(),
            [ColumnSchema("id", "INTEGER", False, 0)]
        )
        snap2 = SchemaSnapshot(
            "test.csv", "xyz", datetime.now(),
            [ColumnSchema("id", "BIGINT", False, 0)]  # Different type
        )

        assert snap1 != snap2


class TestSchemaTracker:
    """Tests for SchemaTracker class."""

    def test_capture_snapshot(self):
        """Test capturing a schema snapshot."""
        from duckguard import connect
        from duckguard.core.engine import DuckGuardEngine
        from duckguard.history import HistoryStorage

        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,amount\n1,test,100.5\n2,test2,200.0\n")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_history.db"
                storage = HistoryStorage(db_path=db_path)
                try:
                    tracker = SchemaTracker(storage=storage)

                    dataset = connect(temp_path)
                    snapshot = tracker.capture(dataset)

                    assert snapshot.source == temp_path
                    assert snapshot.snapshot_id is not None
                    assert snapshot.column_count == 3
                    assert snapshot.row_count == 2
                finally:
                    storage.close()
                    DuckGuardEngine.reset_instance()
        finally:
            import os
            os.unlink(temp_path)

    def test_get_history(self):
        """Test getting schema history."""
        from duckguard import connect
        from duckguard.core.engine import DuckGuardEngine
        from duckguard.history import HistoryStorage

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n1,test\n")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_history.db"
                storage = HistoryStorage(db_path=db_path)
                try:
                    tracker = SchemaTracker(storage=storage)

                    dataset = connect(temp_path)

                    # Capture multiple snapshots
                    tracker.capture(dataset)
                    tracker.capture(dataset)
                    tracker.capture(dataset)

                    history = tracker.get_history(temp_path, limit=10)
                    assert len(history) == 3
                finally:
                    storage.close()
                    DuckGuardEngine.reset_instance()
        finally:
            import os
            os.unlink(temp_path)

    def test_get_latest(self):
        """Test getting latest snapshot."""
        from duckguard import connect
        from duckguard.core.engine import DuckGuardEngine
        from duckguard.history import HistoryStorage

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n1,test\n")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_history.db"
                storage = HistoryStorage(db_path=db_path)
                try:
                    tracker = SchemaTracker(storage=storage)

                    dataset = connect(temp_path)
                    captured = tracker.capture(dataset)

                    latest = tracker.get_latest(temp_path)
                    assert latest is not None
                    assert latest.snapshot_id == captured.snapshot_id
                finally:
                    storage.close()
                    DuckGuardEngine.reset_instance()
        finally:
            import os
            os.unlink(temp_path)

    def test_get_latest_none(self):
        """Test getting latest when no history exists."""
        from duckguard.history import HistoryStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_history.db"
            storage = HistoryStorage(db_path=db_path)
            try:
                tracker = SchemaTracker(storage=storage)

                latest = tracker.get_latest("nonexistent.csv")
                assert latest is None
            finally:
                storage.close()


class TestSchemaChangeAnalyzer:
    """Tests for SchemaChangeAnalyzer class."""

    def test_compare_no_changes(self):
        """Test comparing identical schemas."""
        analyzer = SchemaChangeAnalyzer()

        cols = [
            ColumnSchema("id", "INTEGER", False, 0),
            ColumnSchema("name", "VARCHAR", True, 1),
        ]

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), cols.copy())

        changes = analyzer.compare(prev, curr)
        assert len(changes) == 0

    def test_compare_column_added(self):
        """Test detecting added column."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [ColumnSchema("id", "INTEGER", False, 0)]
        curr_cols = [
            ColumnSchema("id", "INTEGER", False, 0),
            ColumnSchema("name", "VARCHAR", True, 1),
        ]

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.COLUMN_ADDED
        assert changes[0].column_name == "name"
        assert changes[0].is_breaking is False  # Nullable column

    def test_compare_column_added_non_nullable(self):
        """Test adding non-nullable column is breaking."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [ColumnSchema("id", "INTEGER", False, 0)]
        curr_cols = [
            ColumnSchema("id", "INTEGER", False, 0),
            ColumnSchema("required_col", "VARCHAR", False, 1),  # NOT nullable
        ]

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].is_breaking is True

    def test_compare_column_removed(self):
        """Test detecting removed column (breaking)."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [
            ColumnSchema("id", "INTEGER", False, 0),
            ColumnSchema("name", "VARCHAR", True, 1),
        ]
        curr_cols = [ColumnSchema("id", "INTEGER", False, 0)]

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.COLUMN_REMOVED
        assert changes[0].is_breaking is True
        assert changes[0].severity == ChangeSeverity.CRITICAL

    def test_compare_type_changed(self):
        """Test detecting type change."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [ColumnSchema("id", "INTEGER", False, 0)]
        curr_cols = [ColumnSchema("id", "VARCHAR", False, 0)]

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.TYPE_CHANGED
        assert changes[0].is_breaking is True

    def test_compare_safe_type_widening(self):
        """Test safe type widening is not breaking."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [ColumnSchema("id", "INTEGER", False, 0)]
        curr_cols = [ColumnSchema("id", "BIGINT", False, 0)]  # Safe widening

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].is_breaking is False

    def test_compare_nullable_changed(self):
        """Test detecting nullable change."""
        analyzer = SchemaChangeAnalyzer()

        prev_cols = [ColumnSchema("id", "INTEGER", True, 0)]  # Nullable
        curr_cols = [ColumnSchema("id", "INTEGER", False, 0)]  # NOT nullable

        prev = SchemaSnapshot("test.csv", "prev", datetime.now(), prev_cols)
        curr = SchemaSnapshot("test.csv", "curr", datetime.now(), curr_cols)

        changes = analyzer.compare(prev, curr)

        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.NULLABLE_CHANGED
        assert changes[0].is_breaking is True

    def test_detect_changes(self):
        """Test detect_changes with dataset."""
        from duckguard import connect
        from duckguard.core.engine import DuckGuardEngine
        from duckguard.history import HistoryStorage

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n1,test\n")
            temp_path = f.name

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "test_history.db"
                storage = HistoryStorage(db_path=db_path)
                try:
                    analyzer = SchemaChangeAnalyzer(storage=storage)

                    dataset = connect(temp_path)

                    # First call - no previous snapshot
                    report = analyzer.detect_changes(dataset)
                    assert report.previous_snapshot is None
                    assert report.has_changes is False

                    # Second call - should have previous snapshot
                    report2 = analyzer.detect_changes(dataset)
                    assert report2.previous_snapshot is not None
                    assert report2.has_changes is False  # Same schema
                finally:
                    storage.close()
                    DuckGuardEngine.reset_instance()
        finally:
            import os
            os.unlink(temp_path)


class TestSchemaEvolutionReport:
    """Tests for SchemaEvolutionReport class."""

    def test_has_changes(self):
        """Test has_changes property."""
        snapshot = SchemaSnapshot("test.csv", "abc", datetime.now(), [])

        report_empty = SchemaEvolutionReport(
            source="test.csv",
            previous_snapshot=None,
            current_snapshot=snapshot,
            changes=[],
        )
        assert report_empty.has_changes is False

        report_with_changes = SchemaEvolutionReport(
            source="test.csv",
            previous_snapshot=None,
            current_snapshot=snapshot,
            changes=[
                SchemaChange(
                    ChangeType.COLUMN_ADDED, "name", None, "VARCHAR",
                    is_breaking=False, severity=ChangeSeverity.INFO
                )
            ],
        )
        assert report_with_changes.has_changes is True

    def test_has_breaking_changes(self):
        """Test has_breaking_changes property."""
        snapshot = SchemaSnapshot("test.csv", "abc", datetime.now(), [])

        report = SchemaEvolutionReport(
            source="test.csv",
            previous_snapshot=None,
            current_snapshot=snapshot,
            changes=[
                SchemaChange(
                    ChangeType.COLUMN_REMOVED, "old_col", "VARCHAR", None,
                    is_breaking=True, severity=ChangeSeverity.CRITICAL
                ),
                SchemaChange(
                    ChangeType.COLUMN_ADDED, "new_col", None, "VARCHAR",
                    is_breaking=False, severity=ChangeSeverity.INFO
                ),
            ],
        )

        assert report.has_breaking_changes is True
        assert len(report.breaking_changes) == 1
        assert len(report.non_breaking_changes) == 1

    def test_summary(self):
        """Test summary generation."""
        snapshot = SchemaSnapshot("test.csv", "abc", datetime.now(), [])

        report = SchemaEvolutionReport(
            source="test.csv",
            previous_snapshot=None,
            current_snapshot=snapshot,
            changes=[
                SchemaChange(
                    ChangeType.COLUMN_ADDED, "name", None, "VARCHAR",
                    is_breaking=False, severity=ChangeSeverity.INFO
                )
            ],
        )

        summary = report.summary()
        assert "test.csv" in summary
        assert "Total changes: 1" in summary

    def test_to_dict(self):
        """Test to_dict conversion."""
        snapshot = SchemaSnapshot("test.csv", "abc", datetime.now(), [])

        report = SchemaEvolutionReport(
            source="test.csv",
            previous_snapshot=None,
            current_snapshot=snapshot,
            changes=[],
        )

        data = report.to_dict()
        assert data["source"] == "test.csv"
        assert data["has_changes"] is False
        assert data["current_snapshot_id"] == "abc"


class TestSchemaChange:
    """Tests for SchemaChange class."""

    def test_str_column_added(self):
        """Test string representation for column added."""
        change = SchemaChange(
            ChangeType.COLUMN_ADDED, "email", None, "VARCHAR",
            is_breaking=False, severity=ChangeSeverity.INFO
        )

        assert "email" in str(change)
        assert "added" in str(change)

    def test_str_column_removed(self):
        """Test string representation for column removed."""
        change = SchemaChange(
            ChangeType.COLUMN_REMOVED, "old_col", "INTEGER", None,
            is_breaking=True, severity=ChangeSeverity.CRITICAL
        )

        assert "old_col" in str(change)
        assert "removed" in str(change)

    def test_str_type_changed(self):
        """Test string representation for type changed."""
        change = SchemaChange(
            ChangeType.TYPE_CHANGED, "id", "INTEGER", "BIGINT",
            is_breaking=False, severity=ChangeSeverity.WARNING
        )

        assert "INTEGER" in str(change)
        assert "BIGINT" in str(change)
        assert "->" in str(change)

    def test_to_dict(self):
        """Test to_dict conversion."""
        change = SchemaChange(
            ChangeType.COLUMN_ADDED, "name", None, "VARCHAR",
            is_breaking=False, severity=ChangeSeverity.INFO
        )

        data = change.to_dict()
        assert data["change_type"] == "column_added"
        assert data["column_name"] == "name"
        assert data["is_breaking"] is False
