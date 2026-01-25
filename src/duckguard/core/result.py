"""Result types for validation operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CheckStatus(Enum):
    """Status of a validation check."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class FailedRow:
    """Represents a single row that failed validation.

    Attributes:
        row_index: The 1-based row number in the source data
        column: The column name that failed validation
        value: The actual value that failed
        expected: What was expected (e.g., "not null", "between 1-100")
        reason: Human-readable explanation of why validation failed
        context: Additional row data for context (optional)
    """

    row_index: int
    column: str
    value: Any
    expected: str
    reason: str = ""
    context: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"FailedRow(row={self.row_index}, column='{self.column}', value={self.value!r})"


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    status: CheckStatus
    actual_value: Any
    expected_value: Any | None = None
    message: str = ""
    column: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if the validation passed."""
        return self.status == CheckStatus.PASSED

    @property
    def failed(self) -> bool:
        """Check if the validation failed."""
        return self.status == CheckStatus.FAILED

    def __bool__(self) -> bool:
        """Allow using CheckResult in boolean context."""
        return self.passed


@dataclass
class ValidationResult:
    """Result of a validation operation that can be used in assertions.

    Enhanced with row-level error capture for debugging failed checks.

    Attributes:
        passed: Whether the validation passed
        actual_value: The actual value found (e.g., count of failures)
        expected_value: What was expected
        message: Human-readable summary
        details: Additional metadata
        failed_rows: List of individual rows that failed validation
        sample_size: How many failed rows to capture (default: 10)
    """

    passed: bool
    actual_value: Any
    expected_value: Any | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    failed_rows: list[FailedRow] = field(default_factory=list)
    total_failures: int = 0

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context for assertions."""
        return self.passed

    def __repr__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        if self.failed_rows:
            return f"ValidationResult({status}, actual={self.actual_value}, failed_rows={len(self.failed_rows)})"
        return f"ValidationResult({status}, actual={self.actual_value})"

    def get_failed_values(self) -> list[Any]:
        """Get list of values that failed validation."""
        return [row.value for row in self.failed_rows]

    def get_failed_row_indices(self) -> list[int]:
        """Get list of row indices that failed validation."""
        return [row.row_index for row in self.failed_rows]

    def to_dataframe(self):
        """Convert failed rows to a pandas DataFrame (if pandas available).

        Returns:
            pandas.DataFrame with failed row details

        Raises:
            ImportError: If pandas is not installed
        """
        try:
            import pandas as pd

            if not self.failed_rows:
                return pd.DataFrame(columns=["row_index", "column", "value", "expected", "reason"])

            return pd.DataFrame([
                {
                    "row_index": row.row_index,
                    "column": row.column,
                    "value": row.value,
                    "expected": row.expected,
                    "reason": row.reason,
                    **row.context,
                }
                for row in self.failed_rows
            ])
        except ImportError:
            raise ImportError("pandas is required for to_dataframe(). Install with: pip install pandas")

    def summary(self) -> str:
        """Get a summary of the validation result with sample failures."""
        lines = [self.message]

        if self.failed_rows:
            lines.append(f"\nSample of {len(self.failed_rows)} failing rows (total: {self.total_failures}):")
            for row in self.failed_rows[:5]:
                lines.append(f"  Row {row.row_index}: {row.column}={row.value!r} - {row.reason or row.expected}")

            if self.total_failures > 5:
                lines.append(f"  ... and {self.total_failures - 5} more failures")

        return "\n".join(lines)


@dataclass
class ProfileResult:
    """Result of profiling a dataset."""

    source: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    suggested_rules: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ColumnProfile:
    """Profile information for a single column."""

    name: str
    dtype: str
    null_count: int
    null_percent: float
    unique_count: int
    unique_percent: float
    min_value: Any | None = None
    max_value: Any | None = None
    mean_value: float | None = None
    stddev_value: float | None = None
    sample_values: list[Any] = field(default_factory=list)
    suggested_rules: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of scanning a dataset for issues."""

    source: str
    row_count: int
    checks_run: int
    checks_passed: int
    checks_failed: int
    checks_warned: int
    results: list[CheckResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if all validations passed."""
        return self.checks_failed == 0

    @property
    def pass_rate(self) -> float:
        """Calculate the pass rate as a percentage."""
        if self.checks_run == 0:
            return 100.0
        return (self.checks_passed / self.checks_run) * 100
