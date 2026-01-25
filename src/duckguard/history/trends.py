"""Trend analysis for historical validation data.

Provides analysis of quality score trends over time,
helping identify patterns and regressions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from duckguard.history.storage import HistoryStorage, TrendDataPoint


@dataclass
class TrendAnalysis:
    """Result of trend analysis for a data source.

    Attributes:
        source: The data source being analyzed
        period_days: Number of days analyzed
        current_score: Most recent quality score
        average_score: Average score over the period
        min_score: Minimum score in the period
        max_score: Maximum score in the period
        score_trend: Trend direction ("improving", "declining", "stable")
        trend_change: Percentage change in score
        total_runs: Total number of validation runs
        pass_rate: Percentage of runs that passed
        daily_data: Daily trend data points
        anomalies: List of dates with anomalous scores
    """

    source: str
    period_days: int
    current_score: float
    average_score: float
    min_score: float
    max_score: float
    score_trend: str
    trend_change: float
    total_runs: int
    pass_rate: float
    daily_data: list[TrendDataPoint] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)

    @property
    def is_improving(self) -> bool:
        """Check if trend is improving."""
        return self.score_trend == "improving"

    @property
    def is_declining(self) -> bool:
        """Check if trend is declining."""
        return self.score_trend == "declining"

    @property
    def has_anomalies(self) -> bool:
        """Check if there are any anomalies."""
        return len(self.anomalies) > 0

    def summary(self) -> str:
        """Get a human-readable summary of the trend."""
        trend_symbol = {"improving": "[+]", "declining": "[-]", "stable": "[=]"}.get(
            self.score_trend, "[=]"
        )

        return (
            f"{trend_symbol} Quality trend is {self.score_trend} "
            f"({self.trend_change:+.1f}% over {self.period_days} days). "
            f"Current score: {self.current_score:.1f}%, "
            f"Average: {self.average_score:.1f}%, "
            f"Pass rate: {self.pass_rate:.1f}%"
        )


class TrendAnalyzer:
    """Analyzes quality score trends over time.

    Usage:
        from duckguard.history import HistoryStorage, TrendAnalyzer

        storage = HistoryStorage()
        analyzer = TrendAnalyzer(storage)

        # Analyze trends for a source
        analysis = analyzer.analyze("data.csv", days=30)
        print(analysis.summary())

        # Check for regressions
        if analyzer.has_regression("data.csv"):
            print("Quality regression detected!")
    """

    # Threshold for considering a score change significant
    SIGNIFICANT_CHANGE_THRESHOLD = 5.0  # 5%

    # Standard deviations for anomaly detection
    ANOMALY_THRESHOLD = 2.0

    def __init__(self, storage: HistoryStorage):
        """Initialize analyzer.

        Args:
            storage: HistoryStorage instance
        """
        self.storage = storage

    def analyze(self, source: str, days: int = 30) -> TrendAnalysis:
        """Analyze trends for a data source.

        Args:
            source: Data source path
            days: Number of days to analyze

        Returns:
            TrendAnalysis with detailed trend information
        """
        daily_data = self.storage.get_trend(source, days=days)

        # Handle case with no data
        if not daily_data:
            latest = self.storage.get_latest_run(source)
            return TrendAnalysis(
                source=source,
                period_days=days,
                current_score=latest.quality_score if latest else 0.0,
                average_score=latest.quality_score if latest else 0.0,
                min_score=latest.quality_score if latest else 0.0,
                max_score=latest.quality_score if latest else 0.0,
                score_trend="stable",
                trend_change=0.0,
                total_runs=1 if latest else 0,
                pass_rate=100.0 if latest and latest.passed else 0.0,
                daily_data=[],
                anomalies=[],
            )

        # Calculate statistics
        scores = [d.avg_score for d in daily_data]
        total_runs = sum(d.run_count for d in daily_data)
        total_passed = sum(d.passed_count for d in daily_data)

        current_score = scores[-1] if scores else 0.0
        average_score = sum(scores) / len(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        pass_rate = (total_passed / total_runs * 100) if total_runs > 0 else 0.0

        # Determine trend direction
        trend, trend_change = self._calculate_trend(scores)

        # Detect anomalies
        anomalies = self._detect_anomalies(daily_data, average_score, scores)

        return TrendAnalysis(
            source=source,
            period_days=days,
            current_score=current_score,
            average_score=average_score,
            min_score=min_score,
            max_score=max_score,
            score_trend=trend,
            trend_change=trend_change,
            total_runs=total_runs,
            pass_rate=pass_rate,
            daily_data=daily_data,
            anomalies=anomalies,
        )

    def has_regression(
        self,
        source: str,
        threshold: float | None = None,
        days: int = 7,
    ) -> bool:
        """Check if there's been a quality regression.

        A regression is defined as a significant decline in quality score
        compared to the previous period.

        Args:
            source: Data source path
            threshold: Score drop threshold (default: SIGNIFICANT_CHANGE_THRESHOLD)
            days: Number of days to compare

        Returns:
            True if a regression is detected
        """
        if threshold is None:
            threshold = self.SIGNIFICANT_CHANGE_THRESHOLD

        analysis = self.analyze(source, days=days * 2)

        if len(analysis.daily_data) < 2:
            return False

        # Compare recent scores to earlier scores
        midpoint = len(analysis.daily_data) // 2
        earlier_scores = [d.avg_score for d in analysis.daily_data[:midpoint]]
        recent_scores = [d.avg_score for d in analysis.daily_data[midpoint:]]

        if not earlier_scores or not recent_scores:
            return False

        earlier_avg = sum(earlier_scores) / len(earlier_scores)
        recent_avg = sum(recent_scores) / len(recent_scores)

        return (earlier_avg - recent_avg) >= threshold

    def compare_periods(
        self,
        source: str,
        period1_days: int = 7,
        period2_days: int = 7,
    ) -> dict[str, Any]:
        """Compare quality metrics between two periods.

        Args:
            source: Data source path
            period1_days: Days in recent period
            period2_days: Days in comparison period

        Returns:
            Dictionary with comparison metrics
        """
        total_days = period1_days + period2_days
        daily_data = self.storage.get_trend(source, days=total_days)

        if not daily_data:
            return {
                "recent_avg": 0.0,
                "previous_avg": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "improved": False,
            }

        # Split into periods
        if len(daily_data) <= period1_days:
            recent_data = daily_data
            previous_data = []
        else:
            recent_data = daily_data[-period1_days:]
            previous_data = daily_data[:-period1_days]

        recent_avg = (
            sum(d.avg_score for d in recent_data) / len(recent_data)
            if recent_data
            else 0.0
        )
        previous_avg = (
            sum(d.avg_score for d in previous_data) / len(previous_data)
            if previous_data
            else recent_avg
        )

        change = recent_avg - previous_avg
        change_percent = (change / previous_avg * 100) if previous_avg > 0 else 0.0

        return {
            "recent_avg": recent_avg,
            "previous_avg": previous_avg,
            "change": change,
            "change_percent": change_percent,
            "improved": change > 0,
        }

    def _calculate_trend(self, scores: list[float]) -> tuple[str, float]:
        """Calculate trend direction and magnitude.

        Args:
            scores: List of scores ordered by date

        Returns:
            Tuple of (trend_direction, change_percentage)
        """
        if len(scores) < 2:
            return "stable", 0.0

        # Use first and last week averages for comparison
        window = min(7, len(scores) // 2) or 1

        first_avg = sum(scores[:window]) / window
        last_avg = sum(scores[-window:]) / window

        change = last_avg - first_avg

        if change >= self.SIGNIFICANT_CHANGE_THRESHOLD:
            return "improving", change
        elif change <= -self.SIGNIFICANT_CHANGE_THRESHOLD:
            return "declining", change
        else:
            return "stable", change

    def _detect_anomalies(
        self,
        daily_data: list[TrendDataPoint],
        mean: float,
        scores: list[float],
    ) -> list[str]:
        """Detect anomalous days based on score deviation.

        Args:
            daily_data: List of daily trend data
            mean: Mean score
            scores: List of scores

        Returns:
            List of dates with anomalous scores
        """
        if len(scores) < 3:
            return []

        # Calculate standard deviation
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        stddev = variance**0.5

        if stddev == 0:
            return []

        anomalies = []
        for data in daily_data:
            z_score = abs(data.avg_score - mean) / stddev
            if z_score > self.ANOMALY_THRESHOLD:
                anomalies.append(data.date)

        return anomalies


def analyze_trends(
    source: str,
    days: int = 30,
    db_path: str | None = None,
) -> TrendAnalysis:
    """Convenience function for trend analysis.

    Args:
        source: Data source path
        days: Number of days to analyze
        db_path: Path to history database

    Returns:
        TrendAnalysis result
    """
    storage = HistoryStorage(db_path=db_path)
    analyzer = TrendAnalyzer(storage)
    return analyzer.analyze(source, days=days)
