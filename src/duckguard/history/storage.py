"""Historical result storage implementation.

Provides persistent storage for validation results in SQLite,
enabling trend analysis and historical comparison.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from duckguard.history.schema import CREATE_TABLES_SQL, QUERIES, SCHEMA_VERSION

if TYPE_CHECKING:
    from duckguard.rules.executor import ExecutionResult


@dataclass
class StoredRun:
    """Represents a stored validation run.

    Attributes:
        run_id: Unique identifier for this run
        source: Data source that was validated
        ruleset_name: Name of the ruleset used (if any)
        started_at: When validation started
        finished_at: When validation finished
        quality_score: Overall quality score (0-100)
        total_checks: Total number of checks executed
        passed_count: Number of checks that passed
        failed_count: Number of checks that failed
        warning_count: Number of warnings
        passed: Whether the validation passed overall
        metadata: Additional metadata (e.g., Airflow context)
    """

    run_id: str
    source: str
    ruleset_name: str | None
    started_at: datetime
    finished_at: datetime | None
    quality_score: float
    total_checks: int
    passed_count: int
    failed_count: int
    warning_count: int
    passed: bool
    metadata: dict[str, Any] | None = None


@dataclass
class StoredCheckResult:
    """Represents a stored check result.

    Attributes:
        id: Database ID
        run_id: Associated run ID
        check_type: Type of check (e.g., NOT_NULL, UNIQUE)
        column_name: Column that was checked (None for table-level)
        passed: Whether the check passed
        severity: Check severity (error, warning, info)
        actual_value: The actual value found
        expected_value: The expected value
        message: Human-readable result message
        details: Additional details
    """

    id: int
    run_id: str
    check_type: str
    column_name: str | None
    passed: bool
    severity: str
    actual_value: str | None
    expected_value: str | None
    message: str | None
    details: dict[str, Any] | None = None


@dataclass
class TrendDataPoint:
    """A single data point in a quality trend.

    Attributes:
        date: The date of this data point
        avg_score: Average quality score for the day
        min_score: Minimum quality score for the day
        max_score: Maximum quality score for the day
        run_count: Number of runs on this day
        passed_count: Number of passing runs
        failed_count: Number of failing runs
    """

    date: str
    avg_score: float
    min_score: float
    max_score: float
    run_count: int
    passed_count: int
    failed_count: int


class HistoryStorage:
    """Storage for historical validation results.

    Stores validation results in a SQLite database for trend analysis
    and historical comparison.

    Usage:
        from duckguard.history import HistoryStorage
        from duckguard import connect, load_rules, execute_rules

        # Run validation
        result = execute_rules(load_rules("rules.yaml"), connect("data.csv"))

        # Store result
        storage = HistoryStorage()
        run_id = storage.store(result)

        # Query history
        runs = storage.get_runs("data.csv", limit=10)
        trend = storage.get_trend("data.csv", days=30)

    Attributes:
        db_path: Path to the SQLite database file
    """

    DEFAULT_DB_PATH = Path.home() / ".duckguard" / "history.db"

    def __init__(self, db_path: str | Path | None = None):
        """Initialize history storage.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.duckguard/history.db
        """
        self.db_path = Path(db_path) if db_path else self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.executescript(CREATE_TABLES_SQL)

        # Set schema version
        conn.execute(
            "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def store(
        self,
        result: ExecutionResult,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store an execution result.

        Args:
            result: ExecutionResult to store
            metadata: Additional metadata (e.g., Airflow context, environment)

        Returns:
            The generated run_id
        """
        conn = self._get_connection()
        run_id = str(uuid.uuid4())

        # Insert run record
        conn.execute(
            QUERIES["insert_run"],
            (
                run_id,
                result.source,
                result.ruleset.name if result.ruleset else None,
                result.started_at.isoformat(),
                result.finished_at.isoformat() if result.finished_at else None,
                result.quality_score,
                result.total_checks,
                result.passed_count,
                result.failed_count,
                result.warning_count,
                1 if result.passed else 0,
                json.dumps(metadata) if metadata else None,
            ),
        )

        # Insert check results
        for check_result in result.results:
            cursor = conn.execute(
                QUERIES["insert_check_result"],
                (
                    run_id,
                    check_result.check.type.value,
                    check_result.column,
                    1 if check_result.passed else 0,
                    check_result.severity.value,
                    str(check_result.actual_value) if check_result.actual_value is not None else None,
                    str(check_result.expected_value) if check_result.expected_value is not None else None,
                    check_result.message,
                    json.dumps(check_result.details) if check_result.details else None,
                ),
            )
            check_id = cursor.lastrowid

            # Insert failed row samples if available (limited to 10)
            if check_result.details and check_result.details.get("failed_rows"):
                failed_rows = check_result.details["failed_rows"][:10]
                for i, row_data in enumerate(failed_rows):
                    if isinstance(row_data, dict):
                        conn.execute(
                            QUERIES["insert_failed_row"],
                            (
                                run_id,
                                check_id,
                                row_data.get("row_index", i),
                                check_result.column or "",
                                str(row_data.get("value")),
                                str(check_result.expected_value),
                                row_data.get("reason", ""),
                                json.dumps(row_data.get("context")) if row_data.get("context") else None,
                            ),
                        )
                    elif isinstance(row_data, int):
                        # Just row index
                        conn.execute(
                            QUERIES["insert_failed_row"],
                            (
                                run_id,
                                check_id,
                                row_data,
                                check_result.column or "",
                                None,
                                str(check_result.expected_value),
                                "",
                                None,
                            ),
                        )

        # Update quality trends
        self._update_trends(result)

        conn.commit()
        return run_id

    def get_runs(
        self,
        source: str | None = None,
        *,
        limit: int = 100,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[StoredRun]:
        """Get validation runs.

        Args:
            source: Filter by data source path. If None, returns all sources.
            limit: Maximum runs to return
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of StoredRun objects, most recent first
        """
        conn = self._get_connection()

        if source is None:
            cursor = conn.execute(QUERIES["get_all_runs"], (limit,))
        elif start_date and end_date:
            cursor = conn.execute(
                QUERIES["get_runs_in_period"],
                (source, start_date.isoformat(), end_date.isoformat()),
            )
        else:
            cursor = conn.execute(
                QUERIES["get_runs_for_source"],
                (source, limit),
            )

        return [self._row_to_stored_run(row) for row in cursor.fetchall()]

    def get_run(self, run_id: str) -> StoredRun | None:
        """Get a specific run by ID.

        Args:
            run_id: The run ID to retrieve

        Returns:
            StoredRun or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(QUERIES["get_run_by_id"], (run_id,))
        row = cursor.fetchone()
        return self._row_to_stored_run(row) if row else None

    def get_latest_run(self, source: str) -> StoredRun | None:
        """Get the most recent run for a source.

        Args:
            source: Data source path

        Returns:
            StoredRun or None if no runs exist
        """
        conn = self._get_connection()
        cursor = conn.execute(QUERIES["get_latest_run"], (source,))
        row = cursor.fetchone()
        return self._row_to_stored_run(row) if row else None

    def get_check_results(self, run_id: str) -> list[StoredCheckResult]:
        """Get check results for a specific run.

        Args:
            run_id: The run ID

        Returns:
            List of StoredCheckResult objects
        """
        conn = self._get_connection()
        cursor = conn.execute(QUERIES["get_check_results_for_run"], (run_id,))

        results = []
        for row in cursor.fetchall():
            results.append(
                StoredCheckResult(
                    id=row["id"],
                    run_id=row["run_id"],
                    check_type=row["check_type"],
                    column_name=row["column_name"],
                    passed=bool(row["passed"]),
                    severity=row["severity"],
                    actual_value=row["actual_value"],
                    expected_value=row["expected_value"],
                    message=row["message"],
                    details=json.loads(row["details"]) if row["details"] else None,
                )
            )
        return results

    def get_trend(
        self,
        source: str,
        days: int = 30,
    ) -> list[TrendDataPoint]:
        """Get quality score trend for a source.

        Args:
            source: Data source path
            days: Number of days to look back

        Returns:
            List of TrendDataPoint objects, ordered by date
        """
        conn = self._get_connection()
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        cursor = conn.execute(
            QUERIES["get_quality_trend"],
            (source, start_date.strftime("%Y-%m-%d")),
        )

        return [
            TrendDataPoint(
                date=row["date"],
                avg_score=row["avg_quality_score"],
                min_score=row["min_quality_score"],
                max_score=row["max_quality_score"],
                run_count=row["run_count"],
                passed_count=row["passed_count"],
                failed_count=row["failed_count"],
            )
            for row in cursor.fetchall()
        ]

    def get_sources(self) -> list[str]:
        """Get all unique sources in the history.

        Returns:
            List of source paths
        """
        conn = self._get_connection()
        cursor = conn.execute(QUERIES["get_unique_sources"])
        return [row["source"] for row in cursor.fetchall()]

    def cleanup(self, days: int = 90) -> int:
        """Delete runs older than specified days.

        Args:
            days: Delete runs older than this many days

        Returns:
            Number of runs deleted
        """
        conn = self._get_connection()
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        # Get count before deletion
        cursor = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE started_at < ?",
            (cutoff.isoformat(),),
        )
        count = cursor.fetchone()[0]

        # Delete old records (cascading will handle related tables)
        conn.execute(QUERIES["delete_old_runs"], (cutoff.isoformat(),))
        conn.commit()

        return count

    def _update_trends(self, result: ExecutionResult) -> None:
        """Update quality trend aggregation."""
        conn = self._get_connection()
        today = datetime.now().strftime("%Y-%m-%d")

        conn.execute(
            QUERIES["upsert_trend"],
            (
                result.source,
                today,
                result.quality_score,
                result.quality_score,
                result.quality_score,
                1 if result.passed else 0,
                0 if result.passed else 1,
            ),
        )

    def _row_to_stored_run(self, row: sqlite3.Row) -> StoredRun:
        """Convert database row to StoredRun."""
        return StoredRun(
            run_id=row["run_id"],
            source=row["source"],
            ruleset_name=row["ruleset_name"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            quality_score=row["quality_score"],
            total_checks=row["total_checks"],
            passed_count=row["passed_count"],
            failed_count=row["failed_count"],
            warning_count=row["warning_count"],
            passed=bool(row["passed"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> HistoryStorage:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
