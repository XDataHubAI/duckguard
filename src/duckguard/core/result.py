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

    @property
    def row_number(self) -> int:
        """Alias for row_index (backward compatibility)."""
        return self.row_index

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

            return pd.DataFrame(
                [
                    {
                        "row_index": row.row_index,
                        "column": row.column,
                        "value": row.value,
                        "expected": row.expected,
                        "reason": row.reason,
                        **row.context,
                    }
                    for row in self.failed_rows
                ]
            )
        except ImportError:
            raise ImportError(
                "pandas is required for to_dataframe(). Install with: pip install pandas"
            )

    def summary(self) -> str:
        """Get a summary of the validation result with sample failures."""
        lines = [self.message]

        if self.failed_rows:
            lines.append(
                f"\nSample of {len(self.failed_rows)} failing rows (total: {self.total_failures}):"
            )
            for row in self.failed_rows[:5]:
                lines.append(
                    f"  Row {row.row_index}: {row.column}={row.value!r} - {row.reason or row.expected}"
                )

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
    overall_quality_score: float | None = None
    overall_quality_grade: str | None = None


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
    median_value: float | None = None
    p25_value: float | None = None
    p75_value: float | None = None
    sample_values: list[Any] = field(default_factory=list)
    suggested_rules: list[str] = field(default_factory=list)
    quality_score: float | None = None
    quality_grade: str | None = None
    distribution_type: str | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    is_normal: bool | None = None
    outlier_count: int | None = None
    outlier_percentage: float | None = None


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


# =========================================================================
# Distribution Drift Results
# =========================================================================


@dataclass
class DriftResult:
    """Result of distribution drift detection between two columns.

    Attributes:
        is_drifted: Whether significant drift was detected
        p_value: Statistical p-value from the test
        statistic: Test statistic value
        threshold: P-value threshold used for detection
        method: Statistical method used (e.g., "ks_test")
        message: Human-readable summary
        details: Additional metadata
    """

    is_drifted: bool
    p_value: float
    statistic: float
    threshold: float = 0.05
    method: str = "ks_test"
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Returns True if NO drift detected (data is stable)."""
        return not self.is_drifted

    def __repr__(self) -> str:
        status = "DRIFT DETECTED" if self.is_drifted else "STABLE"
        return f"DriftResult({status}, p_value={self.p_value:.4f}, threshold={self.threshold})"

    def summary(self) -> str:
        """Get a human-readable summary."""
        status = "DRIFT DETECTED" if self.is_drifted else "No significant drift"
        return f"{status} (p-value: {self.p_value:.4f}, threshold: {self.threshold}, method: {self.method})"


# =========================================================================
# Reconciliation Results
# =========================================================================


@dataclass
class ReconciliationMismatch:
    """Represents a single row mismatch in reconciliation.

    Attributes:
        key_values: Dictionary of key column values that identify the row
        column: Column name where mismatch occurred
        source_value: Value in source dataset
        target_value: Value in target dataset
        mismatch_type: Type of mismatch ("value_diff", "missing_in_target", "extra_in_target")
    """

    key_values: dict[str, Any]
    column: str
    source_value: Any = None
    target_value: Any = None
    mismatch_type: str = "value_diff"

    def __repr__(self) -> str:
        keys = ", ".join(f"{k}={v}" for k, v in self.key_values.items())
        return f"ReconciliationMismatch({keys}, {self.column}: {self.source_value} vs {self.target_value})"


@dataclass
class ReconciliationResult:
    """Result of reconciling two datasets.

    Attributes:
        passed: Whether reconciliation passed (datasets match)
        source_row_count: Number of rows in source dataset
        target_row_count: Number of rows in target dataset
        missing_in_target: Rows in source but not in target
        extra_in_target: Rows in target but not in source
        value_mismatches: Count of value mismatches by column
        match_percentage: Percentage of rows that match
        key_columns: Columns used as keys for matching
        compared_columns: Columns compared for values
        mismatches: Sample of actual mismatches
        details: Additional metadata
    """

    passed: bool
    source_row_count: int
    target_row_count: int
    missing_in_target: int = 0
    extra_in_target: int = 0
    value_mismatches: dict[str, int] = field(default_factory=dict)
    match_percentage: float = 100.0
    key_columns: list[str] = field(default_factory=list)
    compared_columns: list[str] = field(default_factory=list)
    mismatches: list[ReconciliationMismatch] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow using ReconciliationResult in boolean context."""
        return self.passed

    def __repr__(self) -> str:
        status = "MATCHED" if self.passed else "MISMATCHED"
        return f"ReconciliationResult({status}, match={self.match_percentage:.1f}%, missing={self.missing_in_target}, extra={self.extra_in_target})"

    @property
    def total_mismatches(self) -> int:
        """Total number of mismatches across all columns."""
        return self.missing_in_target + self.extra_in_target + sum(self.value_mismatches.values())

    def summary(self) -> str:
        """Get a human-readable summary."""
        lines = [
            f"Reconciliation: {'PASSED' if self.passed else 'FAILED'} ({self.match_percentage:.1f}% match)",
            f"Source rows: {self.source_row_count}, Target rows: {self.target_row_count}",
        ]

        if self.missing_in_target > 0:
            lines.append(f"Missing in target: {self.missing_in_target} rows")
        if self.extra_in_target > 0:
            lines.append(f"Extra in target: {self.extra_in_target} rows")
        if self.value_mismatches:
            lines.append("Column mismatches:")
            for col, count in self.value_mismatches.items():
                lines.append(f"  {col}: {count} differences")

        if self.mismatches:
            lines.append(f"\nSample mismatches ({len(self.mismatches)} shown):")
            for m in self.mismatches[:5]:
                keys = ", ".join(f"{k}={v}" for k, v in m.key_values.items())
                lines.append(f"  [{keys}] {m.column}: {m.source_value!r} vs {m.target_value!r}")

        return "\n".join(lines)


# =========================================================================
# Group By Results
# =========================================================================


@dataclass
class GroupResult:
    """Validation result for a single group.

    Attributes:
        group_key: Dictionary of group column values
        row_count: Number of rows in this group
        passed: Whether all checks passed for this group
        check_results: List of individual check results
        stats: Group-level statistics
    """

    group_key: dict[str, Any]
    row_count: int
    passed: bool = True
    check_results: list[ValidationResult] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow using GroupResult in boolean context."""
        return self.passed

    def __repr__(self) -> str:
        keys = ", ".join(f"{k}={v}" for k, v in self.group_key.items())
        status = "PASSED" if self.passed else "FAILED"
        return f"GroupResult({keys}, rows={self.row_count}, {status})"

    @property
    def key_string(self) -> str:
        """Get a string representation of the group key."""
        return ", ".join(f"{k}={v}" for k, v in self.group_key.items())


@dataclass
class GroupByResult:
    """Result of group-by validation across all groups.

    Attributes:
        passed: Whether all groups passed validation
        total_groups: Total number of groups
        passed_groups: Number of groups that passed
        failed_groups: Number of groups that failed
        group_results: Individual results per group
        group_columns: Columns used for grouping
        details: Additional metadata
    """

    passed: bool
    total_groups: int
    passed_groups: int = 0
    failed_groups: int = 0
    group_results: list[GroupResult] = field(default_factory=list)
    group_columns: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow using GroupByResult in boolean context."""
        return self.passed

    def __repr__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return f"GroupByResult({status}, groups={self.total_groups}, passed={self.passed_groups}, failed={self.failed_groups})"

    @property
    def pass_rate(self) -> float:
        """Calculate the pass rate as a percentage."""
        if self.total_groups == 0:
            return 100.0
        return (self.passed_groups / self.total_groups) * 100

    def get_failed_groups(self) -> list[GroupResult]:
        """Get list of groups that failed validation."""
        return [g for g in self.group_results if not g.passed]

    def summary(self) -> str:
        """Get a human-readable summary."""
        lines = [
            f"Group By Validation: {'PASSED' if self.passed else 'FAILED'}",
            f"Groups: {self.total_groups} total, {self.passed_groups} passed, {self.failed_groups} failed ({self.pass_rate:.1f}%)",
            f"Grouped by: {', '.join(self.group_columns)}",
        ]

        failed = self.get_failed_groups()
        if failed:
            lines.append(f"\nFailed groups ({len(failed)}):")
            for g in failed[:5]:
                lines.append(f"  [{g.key_string}]: {g.row_count} rows")
                for cr in g.check_results:
                    if not cr.passed:
                        lines.append(f"    - {cr.message}")

        return "\n".join(lines)
