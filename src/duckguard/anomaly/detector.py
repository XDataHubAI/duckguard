"""High-level anomaly detector for DuckGuard.

Provides easy-to-use anomaly detection for datasets and columns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from duckguard.anomaly.methods import (
    AnomalyScore,
    create_method,
)
from duckguard.core.dataset import Dataset


class AnomalyType(Enum):
    """Types of anomalies."""

    VALUE_OUTLIER = "value_outlier"           # Individual value is unusual
    DISTRIBUTION_SHIFT = "distribution_shift"  # Overall distribution changed
    VOLUME_ANOMALY = "volume_anomaly"          # Row count anomaly
    NULL_SPIKE = "null_spike"                  # Unusual increase in nulls
    CARDINALITY_CHANGE = "cardinality_change"  # Number of distinct values changed


@dataclass
class AnomalyResult:
    """Result of anomaly detection.

    Attributes:
        column: Column name (None for table-level)
        anomaly_type: Type of anomaly
        is_anomaly: Whether an anomaly was detected
        score: Anomaly score
        threshold: Detection threshold
        message: Human-readable message
        details: Additional details
        samples: Sample anomalous values
        detected_at: When the anomaly was detected
    """

    column: str | None
    anomaly_type: AnomalyType
    is_anomaly: bool
    score: float
    threshold: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    samples: list[Any] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class DatasetAnomalyReport:
    """Anomaly detection report for a dataset.

    Attributes:
        source: Data source path
        anomalies: List of detected anomalies
        checked_at: When the check was performed
        statistics: Detection statistics
    """

    source: str
    anomalies: list[AnomalyResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)
    statistics: dict[str, Any] = field(default_factory=dict)

    @property
    def has_anomalies(self) -> bool:
        return any(a.is_anomaly for a in self.anomalies)

    @property
    def anomaly_count(self) -> int:
        return sum(1 for a in self.anomalies if a.is_anomaly)

    def get_anomalies(self) -> list[AnomalyResult]:
        """Get only the detected anomalies."""
        return [a for a in self.anomalies if a.is_anomaly]

    def summary(self) -> str:
        """Generate a summary."""
        if not self.has_anomalies:
            return "No anomalies detected."

        lines = [f"Detected {self.anomaly_count} anomalies:"]
        for anomaly in self.get_anomalies():
            col_str = f"[{anomaly.column}]" if anomaly.column else "[table]"
            lines.append(f"  ⚠️ {col_str} {anomaly.message}")

        return "\n".join(lines)


class AnomalyDetector:
    """Detects anomalies in datasets."""

    def __init__(
        self,
        method: str = "zscore",
        threshold: float | None = None,
        **method_kwargs
    ):
        """Initialize detector.

        Args:
            method: Detection method ("zscore", "iqr", "percent_change")
            threshold: Detection threshold (method-specific default if None)
            **method_kwargs: Additional method parameters
        """
        self.method_name = method

        # Set default thresholds
        if threshold is None:
            defaults = {"zscore": 3.0, "iqr": 1.5, "percent_change": 0.2}
            threshold = defaults.get(method, 3.0)

        self.threshold = threshold
        self.method_kwargs = method_kwargs

    def detect(
        self,
        dataset: Dataset,
        columns: list[str] | None = None,
        include_row_count: bool = True,
        include_null_check: bool = True,
    ) -> DatasetAnomalyReport:
        """Detect anomalies in a dataset.

        Args:
            dataset: Dataset to analyze
            columns: Specific columns to check (None = all numeric)
            include_row_count: Check for row count anomalies
            include_null_check: Check for null percentage spikes

        Returns:
            DatasetAnomalyReport
        """
        report = DatasetAnomalyReport(source=dataset.source)

        # Determine columns to check
        if columns is None:
            columns = self._get_numeric_columns(dataset)

        # Check each column for value anomalies
        for col_name in columns:
            result = self.detect_column(dataset, col_name)
            report.anomalies.append(result)

        # Check null percentages
        if include_null_check:
            for col_name in dataset.columns:
                null_result = self._check_null_anomaly(dataset, col_name)
                if null_result.is_anomaly:
                    report.anomalies.append(null_result)

        report.statistics = {
            "columns_checked": len(columns),
            "method": self.method_name,
            "threshold": self.threshold,
        }

        return report

    def detect_column(
        self,
        dataset: Dataset,
        column: str,
        baseline_values: list[float] | None = None
    ) -> AnomalyResult:
        """Detect anomalies in a specific column.

        Args:
            dataset: Dataset to analyze
            column: Column name
            baseline_values: Historical values for comparison

        Returns:
            AnomalyResult
        """
        col = dataset[column]

        # Get column values
        try:
            # Get numeric stats
            mean = col.mean
            if mean is None:
                return AnomalyResult(
                    column=column,
                    anomaly_type=AnomalyType.VALUE_OUTLIER,
                    is_anomaly=False,
                    score=0.0,
                    threshold=self.threshold,
                    message=f"Column '{column}' is not numeric",
                    details={"reason": "not_numeric"},
                )

            min_val = col.min
            max_val = col.max
            stddev = col.stddev or 0

            # Create detection method
            method = create_method(
                self.method_name,
                threshold=self.threshold,
                **self.method_kwargs
            )

            # If we have baseline values, fit on those
            if baseline_values:
                method.fit(baseline_values)

                # Score current values (using min, max, mean as representatives)
                scores = [
                    method.score(min_val),
                    method.score(max_val),
                    method.score(mean),
                ]

                # Find worst anomaly
                worst = max(scores, key=lambda s: s.score)
                is_anomaly = worst.is_anomaly

            else:
                # No baseline - check current distribution characteristics
                # Look for extreme values relative to mean
                if stddev > 0:
                    z_min = abs(min_val - mean) / stddev if min_val is not None else 0
                    z_max = abs(max_val - mean) / stddev if max_val is not None else 0

                    worst_z = max(z_min, z_max)
                    is_anomaly = worst_z > self.threshold

                    worst = AnomalyScore(
                        value=max_val if z_max > z_min else min_val,
                        score=worst_z,
                        is_anomaly=is_anomaly,
                        threshold=self.threshold,
                        details={
                            "mean": mean,
                            "stddev": stddev,
                            "min": min_val,
                            "max": max_val,
                        }
                    )
                else:
                    is_anomaly = False
                    worst = AnomalyScore(
                        value=mean,
                        score=0.0,
                        is_anomaly=False,
                        threshold=self.threshold,
                    )

            # Build result
            message = self._build_message(column, worst, mean, stddev)

            return AnomalyResult(
                column=column,
                anomaly_type=AnomalyType.VALUE_OUTLIER,
                is_anomaly=is_anomaly,
                score=worst.score,
                threshold=self.threshold,
                message=message,
                details={
                    "mean": mean,
                    "stddev": stddev,
                    "min": min_val,
                    "max": max_val,
                    "method": self.method_name,
                    **worst.details,
                },
                samples=[worst.value] if is_anomaly else [],
            )

        except Exception as e:
            return AnomalyResult(
                column=column,
                anomaly_type=AnomalyType.VALUE_OUTLIER,
                is_anomaly=False,
                score=0.0,
                threshold=self.threshold,
                message=f"Error analyzing column '{column}': {e}",
                details={"error": str(e)},
            )

    def _check_null_anomaly(
        self,
        dataset: Dataset,
        column: str,
        expected_null_pct: float = 5.0
    ) -> AnomalyResult:
        """Check for unusual null percentages."""
        col = dataset[column]
        null_pct = col.null_percent

        # Consider it anomalous if null % is much higher than expected
        is_anomaly = null_pct > expected_null_pct * 2 and null_pct > 10

        return AnomalyResult(
            column=column,
            anomaly_type=AnomalyType.NULL_SPIKE,
            is_anomaly=is_anomaly,
            score=null_pct,
            threshold=expected_null_pct,
            message=f"Column '{column}' has {null_pct:.1f}% nulls (threshold: {expected_null_pct}%)",
            details={
                "null_percent": null_pct,
                "null_count": col.null_count,
                "expected_max": expected_null_pct,
            },
        )

    def _get_numeric_columns(self, dataset: Dataset) -> list[str]:
        """Get list of numeric columns."""
        numeric_cols = []
        for col_name in dataset.columns:
            col = dataset[col_name]
            try:
                if col.mean is not None:
                    numeric_cols.append(col_name)
            except Exception:
                pass
        return numeric_cols

    def _build_message(
        self,
        column: str,
        worst: AnomalyScore,
        mean: float,
        stddev: float
    ) -> str:
        """Build human-readable message."""
        if not worst.is_anomaly:
            return f"Column '{column}' values are within normal range"

        direction = worst.details.get("deviation_direction", "")
        if direction == "above":
            return f"Column '{column}' has unusually high values (max: {worst.value:.2f}, mean: {mean:.2f})"
        elif direction == "below":
            return f"Column '{column}' has unusually low values (min: {worst.value:.2f}, mean: {mean:.2f})"
        else:
            return f"Column '{column}' has anomalous values (score: {worst.score:.2f})"


def detect_anomalies(
    dataset: Dataset,
    method: str = "zscore",
    threshold: float | None = None,
    columns: list[str] | None = None,
) -> DatasetAnomalyReport:
    """Detect anomalies in a dataset.

    Args:
        dataset: Dataset to analyze
        method: Detection method
        threshold: Detection threshold
        columns: Columns to check

    Returns:
        DatasetAnomalyReport
    """
    detector = AnomalyDetector(method=method, threshold=threshold)
    return detector.detect(dataset, columns=columns)


def detect_column_anomalies(
    dataset: Dataset,
    column: str,
    method: str = "zscore",
    threshold: float | None = None,
    baseline: list[float] | None = None,
) -> AnomalyResult:
    """Detect anomalies in a specific column.

    Args:
        dataset: Dataset
        column: Column name
        method: Detection method
        threshold: Detection threshold
        baseline: Historical values for comparison

    Returns:
        AnomalyResult
    """
    detector = AnomalyDetector(method=method, threshold=threshold)
    return detector.detect_column(dataset, column, baseline_values=baseline)
