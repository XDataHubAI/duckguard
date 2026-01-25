"""Baseline storage for ML-based anomaly detection.

Provides functionality to store and retrieve learned baselines for
comparison-based anomaly detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from duckguard.history.schema import QUERIES
from duckguard.history.storage import HistoryStorage


@dataclass
class StoredBaseline:
    """Represents a stored baseline.

    Attributes:
        source: Data source path
        column_name: Column name
        metric: Metric name (mean, stddev, distribution, etc.)
        value: Baseline value (can be complex for distributions)
        sample_size: Number of samples used to compute baseline
        created_at: When baseline was first created
        updated_at: When baseline was last updated
    """

    source: str
    column_name: str
    metric: str
    value: Any
    sample_size: int | None
    created_at: datetime
    updated_at: datetime | None


class BaselineStorage:
    """Store and retrieve learned baselines for anomaly detection.

    Usage:
        from duckguard.anomaly.baselines import BaselineStorage
        from duckguard.history import HistoryStorage

        storage = BaselineStorage()

        # Store a baseline
        storage.store("data.csv", "amount", "mean", 150.5, sample_size=1000)

        # Get a baseline
        baseline = storage.get("data.csv", "amount", "mean")
        if baseline:
            print(f"Baseline mean: {baseline.value}")

        # Update with rolling average
        storage.update("data.csv", "amount", "mean", 155.2,
                      sample_size=100, method="rolling")
    """

    def __init__(self, storage: HistoryStorage | None = None):
        """Initialize baseline storage.

        Args:
            storage: Optional HistoryStorage instance. Uses default if not provided.
        """
        self._storage = storage or HistoryStorage()

    @property
    def storage(self) -> HistoryStorage:
        """Get the underlying storage."""
        return self._storage

    def store(
        self,
        source: str,
        column_name: str,
        metric: str,
        value: Any,
        *,
        sample_size: int | None = None,
    ) -> None:
        """Store or update a baseline.

        Args:
            source: Data source path
            column_name: Column name
            metric: Metric name (mean, stddev, min, max, distribution, etc.)
            value: Baseline value (will be JSON serialized if complex)
            sample_size: Number of samples used to compute the baseline
        """
        conn = self._storage._get_connection()
        now = datetime.now().isoformat()

        # Serialize complex values to JSON
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value)
        else:
            serialized_value = json.dumps(value)

        conn.execute(
            QUERIES["upsert_baseline"],
            (
                source,
                column_name,
                metric,
                serialized_value,
                sample_size,
                now,
                now,
            ),
        )
        conn.commit()

    def get(
        self,
        source: str,
        column_name: str,
        metric: str,
    ) -> StoredBaseline | None:
        """Get a specific baseline.

        Args:
            source: Data source path
            column_name: Column name
            metric: Metric name

        Returns:
            StoredBaseline or None if not found
        """
        conn = self._storage._get_connection()
        cursor = conn.execute(
            QUERIES["get_baseline"],
            (source, column_name, metric),
        )
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_baseline(row)

    def get_all(self, source: str) -> list[StoredBaseline]:
        """Get all baselines for a source.

        Args:
            source: Data source path

        Returns:
            List of StoredBaseline objects
        """
        conn = self._storage._get_connection()
        cursor = conn.execute(
            QUERIES["get_baselines_for_source"],
            (source,),
        )

        return [self._row_to_baseline(row) for row in cursor.fetchall()]

    def update(
        self,
        source: str,
        column_name: str,
        metric: str,
        new_value: Any,
        *,
        sample_size: int | None = None,
        method: str = "replace",
    ) -> None:
        """Update an existing baseline.

        Args:
            source: Data source path
            column_name: Column name
            metric: Metric name
            new_value: New value
            sample_size: Number of samples in new data
            method: Update method - "replace" or "rolling"
        """
        if method == "replace":
            self.store(source, column_name, metric, new_value, sample_size=sample_size)
        elif method == "rolling":
            # Get existing baseline
            existing = self.get(source, column_name, metric)
            if existing and isinstance(existing.value, (int, float)):
                # Rolling average
                old_weight = 0.7  # Give more weight to historical
                new_weight = 0.3
                blended = old_weight * existing.value + new_weight * new_value
                total_samples = (existing.sample_size or 0) + (sample_size or 0)
                self.store(source, column_name, metric, blended, sample_size=total_samples)
            else:
                self.store(source, column_name, metric, new_value, sample_size=sample_size)
        else:
            raise ValueError(f"Unknown update method: {method}")

    def delete(self, source: str) -> int:
        """Delete all baselines for a source.

        Args:
            source: Data source path

        Returns:
            Number of baselines deleted
        """
        conn = self._storage._get_connection()

        # Get count first
        cursor = conn.execute(
            "SELECT COUNT(*) FROM baselines WHERE source = ?",
            (source,),
        )
        count = cursor.fetchone()[0]

        conn.execute(QUERIES["delete_baselines_for_source"], (source,))
        conn.commit()

        return count

    def _row_to_baseline(self, row) -> StoredBaseline:
        """Convert database row to StoredBaseline."""
        value = json.loads(row["baseline_value"])

        return StoredBaseline(
            source=row["source"],
            column_name=row["column_name"],
            metric=row["metric"],
            value=value,
            sample_size=row["sample_size"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )


@dataclass
class ColumnBaseline:
    """Complete baseline for a single column.

    Attributes:
        column_name: Column name
        mean: Mean value
        stddev: Standard deviation
        min: Minimum value
        max: Maximum value
        median: Median value
        null_percent: Percentage of nulls
        unique_percent: Percentage of unique values
        sample_size: Number of samples
        distribution: Optional distribution histogram
    """

    column_name: str
    mean: float | None = None
    stddev: float | None = None
    min: float | None = None
    max: float | None = None
    median: float | None = None
    null_percent: float | None = None
    unique_percent: float | None = None
    sample_size: int | None = None
    distribution: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "column_name": self.column_name,
            "mean": self.mean,
            "stddev": self.stddev,
            "min": self.min,
            "max": self.max,
            "median": self.median,
            "null_percent": self.null_percent,
            "unique_percent": self.unique_percent,
            "sample_size": self.sample_size,
            "distribution": self.distribution,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnBaseline:
        """Create from dictionary."""
        return cls(
            column_name=data["column_name"],
            mean=data.get("mean"),
            stddev=data.get("stddev"),
            min=data.get("min"),
            max=data.get("max"),
            median=data.get("median"),
            null_percent=data.get("null_percent"),
            unique_percent=data.get("unique_percent"),
            sample_size=data.get("sample_size"),
            distribution=data.get("distribution"),
        )
