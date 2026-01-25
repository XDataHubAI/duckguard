"""Rule executor for DuckGuard.

Executes validation rules against datasets and collects results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from duckguard.connectors import connect
from duckguard.core.dataset import Dataset
from duckguard.rules.schema import (
    BUILTIN_PATTERNS,
    Check,
    CheckType,
    RuleSet,
    Severity,
)


@dataclass
class CheckResult:
    """Result of a single check execution.

    Attributes:
        check: The check that was executed
        column: Column name (None for table-level checks)
        passed: Whether the check passed
        actual_value: The actual value found
        expected_value: The expected value or threshold
        message: Human-readable result message
        severity: Severity level of the check
        details: Additional details about the check
    """

    check: Check
    column: str | None
    passed: bool
    actual_value: Any
    expected_value: Any
    message: str
    severity: Severity = Severity.ERROR
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        """Get status string."""
        if self.passed:
            return "PASSED"
        if self.severity == Severity.WARNING:
            return "WARNING"
        if self.severity == Severity.INFO:
            return "INFO"
        return "FAILED"

    @property
    def is_failure(self) -> bool:
        """Check if this is a hard failure."""
        return not self.passed and self.severity == Severity.ERROR


@dataclass
class ExecutionResult:
    """Result of executing a complete rule set.

    Attributes:
        ruleset: The rule set that was executed
        source: The data source that was validated
        results: Individual check results
        started_at: When execution started
        finished_at: When execution finished
    """

    ruleset: RuleSet
    source: str
    results: list[CheckResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None

    @property
    def passed(self) -> bool:
        """Check if all error-level checks passed."""
        return not any(r.is_failure for r in self.results)

    @property
    def total_checks(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.is_failure)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if not r.passed and r.severity == Severity.WARNING)

    @property
    def quality_score(self) -> float:
        """Calculate quality score (0-100)."""
        if not self.results:
            return 100.0
        return (self.passed_count / self.total_checks) * 100

    def get_failures(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [r for r in self.results if r.is_failure]

    def get_warnings(self) -> list[CheckResult]:
        """Get all warning checks."""
        return [r for r in self.results if not r.passed and r.severity == Severity.WARNING]


class RuleExecutor:
    """Executes validation rules against datasets."""

    def __init__(self, dataset: Dataset | None = None):
        """Initialize the executor.

        Args:
            dataset: Optional pre-loaded dataset
        """
        self._dataset = dataset

    def execute(
        self,
        ruleset: RuleSet,
        source: str | None = None,
        dataset: Dataset | None = None
    ) -> ExecutionResult:
        """Execute a rule set against a data source.

        Args:
            ruleset: The rules to execute
            source: Data source path (overrides ruleset.source)
            dataset: Pre-loaded dataset (overrides source)

        Returns:
            ExecutionResult with all check results
        """
        # Determine data source
        if dataset is not None:
            ds = dataset
            source_str = dataset.source
        elif source is not None:
            ds = connect(source)
            source_str = source
        elif ruleset.source is not None:
            ds = connect(ruleset.source)
            source_str = ruleset.source
        elif self._dataset is not None:
            ds = self._dataset
            source_str = ds.source
        else:
            raise ValueError("No data source specified")

        result = ExecutionResult(
            ruleset=ruleset,
            source=source_str,
        )

        # Execute table-level checks
        for check in ruleset.table.checks:
            if check.enabled:
                check_result = self._execute_table_check(ds, check)
                result.results.append(check_result)

        # Execute column-level checks
        for col_name, col_rules in ruleset.columns.items():
            if col_name not in ds.columns:
                # Column doesn't exist - add error
                result.results.append(CheckResult(
                    check=Check(type=CheckType.NOT_NULL),
                    column=col_name,
                    passed=False,
                    actual_value=None,
                    expected_value="column exists",
                    message=f"Column '{col_name}' not found in dataset",
                    severity=Severity.ERROR,
                ))
                continue

            for check in col_rules.checks:
                if check.enabled:
                    check_result = self._execute_column_check(ds, col_name, check)
                    result.results.append(check_result)

        result.finished_at = datetime.now()
        return result

    def _execute_table_check(self, dataset: Dataset, check: Check) -> CheckResult:
        """Execute a table-level check."""
        try:
            if check.type == CheckType.ROW_COUNT:
                return self._check_row_count(dataset, check)
            else:
                return CheckResult(
                    check=check,
                    column=None,
                    passed=False,
                    actual_value=None,
                    expected_value=None,
                    message=f"Unsupported table check type: {check.type.value}",
                    severity=Severity.ERROR,
                )
        except Exception as e:
            return CheckResult(
                check=check,
                column=None,
                passed=False,
                actual_value=None,
                expected_value=None,
                message=f"Error executing check: {e}",
                severity=Severity.ERROR,
            )

    def _execute_column_check(
        self,
        dataset: Dataset,
        col_name: str,
        check: Check
    ) -> CheckResult:
        """Execute a column-level check."""
        try:
            col = dataset[col_name]

            check_handlers = {
                CheckType.NOT_NULL: self._check_not_null,
                CheckType.NULL_PERCENT: self._check_null_percent,
                CheckType.UNIQUE: self._check_unique,
                CheckType.UNIQUE_PERCENT: self._check_unique_percent,
                CheckType.NO_DUPLICATES: self._check_no_duplicates,
                CheckType.BETWEEN: self._check_between,
                CheckType.RANGE: self._check_between,
                CheckType.MIN: self._check_min,
                CheckType.MAX: self._check_max,
                CheckType.POSITIVE: self._check_positive,
                CheckType.NEGATIVE: self._check_negative,
                CheckType.NON_NEGATIVE: self._check_non_negative,
                CheckType.PATTERN: self._check_pattern,
                CheckType.LENGTH: self._check_length,
                CheckType.MIN_LENGTH: self._check_min_length,
                CheckType.MAX_LENGTH: self._check_max_length,
                CheckType.ALLOWED_VALUES: self._check_allowed_values,
                CheckType.ISIN: self._check_allowed_values,
            }

            handler = check_handlers.get(check.type)
            if handler:
                return handler(col, check)
            else:
                return CheckResult(
                    check=check,
                    column=col_name,
                    passed=False,
                    actual_value=None,
                    expected_value=None,
                    message=f"Unsupported check type: {check.type.value}",
                    severity=Severity.ERROR,
                )

        except Exception as e:
            return CheckResult(
                check=check,
                column=col_name,
                passed=False,
                actual_value=None,
                expected_value=None,
                message=f"Error executing check: {e}",
                severity=Severity.ERROR,
            )

    def _check_row_count(self, dataset: Dataset, check: Check) -> CheckResult:
        """Check row count against threshold."""
        actual = dataset.row_count
        expected = check.value
        passed = self._compare(actual, expected, check.operator)

        return CheckResult(
            check=check,
            column=None,
            passed=passed,
            actual_value=actual,
            expected_value=f"{check.operator} {expected}",
            message=f"Row count is {actual:,} (expected {check.operator} {expected})",
            severity=check.severity,
        )

    def _check_not_null(self, col, check: Check) -> CheckResult:
        """Check that column has no nulls."""
        null_count = col.null_count
        passed = null_count == 0

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=null_count,
            expected_value=0,
            message=f"Column '{col.name}' has {null_count} null values" if not passed
                    else f"Column '{col.name}' has no null values",
            severity=check.severity,
            details={"null_percent": col.null_percent},
        )

    def _check_null_percent(self, col, check: Check) -> CheckResult:
        """Check null percentage against threshold."""
        actual = col.null_percent
        expected = check.value
        passed = self._compare(actual, expected, check.operator)

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=actual,
            expected_value=f"{check.operator} {expected}%",
            message=f"Column '{col.name}' null_percent is {actual:.2f}% (expected {check.operator} {expected}%)",
            severity=check.severity,
        )

    def _check_unique(self, col, check: Check) -> CheckResult:
        """Check that column values are unique."""
        unique_pct = col.unique_percent
        passed = unique_pct == 100

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=unique_pct,
            expected_value=100,
            message=f"Column '{col.name}' is {unique_pct:.2f}% unique" if not passed
                    else f"Column '{col.name}' is 100% unique",
            severity=check.severity,
            details={
                "unique_count": col.unique_count,
                "total_count": col.total_count,
                "duplicate_count": col.total_count - col.unique_count,
            },
        )

    def _check_unique_percent(self, col, check: Check) -> CheckResult:
        """Check unique percentage against threshold."""
        actual = col.unique_percent
        expected = check.value
        passed = self._compare(actual, expected, check.operator)

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=actual,
            expected_value=f"{check.operator} {expected}%",
            message=f"Column '{col.name}' unique_percent is {actual:.2f}% (expected {check.operator} {expected}%)",
            severity=check.severity,
        )

    def _check_no_duplicates(self, col, check: Check) -> CheckResult:
        """Check that column has no duplicate values."""
        result = col.has_no_duplicates()

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=0,
            message=result.message,
            severity=check.severity,
        )

    def _check_between(self, col, check: Check) -> CheckResult:
        """Check that values are within a range."""
        if not isinstance(check.value, (list, tuple)) or len(check.value) != 2:
            return CheckResult(
                check=check,
                column=col.name,
                passed=False,
                actual_value=None,
                expected_value=check.value,
                message=f"Range check requires [min, max], got: {check.value}",
                severity=Severity.ERROR,
            )

        min_val, max_val = check.value
        result = col.between(min_val, max_val)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"[{min_val}, {max_val}]",
            message=result.message,
            severity=check.severity,
            details=result.details or {},
        )

    def _check_min(self, col, check: Check) -> CheckResult:
        """Check that all values are >= min."""
        actual_min = col.min
        expected_min = check.value
        passed = actual_min is not None and actual_min >= expected_min

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=actual_min,
            expected_value=f">= {expected_min}",
            message=f"Column '{col.name}' min is {actual_min} (expected >= {expected_min})",
            severity=check.severity,
        )

    def _check_max(self, col, check: Check) -> CheckResult:
        """Check that all values are <= max."""
        actual_max = col.max
        expected_max = check.value
        passed = actual_max is not None and actual_max <= expected_max

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=actual_max,
            expected_value=f"<= {expected_max}",
            message=f"Column '{col.name}' max is {actual_max} (expected <= {expected_max})",
            severity=check.severity,
        )

    def _check_positive(self, col, check: Check) -> CheckResult:
        """Check that all values are positive (> 0)."""
        result = col.greater_than(0)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value="> 0",
            message=result.message if not result.passed
                    else f"Column '{col.name}' has all positive values",
            severity=check.severity,
        )

    def _check_negative(self, col, check: Check) -> CheckResult:
        """Check that all values are negative (< 0)."""
        result = col.less_than(0)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value="< 0",
            message=result.message if not result.passed
                    else f"Column '{col.name}' has all negative values",
            severity=check.severity,
        )

    def _check_non_negative(self, col, check: Check) -> CheckResult:
        """Check that all values are non-negative (>= 0)."""
        actual_min = col.min
        passed = actual_min is not None and actual_min >= 0

        return CheckResult(
            check=check,
            column=col.name,
            passed=passed,
            actual_value=actual_min,
            expected_value=">= 0",
            message=f"Column '{col.name}' min is {actual_min} (expected >= 0)",
            severity=check.severity,
        )

    def _check_pattern(self, col, check: Check) -> CheckResult:
        """Check that values match a regex pattern."""
        pattern = check.value

        # Handle built-in pattern names
        pattern_name = check.params.get("pattern_name")
        if pattern_name:
            pattern = BUILTIN_PATTERNS.get(pattern_name, pattern)

        result = col.matches(pattern)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"matches '{pattern_name or pattern}'",
            message=result.message,
            severity=check.severity,
            details=result.details or {},
        )

    def _check_length(self, col, check: Check) -> CheckResult:
        """Check that string lengths are within range."""
        if not isinstance(check.value, (list, tuple)) or len(check.value) != 2:
            return CheckResult(
                check=check,
                column=col.name,
                passed=False,
                actual_value=None,
                expected_value=check.value,
                message=f"Length check requires [min, max], got: {check.value}",
                severity=Severity.ERROR,
            )

        min_len, max_len = check.value
        result = col.value_lengths_between(min_len, max_len)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"length in [{min_len}, {max_len}]",
            message=result.message,
            severity=check.severity,
        )

    def _check_min_length(self, col, check: Check) -> CheckResult:
        """Check that string lengths are >= min."""
        min_len = check.value
        result = col.value_lengths_between(min_len, 1000000)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"length >= {min_len}",
            message=result.message,
            severity=check.severity,
        )

    def _check_max_length(self, col, check: Check) -> CheckResult:
        """Check that string lengths are <= max."""
        max_len = check.value
        result = col.value_lengths_between(0, max_len)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"length <= {max_len}",
            message=result.message,
            severity=check.severity,
        )

    def _check_allowed_values(self, col, check: Check) -> CheckResult:
        """Check that values are in allowed set."""
        allowed = check.value
        if not isinstance(allowed, list):
            allowed = [allowed]

        result = col.isin(allowed)

        return CheckResult(
            check=check,
            column=col.name,
            passed=result.passed,
            actual_value=result.actual_value,
            expected_value=f"in {allowed}",
            message=result.message,
            severity=check.severity,
            details=result.details or {},
        )

    def _compare(self, actual: Any, expected: Any, operator: str) -> bool:
        """Compare actual value to expected using operator."""
        if actual is None or expected is None:
            return False

        comparisons = {
            "=": lambda a, e: a == e,
            "==": lambda a, e: a == e,
            "!=": lambda a, e: a != e,
            "<>": lambda a, e: a != e,
            "<": lambda a, e: a < e,
            ">": lambda a, e: a > e,
            "<=": lambda a, e: a <= e,
            ">=": lambda a, e: a >= e,
        }

        compare_fn = comparisons.get(operator, comparisons["="])
        return compare_fn(actual, expected)


def execute_rules(
    ruleset: RuleSet,
    source: str | None = None,
    dataset: Dataset | None = None
) -> ExecutionResult:
    """Convenience function to execute rules.

    Args:
        ruleset: The rules to execute
        source: Data source path
        dataset: Pre-loaded dataset

    Returns:
        ExecutionResult
    """
    executor = RuleExecutor()
    return executor.execute(ruleset, source=source, dataset=dataset)
