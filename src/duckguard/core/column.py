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

    # =========================================================================
    # Cross-Dataset Validation Methods (Reference/FK Checks)
    # =========================================================================

    def exists_in(
        self,
        reference_column: Column,
        capture_failures: bool = True,
    ) -> ValidationResult:
        """
        Check that all non-null values in this column exist in the reference column.

        This is the core foreign key validation method using an efficient SQL anti-join.
        Null values in this column are ignored (they don't need to exist in reference).

        Args:
            reference_column: Column object from the reference dataset
            capture_failures: Whether to capture sample orphaned rows (default: True)

        Returns:
            ValidationResult with orphan count and sample failed rows

        Example:
            orders = connect("orders.parquet")
            customers = connect("customers.parquet")
            result = orders["customer_id"].exists_in(customers["id"])
            if not result:
                print(f"Found {result.actual_value} orphan customer IDs")
        """
        # Get source references for both datasets
        source_ref = self._dataset.engine.get_source_reference(self._dataset.source)
        ref_ref = reference_column._dataset.engine.get_source_reference(
            reference_column._dataset.source
        )
        source_col = f'"{self._name}"'
        ref_col = f'"{reference_column._name}"'

        # Count orphans using efficient anti-join pattern
        sql = f"""
        SELECT COUNT(*) as orphan_count
        FROM {source_ref} s
        WHERE s.{source_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {ref_ref} r
            WHERE r.{ref_col} = s.{source_col}
          )
        """

        orphan_count = self._dataset.engine.fetch_value(sql) or 0
        passed = orphan_count == 0

        # Capture sample of orphan rows for debugging
        failed_rows = []
        if not passed and capture_failures:
            failed_rows = self._get_failed_rows_exists_in(reference_column)

        ref_dataset_name = reference_column._dataset.name or reference_column._dataset.source
        return ValidationResult(
            passed=passed,
            actual_value=orphan_count,
            expected_value=0,
            message=f"Column '{self._name}' has {orphan_count} values not found in {ref_dataset_name}.{reference_column._name}",
            details={
                "orphan_count": orphan_count,
                "reference_dataset": ref_dataset_name,
                "reference_column": reference_column._name,
            },
            failed_rows=failed_rows,
            total_failures=orphan_count,
        )

    def _get_failed_rows_exists_in(
        self, reference_column: Column, limit: int = DEFAULT_SAMPLE_SIZE
    ) -> list[FailedRow]:
        """Get sample of rows with orphan values (not found in reference)."""
        source_ref = self._dataset.engine.get_source_reference(self._dataset.source)
        ref_ref = reference_column._dataset.engine.get_source_reference(
            reference_column._dataset.source
        )
        source_col = f'"{self._name}"'
        ref_col = f'"{reference_column._name}"'

        sql = f"""
        SELECT row_number() OVER () as row_idx, s.{source_col} as val
        FROM {source_ref} s
        WHERE s.{source_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {ref_ref} r
            WHERE r.{ref_col} = s.{source_col}
          )
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        ref_dataset_name = reference_column._dataset.name or reference_column._dataset.source
        return [
            FailedRow(
                row_index=row[0],
                column=self._name,
                value=row[1],
                expected=f"exists in {ref_dataset_name}.{reference_column._name}",
                reason=f"Value '{row[1]}' not found in reference",
                context={"reference_dataset": ref_dataset_name},
            )
            for row in rows
        ]

    def references(
        self,
        reference_column: Column,
        allow_nulls: bool = True,
        capture_failures: bool = True,
    ) -> ValidationResult:
        """
        Check foreign key relationship with configurable options.

        This is a more configurable version of exists_in() that allows
        controlling how null values are handled.

        Args:
            reference_column: Column in the reference dataset
            allow_nulls: If True (default), null values pass. If False, nulls fail.
            capture_failures: Whether to capture sample orphaned rows (default: True)

        Returns:
            ValidationResult

        Example:
            # Nulls are OK (default)
            result = orders["customer_id"].references(customers["id"])

            # Nulls should fail
            result = orders["customer_id"].references(
                customers["id"],
                allow_nulls=False,
            )
        """
        # First, check for orphans (values not in reference)
        result = self.exists_in(reference_column, capture_failures=capture_failures)

        if not allow_nulls:
            # Also count nulls as failures
            null_count = self.null_count
            if null_count > 0:
                # Combine orphan failures with null failures
                total_failures = result.actual_value + null_count
                passed = total_failures == 0

                # Add null rows to failed_rows if capturing
                null_failed_rows = []
                if capture_failures and null_count > 0:
                    null_failed_rows = self._get_null_rows_sample()

                ref_dataset_name = reference_column._dataset.name or reference_column._dataset.source
                return ValidationResult(
                    passed=passed,
                    actual_value=total_failures,
                    expected_value=0,
                    message=f"Column '{self._name}' has {result.actual_value} orphans and {null_count} nulls (references {ref_dataset_name}.{reference_column._name})",
                    details={
                        "orphan_count": result.actual_value,
                        "null_count": null_count,
                        "reference_dataset": ref_dataset_name,
                        "reference_column": reference_column._name,
                        "allow_nulls": allow_nulls,
                    },
                    failed_rows=result.failed_rows + null_failed_rows,
                    total_failures=total_failures,
                )

        return result

    def _get_null_rows_sample(self, limit: int = DEFAULT_SAMPLE_SIZE) -> list[FailedRow]:
        """Get sample of rows with null values."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT row_number() OVER () as row_idx
        FROM {ref}
        WHERE {col} IS NULL
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [
            FailedRow(
                row_index=row[0],
                column=self._name,
                value=None,
                expected="not null (allow_nulls=False)",
                reason="Null value not allowed",
            )
            for row in rows
        ]

    def find_orphans(
        self,
        reference_column: Column,
        limit: int = 100,
    ) -> list[Any]:
        """
        Find values that don't exist in the reference column.

        This is a helper method to quickly identify orphan values
        without running a full validation.

        Args:
            reference_column: Column in the reference dataset
            limit: Maximum number of orphan values to return (default: 100)

        Returns:
            List of orphan values

        Example:
            orphan_ids = orders["customer_id"].find_orphans(customers["id"])
            print(f"Invalid customer IDs: {orphan_ids}")
        """
        source_ref = self._dataset.engine.get_source_reference(self._dataset.source)
        ref_ref = reference_column._dataset.engine.get_source_reference(
            reference_column._dataset.source
        )
        source_col = f'"{self._name}"'
        ref_col = f'"{reference_column._name}"'

        sql = f"""
        SELECT DISTINCT s.{source_col}
        FROM {source_ref} s
        WHERE s.{source_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {ref_ref} r
            WHERE r.{ref_col} = s.{source_col}
          )
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [row[0] for row in rows]

    def matches_values(
        self,
        other_column: Column,
        capture_failures: bool = True,
    ) -> ValidationResult:
        """
        Check that this column's distinct values match another column's distinct values.

        Useful for comparing reference data or checking data synchronization.
        Both "missing in other" and "extra in other" are considered failures.

        Args:
            other_column: Column to compare against
            capture_failures: Whether to capture sample mismatched values (default: True)

        Returns:
            ValidationResult indicating if value sets match

        Example:
            result = orders["status"].matches_values(status_lookup["code"])
        """
        source_ref = self._dataset.engine.get_source_reference(self._dataset.source)
        other_ref = other_column._dataset.engine.get_source_reference(
            other_column._dataset.source
        )
        source_col = f'"{self._name}"'
        other_col = f'"{other_column._name}"'

        # Count values in source but not in other
        sql_missing = f"""
        SELECT COUNT(DISTINCT s.{source_col}) as missing_count
        FROM {source_ref} s
        WHERE s.{source_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {other_ref} o
            WHERE o.{other_col} = s.{source_col}
          )
        """

        # Count values in other but not in source
        sql_extra = f"""
        SELECT COUNT(DISTINCT o.{other_col}) as extra_count
        FROM {other_ref} o
        WHERE o.{other_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {source_ref} s
            WHERE s.{source_col} = o.{other_col}
          )
        """

        missing_count = self._dataset.engine.fetch_value(sql_missing) or 0
        extra_count = self._dataset.engine.fetch_value(sql_extra) or 0
        total_diff = missing_count + extra_count
        passed = total_diff == 0

        # Capture sample of mismatched values
        failed_rows = []
        if not passed and capture_failures:
            failed_rows = self._get_failed_rows_matches_values(other_column)

        other_dataset_name = other_column._dataset.name or other_column._dataset.source
        return ValidationResult(
            passed=passed,
            actual_value=total_diff,
            expected_value=0,
            message=f"Column '{self._name}' has {missing_count} values missing in {other_dataset_name}.{other_column._name}, {extra_count} extra",
            details={
                "missing_in_other": missing_count,
                "extra_in_other": extra_count,
                "other_dataset": other_dataset_name,
                "other_column": other_column._name,
            },
            failed_rows=failed_rows,
            total_failures=total_diff,
        )

    def _get_failed_rows_matches_values(
        self, other_column: Column, limit: int = DEFAULT_SAMPLE_SIZE
    ) -> list[FailedRow]:
        """Get sample of values that don't match between columns."""
        source_ref = self._dataset.engine.get_source_reference(self._dataset.source)
        other_ref = other_column._dataset.engine.get_source_reference(
            other_column._dataset.source
        )
        source_col = f'"{self._name}"'
        other_col = f'"{other_column._name}"'

        # Get values in source but not in other
        sql = f"""
        SELECT DISTINCT s.{source_col} as val, 'missing_in_other' as diff_type
        FROM {source_ref} s
        WHERE s.{source_col} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM {other_ref} o
            WHERE o.{other_col} = s.{source_col}
          )
        LIMIT {limit}
        """

        rows = self._dataset.engine.fetch_all(sql)
        other_dataset_name = other_column._dataset.name or other_column._dataset.source
        return [
            FailedRow(
                row_index=idx + 1,
                column=self._name,
                value=row[0],
                expected=f"exists in {other_dataset_name}.{other_column._name}",
                reason=f"Value '{row[0]}' not found in other column",
                context={"diff_type": row[1]},
            )
            for idx, row in enumerate(rows)
        ]

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

    # =========================================================================
    # Distribution Drift Detection
    # =========================================================================

    def detect_drift(
        self,
        reference_column: Column,
        threshold: float = 0.05,
        method: str = "ks_test",
    ) -> DriftResult:
        """
        Detect distribution drift between this column and a reference column.

        Uses statistical tests to determine if the distribution of values
        has changed significantly. Useful for ML model monitoring and
        data pipeline validation.

        Args:
            reference_column: Column from reference/baseline dataset
            threshold: P-value threshold for drift detection (default: 0.05)
            method: Statistical test method ("ks_test" for Kolmogorov-Smirnov)

        Returns:
            DriftResult with drift detection outcome

        Example:
            current = connect("orders_today.parquet")
            baseline = connect("orders_baseline.parquet")
            result = current["amount"].detect_drift(baseline["amount"])
            if result.is_drifted:
                print(f"Distribution drift detected! p-value: {result.p_value}")
        """
        from duckguard.core.result import DriftResult

        # Get values from both columns
        current_values = self._get_numeric_values()
        reference_values = reference_column._get_numeric_values()

        if len(current_values) == 0 or len(reference_values) == 0:
            return DriftResult(
                is_drifted=False,
                p_value=1.0,
                statistic=0.0,
                threshold=threshold,
                method=method,
                message="Insufficient data for drift detection",
                details={"current_count": len(current_values), "reference_count": len(reference_values)},
            )

        # Perform KS test
        ks_stat, p_value = self._ks_test(current_values, reference_values)
        is_drifted = p_value < threshold

        ref_dataset_name = reference_column._dataset.name or reference_column._dataset.source
        if is_drifted:
            message = f"Distribution drift detected in '{self._name}' vs {ref_dataset_name}.{reference_column._name} (p-value: {p_value:.4f} < {threshold})"
        else:
            message = f"No significant drift in '{self._name}' vs {ref_dataset_name}.{reference_column._name} (p-value: {p_value:.4f})"

        return DriftResult(
            is_drifted=is_drifted,
            p_value=p_value,
            statistic=ks_stat,
            threshold=threshold,
            method=method,
            message=message,
            details={
                "current_column": self._name,
                "reference_column": reference_column._name,
                "reference_dataset": ref_dataset_name,
                "current_count": len(current_values),
                "reference_count": len(reference_values),
            },
        )

    def _get_numeric_values(self, limit: int = 10000) -> list[float]:
        """Get numeric values from this column for statistical analysis."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT CAST({col} AS DOUBLE) as val
        FROM {ref}
        WHERE {col} IS NOT NULL
        LIMIT {limit}
        """

        try:
            rows = self._dataset.engine.fetch_all(sql)
            return [float(row[0]) for row in rows if row[0] is not None]
        except Exception:
            return []

    def _ks_test(self, data1: list[float], data2: list[float]) -> tuple[float, float]:
        """Perform two-sample Kolmogorov-Smirnov test.

        Returns (ks_statistic, p_value).
        """
        import math

        # Sort both datasets
        data1_sorted = sorted(data1)
        data2_sorted = sorted(data2)
        n1, n2 = len(data1_sorted), len(data2_sorted)

        # Compute the maximum difference between empirical CDFs
        all_values = sorted(set(data1_sorted + data2_sorted))

        max_diff = 0.0
        for val in all_values:
            # CDF of data1 at val
            cdf1 = sum(1 for x in data1_sorted if x <= val) / n1
            # CDF of data2 at val
            cdf2 = sum(1 for x in data2_sorted if x <= val) / n2
            max_diff = max(max_diff, abs(cdf1 - cdf2))

        ks_stat = max_diff

        # Approximate p-value using asymptotic formula
        # P(D > d) ≈ 2 * exp(-2 * d^2 * n1 * n2 / (n1 + n2))
        en = math.sqrt(n1 * n2 / (n1 + n2))
        p_value = 2.0 * math.exp(-2.0 * (ks_stat * en) ** 2)
        p_value = min(1.0, max(0.0, p_value))

        return ks_stat, p_value

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
