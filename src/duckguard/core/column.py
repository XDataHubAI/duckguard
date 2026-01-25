"""Column class with validation methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from duckguard.core.result import FailedRow, ValidationResult

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset

# Default number of failed rows to capture for debugging
DEFAULT_SAMPLE_SIZE = 10


class Column:
    """
    Represents a column in a dataset with validation capabilities.

    Columns provide a fluent interface for data validation that
    feels natural to Python developers.

    Example:
        assert orders.customer_id.null_percent < 5
        assert orders.amount.between(0, 10000)
        assert orders.email.matches(r'^[\\w.-]+@[\\w.-]+\\.\\w+$')
    """

    def __init__(self, name: str, dataset: Dataset):
        """
        Initialize a Column.

        Args:
            name: Column name
            dataset: Parent dataset
        """
        self._name = name
        self._dataset = dataset
        self._stats_cache: dict[str, Any] | None = None
        self._numeric_stats_cache: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        """Get the column name."""
        return self._name

    @property
    def dataset(self) -> Dataset:
        """Get the parent dataset."""
        return self._dataset

    def _get_stats(self) -> dict[str, Any]:
        """Get cached or fetch column statistics."""
        if self._stats_cache is None:
            self._stats_cache = self._dataset.engine.get_column_stats(
                self._dataset.source, self._name
            )
        return self._stats_cache

    def _get_numeric_stats(self) -> dict[str, Any]:
        """Get cached or fetch numeric statistics."""
        if self._numeric_stats_cache is None:
            self._numeric_stats_cache = self._dataset.engine.get_numeric_stats(
                self._dataset.source, self._name
            )
        return self._numeric_stats_cache

    # =========================================================================
    # Basic Statistics (return values for use in assertions)
    # =========================================================================

    @property
    def null_count(self) -> int:
        """Get the number of null values."""
        return self._get_stats().get("null_count", 0)

    @property
    def null_percent(self) -> float:
        """Get the percentage of null values (0-100)."""
        return self._get_stats().get("null_percent", 0.0)

    @property
    def non_null_count(self) -> int:
        """Get the number of non-null values."""
        return self._get_stats().get("non_null_count", 0)

    @property
    def unique_count(self) -> int:
        """Get the number of unique values."""
        return self._get_stats().get("unique_count", 0)

    @property
    def unique_percent(self) -> float:
        """Get the percentage of unique values (0-100)."""
        return self._get_stats().get("unique_percent", 0.0)

    @property
    def total_count(self) -> int:
        """Get the total number of values."""
        return self._get_stats().get("total_count", 0)

    @property
    def min(self) -> Any:
        """Get the minimum value."""
        return self._get_stats().get("min_value")

    @property
    def max(self) -> Any:
        """Get the maximum value."""
        return self._get_stats().get("max_value")

    @property
    def mean(self) -> float | None:
        """Get the mean value (for numeric columns)."""
        return self._get_numeric_stats().get("mean")

    @property
    def stddev(self) -> float | None:
        """Get the standard deviation (for numeric columns)."""
        return self._get_numeric_stats().get("stddev")

    @property
    def median(self) -> float | None:
        """Get the median value (for numeric columns)."""
        return self._get_numeric_stats().get("median")

    # =========================================================================
    # Validation Methods (return ValidationResult or bool)
    # =========================================================================

    def is_not_null(self, threshold: float = 0.0) -> ValidationResult:
        """
        Check that null percentage is below threshold.

        Args:
            threshold: Maximum allowed null percentage (0-100)

        Returns:
            ValidationResult
        """
        actual = self.null_percent
        passed = actual <= threshold
        return ValidationResult(
            passed=passed,
            actual_value=actual,
            expected_value=f"<= {threshold}%",
            message=f"Column '{self._name}' null_percent is {actual:.2f}% (threshold: {threshold}%)",
        )

    def is_unique(self, threshold: float = 100.0) -> ValidationResult:
        """
        Check that unique percentage is at or above threshold.

        Args:
            threshold: Minimum required unique percentage (0-100)

        Returns:
            ValidationResult
        """
        actual = self.unique_percent
        passed = actual >= threshold
        return ValidationResult(
            passed=passed,
            actual_value=actual,
            expected_value=f">= {threshold}%",
            message=f"Column '{self._name}' unique_percent is {actual:.2f}% (threshold: {threshold}%)",
        )

    def between(self, min_val: Any, max_val: Any, capture_failures: bool = True) -> ValidationResult:
        """
        Check that all values are between min and max (inclusive).

        Args:
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            capture_failures: Whether to capture sample failing rows (default: True)

        Returns:
            ValidationResult indicating if all non-null values are in range
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT(*) as out_of_range
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND ({col} < {min_val} OR {col} > {max_val})
        """

        out_of_range = self._dataset.engine.fetch_value(sql) or 0
        passed = out_of_range == 0

        # Capture sample of failing rows for debugging
        failed_rows = []
        if not passed and capture_failures:
            failed_rows = self._get_failed_rows_between(min_val, max_val)

        return ValidationResult(
            passed=passed,
            actual_value=out_of_range,
            expected_value=0,
            message=f"Column '{self._name}' has {out_of_range} values outside [{min_val}, {max_val}]",
            details={"min": min_val, "max": max_val, "out_of_range_count": out_of_range},
            failed_rows=failed_rows,
            total_failures=out_of_range,
        )

    def _get_failed_rows_between(self, min_val: Any, max_val: Any, limit: int = DEFAULT_SAMPLE_SIZE) -> list[FailedRow]:
        """Get sample of rows that failed between check."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT row_number() OVER () as row_idx, {col} as val
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND ({col} < {min_val} OR {col} > {max_val})
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [
            FailedRow(
                row_index=row[0],
                column=self._name,
                value=row[1],
                expected=f"between {min_val} and {max_val}",
                reason=f"Value {row[1]} is outside range [{min_val}, {max_val}]",
            )
            for row in rows
        ]

    def matches(self, pattern: str, capture_failures: bool = True) -> ValidationResult:
        """
        Check that all non-null values match a regex pattern.

        Args:
            pattern: Regular expression pattern
            capture_failures: Whether to capture sample failing rows (default: True)

        Returns:
            ValidationResult
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        # DuckDB uses regexp_matches for regex
        sql = f"""
        SELECT COUNT(*) as non_matching
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND NOT regexp_matches({col}::VARCHAR, '{pattern}')
        """

        non_matching = self._dataset.engine.fetch_value(sql) or 0
        passed = non_matching == 0

        # Capture sample of failing rows
        failed_rows = []
        if not passed and capture_failures:
            failed_rows = self._get_failed_rows_pattern(pattern)

        return ValidationResult(
            passed=passed,
            actual_value=non_matching,
            expected_value=0,
            message=f"Column '{self._name}' has {non_matching} values not matching pattern '{pattern}'",
            details={"pattern": pattern, "non_matching_count": non_matching},
            failed_rows=failed_rows,
            total_failures=non_matching,
        )

    def _get_failed_rows_pattern(self, pattern: str, limit: int = DEFAULT_SAMPLE_SIZE) -> list[FailedRow]:
        """Get sample of rows that failed pattern match."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT row_number() OVER () as row_idx, {col} as val
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND NOT regexp_matches({col}::VARCHAR, '{pattern}')
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [
            FailedRow(
                row_index=row[0],
                column=self._name,
                value=row[1],
                expected=f"matches pattern '{pattern}'",
                reason=f"Value '{row[1]}' does not match pattern",
            )
            for row in rows
        ]

    def isin(self, values: list[Any], capture_failures: bool = True) -> ValidationResult:
        """
        Check that all non-null values are in the allowed set.

        Args:
            values: List of allowed values
            capture_failures: Whether to capture sample failing rows (default: True)

        Returns:
            ValidationResult
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        # Build value list for SQL
        formatted_values = ", ".join(
            f"'{v}'" if isinstance(v, str) else str(v) for v in values
        )

        sql = f"""
        SELECT COUNT(*) as invalid_count
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND {col} NOT IN ({formatted_values})
        """

        invalid_count = self._dataset.engine.fetch_value(sql) or 0
        passed = invalid_count == 0

        # Capture sample of failing rows
        failed_rows = []
        if not passed and capture_failures:
            failed_rows = self._get_failed_rows_isin(values)

        return ValidationResult(
            passed=passed,
            actual_value=invalid_count,
            expected_value=0,
            message=f"Column '{self._name}' has {invalid_count} values not in allowed set",
            details={"allowed_values": values, "invalid_count": invalid_count},
            failed_rows=failed_rows,
            total_failures=invalid_count,
        )

    def _get_failed_rows_isin(self, values: list[Any], limit: int = DEFAULT_SAMPLE_SIZE) -> list[FailedRow]:
        """Get sample of rows that failed isin check."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        formatted_values = ", ".join(
            f"'{v}'" if isinstance(v, str) else str(v) for v in values
        )

        sql = f"""
        SELECT row_number() OVER () as row_idx, {col} as val
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND {col} NOT IN ({formatted_values})
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [
            FailedRow(
                row_index=row[0],
                column=self._name,
                value=row[1],
                expected=f"in {values}",
                reason=f"Value '{row[1]}' is not in allowed set",
            )
            for row in rows
        ]

    def has_no_duplicates(self) -> ValidationResult:
        """
        Check that all values are unique (no duplicates).

        Returns:
            ValidationResult
        """
        total = self.total_count
        unique = self.unique_count
        duplicates = total - unique
        passed = duplicates == 0

        return ValidationResult(
            passed=passed,
            actual_value=duplicates,
            expected_value=0,
            message=f"Column '{self._name}' has {duplicates} duplicate values",
        )

    def greater_than(self, value: Any) -> ValidationResult:
        """
        Check that all non-null values are greater than a value.

        Args:
            value: Minimum value (exclusive)

        Returns:
            ValidationResult
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT(*) as invalid_count
        FROM {ref}
        WHERE {col} IS NOT NULL AND {col} <= {value}
        """

        invalid_count = self._dataset.engine.fetch_value(sql) or 0
        passed = invalid_count == 0

        return ValidationResult(
            passed=passed,
            actual_value=invalid_count,
            expected_value=0,
            message=f"Column '{self._name}' has {invalid_count} values <= {value}",
        )

    def less_than(self, value: Any) -> ValidationResult:
        """
        Check that all non-null values are less than a value.

        Args:
            value: Maximum value (exclusive)

        Returns:
            ValidationResult
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT(*) as invalid_count
        FROM {ref}
        WHERE {col} IS NOT NULL AND {col} >= {value}
        """

        invalid_count = self._dataset.engine.fetch_value(sql) or 0
        passed = invalid_count == 0

        return ValidationResult(
            passed=passed,
            actual_value=invalid_count,
            expected_value=0,
            message=f"Column '{self._name}' has {invalid_count} values >= {value}",
        )

    def value_lengths_between(self, min_len: int, max_len: int) -> ValidationResult:
        """
        Check that string value lengths are within range.

        Args:
            min_len: Minimum length
            max_len: Maximum length

        Returns:
            ValidationResult
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT(*) as invalid_count
        FROM {ref}
        WHERE {col} IS NOT NULL
          AND (LENGTH({col}::VARCHAR) < {min_len} OR LENGTH({col}::VARCHAR) > {max_len})
        """

        invalid_count = self._dataset.engine.fetch_value(sql) or 0
        passed = invalid_count == 0

        return ValidationResult(
            passed=passed,
            actual_value=invalid_count,
            expected_value=0,
            message=f"Column '{self._name}' has {invalid_count} values with length outside [{min_len}, {max_len}]",
        )

    def get_distinct_values(self, limit: int = 100) -> list[Any]:
        """
        Get distinct values in the column.

        Args:
            limit: Maximum number of values to return

        Returns:
            List of distinct values
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT DISTINCT {col}
        FROM {ref}
        WHERE {col} IS NOT NULL
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [row[0] for row in rows]

    def get_value_counts(self, limit: int = 20) -> dict[Any, int]:
        """
        Get value counts for the column.

        Args:
            limit: Maximum number of values to return

        Returns:
            Dictionary of value -> count
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT {col}, COUNT(*) as cnt
        FROM {ref}
        GROUP BY {col}
        ORDER BY cnt DESC
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return {row[0]: row[1] for row in rows}

    def clear_cache(self) -> None:
        """Clear cached statistics."""
        self._stats_cache = None
        self._numeric_stats_cache = None

    def __repr__(self) -> str:
        return f"Column('{self._name}', dataset='{self._dataset.name}')"

    def __str__(self) -> str:
        stats = self._get_stats()
        return (
            f"Column: {self._name}\n"
            f"  Total: {stats.get('total_count', 'N/A')}\n"
            f"  Nulls: {stats.get('null_count', 'N/A')} ({stats.get('null_percent', 0):.2f}%)\n"
            f"  Unique: {stats.get('unique_count', 'N/A')} ({stats.get('unique_percent', 0):.2f}%)"
        )
