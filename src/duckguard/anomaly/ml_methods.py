"""ML-based anomaly detection methods for DuckGuard.

Provides advanced anomaly detection methods that learn from historical data
rather than requiring manual threshold configuration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from duckguard.anomaly.baselines import BaselineStorage
from duckguard.anomaly.methods import AnomalyMethod, AnomalyScore
from duckguard.history.storage import HistoryStorage


@dataclass
class BaselineComparison:
    """Result of comparing current data to baseline.

    Attributes:
        column_name: Name of the column
        metric: Metric being compared
        baseline_value: Stored baseline value
        current_value: Current value
        deviation: How far current deviates from baseline
        deviation_percent: Deviation as percentage
        is_anomalous: Whether this deviation is anomalous
        details: Additional comparison details
    """

    column_name: str
    metric: str
    baseline_value: float
    current_value: float
    deviation: float
    deviation_percent: float
    is_anomalous: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionComparison:
    """Result of comparing distributions.

    Attributes:
        column_name: Name of the column
        statistic: Test statistic value
        p_value: P-value of the test
        is_drifted: Whether significant drift was detected
        method: Statistical test used
        details: Additional test details
    """

    column_name: str
    statistic: float
    p_value: float
    is_drifted: bool
    method: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_drift(self) -> bool:
        """Alias for is_drifted (backward compatibility)."""
        return self.is_drifted

    @property
    def message(self) -> str:
        """Generate a human-readable message about the comparison."""
        if self.is_drifted:
            return f"Distribution drift detected (p-value: {self.p_value:.4f} < threshold)"
        return f"No significant drift detected (p-value: {self.p_value:.4f})"


class BaselineMethod(AnomalyMethod):
    """Detect anomalies by comparing to learned baseline.

    This method learns statistical properties from historical data and
    detects values that deviate significantly from the learned baseline.

    Usage:
        from duckguard.anomaly.ml_methods import BaselineMethod

        # Create method with storage
        method = BaselineMethod(sensitivity=2.0)

        # Fit to baseline data
        baseline_values = [100, 102, 98, 105, 97, 103]
        method.fit(baseline_values)

        # Score new values
        score = method.score(150)  # High score = anomalous
    """

    def __init__(
        self,
        storage: HistoryStorage | None = None,
        sensitivity: float = 2.0,
        min_samples: int = 5,
    ):
        """Initialize baseline method.

        Args:
            storage: Optional HistoryStorage for persisting baselines
            sensitivity: Number of standard deviations for anomaly threshold
            min_samples: Minimum samples needed before flagging anomalies
        """
        self._storage = storage
        self._baseline_storage = BaselineStorage(storage) if storage else None
        self.sensitivity = sensitivity
        self.min_samples = min_samples

        # Learned parameters
        self._mean: float = 0.0
        self._stddev: float = 1.0
        self._min: float = float('-inf')
        self._max: float = float('inf')
        self._sample_count: int = 0
        self._fitted = False

    @property
    def name(self) -> str:
        return "baseline"

    @property
    def baseline_mean(self) -> float:
        """Get the baseline mean value."""
        return self._mean

    @property
    def baseline_std(self) -> float:
        """Get the baseline standard deviation."""
        return self._stddev

    @property
    def is_fitted(self) -> bool:
        """Check if the model has been fitted."""
        return self._fitted

    def fit(self, values: list[float] | Any) -> None:
        """Learn baseline from values.

        Args:
            values: List of numeric values or Column object to learn from
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(values, Column):
            values = self._get_column_values(values)

        clean = [v for v in values if v is not None and not math.isnan(v)]
        if not clean:
            return

        n = len(clean)
        self._mean = sum(clean) / n
        self._min = min(clean)
        self._max = max(clean)

        if n > 1:
            variance = sum((x - self._mean) ** 2 for x in clean) / (n - 1)
            self._stddev = math.sqrt(variance) if variance > 0 else 1.0
        else:
            self._stddev = 1.0

        self._sample_count = n
        self._fitted = True

    def _get_column_values(self, column) -> list[float]:
        """Extract numeric values from a Column object."""
        dataset = column._dataset
        column_name = column._name
        engine = dataset._engine
        table_name = dataset._source.replace('\\', '/')

        query = f"""
            SELECT "{column_name}"
            FROM '{table_name}'
            WHERE "{column_name}" IS NOT NULL
        """

        result = engine.fetch_all(query)
        return [float(row[0]) for row in result]

    def score(self, value: float | Any) -> AnomalyScore | list[AnomalyScore]:
        """Score a value or column against the baseline.

        Args:
            value: Single numeric value or Column object to score

        Returns:
            AnomalyScore for single value, or list of AnomalyScores for Column
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(value, Column):
            values = self._get_column_values(value)
            return [self.score(v) for v in values]

        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.sensitivity,
                details={"reason": "null_or_nan"}
            )

        # Not enough samples to determine anomaly
        if self._sample_count < self.min_samples:
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.sensitivity,
                details={"reason": "insufficient_samples", "sample_count": self._sample_count}
            )

        # Calculate z-score deviation from baseline
        if self._stddev == 0:
            deviation = 0.0
        else:
            deviation = abs((value - self._mean) / self._stddev)

        is_anomaly = deviation > self.sensitivity

        return AnomalyScore(
            value=value,
            score=deviation,
            is_anomaly=is_anomaly,
            threshold=self.sensitivity,
            details={
                "baseline_mean": self._mean,
                "baseline_stddev": self._stddev,
                "baseline_min": self._min,
                "baseline_max": self._max,
                "deviation_stddevs": deviation,
                "sample_count": self._sample_count,
            }
        )

    def compare_to_baseline(
        self,
        values: list[float],
        metric: str = "mean",
    ) -> BaselineComparison:
        """Compare current values to stored baseline.

        Args:
            values: Current values to compare
            metric: Metric to compare (mean, stddev, min, max)

        Returns:
            BaselineComparison result
        """
        clean = [v for v in values if v is not None and not math.isnan(v)]
        if not clean:
            raise ValueError("No valid values to compare")

        # Calculate current metric
        if metric == "mean":
            current = sum(clean) / len(clean)
            baseline = self._mean
        elif metric == "stddev":
            current_mean = sum(clean) / len(clean)
            variance = sum((x - current_mean) ** 2 for x in clean) / (len(clean) - 1)
            current = math.sqrt(variance) if variance > 0 else 0.0
            baseline = self._stddev
        elif metric == "min":
            current = min(clean)
            baseline = self._min
        elif metric == "max":
            current = max(clean)
            baseline = self._max
        else:
            raise ValueError(f"Unknown metric: {metric}")

        deviation = abs(current - baseline)
        deviation_percent = (deviation / baseline * 100) if baseline != 0 else 0.0

        # Use sensitivity threshold for anomaly detection
        threshold = self.sensitivity * self._stddev if metric == "mean" else deviation_percent > 20

        is_anomalous = deviation > threshold if isinstance(threshold, float) else threshold

        return BaselineComparison(
            column_name="",  # Set by caller
            metric=metric,
            baseline_value=baseline,
            current_value=current,
            deviation=deviation,
            deviation_percent=deviation_percent,
            is_anomalous=is_anomalous,
            details={
                "sensitivity": self.sensitivity,
                "threshold": threshold if isinstance(threshold, float) else 20.0,
            }
        )

    def save_baseline(
        self,
        source: str,
        column_name: str,
    ) -> None:
        """Save learned baseline to storage.

        Args:
            source: Data source path
            column_name: Column name
        """
        if not self._baseline_storage:
            raise ValueError("No storage configured for baseline persistence")

        if not self._fitted:
            raise ValueError("Method not fitted - call fit() first")

        self._baseline_storage.store(source, column_name, "mean", self._mean, sample_size=self._sample_count)
        self._baseline_storage.store(source, column_name, "stddev", self._stddev, sample_size=self._sample_count)
        self._baseline_storage.store(source, column_name, "min", self._min, sample_size=self._sample_count)
        self._baseline_storage.store(source, column_name, "max", self._max, sample_size=self._sample_count)

    def load_baseline(
        self,
        source: str,
        column_name: str,
    ) -> bool:
        """Load baseline from storage.

        Args:
            source: Data source path
            column_name: Column name

        Returns:
            True if baseline was loaded, False if not found
        """
        if not self._baseline_storage:
            raise ValueError("No storage configured for baseline persistence")

        mean_bl = self._baseline_storage.get(source, column_name, "mean")
        if not mean_bl:
            return False

        self._mean = mean_bl.value
        self._sample_count = mean_bl.sample_size or 0

        stddev_bl = self._baseline_storage.get(source, column_name, "stddev")
        if stddev_bl:
            self._stddev = stddev_bl.value

        min_bl = self._baseline_storage.get(source, column_name, "min")
        if min_bl:
            self._min = min_bl.value

        max_bl = self._baseline_storage.get(source, column_name, "max")
        if max_bl:
            self._max = max_bl.value

        self._fitted = True
        return True


class KSTestMethod(AnomalyMethod):
    """Detect distribution drift using Kolmogorov-Smirnov test.

    This method compares the current data distribution to a baseline
    distribution and detects statistically significant differences.

    Usage:
        from duckguard.anomaly.ml_methods import KSTestMethod

        method = KSTestMethod(p_value_threshold=0.05)

        # Fit to baseline data
        baseline_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        method.fit(baseline_data)

        # Detect if new data has drifted
        new_data = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        comparison = method.compare_distributions(new_data)
        if comparison.is_drifted:
            print(f"Distribution drift detected! p-value: {comparison.p_value}")
    """

    def __init__(self, p_value_threshold: float = 0.05):
        """Initialize KS test method.

        Args:
            p_value_threshold: P-value below which drift is detected
        """
        self.p_value_threshold = p_value_threshold
        self._baseline_values: list[float] = []
        self._baseline_ecdf: list[tuple[float, float]] = []
        self._fitted = False

    @property
    def name(self) -> str:
        return "ks_test"

    def fit(self, values: list[float] | Any) -> None:
        """Learn baseline distribution.

        Args:
            values: List of numeric values or Column object for baseline
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(values, Column):
            values = self._get_column_values(values)

        clean = sorted(v for v in values if v is not None and not math.isnan(v))
        if not clean:
            return

        self._baseline_values = clean
        self._baseline_ecdf = self._compute_ecdf(clean)
        self._fitted = True

    def _get_column_values(self, column) -> list[float]:
        """Extract numeric values from a Column object."""
        dataset = column._dataset
        column_name = column._name
        engine = dataset._engine
        table_name = dataset._source.replace('\\', '/')

        query = f"""
            SELECT "{column_name}"
            FROM '{table_name}'
            WHERE "{column_name}" IS NOT NULL
        """

        result = engine.fetch_all(query)
        return [float(row[0]) for row in result]

    def score(self, value: float | Any) -> AnomalyScore | list[AnomalyScore]:
        """Score a value or column (uses empirical CDF).

        For distribution testing, use compare_distributions() instead.

        Args:
            value: Single numeric value or Column object to score

        Returns:
            AnomalyScore for single value, or list of AnomalyScores for Column
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(value, Column):
            values = self._get_column_values(value)
            return [self.score(v) for v in values]

        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.p_value_threshold,
                details={"reason": "null_or_nan"}
            )

        if not self._fitted:
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.p_value_threshold,
                details={"reason": "not_fitted"}
            )

        # Find percentile in baseline
        percentile = self._get_percentile(value)

        # Extreme percentiles indicate potential anomalies
        is_anomaly = percentile < 0.01 or percentile > 0.99

        return AnomalyScore(
            value=value,
            score=min(percentile, 1 - percentile),  # Distance from extremes
            is_anomaly=is_anomaly,
            threshold=0.01,
            details={
                "percentile": percentile,
                "baseline_size": len(self._baseline_values),
            }
        )

    def compare_distributions(
        self,
        current_values: list[float] | Any,
        baseline_values: list[float] | Any | None = None,
    ) -> DistributionComparison:
        """Compare current distribution to baseline using KS test.

        Args:
            current_values: List of values or Column object to compare
            baseline_values: Optional baseline data. If not provided and not fitted,
                           will use current_values as baseline (self-comparison)

        Returns:
            DistributionComparison with test results
        """
        # Handle Column objects for current_values
        from duckguard.core.column import Column
        if isinstance(current_values, Column):
            current_values = self._get_column_values(current_values)

        # Handle Column objects for baseline_values
        if baseline_values is not None and isinstance(baseline_values, Column):
            baseline_values = self._get_column_values(baseline_values)

        # Auto-fit if not fitted and baseline provided
        if not self._fitted:
            if baseline_values is not None:
                self.fit(baseline_values)
            else:
                # Use current_values as baseline (self-comparison for normality test)
                self.fit(current_values)

        clean_current = sorted(v for v in current_values if v is not None and not math.isnan(v))
        if not clean_current:
            raise ValueError("No valid values to compare")

        # Compute KS statistic (two-sample)
        ks_stat, p_value = self._ks_two_sample(self._baseline_values, clean_current)

        return DistributionComparison(
            column_name="",  # Set by caller
            statistic=ks_stat,
            p_value=p_value,
            is_drifted=p_value < self.p_value_threshold,
            method="ks_test",
            details={
                "baseline_size": len(self._baseline_values),
                "current_size": len(clean_current),
                "threshold": self.p_value_threshold,
            }
        )

    def _compute_ecdf(self, sorted_values: list[float]) -> list[tuple[float, float]]:
        """Compute empirical CDF from sorted values."""
        n = len(sorted_values)
        return [(v, (i + 1) / n) for i, v in enumerate(sorted_values)]

    def _get_percentile(self, value: float) -> float:
        """Get percentile of value in baseline distribution."""
        if not self._baseline_values:
            return 0.5

        count_below = sum(1 for v in self._baseline_values if v <= value)
        return count_below / len(self._baseline_values)

    def _ks_two_sample(
        self,
        sample1: list[float],
        sample2: list[float],
    ) -> tuple[float, float]:
        """Compute two-sample KS test statistic and approximate p-value.

        Returns:
            Tuple of (KS statistic, approximate p-value)
        """
        n1, n2 = len(sample1), len(sample2)
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0

        # Merge and sort all values with source labels
        combined = [(v, 1) for v in sample1] + [(v, 2) for v in sample2]
        combined.sort(key=lambda x: x[0])

        # Compute ECDFs and find max difference
        ecdf1, ecdf2 = 0.0, 0.0
        max_diff = 0.0

        for value, source in combined:
            if source == 1:
                ecdf1 += 1 / n1
            else:
                ecdf2 += 1 / n2
            max_diff = max(max_diff, abs(ecdf1 - ecdf2))

        # Approximate p-value using asymptotic formula
        # P(D > d) ≈ 2 * exp(-2 * n * d^2) where n = n1*n2/(n1+n2)
        n_effective = (n1 * n2) / (n1 + n2)
        p_value = 2 * math.exp(-2 * n_effective * max_diff ** 2)
        p_value = min(1.0, max(0.0, p_value))

        return max_diff, p_value


class SeasonalMethod(AnomalyMethod):
    """Detect anomalies accounting for seasonal patterns.

    This method learns typical values for different time periods
    (hour of day, day of week, etc.) and detects deviations from
    expected seasonal patterns.

    Usage:
        from duckguard.anomaly.ml_methods import SeasonalMethod

        method = SeasonalMethod(period="daily", sensitivity=2.0)

        # Fit with time-value pairs
        # values format: [(timestamp, value), ...]
        method.fit_with_timestamps(historical_data)

        # Score new values
        score = method.score_with_timestamp(new_timestamp, new_value)
    """

    PERIODS = {
        "hourly": 24,      # 24 buckets (hours of day)
        "daily": 7,       # 7 buckets (days of week)
        "weekly": 52,     # 52 buckets (weeks of year)
        "monthly": 12,    # 12 buckets (months of year)
    }

    def __init__(
        self,
        period: str = "daily",
        sensitivity: float = 2.0,
    ):
        """Initialize seasonal method.

        Args:
            period: Seasonality period (hourly, daily, weekly, monthly)
            sensitivity: Number of standard deviations for anomaly threshold
        """
        if period not in self.PERIODS:
            raise ValueError(f"Unknown period: {period}. Valid: {list(self.PERIODS.keys())}")

        self.period = period
        self.sensitivity = sensitivity
        self._num_buckets = self.PERIODS[period]

        # Learned parameters per bucket
        self._bucket_means: dict[int, float] = {}
        self._bucket_stddevs: dict[int, float] = {}
        self._bucket_counts: dict[int, int] = {}
        self._fitted = False

        # For non-timestamped fitting
        self._global_mean: float = 0.0
        self._global_stddev: float = 1.0

    @property
    def name(self) -> str:
        return f"seasonal_{self.period}"

    def fit(self, values: list[float] | Any) -> None:
        """Fit without timestamps (falls back to global statistics).

        For proper seasonal detection, use fit_with_timestamps().

        Args:
            values: List of numeric values or Column object
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(values, Column):
            values = self._get_column_values(values)

        clean = [v for v in values if v is not None and not math.isnan(v)]
        if not clean:
            return

        n = len(clean)
        self._global_mean = sum(clean) / n

        if n > 1:
            variance = sum((x - self._global_mean) ** 2 for x in clean) / (n - 1)
            self._global_stddev = math.sqrt(variance) if variance > 0 else 1.0

        self._fitted = True

    def _get_column_values(self, column) -> list[float]:
        """Extract numeric values from a Column object."""
        dataset = column._dataset
        column_name = column._name
        engine = dataset._engine
        table_name = dataset._source.replace('\\', '/')

        query = f"""
            SELECT "{column_name}"
            FROM '{table_name}'
            WHERE "{column_name}" IS NOT NULL
        """

        result = engine.fetch_all(query)
        return [float(row[0]) for row in result]

    def fit_with_timestamps(
        self,
        data: list[tuple[Any, float]],
    ) -> None:
        """Fit with timestamps for seasonal pattern learning.

        Args:
            data: List of (timestamp, value) tuples.
                  Timestamps can be datetime objects or timestamps.
        """
        from datetime import datetime

        # Group values by bucket
        buckets: dict[int, list[float]] = {i: [] for i in range(self._num_buckets)}

        for timestamp, value in data:
            if value is None or math.isnan(value):
                continue

            if isinstance(timestamp, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp)

            bucket = self._get_bucket(timestamp)
            buckets[bucket].append(value)

        # Compute statistics per bucket
        for bucket, values in buckets.items():
            if values:
                n = len(values)
                mean = sum(values) / n
                self._bucket_means[bucket] = mean
                self._bucket_counts[bucket] = n

                if n > 1:
                    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
                    self._bucket_stddevs[bucket] = math.sqrt(variance) if variance > 0 else 1.0
                else:
                    self._bucket_stddevs[bucket] = 1.0

        # Compute global stats as fallback
        all_values = [v for bucket_values in buckets.values() for v in bucket_values]
        if all_values:
            self._global_mean = sum(all_values) / len(all_values)
            if len(all_values) > 1:
                variance = sum((x - self._global_mean) ** 2 for x in all_values) / (len(all_values) - 1)
                self._global_stddev = math.sqrt(variance) if variance > 0 else 1.0

        self._fitted = True

    def score(self, value: float | Any) -> AnomalyScore | list[AnomalyScore]:
        """Score a value or column without timestamp (uses global stats).

        For proper seasonal scoring, use score_with_timestamp().

        Args:
            value: Single numeric value or Column object to score

        Returns:
            AnomalyScore for single value, or list of AnomalyScores for Column
        """
        # Handle Column objects
        from duckguard.core.column import Column
        if isinstance(value, Column):
            values = self._get_column_values(value)
            return [self.score(v) for v in values]

        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.sensitivity,
                details={"reason": "null_or_nan"}
            )

        deviation = abs((value - self._global_mean) / self._global_stddev) if self._global_stddev != 0 else 0.0
        is_anomaly = deviation > self.sensitivity

        return AnomalyScore(
            value=value,
            score=deviation,
            is_anomaly=is_anomaly,
            threshold=self.sensitivity,
            details={
                "global_mean": self._global_mean,
                "global_stddev": self._global_stddev,
                "note": "No timestamp provided - using global statistics",
            }
        )

    def score_with_timestamp(
        self,
        timestamp: Any,
        value: float,
    ) -> AnomalyScore:
        """Score a value with timestamp for seasonal comparison.

        Args:
            timestamp: Datetime or timestamp
            value: Value to score

        Returns:
            AnomalyScore considering seasonal patterns
        """
        from datetime import datetime

        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.sensitivity,
                details={"reason": "null_or_nan"}
            )

        if isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)

        bucket = self._get_bucket(timestamp)

        # Use bucket-specific stats if available, otherwise global
        if bucket in self._bucket_means and self._bucket_counts.get(bucket, 0) >= 3:
            mean = self._bucket_means[bucket]
            stddev = self._bucket_stddevs.get(bucket, 1.0)
            used_bucket = True
        else:
            mean = self._global_mean
            stddev = self._global_stddev
            used_bucket = False

        deviation = abs((value - mean) / stddev) if stddev != 0 else 0.0
        is_anomaly = deviation > self.sensitivity

        return AnomalyScore(
            value=value,
            score=deviation,
            is_anomaly=is_anomaly,
            threshold=self.sensitivity,
            details={
                "bucket": bucket,
                "period": self.period,
                "bucket_mean": mean,
                "bucket_stddev": stddev,
                "used_seasonal": used_bucket,
                "bucket_sample_count": self._bucket_counts.get(bucket, 0),
            }
        )

    def _get_bucket(self, timestamp) -> int:
        """Get bucket index for a timestamp."""
        if self.period == "hourly":
            return timestamp.hour
        elif self.period == "daily":
            return timestamp.weekday()
        elif self.period == "weekly":
            return timestamp.isocalendar()[1] - 1  # Week of year (0-indexed)
        elif self.period == "monthly":
            return timestamp.month - 1  # Month (0-indexed)
        return 0
