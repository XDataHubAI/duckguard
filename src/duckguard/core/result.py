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
    """Result of a validation operation that can be used in assertions."""

    passed: bool
    actual_value: Any
    expected_value: Any | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context for assertions."""
        return self.passed

    def __repr__(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return f"ValidationResult({status}, actual={self.actual_value})"


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
