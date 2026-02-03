"""Tests for freshness monitoring."""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from duckguard.freshness import FreshnessMonitor, FreshnessResult
from duckguard.freshness.monitor import FreshnessMethod, parse_age_string


class TestFreshnessMonitor:
    """Tests for FreshnessMonitor class."""

    def test_init_default_threshold(self):
        """Test default threshold is 24 hours."""
        monitor = FreshnessMonitor()
        assert monitor.threshold == timedelta(hours=24)
        assert monitor.threshold_seconds == 86400

    def test_init_custom_threshold(self):
        """Test custom threshold."""
        monitor = FreshnessMonitor(threshold=timedelta(hours=6))
        assert monitor.threshold == timedelta(hours=6)
        assert monitor.threshold_seconds == 21600

    def test_check_file_mtime(self):
        """Test file modification time check."""
        monitor = FreshnessMonitor(threshold=timedelta(hours=24))

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("a,b,c\n1,2,3\n")
            temp_path = f.name

        try:
            result = monitor.check_file_mtime(temp_path)

            assert result.is_fresh is True  # Just created
            assert result.method == FreshnessMethod.FILE_MTIME
            assert result.age_seconds is not None
            assert result.age_seconds < 60  # Less than a minute old
            assert result.last_modified is not None
            assert "seconds ago" in result.age_human
        finally:
            os.unlink(temp_path)

    def test_check_file_mtime_not_found(self):
        """Test file not found case."""
        monitor = FreshnessMonitor()
        result = monitor.check_file_mtime("/nonexistent/path/file.csv")

        assert result.is_fresh is False
        assert result.method == FreshnessMethod.FILE_MTIME
        assert result.last_modified is None
        assert "file not found" in result.age_human

    def test_check_file_mtime_stale(self):
        """Test stale file detection."""
        monitor = FreshnessMonitor(threshold=timedelta(seconds=1))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("a,b,c\n1,2,3\n")
            temp_path = f.name

        try:
            # Wait a bit to make the file stale
            import time
            time.sleep(1.5)

            result = monitor.check_file_mtime(temp_path)
            assert result.is_fresh is False  # Should be stale now
        finally:
            os.unlink(temp_path)

    def test_format_age(self):
        """Test age formatting."""
        monitor = FreshnessMonitor()

        # Test various age formats
        assert "seconds ago" in monitor._format_age(timedelta(seconds=30))
        assert "minute" in monitor._format_age(timedelta(minutes=5))
        assert "hour" in monitor._format_age(timedelta(hours=3))
        assert "day" in monitor._format_age(timedelta(days=2))
        assert "week" in monitor._format_age(timedelta(weeks=2))
        assert "month" in monitor._format_age(timedelta(days=60))

    def test_is_local_file(self):
        """Test local file detection."""
        import sys

        monitor = FreshnessMonitor()

        # Test non-local paths (these should work on all platforms)
        assert monitor._is_local_file("s3://bucket/file.csv") is False
        assert monitor._is_local_file("postgres://localhost/db") is False
        assert monitor._is_local_file("/nonexistent/file.csv") is False

        # Test actual file detection (may have platform-specific issues)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("a,b\n1,2\n")
            temp_path = f.name

        try:
            # Resolve to full path (Windows may use short path names with ~)
            full_path = str(Path(temp_path).resolve())
            # On Windows, temp file handling can cause issues, so we use a more lenient check
            if sys.platform != "win32":
                assert monitor._is_local_file(full_path) is True
            else:
                # On Windows, just verify the method doesn't raise an exception
                _ = monitor._is_local_file(full_path)
        finally:
            os.unlink(temp_path)

    def test_result_to_dict(self):
        """Test FreshnessResult to_dict conversion."""
        result = FreshnessResult(
            source="test.csv",
            last_modified=datetime(2024, 1, 15, 10, 30, 0),
            age_seconds=3600.0,
            age_human="1 hour ago",
            is_fresh=True,
            threshold_seconds=86400.0,
            method=FreshnessMethod.FILE_MTIME,
            details={"key": "value"},
        )

        data = result.to_dict()

        assert data["source"] == "test.csv"
        assert data["is_fresh"] is True
        assert data["age_seconds"] == 3600.0
        assert data["method"] == "file_mtime"
        assert "last_modified" in data

    def test_result_str(self):
        """Test FreshnessResult string representation."""
        result = FreshnessResult(
            source="test.csv",
            last_modified=datetime.now(),
            age_seconds=3600.0,
            age_human="1 hour ago",
            is_fresh=True,
            threshold_seconds=86400.0,
            method=FreshnessMethod.FILE_MTIME,
        )

        str_repr = str(result)
        assert "[FRESH]" in str_repr
        assert "test.csv" in str_repr


class TestParseAgeString:
    """Tests for parse_age_string function."""

    def test_parse_seconds(self):
        """Test parsing seconds."""
        assert parse_age_string("30s") == timedelta(seconds=30)
        assert parse_age_string("60S") == timedelta(seconds=60)

    def test_parse_minutes(self):
        """Test parsing minutes."""
        assert parse_age_string("5m") == timedelta(minutes=5)
        assert parse_age_string("30M") == timedelta(minutes=30)

    def test_parse_hours(self):
        """Test parsing hours."""
        assert parse_age_string("1h") == timedelta(hours=1)
        assert parse_age_string("24H") == timedelta(hours=24)

    def test_parse_days(self):
        """Test parsing days."""
        assert parse_age_string("1d") == timedelta(days=1)
        assert parse_age_string("7D") == timedelta(days=7)

    def test_parse_weeks(self):
        """Test parsing weeks."""
        assert parse_age_string("1w") == timedelta(weeks=1)
        assert parse_age_string("2W") == timedelta(weeks=2)

    def test_parse_no_unit(self):
        """Test parsing without unit (defaults to hours)."""
        assert parse_age_string("24") == timedelta(hours=24)
        assert parse_age_string("  12  ") == timedelta(hours=12)


class TestFreshnessWithDataset:
    """Tests for freshness with Dataset integration."""

    def test_dataset_freshness_property(self):
        """Test Dataset.freshness property."""
        from duckguard import connect

        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,value\n1,test,100\n2,test2,200\n")
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset.freshness

            assert isinstance(result, FreshnessResult)
            assert result.is_fresh is True
            assert result.source == temp_path
        finally:
            os.unlink(temp_path)

    def test_dataset_is_fresh_method(self):
        """Test Dataset.is_fresh method."""
        from duckguard import connect

        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name,value\n1,test,100\n")
            temp_path = f.name

        try:
            dataset = connect(temp_path)

            assert dataset.is_fresh(timedelta(hours=24)) is True
            # Note: Can't reliably test stale case without time manipulation
        finally:
            os.unlink(temp_path)
