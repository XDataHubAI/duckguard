"""Freshness monitoring implementation.

Provides functionality to check data freshness via file modification times
and timestamp columns in the data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset


class FreshnessMethod(str, Enum):
    """Methods for checking freshness."""

    FILE_MTIME = "file_mtime"
    COLUMN_MAX = "column_max"
    COLUMN_MIN = "column_min"
    METADATA = "metadata"
    UNKNOWN = "unknown"


@dataclass
class FreshnessResult:
    """Result of a freshness check.

    Attributes:
        source: Data source path
        last_modified: Timestamp of last modification
        age_seconds: Age in seconds (None if unknown)
        age_human: Human-readable age string
        is_fresh: Whether the data meets freshness threshold
        threshold_seconds: Threshold used (None if no threshold)
        method: Method used to determine freshness
        details: Additional details about the check
    """

    source: str
    last_modified: datetime | None
    age_seconds: float | None
    age_human: str
    is_fresh: bool
    threshold_seconds: float | None
    method: FreshnessMethod
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "FRESH" if self.is_fresh else "STALE"
        return f"[{status}] {self.source}: {self.age_human} (method: {self.method.value})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "age_seconds": self.age_seconds,
            "age_human": self.age_human,
            "is_fresh": self.is_fresh,
            "threshold_seconds": self.threshold_seconds,
            "method": self.method.value,
            "details": self.details,
        }


class FreshnessMonitor:
    """Monitor data freshness.

    Usage:
        from duckguard.freshness import FreshnessMonitor
        from datetime import timedelta

        # Create monitor with default 24-hour threshold
        monitor = FreshnessMonitor()

        # Check file freshness
        result = monitor.check("data.csv")
        print(f"Fresh: {result.is_fresh}, Age: {result.age_human}")

        # Check with custom threshold
        monitor = FreshnessMonitor(threshold=timedelta(hours=6))
        result = monitor.check("data.csv")

        # Check column timestamp
        from duckguard import connect
        data = connect("data.csv")
        result = monitor.check_column_timestamp(data, "updated_at")
    """

    def __init__(self, threshold: timedelta | None = None):
        """Initialize freshness monitor.

        Args:
            threshold: Maximum acceptable age for data to be considered fresh.
                      Defaults to 24 hours.
        """
        self.threshold = threshold or timedelta(hours=24)

    @property
    def threshold_seconds(self) -> float:
        """Get threshold in seconds."""
        return self.threshold.total_seconds()

    def check(
        self,
        source: str | Dataset,
        column: str | None = None,
    ) -> FreshnessResult:
        """Check freshness using the most appropriate method.

        Args:
            source: Data source path or Dataset object
            column: Optional timestamp column to check

        Returns:
            FreshnessResult with freshness information
        """
        # Import here to avoid circular imports
        from duckguard.core.dataset import Dataset

        if isinstance(source, Dataset):
            dataset = source
            source_path = dataset.source
        else:
            source_path = source
            dataset = None

        # If column specified, use column method
        if column and dataset:
            return self.check_column_timestamp(dataset, column)

        # Try to determine best method
        if self._is_local_file(source_path):
            return self.check_file_mtime(source_path)
        elif dataset:
            # Try to auto-detect timestamp column
            timestamp_col = self._detect_timestamp_column(dataset)
            if timestamp_col:
                return self.check_column_timestamp(dataset, timestamp_col)

        # Return unknown result
        return FreshnessResult(
            source=source_path,
            last_modified=None,
            age_seconds=None,
            age_human="unknown",
            is_fresh=True,  # Default to fresh if can't determine
            threshold_seconds=self.threshold_seconds,
            method=FreshnessMethod.UNKNOWN,
            details={"reason": "Cannot determine freshness for this source type"},
        )

    def check_file_mtime(self, path: str | Path) -> FreshnessResult:
        """Check freshness via file modification time.

        Args:
            path: Path to the file

        Returns:
            FreshnessResult with file modification information
        """
        path = Path(path)
        source_str = str(path)

        if not path.exists():
            return FreshnessResult(
                source=source_str,
                last_modified=None,
                age_seconds=None,
                age_human="file not found",
                is_fresh=False,
                threshold_seconds=self.threshold_seconds,
                method=FreshnessMethod.FILE_MTIME,
                details={"error": "File does not exist"},
            )

        try:
            mtime = os.path.getmtime(path)
            last_modified = datetime.fromtimestamp(mtime)
            now = datetime.now()
            age = now - last_modified
            age_seconds = age.total_seconds()

            is_fresh = age_seconds <= self.threshold_seconds

            return FreshnessResult(
                source=source_str,
                last_modified=last_modified,
                age_seconds=age_seconds,
                age_human=self._format_age(age),
                is_fresh=is_fresh,
                threshold_seconds=self.threshold_seconds,
                method=FreshnessMethod.FILE_MTIME,
                details={
                    "file_size": path.stat().st_size,
                    "threshold_human": self._format_age(self.threshold),
                },
            )
        except OSError as e:
            return FreshnessResult(
                source=source_str,
                last_modified=None,
                age_seconds=None,
                age_human="error reading file",
                is_fresh=False,
                threshold_seconds=self.threshold_seconds,
                method=FreshnessMethod.FILE_MTIME,
                details={"error": str(e)},
            )

    def check_column_timestamp(
        self,
        dataset: Dataset,
        column: str,
        use_max: bool = True,
    ) -> FreshnessResult:
        """Check freshness via timestamp column.

        Args:
            dataset: Dataset to check
            column: Timestamp column name
            use_max: Use MAX (most recent) if True, MIN (oldest) if False

        Returns:
            FreshnessResult with column timestamp information
        """
        source_str = dataset.source
        method = FreshnessMethod.COLUMN_MAX if use_max else FreshnessMethod.COLUMN_MIN

        # Verify column exists
        if column not in dataset.columns:
            return FreshnessResult(
                source=source_str,
                last_modified=None,
                age_seconds=None,
                age_human="column not found",
                is_fresh=False,
                threshold_seconds=self.threshold_seconds,
                method=method,
                details={"error": f"Column '{column}' not found in dataset"},
            )

        try:
            # Get max/min timestamp from column
            ref = dataset.engine.get_source_reference(dataset.source)
            agg_func = "MAX" if use_max else "MIN"
            sql = f"SELECT {agg_func}({column}) as ts FROM {ref}"
            result = dataset.engine.fetch_all(sql)

            if not result or result[0][0] is None:
                return FreshnessResult(
                    source=source_str,
                    last_modified=None,
                    age_seconds=None,
                    age_human="no data",
                    is_fresh=False,
                    threshold_seconds=self.threshold_seconds,
                    method=method,
                    details={"error": "Column contains no timestamp values"},
                )

            timestamp_value = result[0][0]

            # Parse timestamp
            if isinstance(timestamp_value, datetime):
                last_modified = timestamp_value
            elif isinstance(timestamp_value, str):
                # Try common formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%d",
                ]:
                    try:
                        last_modified = datetime.strptime(timestamp_value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return FreshnessResult(
                        source=source_str,
                        last_modified=None,
                        age_seconds=None,
                        age_human="invalid timestamp format",
                        is_fresh=False,
                        threshold_seconds=self.threshold_seconds,
                        method=method,
                        details={"error": f"Cannot parse timestamp: {timestamp_value}"},
                    )
            else:
                return FreshnessResult(
                    source=source_str,
                    last_modified=None,
                    age_seconds=None,
                    age_human="unsupported type",
                    is_fresh=False,
                    threshold_seconds=self.threshold_seconds,
                    method=method,
                    details={"error": f"Unsupported timestamp type: {type(timestamp_value)}"},
                )

            now = datetime.now()
            age = now - last_modified
            age_seconds = age.total_seconds()

            is_fresh = age_seconds <= self.threshold_seconds

            return FreshnessResult(
                source=source_str,
                last_modified=last_modified,
                age_seconds=age_seconds,
                age_human=self._format_age(age),
                is_fresh=is_fresh,
                threshold_seconds=self.threshold_seconds,
                method=method,
                details={
                    "column": column,
                    "aggregation": agg_func,
                    "threshold_human": self._format_age(self.threshold),
                },
            )

        except Exception as e:
            return FreshnessResult(
                source=source_str,
                last_modified=None,
                age_seconds=None,
                age_human="query error",
                is_fresh=False,
                threshold_seconds=self.threshold_seconds,
                method=method,
                details={"error": str(e)},
            )

    def _is_local_file(self, source: str) -> bool:
        """Check if source is a local file path."""
        # Check for URL schemes
        parsed = urlparse(source)
        if parsed.scheme and parsed.scheme not in ("", "file"):
            return False

        # Check for connection strings
        if "://" in source and not source.startswith("file://"):
            return False

        # Check if path exists
        path = Path(source)
        return path.exists() and path.is_file()

    def _detect_timestamp_column(self, dataset: Dataset) -> str | None:
        """Try to auto-detect a timestamp column."""
        timestamp_patterns = [
            "updated_at", "modified_at", "last_modified", "modified",
            "created_at", "timestamp", "date", "datetime", "time",
            "update_time", "modify_time", "last_update",
        ]

        columns_lower = {c.lower(): c for c in dataset.columns}

        for pattern in timestamp_patterns:
            if pattern in columns_lower:
                return columns_lower[pattern]

        return None

    def _format_age(self, age: timedelta) -> str:
        """Format a timedelta as human-readable string."""
        total_seconds = int(age.total_seconds())

        if total_seconds < 0:
            return "in the future"
        elif total_seconds < 60:
            return f"{total_seconds} seconds ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif total_seconds < 604800:
            days = total_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif total_seconds < 2592000:
            weeks = total_seconds // 604800
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            months = total_seconds // 2592000
            return f"{months} month{'s' if months != 1 else ''} ago"


def parse_age_string(age_str: str) -> timedelta:
    """Parse an age string like '24h', '7d', '1w' into timedelta.

    Args:
        age_str: Age string with unit (s, m, h, d, w)

    Returns:
        timedelta representing the age

    Examples:
        parse_age_string("24h") -> timedelta(hours=24)
        parse_age_string("7d") -> timedelta(days=7)
        parse_age_string("1w") -> timedelta(weeks=1)
    """
    age_str = age_str.strip().lower()

    if age_str.endswith("s"):
        return timedelta(seconds=int(age_str[:-1]))
    elif age_str.endswith("m"):
        return timedelta(minutes=int(age_str[:-1]))
    elif age_str.endswith("h"):
        return timedelta(hours=int(age_str[:-1]))
    elif age_str.endswith("d"):
        return timedelta(days=int(age_str[:-1]))
    elif age_str.endswith("w"):
        return timedelta(weeks=int(age_str[:-1]))
    else:
        # Assume hours if no unit
        return timedelta(hours=int(age_str))
