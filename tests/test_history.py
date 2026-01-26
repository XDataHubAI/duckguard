"""Tests for the history module."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from duckguard.history import (
    HistoryStorage,
    StoredRun,
    TrendAnalysis,
    TrendAnalyzer,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_history.db"


@pytest.fixture
def mock_execution_result():
    """Create a mock ExecutionResult for testing."""
    # Create mock objects
    mock_check = MagicMock()
    mock_check.type.value = "not_null"

    mock_result = MagicMock()
    mock_result.passed = True
    mock_result.column = "email"
    mock_result.check = mock_check
    mock_result.severity.value = "error"
    mock_result.actual_value = 0
    mock_result.expected_value = 0
    mock_result.message = "No null values"
    mock_result.details = {}

    mock_ruleset = MagicMock()
    mock_ruleset.name = "test_rules"

    mock_exec_result = MagicMock()
    mock_exec_result.source = "test_data.csv"
    mock_exec_result.ruleset = mock_ruleset
    mock_exec_result.started_at = datetime.now()
    mock_exec_result.finished_at = datetime.now()
    mock_exec_result.quality_score = 85.0
    mock_exec_result.total_checks = 10
    mock_exec_result.passed_count = 8
    mock_exec_result.failed_count = 1
    mock_exec_result.warning_count = 1
    mock_exec_result.passed = True
    mock_exec_result.results = [mock_result]
    mock_exec_result.get_failures.return_value = []
    mock_exec_result.get_warnings.return_value = []

    return mock_exec_result


class TestHistoryStorage:
    """Tests for HistoryStorage class."""

    def test_init_creates_database(self, temp_db_path):
        """Test that initialization creates the database file."""
        storage = HistoryStorage(db_path=temp_db_path)
        assert temp_db_path.exists()
        storage.close()

    def test_init_creates_parent_directories(self, temp_db_path):
        """Test that initialization creates parent directories."""
        nested_path = temp_db_path.parent / "nested" / "dir" / "history.db"
        storage = HistoryStorage(db_path=nested_path)
        assert nested_path.exists()
        storage.close()

    def test_store_returns_run_id(self, temp_db_path, mock_execution_result):
        """Test that store returns a valid run_id."""
        storage = HistoryStorage(db_path=temp_db_path)
        run_id = storage.store(mock_execution_result)

        assert run_id is not None
        assert len(run_id) == 36  # UUID format
        storage.close()

    def test_store_with_metadata(self, temp_db_path, mock_execution_result):
        """Test storing results with metadata."""
        storage = HistoryStorage(db_path=temp_db_path)
        metadata = {"dag_id": "test_dag", "task_id": "test_task"}
        run_id = storage.store(mock_execution_result, metadata=metadata)

        # Retrieve and verify
        run = storage.get_run(run_id)
        assert run is not None
        assert run.metadata == metadata
        storage.close()

    def test_get_runs_returns_stored_runs(self, temp_db_path, mock_execution_result):
        """Test retrieving stored runs."""
        storage = HistoryStorage(db_path=temp_db_path)

        # Store multiple runs
        storage.store(mock_execution_result)
        storage.store(mock_execution_result)
        storage.store(mock_execution_result)

        runs = storage.get_runs("test_data.csv")
        assert len(runs) == 3
        assert all(isinstance(r, StoredRun) for r in runs)
        storage.close()

    def test_get_runs_respects_limit(self, temp_db_path, mock_execution_result):
        """Test that get_runs respects the limit parameter."""
        storage = HistoryStorage(db_path=temp_db_path)

        # Store 5 runs
        for _ in range(5):
            storage.store(mock_execution_result)

        runs = storage.get_runs("test_data.csv", limit=2)
        assert len(runs) == 2
        storage.close()

    def test_get_latest_run(self, temp_db_path, mock_execution_result):
        """Test getting the latest run."""
        storage = HistoryStorage(db_path=temp_db_path)

        # Store a run
        run_id = storage.store(mock_execution_result)

        latest = storage.get_latest_run("test_data.csv")
        assert latest is not None
        assert latest.run_id == run_id
        storage.close()

    def test_get_latest_run_returns_none_for_unknown_source(self, temp_db_path):
        """Test that get_latest_run returns None for unknown source."""
        storage = HistoryStorage(db_path=temp_db_path)
        latest = storage.get_latest_run("nonexistent.csv")
        assert latest is None
        storage.close()

    def test_get_sources(self, temp_db_path, mock_execution_result):
        """Test getting unique sources."""
        storage = HistoryStorage(db_path=temp_db_path)

        # Store runs for different sources
        mock_execution_result.source = "source1.csv"
        storage.store(mock_execution_result)

        mock_execution_result.source = "source2.csv"
        storage.store(mock_execution_result)

        mock_execution_result.source = "source1.csv"  # Duplicate
        storage.store(mock_execution_result)

        sources = storage.get_sources()
        assert len(sources) == 2
        assert "source1.csv" in sources
        assert "source2.csv" in sources
        storage.close()

    def test_get_trend_returns_data_points(self, temp_db_path, mock_execution_result):
        """Test getting trend data."""
        storage = HistoryStorage(db_path=temp_db_path)
        storage.store(mock_execution_result)

        trend = storage.get_trend("test_data.csv", days=30)
        assert len(trend) >= 1
        assert trend[0].avg_score == 85.0
        storage.close()

    def test_context_manager(self, temp_db_path, mock_execution_result):
        """Test using storage as context manager."""
        with HistoryStorage(db_path=temp_db_path) as storage:
            storage.store(mock_execution_result)
            runs = storage.get_runs("test_data.csv")
            assert len(runs) == 1


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class."""

    def test_analyze_returns_trend_analysis(self, temp_db_path, mock_execution_result):
        """Test that analyze returns a TrendAnalysis."""
        storage = HistoryStorage(db_path=temp_db_path)
        storage.store(mock_execution_result)

        analyzer = TrendAnalyzer(storage)
        analysis = analyzer.analyze("test_data.csv", days=30)

        assert isinstance(analysis, TrendAnalysis)
        assert analysis.source == "test_data.csv"
        assert analysis.current_score == 85.0
        storage.close()

    def test_analyze_empty_source(self, temp_db_path):
        """Test analyzing a source with no data."""
        storage = HistoryStorage(db_path=temp_db_path)
        analyzer = TrendAnalyzer(storage)
        analysis = analyzer.analyze("nonexistent.csv", days=30)

        assert analysis.total_runs == 0
        assert analysis.score_trend == "stable"
        storage.close()

    def test_trend_analysis_summary(self, temp_db_path, mock_execution_result):
        """Test TrendAnalysis.summary() method."""
        storage = HistoryStorage(db_path=temp_db_path)
        storage.store(mock_execution_result)

        analyzer = TrendAnalyzer(storage)
        analysis = analyzer.analyze("test_data.csv")

        summary = analysis.summary()
        assert "85.0%" in summary
        assert "stable" in summary.lower() or "improving" in summary.lower() or "declining" in summary.lower()
        storage.close()


class TestAnalyzeTrendsFunction:
    """Tests for the analyze_trends convenience function."""

    def test_analyze_trends(self):
        """Test the convenience function."""
        import os
        import tempfile

        # Use a unique temp file that we manage ourselves
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_history.db")

            # Create a mock execution result inline
            mock_check = MagicMock()
            mock_check.type.value = "not_null"

            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.column = "email"
            mock_result.check = mock_check
            mock_result.severity.value = "error"
            mock_result.actual_value = 0
            mock_result.expected_value = 0
            mock_result.message = "No null values"
            mock_result.details = {}

            mock_ruleset = MagicMock()
            mock_ruleset.name = "test_rules"

            mock_exec_result = MagicMock()
            mock_exec_result.source = "test_data.csv"
            mock_exec_result.ruleset = mock_ruleset
            mock_exec_result.started_at = datetime.now()
            mock_exec_result.finished_at = datetime.now()
            mock_exec_result.quality_score = 85.0
            mock_exec_result.total_checks = 10
            mock_exec_result.passed_count = 8
            mock_exec_result.failed_count = 1
            mock_exec_result.warning_count = 1
            mock_exec_result.passed = True
            mock_exec_result.results = [mock_result]
            mock_exec_result.get_failures.return_value = []
            mock_exec_result.get_warnings.return_value = []

            # Store data
            with HistoryStorage(db_path=db_path) as storage:
                storage.store(mock_exec_result)

            # Now test analyze_trends - it will create its own connection
            # We need to make sure it closes properly
            from duckguard.history.storage import HistoryStorage as HistStorage
            from duckguard.history.trends import TrendAnalyzer

            storage2 = HistStorage(db_path=db_path)
            try:
                analyzer = TrendAnalyzer(storage2)
                analysis = analyzer.analyze("test_data.csv", days=30)
                assert isinstance(analysis, TrendAnalysis)
                assert analysis.current_score == 85.0
            finally:
                storage2.close()
