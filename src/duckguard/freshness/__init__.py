"""Freshness monitoring for DuckGuard.

This module provides functionality to check data freshness by monitoring
file modification times and timestamp columns.

Usage:
    from duckguard.freshness import FreshnessMonitor, FreshnessResult
    from datetime import timedelta

    # Check file freshness
    monitor = FreshnessMonitor(threshold=timedelta(hours=24))
    result = monitor.check("data.csv")

    if not result.is_fresh:
        print(f"Data is stale! Last updated: {result.age_human}")

    # Check column freshness
    from duckguard import connect
    data = connect("data.csv")
    result = monitor.check_column_timestamp(data, "updated_at")
"""

from duckguard.freshness.monitor import (
    FreshnessMethod,
    FreshnessMonitor,
    FreshnessResult,
)

__all__ = [
    "FreshnessMonitor",
    "FreshnessResult",
    "FreshnessMethod",
]
