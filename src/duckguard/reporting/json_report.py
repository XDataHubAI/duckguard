"""JSON reporter for DuckGuard."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from duckguard.core.result import ProfileResult, ScanResult


class JSONReporter:
    """Reporter that outputs to JSON format."""

    def __init__(self, pretty: bool = True):
        self.pretty = pretty

    def profile_to_dict(self, profile: ProfileResult) -> dict[str, Any]:
        """Convert profile result to dictionary."""
        return {
            "type": "profile",
            "source": profile.source,
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "timestamp": profile.timestamp.isoformat(),
            "columns": [
                {
                    "name": col.name,
                    "dtype": col.dtype,
                    "null_count": col.null_count,
                    "null_percent": col.null_percent,
                    "unique_count": col.unique_count,
                    "unique_percent": col.unique_percent,
                    "min_value": self._serialize_value(col.min_value),
                    "max_value": self._serialize_value(col.max_value),
                    "mean_value": col.mean_value,
                    "stddev_value": col.stddev_value,
                    "suggested_rules": col.suggested_rules,
                }
                for col in profile.columns
            ],
            "suggested_rules": profile.suggested_rules,
        }

    def scan_to_dict(self, scan: ScanResult) -> dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            "type": "scan",
            "source": scan.source,
            "row_count": scan.row_count,
            "checks_run": scan.checks_run,
            "checks_passed": scan.checks_passed,
            "checks_failed": scan.checks_failed,
            "checks_warned": scan.checks_warned,
            "pass_rate": scan.pass_rate,
            "passed": scan.passed,
            "timestamp": scan.timestamp.isoformat(),
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "actual_value": self._serialize_value(r.actual_value),
                    "expected_value": self._serialize_value(r.expected_value),
                    "message": r.message,
                    "column": r.column,
                }
                for r in scan.results
            ],
        }

    def to_json(self, data: dict[str, Any]) -> str:
        """Convert dictionary to JSON string."""
        if self.pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def save_profile(self, profile: ProfileResult, path: str | Path) -> None:
        """Save profile result to JSON file."""
        data = self.profile_to_dict(profile)
        Path(path).write_text(self.to_json(data))

    def save_scan(self, scan: ScanResult, path: str | Path) -> None:
        """Save scan result to JSON file."""
        data = self.scan_to_dict(scan)
        Path(path).write_text(self.to_json(data))

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value to JSON-compatible type."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)
