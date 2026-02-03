"""Anomaly detection methods for DuckGuard.

Implements various statistical methods for detecting anomalies in data.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnomalyScore:
    """Score for a single value indicating how anomalous it is.

    Attributes:
        value: The original value
        score: Anomaly score (higher = more anomalous)
        is_anomaly: Whether this value is considered anomalous
        threshold: The threshold used for classification
        details: Additional method-specific details
    """

    value: Any
    score: float
    is_anomaly: bool
    threshold: float
    details: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: AnomalyScore | float) -> bool:
        """Less than comparison based on score."""
        if isinstance(other, AnomalyScore):
            return self.score < other.score
        return self.score < other

    def __le__(self, other: AnomalyScore | float) -> bool:
        """Less than or equal comparison based on score."""
        if isinstance(other, AnomalyScore):
            return self.score <= other.score
        return self.score <= other

    def __gt__(self, other: AnomalyScore | float) -> bool:
        """Greater than comparison based on score."""
        if isinstance(other, AnomalyScore):
            return self.score > other.score
        return self.score > other

    def __ge__(self, other: AnomalyScore | float) -> bool:
        """Greater than or equal comparison based on score."""
        if isinstance(other, AnomalyScore):
            return self.score >= other.score
        return self.score >= other

    def __eq__(self, other: object) -> bool:
        """Equality comparison based on score."""
        if isinstance(other, AnomalyScore):
            return self.score == other.score
        if isinstance(other, (int, float)):
            return self.score == other
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        """Inequality comparison based on score."""
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __float__(self) -> float:
        """Convert to float (returns the score)."""
        return self.score

    def __format__(self, format_spec: str) -> str:
        """Format the score using the given format specification."""
        return format(self.score, format_spec)


class AnomalyMethod(ABC):
    """Base class for anomaly detection methods."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Method name."""
        pass

    @abstractmethod
    def fit(self, values: list[float]) -> None:
        """Fit the method to historical data.

        Args:
            values: List of numeric values to learn from
        """
        pass

    @abstractmethod
    def score(self, value: float) -> AnomalyScore:
        """Score a single value.

        Args:
            value: Value to score

        Returns:
            AnomalyScore for the value
        """
        pass

    def detect(self, values: list[float]) -> list[AnomalyScore]:
        """Detect anomalies in a list of values.

        Args:
            values: Values to check

        Returns:
            List of AnomalyScore for each value
        """
        return [self.score(v) for v in values]


class ZScoreMethod(AnomalyMethod):
    """Z-Score based anomaly detection.

    Detects values that are many standard deviations from the mean.
    Good for normally distributed data.
    """

    def __init__(self, threshold: float = 3.0):
        """Initialize Z-Score method.

        Args:
            threshold: Number of standard deviations to consider anomalous
        """
        self.threshold = threshold
        self._mean: float = 0.0
        self._std: float = 1.0
        self._fitted = False

    @property
    def name(self) -> str:
        return "zscore"

    def fit(self, values: list[float]) -> None:
        """Fit to data by computing mean and standard deviation."""
        if not values:
            return

        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return

        n = len(clean_values)
        self._mean = sum(clean_values) / n

        if n > 1:
            variance = sum((x - self._mean) ** 2 for x in clean_values) / (n - 1)
            self._std = math.sqrt(variance) if variance > 0 else 1.0
        else:
            self._std = 1.0

        self._fitted = True

    def score(self, value: float) -> AnomalyScore:
        """Score a value using z-score."""
        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.threshold,
                details={"reason": "null_or_nan"}
            )

        if self._std == 0:
            z_score = 0.0
        else:
            z_score = abs((value - self._mean) / self._std)

        is_anomaly = z_score > self.threshold

        return AnomalyScore(
            value=value,
            score=z_score,
            is_anomaly=is_anomaly,
            threshold=self.threshold,
            details={
                "mean": self._mean,
                "std": self._std,
                "z_score": z_score,
                "deviation_direction": "above" if value > self._mean else "below",
            }
        )


class IQRMethod(AnomalyMethod):
    """Interquartile Range based anomaly detection.

    Detects values outside the typical range defined by quartiles.
    More robust to outliers than z-score.
    """

    def __init__(self, multiplier: float = 1.5):
        """Initialize IQR method.

        Args:
            multiplier: IQR multiplier for bounds (1.5 = outlier, 3.0 = extreme)
        """
        self.multiplier = multiplier
        self._q1: float = 0.0
        self._q3: float = 0.0
        self._iqr: float = 0.0
        self._lower_bound: float = float('-inf')
        self._upper_bound: float = float('inf')
        self._fitted = False

    @property
    def name(self) -> str:
        return "iqr"

    def fit(self, values: list[float]) -> None:
        """Fit to data by computing quartiles."""
        clean_values = sorted(v for v in values if v is not None and not math.isnan(v))
        if not clean_values:
            return

        # Calculate Q1 and Q3
        self._q1 = self._percentile(clean_values, 25)
        self._q3 = self._percentile(clean_values, 75)
        self._iqr = self._q3 - self._q1

        # Calculate bounds
        self._lower_bound = self._q1 - (self.multiplier * self._iqr)
        self._upper_bound = self._q3 + (self.multiplier * self._iqr)

        self._fitted = True

    def _percentile(self, sorted_values: list[float], p: float) -> float:
        """Calculate percentile of sorted values."""
        n = len(sorted_values)
        k = (n - 1) * p / 100
        f = math.floor(k)
        c = math.ceil(k)

        if f == c:
            return sorted_values[int(k)]

        return sorted_values[int(f)] * (c - k) + sorted_values[int(c)] * (k - f)

    def score(self, value: float) -> AnomalyScore:
        """Score a value using IQR method."""
        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.multiplier,
                details={"reason": "null_or_nan"}
            )

        # Calculate how many IQRs away from bounds
        if value < self._lower_bound:
            distance = (self._lower_bound - value) / self._iqr if self._iqr > 0 else 0
            is_anomaly = True
            direction = "below"
        elif value > self._upper_bound:
            distance = (value - self._upper_bound) / self._iqr if self._iqr > 0 else 0
            is_anomaly = True
            direction = "above"
        else:
            distance = 0
            is_anomaly = False
            direction = "within"

        return AnomalyScore(
            value=value,
            score=distance,
            is_anomaly=is_anomaly,
            threshold=self.multiplier,
            details={
                "q1": self._q1,
                "q3": self._q3,
                "iqr": self._iqr,
                "lower_bound": self._lower_bound,
                "upper_bound": self._upper_bound,
                "direction": direction,
            }
        )


class PercentChangeMethod(AnomalyMethod):
    """Percent change based anomaly detection.

    Detects values that differ significantly from a baseline.
    Useful for monitoring metrics over time.
    """

    def __init__(self, threshold: float = 0.2, baseline_type: str = "mean"):
        """Initialize percent change method.

        Args:
            threshold: Maximum allowed percent change (0.2 = 20%)
            baseline_type: How to calculate baseline ("mean", "median", "last")
        """
        self.threshold = threshold
        self.baseline_type = baseline_type
        self._baseline: float = 0.0
        self._fitted = False

    @property
    def name(self) -> str:
        return "percent_change"

    def fit(self, values: list[float]) -> None:
        """Fit to data by computing baseline."""
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return

        if self.baseline_type == "mean":
            self._baseline = sum(clean_values) / len(clean_values)
        elif self.baseline_type == "median":
            sorted_vals = sorted(clean_values)
            mid = len(sorted_vals) // 2
            if len(sorted_vals) % 2 == 0:
                self._baseline = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            else:
                self._baseline = sorted_vals[mid]
        elif self.baseline_type == "last":
            self._baseline = clean_values[-1]
        else:
            self._baseline = sum(clean_values) / len(clean_values)

        self._fitted = True

    def score(self, value: float) -> AnomalyScore:
        """Score a value based on percent change from baseline."""
        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.threshold,
                details={"reason": "null_or_nan"}
            )

        if self._baseline == 0:
            # Avoid division by zero
            pct_change = float('inf') if value != 0 else 0
        else:
            pct_change = abs(value - self._baseline) / abs(self._baseline)

        is_anomaly = pct_change > self.threshold

        return AnomalyScore(
            value=value,
            score=pct_change,
            is_anomaly=is_anomaly,
            threshold=self.threshold,
            details={
                "baseline": self._baseline,
                "baseline_type": self.baseline_type,
                "percent_change": pct_change,
                "change_direction": "increase" if value > self._baseline else "decrease",
            }
        )


class ModifiedZScoreMethod(AnomalyMethod):
    """Modified Z-Score using median and MAD.

    More robust than standard z-score for non-normal distributions.
    Uses Median Absolute Deviation instead of standard deviation.
    """

    def __init__(self, threshold: float = 3.5):
        """Initialize Modified Z-Score method.

        Args:
            threshold: Threshold for anomaly detection
        """
        self.threshold = threshold
        self._median: float = 0.0
        self._mad: float = 1.0
        self._fitted = False

    @property
    def name(self) -> str:
        return "modified_zscore"

    def fit(self, values: list[float]) -> None:
        """Fit to data by computing median and MAD."""
        clean_values = sorted(v for v in values if v is not None and not math.isnan(v))
        if not clean_values:
            return

        n = len(clean_values)

        # Calculate median
        mid = n // 2
        if n % 2 == 0:
            self._median = (clean_values[mid - 1] + clean_values[mid]) / 2
        else:
            self._median = clean_values[mid]

        # Calculate MAD (Median Absolute Deviation)
        deviations = sorted(abs(x - self._median) for x in clean_values)
        mid = len(deviations) // 2
        if len(deviations) % 2 == 0:
            self._mad = (deviations[mid - 1] + deviations[mid]) / 2
        else:
            self._mad = deviations[mid]

        # Avoid zero MAD
        if self._mad == 0:
            self._mad = 1.0

        self._fitted = True

    def score(self, value: float) -> AnomalyScore:
        """Score a value using modified z-score."""
        if value is None or math.isnan(value):
            return AnomalyScore(
                value=value,
                score=0.0,
                is_anomaly=False,
                threshold=self.threshold,
                details={"reason": "null_or_nan"}
            )

        # Modified z-score formula: 0.6745 * (x - median) / MAD
        modified_z = 0.6745 * abs(value - self._median) / self._mad

        is_anomaly = modified_z > self.threshold

        return AnomalyScore(
            value=value,
            score=modified_z,
            is_anomaly=is_anomaly,
            threshold=self.threshold,
            details={
                "median": self._median,
                "mad": self._mad,
                "modified_z_score": modified_z,
            }
        )


# Factory for creating methods
def create_method(
    method_name: str,
    **kwargs
) -> AnomalyMethod:
    """Create an anomaly detection method by name.

    Args:
        method_name: Name of the method. Options:
            - "zscore", "z_score": Z-Score method
            - "iqr": Interquartile Range method
            - "percent_change", "pct_change": Percent change method
            - "modified_zscore", "mad": Modified Z-Score (MAD) method
            - "baseline": ML-based baseline comparison
            - "ks_test": Kolmogorov-Smirnov distribution test
            - "seasonal": Seasonal pattern detection
        **kwargs: Method-specific parameters

    Returns:
        Configured AnomalyMethod
    """
    # Import ML methods lazily to avoid circular imports
    from duckguard.anomaly.ml_methods import BaselineMethod, KSTestMethod, SeasonalMethod

    methods = {
        "zscore": ZScoreMethod,
        "z_score": ZScoreMethod,
        "iqr": IQRMethod,
        "percent_change": PercentChangeMethod,
        "pct_change": PercentChangeMethod,
        "modified_zscore": ModifiedZScoreMethod,
        "mad": ModifiedZScoreMethod,
        "baseline": BaselineMethod,
        "ks_test": KSTestMethod,
        "ks": KSTestMethod,
        "seasonal": SeasonalMethod,
    }

    method_class = methods.get(method_name.lower())
    if not method_class:
        raise ValueError(f"Unknown anomaly method: {method_name}. Available: {list(methods.keys())}")

    return method_class(**kwargs)
