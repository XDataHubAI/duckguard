"""Historical result storage and trend analysis for DuckGuard.

This module provides persistent storage for validation results,
enabling trend analysis and historical comparison.

Usage:
    from duckguard.history import HistoryStorage, TrendAnalyzer

    # Store validation results
    storage = HistoryStorage()
    storage.store(result)

    # Query history
    runs = storage.get_runs("data.csv", limit=10)

    # Analyze trends
    analyzer = TrendAnalyzer(storage)
    analysis = analyzer.analyze("data.csv", days=30)
    print(analysis.summary())
"""

from duckguard.history.storage import (
    HistoryStorage,
    StoredCheckResult,
    StoredRun,
    TrendDataPoint,
)
from duckguard.history.trends import (
    TrendAnalysis,
    TrendAnalyzer,
    analyze_trends,
)

__all__ = [
    # Storage
    "HistoryStorage",
    "StoredRun",
    "StoredCheckResult",
    "TrendDataPoint",
    # Trends
    "TrendAnalyzer",
    "TrendAnalysis",
    "analyze_trends",
]
