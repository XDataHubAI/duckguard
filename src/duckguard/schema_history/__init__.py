"""Schema evolution tracking for DuckGuard.

This module provides functionality to track schema changes over time,
enabling detection of breaking changes and schema drift.

Usage:
    from duckguard.schema_history import SchemaTracker, SchemaChangeAnalyzer

    # Track schema
    tracker = SchemaTracker()
    snapshot = tracker.capture(dataset)

    # Detect changes
    analyzer = SchemaChangeAnalyzer()
    report = analyzer.detect_changes(dataset)
    if report.has_breaking_changes:
        print("Breaking changes detected!")
"""

from duckguard.schema_history.analyzer import (
    SchemaChange,
    SchemaChangeAnalyzer,
    SchemaEvolutionReport,
)
from duckguard.schema_history.tracker import (
    ColumnSchema,
    SchemaSnapshot,
    SchemaTracker,
)

__all__ = [
    # Tracker
    "SchemaTracker",
    "SchemaSnapshot",
    "ColumnSchema",
    # Analyzer
    "SchemaChangeAnalyzer",
    "SchemaChange",
    "SchemaEvolutionReport",
]
