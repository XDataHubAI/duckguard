"""Dataset class representing a data source for validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from duckguard.core.column import Column
from duckguard.core.engine import DuckGuardEngine
from duckguard.core.result import GroupByResult, ReconciliationResult, ValidationResult

if TYPE_CHECKING:
    from datetime import timedelta

    from duckguard.core.scoring import QualityScore
    from duckguard.freshness import FreshnessResult


class Dataset:
    """
    Represents a data source with validation capabilities.

    A Dataset wraps a data source (file, database table, etc.) and provides
    a Pythonic interface for accessing columns and performing validations.

    Example:
        orders = Dataset("data/orders.csv")
        assert orders.row_count > 0
        assert orders.customer_id.null_percent < 5
    """

    def __init__(
        self,
        source: str,
        engine: DuckGuardEngine | None = None,
        name: str | None = None,
    ):
        """
        Initialize a Dataset.

        Args:
            source: Path to file or connection string
            engine: Optional DuckGuardEngine instance (uses singleton if not provided)
            name: Optional name for the dataset (defaults to source)
        """
        self._source = source
        self._engine = engine or DuckGuardEngine.get_instance()
        self._name = name or source
        self._columns_cache: list[str] | None = None
        self._row_count_cache: int | None = None

    @property
    def source(self) -> str:
        """Get the source path or connection string."""
        return self._source

    @property
    def name(self) -> str:
        """Get the dataset name."""
        return self._name

    @property
    def engine(self) -> DuckGuardEngine:
        """Get the underlying engine."""
        return self._engine

    @property
    def row_count(self) -> int:
        """
        Get the number of rows in the dataset.

        Returns:
            Number of rows
        """
        if self._row_count_cache is None:
            self._row_count_cache = self._engine.get_row_count(self._source)
        return self._row_count_cache

    @property
    def columns(self) -> list[str]:
        """
        Get the list of column names.

        Returns:
            List of column names
        """
        if self._columns_cache is None:
            self._columns_cache = self._engine.get_columns(self._source)
        return self._columns_cache

    @property
    def column_count(self) -> int:
        """Get the number of columns."""
        return len(self.columns)

    def __getattr__(self, name: str) -> Column:
        """
        Access columns as attributes.

        This allows Pythonic access like: dataset.customer_id

        Args:
            name: Column name

        Returns:
            Column object for the specified column

        Raises:
            AttributeError: If the column doesn't exist
        """
        # Avoid infinite recursion for private attributes
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        # Check if column exists
        if name not in self.columns:
            raise AttributeError(
                f"Column '{name}' not found. Available columns: {', '.join(self.columns)}"
            )

        return Column(name, self)

    def __getitem__(self, name: str) -> Column:
        """
        Access columns using bracket notation.

        This allows access like: dataset["customer_id"]

        Args:
            name: Column name

        Returns:
            Column object for the specified column
        """
        if name not in self.columns:
            raise KeyError(
                f"Column '{name}' not found. Available columns: {', '.join(self.columns)}"
            )
        return Column(name, self)

    def column(self, name: str) -> Column:
        """
        Get a Column object by name.

        Args:
            name: Column name

        Returns:
            Column object
        """
        return self[name]

    def has_column(self, name: str) -> bool:
        """
        Check if a column exists.

        Args:
            name: Column name to check

        Returns:
            True if column exists
        """
        return name in self.columns

    def sample(self, n: int = 10) -> list[dict[str, Any]]:
        """
        Get a sample of rows from the dataset.

        Args:
            n: Number of rows to sample

        Returns:
            List of dictionaries representing rows
        """
        ref = self._engine.get_source_reference(self._source)
        sql = f"SELECT * FROM {ref} LIMIT {n}"
        result = self._engine.execute(sql)

        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def head(self, n: int = 5) -> list[dict[str, Any]]:
        """
        Get the first n rows from the dataset.

        Args:
            n: Number of rows

        Returns:
            List of dictionaries representing rows
        """
        return self.sample(n)

    def execute_sql(self, sql: str) -> list[tuple[Any, ...]]:
        """
        Execute a custom SQL query against this dataset.

        The query can reference the dataset using {source} placeholder.

        Args:
            sql: SQL query with optional {source} placeholder

        Returns:
            Query results as list of tuples
        """
        ref = self._engine.get_source_reference(self._source)
        formatted_sql = sql.format(source=ref)
        return self._engine.fetch_all(formatted_sql)

    def clear_cache(self) -> None:
        """Clear cached values (row count, columns)."""
        self._row_count_cache = None
        self._columns_cache = None

    def __repr__(self) -> str:
        return f"Dataset('{self._source}', rows={self.row_count}, columns={self.column_count})"

    def __str__(self) -> str:
        return f"Dataset: {self._name} ({self.row_count} rows, {self.column_count} columns)"

    def __len__(self) -> int:
        """Return the number of rows."""
        return self.row_count

    def __contains__(self, column: str) -> bool:
        """Check if a column exists."""
        return column in self.columns

    def __iter__(self):
        """Iterate over column names."""
        return iter(self.columns)

    @property
    def freshness(self) -> FreshnessResult:
        """
        Get freshness information for this dataset.

        Returns:
            FreshnessResult with freshness information including:
            - last_modified: When data was last updated
            - age_seconds: Age in seconds
            - age_human: Human-readable age string
            - is_fresh: Whether data meets default 24h threshold

        Example:
            data = connect("data.csv")
            print(data.freshness.age_human)  # "2 hours ago"
            print(data.freshness.is_fresh)   # True
        """
        from duckguard.freshness import FreshnessMonitor

        monitor = FreshnessMonitor()
        return monitor.check(self)

    def is_fresh(self, max_age: timedelta) -> bool:
        """
        Check if data is fresher than the specified maximum age.

        Args:
            max_age: Maximum acceptable age for the data

        Returns:
            True if data is fresher than max_age

        Example:
            from datetime import timedelta
            data = connect("data.csv")

            if not data.is_fresh(timedelta(hours=6)):
                print("Data is stale!")
        """
        from duckguard.freshness import FreshnessMonitor

        monitor = FreshnessMonitor(threshold=max_age)
        result = monitor.check(self)
        return result.is_fresh

    # =========================================================================
    # Cross-Dataset Validation Methods
    # =========================================================================

    def row_count_matches(
        self,
        other_dataset: Dataset,
        tolerance: int = 0,
    ) -> ValidationResult:
        """
        Check that row count matches another dataset within tolerance.

        Useful for comparing backup data, validating migrations,
        or ensuring parallel pipelines produce consistent results.

        Args:
            other_dataset: Dataset to compare against
            tolerance: Allowed difference in row counts (default: 0 = exact match)

        Returns:
            ValidationResult indicating if row counts match

        Example:
            orders = connect("orders.parquet")
            backup = connect("orders_backup.parquet")

            # Exact match
            result = orders.row_count_matches(backup)

            # Allow small difference
            result = orders.row_count_matches(backup, tolerance=10)
        """
        source_count = self.row_count
        other_count = other_dataset.row_count
        diff = abs(source_count - other_count)
        passed = diff <= tolerance

        other_name = other_dataset.name or other_dataset.source
        if tolerance == 0:
            message = f"Row counts {'match' if passed else 'differ'}: {self._name}={source_count}, {other_name}={other_count}"
        else:
            message = f"Row count difference is {diff} (tolerance: {tolerance}): {self._name}={source_count}, {other_name}={other_count}"

        return ValidationResult(
            passed=passed,
            actual_value=diff,
            expected_value=f"<= {tolerance}",
            message=message,
            details={
                "source_count": source_count,
                "other_count": other_count,
                "difference": diff,
                "tolerance": tolerance,
                "source_dataset": self._name,
                "other_dataset": other_name,
            },
        )

    def row_count_equals(
        self,
        other_dataset: Dataset,
    ) -> ValidationResult:
        """
        Check that row count exactly equals another dataset.

        This is a convenience alias for row_count_matches(other, tolerance=0).

        Args:
            other_dataset: Dataset to compare against

        Returns:
            ValidationResult indicating if row counts are equal

        Example:
            result = orders.row_count_equals(backup_orders)
        """
        return self.row_count_matches(other_dataset, tolerance=0)

    def score(
        self,
        weights: dict | None = None,
    ) -> QualityScore:
        """
        Calculate data quality score for this dataset.

        Evaluates data across standard quality dimensions:
        - Completeness: Are all required values present?
        - Uniqueness: Are values appropriately unique?
        - Validity: Do values conform to expected formats/ranges?
        - Consistency: Are values consistent?

        Args:
            weights: Optional custom weights for dimensions.
                     Keys: 'completeness', 'uniqueness', 'validity', 'consistency'
                     Values must sum to 1.0

        Returns:
            QualityScore with overall score, grade, and dimension breakdowns.

        Example:
            score = orders.score()
            print(score.overall)        # 87.5
            print(score.grade)          # 'B'
            print(score.completeness)   # 95.0

            # With custom weights
            score = orders.score(weights={
                'completeness': 0.4,
                'uniqueness': 0.2,
                'validity': 0.3,
                'consistency': 0.1,
            })
        """
        from duckguard.core.scoring import QualityDimension, QualityScorer

        # Convert string keys to QualityDimension enums if needed
        scorer_weights = None
        if weights:
            scorer_weights = {}
            key_mapping = {
                "completeness": QualityDimension.COMPLETENESS,
                "uniqueness": QualityDimension.UNIQUENESS,
                "validity": QualityDimension.VALIDITY,
                "consistency": QualityDimension.CONSISTENCY,
            }
            for key, value in weights.items():
                if isinstance(key, str):
                    scorer_weights[key_mapping[key]] = value
                else:
                    scorer_weights[key] = value

        scorer = QualityScorer(weights=scorer_weights)
        return scorer.score(self)

    # =========================================================================
    # Reconciliation Methods
    # =========================================================================

    def reconcile(
        self,
        target_dataset: Dataset,
        key_columns: list[str],
        compare_columns: list[str] | None = None,
        tolerance: float = 0.0,
        sample_mismatches: int = 10,
    ) -> ReconciliationResult:
        """
        Reconcile this dataset with a target dataset.

        Performs comprehensive comparison including row matching, missing/extra
        detection, and column-by-column value comparison. Essential for
        migration validation and data synchronization checks.

        Args:
            target_dataset: Dataset to compare against
            key_columns: Columns to use for matching rows (like a primary key)
            compare_columns: Columns to compare values (default: all non-key columns)
            tolerance: Numeric tolerance for value comparison (default: 0 = exact match)
            sample_mismatches: Number of sample mismatches to capture (default: 10)

        Returns:
            ReconciliationResult with detailed comparison metrics

        Example:
            source = connect("orders_source.parquet")
            target = connect("orders_target.parquet")

            result = source.reconcile(
                target,
                key_columns=["order_id"],
                compare_columns=["amount", "status", "customer_id"]
            )

            if not result.passed:
                print(f"Missing in target: {result.missing_in_target}")
                print(f"Extra in target: {result.extra_in_target}")
                print(result.summary())
        """
        from duckguard.core.result import ReconciliationMismatch, ReconciliationResult

        source_ref = self._engine.get_source_reference(self._source)
        target_ref = target_dataset.engine.get_source_reference(target_dataset.source)
        target_name = target_dataset.name or target_dataset.source

        # Determine columns to compare
        if compare_columns is None:
            compare_columns = [c for c in self.columns if c not in key_columns]

        # Build key column references
        key_join_condition = " AND ".join(
            f's."{k}" = t."{k}"' for k in key_columns
        )

        # Count rows in source not in target (missing)
        sql_missing = f"""
        SELECT COUNT(*) FROM {source_ref} s
        WHERE NOT EXISTS (
            SELECT 1 FROM {target_ref} t
            WHERE {key_join_condition}
        )
        """
        missing_count = self._engine.fetch_value(sql_missing) or 0

        # Count rows in target not in source (extra)
        sql_extra = f"""
        SELECT COUNT(*) FROM {target_ref} t
        WHERE NOT EXISTS (
            SELECT 1 FROM {source_ref} s
            WHERE {key_join_condition}
        )
        """
        extra_count = self._engine.fetch_value(sql_extra) or 0

        # Count value mismatches per column for matching rows
        value_mismatches: dict[str, int] = {}
        for col in compare_columns:
            if tolerance > 0:
                # Numeric tolerance comparison
                sql_mismatch = f"""
                SELECT COUNT(*) FROM {source_ref} s
                INNER JOIN {target_ref} t ON {key_join_condition}
                WHERE ABS(COALESCE(CAST(s."{col}" AS DOUBLE), 0) -
                          COALESCE(CAST(t."{col}" AS DOUBLE), 0)) > {tolerance}
                   OR (s."{col}" IS NULL AND t."{col}" IS NOT NULL)
                   OR (s."{col}" IS NOT NULL AND t."{col}" IS NULL)
                """
            else:
                # Exact match comparison
                sql_mismatch = f"""
                SELECT COUNT(*) FROM {source_ref} s
                INNER JOIN {target_ref} t ON {key_join_condition}
                WHERE s."{col}" IS DISTINCT FROM t."{col}"
                """
            mismatch_count = self._engine.fetch_value(sql_mismatch) or 0
            if mismatch_count > 0:
                value_mismatches[col] = mismatch_count

        # Calculate match percentage
        source_count = self.row_count
        target_count = target_dataset.row_count
        matched_rows = source_count - missing_count
        total_comparisons = matched_rows * len(compare_columns) if compare_columns else matched_rows
        total_mismatches = sum(value_mismatches.values())

        if total_comparisons > 0:
            match_percentage = ((total_comparisons - total_mismatches) / total_comparisons) * 100
        else:
            match_percentage = 100.0 if missing_count == 0 and extra_count == 0 else 0.0

        # Capture sample mismatches
        mismatches: list[ReconciliationMismatch] = []
        if sample_mismatches > 0 and (missing_count > 0 or extra_count > 0 or value_mismatches):
            mismatches = self._get_sample_mismatches(
                target_dataset,
                key_columns,
                compare_columns,
                tolerance,
                sample_mismatches,
            )

        # Determine if passed (no mismatches at all)
        passed = missing_count == 0 and extra_count == 0 and len(value_mismatches) == 0

        return ReconciliationResult(
            passed=passed,
            source_row_count=source_count,
            target_row_count=target_count,
            missing_in_target=missing_count,
            extra_in_target=extra_count,
            value_mismatches=value_mismatches,
            match_percentage=match_percentage,
            key_columns=key_columns,
            compared_columns=compare_columns,
            mismatches=mismatches,
            details={
                "source_dataset": self._name,
                "target_dataset": target_name,
                "tolerance": tolerance,
            },
        )

    def _get_sample_mismatches(
        self,
        target_dataset: Dataset,
        key_columns: list[str],
        compare_columns: list[str],
        tolerance: float,
        limit: int,
    ) -> list:
        """Get sample of reconciliation mismatches."""
        from duckguard.core.result import ReconciliationMismatch

        source_ref = self._engine.get_source_reference(self._source)
        target_ref = target_dataset.engine.get_source_reference(target_dataset.source)

        key_cols_sql = ", ".join(f's."{k}"' for k in key_columns)
        key_join_condition = " AND ".join(
            f's."{k}" = t."{k}"' for k in key_columns
        )

        mismatches: list[ReconciliationMismatch] = []

        # Sample missing in target
        sql_missing = f"""
        SELECT {key_cols_sql} FROM {source_ref} s
        WHERE NOT EXISTS (
            SELECT 1 FROM {target_ref} t
            WHERE {key_join_condition}
        )
        LIMIT {limit}
        """
        missing_rows = self._engine.fetch_all(sql_missing)
        for row in missing_rows:
            key_values = dict(zip(key_columns, row))
            mismatches.append(ReconciliationMismatch(
                key_values=key_values,
                column="(row)",
                source_value="exists",
                target_value="missing",
                mismatch_type="missing_in_target",
            ))

        # Sample value mismatches
        remaining = limit - len(mismatches)
        if remaining > 0 and compare_columns:
            for col in compare_columns[:3]:  # Limit columns for sampling
                if tolerance > 0:
                    sql_diff = f"""
                    SELECT {key_cols_sql}, s."{col}" as source_val, t."{col}" as target_val
                    FROM {source_ref} s
                    INNER JOIN {target_ref} t ON {key_join_condition}
                    WHERE ABS(COALESCE(CAST(s."{col}" AS DOUBLE), 0) -
                              COALESCE(CAST(t."{col}" AS DOUBLE), 0)) > {tolerance}
                       OR (s."{col}" IS NULL AND t."{col}" IS NOT NULL)
                       OR (s."{col}" IS NOT NULL AND t."{col}" IS NULL)
                    LIMIT {remaining}
                    """
                else:
                    sql_diff = f"""
                    SELECT {key_cols_sql}, s."{col}" as source_val, t."{col}" as target_val
                    FROM {source_ref} s
                    INNER JOIN {target_ref} t ON {key_join_condition}
                    WHERE s."{col}" IS DISTINCT FROM t."{col}"
                    LIMIT {remaining}
                    """
                diff_rows = self._engine.fetch_all(sql_diff)
                for row in diff_rows:
                    key_values = dict(zip(key_columns, row[:len(key_columns)]))
                    mismatches.append(ReconciliationMismatch(
                        key_values=key_values,
                        column=col,
                        source_value=row[len(key_columns)],
                        target_value=row[len(key_columns) + 1],
                        mismatch_type="value_diff",
                    ))

        return mismatches[:limit]

    # =========================================================================
    # Group By Methods
    # =========================================================================

    def group_by(self, columns: list[str] | str) -> GroupedDataset:
        """
        Group the dataset by one or more columns for segmented validation.

        Returns a GroupedDataset that allows running validation checks
        on each group separately. Useful for partition-level data quality
        checks and segmented analysis.

        Args:
            columns: Column name(s) to group by

        Returns:
            GroupedDataset for running group-level validations

        Example:
            # Validate each region has data
            result = orders.group_by("region").row_count_greater_than(0)

            # Validate per-date quality
            result = orders.group_by(["date", "region"]).validate(
                lambda g: g["amount"].null_percent < 5
            )

            # Get group statistics
            stats = orders.group_by("status").stats()
        """
        if isinstance(columns, str):
            columns = [columns]

        # Validate columns exist
        for col in columns:
            if col not in self.columns:
                raise KeyError(
                    f"Column '{col}' not found. Available columns: {', '.join(self.columns)}"
                )

        return GroupedDataset(self, columns)

    # =================================================================
    # Multi-Column Validation Methods (DuckGuard 3.0)
    # =================================================================

    def expect_column_pair_satisfy(
        self,
        column_a: str,
        column_b: str,
        expression: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check that column pair satisfies expression.

        Args:
            column_a: First column name
            column_b: Second column name
            expression: Expression to evaluate (e.g., "A > B", "A + B = 100")
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> data = connect("orders.csv")
            >>> # Date range validation
            >>> result = data.expect_column_pair_satisfy(
            ...     column_a="end_date",
            ...     column_b="start_date",
            ...     expression="end_date >= start_date"
            ... )
            >>> assert result.passed

            >>> # Arithmetic validation
            >>> result = data.expect_column_pair_satisfy(
            ...     column_a="total",
            ...     column_b="subtotal",
            ...     expression="total = subtotal * 1.1"
            ... )
        """
        from duckguard.checks.multicolumn import MultiColumnCheckHandler

        handler = MultiColumnCheckHandler()
        return handler.execute_column_pair_satisfy(
            dataset=self,
            column_a=column_a,
            column_b=column_b,
            expression=expression,
            threshold=threshold
        )

    def expect_columns_unique(
        self,
        columns: list[str],
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check that combination of columns is unique (composite key).

        Args:
            columns: List of column names forming composite key
            threshold: Minimum required uniqueness rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> # Two-column composite key
            >>> result = data.expect_columns_unique(
            ...     columns=["user_id", "session_id"]
            ... )
            >>> assert result.passed

            >>> # Three-column composite key
            >>> result = data.expect_columns_unique(
            ...     columns=["year", "month", "product_id"]
            ... )
        """
        from duckguard.checks.multicolumn import MultiColumnCheckHandler

        handler = MultiColumnCheckHandler()
        return handler.execute_columns_unique(
            dataset=self,
            columns=columns,
            threshold=threshold
        )

    def expect_multicolumn_sum_to_equal(
        self,
        columns: list[str],
        expected_sum: float,
        threshold: float = 0.01
    ) -> ValidationResult:
        """Check that sum of columns equals expected value.

        Args:
            columns: List of columns to sum
            expected_sum: Expected sum value
            threshold: Maximum allowed deviation

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> # Components must sum to 100%
            >>> result = data.expect_multicolumn_sum_to_equal(
            ...     columns=["q1_pct", "q2_pct", "q3_pct", "q4_pct"],
            ...     expected_sum=100.0
            ... )
            >>> assert result.passed

            >>> # Budget allocation check
            >>> result = data.expect_multicolumn_sum_to_equal(
            ...     columns=["marketing", "sales", "r_and_d"],
            ...     expected_sum=data.total_budget
            ... )
        """
        from duckguard.checks.multicolumn import MultiColumnCheckHandler

        handler = MultiColumnCheckHandler()
        return handler.execute_multicolumn_sum_equal(
            dataset=self,
            columns=columns,
            expected_sum=expected_sum,
            threshold=threshold
        )

    # =================================================================
    # Query-Based Validation Methods (DuckGuard 3.0)
    # =================================================================

    def expect_query_to_return_no_rows(
        self,
        query: str,
        message: str | None = None
    ) -> ValidationResult:
        """Check that custom SQL query returns no rows (finds no violations).

        Use case: Write a query that finds violations. The check passes if
        the query returns no rows (no violations found).

        Args:
            query: SQL SELECT query (use 'table' to reference the dataset)
            message: Optional custom message

        Returns:
            ValidationResult (passed if query returns 0 rows)

        Examples:
            >>> data = connect("orders.csv")
            >>> # Find invalid totals (total < subtotal)
            >>> result = data.expect_query_to_return_no_rows(
            ...     query="SELECT * FROM table WHERE total < subtotal"
            ... )
            >>> assert result.passed

            >>> # Find future dates
            >>> result = data.expect_query_to_return_no_rows(
            ...     query="SELECT * FROM table WHERE order_date > CURRENT_DATE"
            ... )

        Security:
            - Query is validated to prevent SQL injection
            - Only SELECT queries allowed
            - READ-ONLY mode enforced
            - 30-second timeout
            - 10,000 row result limit
        """
        from duckguard.checks.query_based import QueryCheckHandler

        handler = QueryCheckHandler()
        return handler.execute_query_no_rows(
            dataset=self,
            query=query,
            message=message
        )

    def expect_query_to_return_rows(
        self,
        query: str,
        message: str | None = None
    ) -> ValidationResult:
        """Check that custom SQL query returns at least one row.

        Use case: Ensure expected data exists in the dataset.

        Args:
            query: SQL SELECT query (use 'table' to reference the dataset)
            message: Optional custom message

        Returns:
            ValidationResult (passed if query returns > 0 rows)

        Examples:
            >>> data = connect("products.csv")
            >>> # Ensure we have active products
            >>> result = data.expect_query_to_return_rows(
            ...     query="SELECT * FROM table WHERE status = 'active'"
            ... )
            >>> assert result.passed

            >>> # Ensure we have recent data
            >>> result = data.expect_query_to_return_rows(
            ...     query="SELECT * FROM table WHERE created_at >= CURRENT_DATE - 7"
            ... )

        Security:
            - Query is validated to prevent SQL injection
            - Only SELECT queries allowed
            - READ-ONLY mode enforced
        """
        from duckguard.checks.query_based import QueryCheckHandler

        handler = QueryCheckHandler()
        return handler.execute_query_returns_rows(
            dataset=self,
            query=query,
            message=message
        )

    def expect_query_result_to_equal(
        self,
        query: str,
        expected: Any,
        tolerance: float | None = None,
        message: str | None = None
    ) -> ValidationResult:
        """Check that custom SQL query returns a specific value.

        Use case: Aggregate validation (COUNT, SUM, AVG, etc.)

        Args:
            query: SQL query returning single value (use 'table' to reference dataset)
            expected: Expected value
            tolerance: Optional tolerance for numeric comparisons
            message: Optional custom message

        Returns:
            ValidationResult (passed if query result equals expected)

        Examples:
            >>> data = connect("orders.csv")
            >>> # Check pending order count
            >>> result = data.expect_query_result_to_equal(
            ...     query="SELECT COUNT(*) FROM table WHERE status = 'pending'",
            ...     expected=0
            ... )
            >>> assert result.passed

            >>> # Check average with tolerance
            >>> result = data.expect_query_result_to_equal(
            ...     query="SELECT AVG(price) FROM table",
            ...     expected=100.0,
            ...     tolerance=5.0
            ... )

            >>> # Check sum constraint
            >>> result = data.expect_query_result_to_equal(
            ...     query="SELECT SUM(quantity) FROM table WHERE category = 'electronics'",
            ...     expected=1000
            ... )

        Security:
            - Query must return exactly 1 row with 1 column
            - Query is validated to prevent SQL injection
        """
        from duckguard.checks.query_based import QueryCheckHandler

        handler = QueryCheckHandler()
        return handler.execute_query_result_equals(
            dataset=self,
            query=query,
            expected=expected,
            tolerance=tolerance,
            message=message
        )

    def expect_query_result_to_be_between(
        self,
        query: str,
        min_value: float,
        max_value: float,
        message: str | None = None
    ) -> ValidationResult:
        """Check that custom SQL query result is within a range.

        Use case: Metric validation (e.g., average must be between X and Y)

        Args:
            query: SQL query returning single numeric value
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            message: Optional custom message

        Returns:
            ValidationResult (passed if min_value <= result <= max_value)

        Examples:
            >>> data = connect("metrics.csv")
            >>> # Average price in range
            >>> result = data.expect_query_result_to_be_between(
            ...     query="SELECT AVG(price) FROM table",
            ...     min_value=10.0,
            ...     max_value=1000.0
            ... )
            >>> assert result.passed

            >>> # Null rate validation
            >>> result = data.expect_query_result_to_be_between(
            ...     query='''
            ...         SELECT (COUNT(*) FILTER (WHERE price IS NULL)) * 100.0 / COUNT(*)
            ...         FROM table
            ...     ''',
            ...     min_value=0.0,
            ...     max_value=5.0  # Max 5% nulls
            ... )

        Security:
            - Query must return exactly 1 row with 1 numeric column
            - Query is validated to prevent SQL injection
        """
        from duckguard.checks.query_based import QueryCheckHandler

        handler = QueryCheckHandler()
        return handler.execute_query_result_between(
            dataset=self,
            query=query,
            min_value=min_value,
            max_value=max_value,
            message=message
        )


class GroupedDataset:
    """
    Represents a dataset grouped by one or more columns.

    Provides methods for running validation checks and getting statistics
    at the group level. Created via Dataset.group_by().

    Example:
        grouped = orders.group_by("region")
        result = grouped.row_count_greater_than(100)
        stats = grouped.stats()
    """

    def __init__(self, dataset: Dataset, group_columns: list[str]):
        """Initialize a grouped dataset.

        Args:
            dataset: The source dataset
            group_columns: Columns to group by
        """
        self._dataset = dataset
        self._group_columns = group_columns

    @property
    def groups(self) -> list[dict[str, Any]]:
        """Get all distinct group key combinations."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        cols_sql = ", ".join(f'"{c}"' for c in self._group_columns)

        sql = f"""
        SELECT DISTINCT {cols_sql}
        FROM {ref}
        ORDER BY {cols_sql}
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [dict(zip(self._group_columns, row)) for row in rows]

    @property
    def group_count(self) -> int:
        """Get the number of distinct groups."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        cols_sql = ", ".join(f'"{c}"' for c in self._group_columns)

        sql = f"""
        SELECT COUNT(DISTINCT ({cols_sql}))
        FROM {ref}
        """

        return self._dataset.engine.fetch_value(sql) or 0

    def stats(self) -> list[dict[str, Any]]:
        """
        Get statistics for each group.

        Returns a list of dictionaries with group key values and statistics
        including row count, null counts, and basic aggregations.

        Returns:
            List of group statistics dictionaries

        Example:
            stats = orders.group_by("status").stats()
            for g in stats:
                print(f"{g['status']}: {g['row_count']} rows")
        """
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        cols_sql = ", ".join(f'"{c}"' for c in self._group_columns)

        sql = f"""
        SELECT {cols_sql}, COUNT(*) as row_count
        FROM {ref}
        GROUP BY {cols_sql}
        ORDER BY row_count DESC
        """

        rows = self._dataset.engine.fetch_all(sql)
        return [
            {**dict(zip(self._group_columns, row[:-1])), "row_count": row[-1]}
            for row in rows
        ]

    def row_count_greater_than(self, min_count: int) -> GroupByResult:
        """
        Validate that each group has more than min_count rows.

        Args:
            min_count: Minimum required rows per group

        Returns:
            GroupByResult with per-group validation results

        Example:
            result = orders.group_by("region").row_count_greater_than(100)
            if not result.passed:
                for g in result.get_failed_groups():
                    print(f"Region {g.group_key} has only {g.row_count} rows")
        """
        from duckguard.core.result import GroupByResult, GroupResult, ValidationResult

        group_results: list[GroupResult] = []
        passed_count = 0

        for group_stats in self.stats():
            group_key = {k: group_stats[k] for k in self._group_columns}
            row_count = group_stats["row_count"]
            passed = row_count > min_count

            check_result = ValidationResult(
                passed=passed,
                actual_value=row_count,
                expected_value=f"> {min_count}",
                message=f"row_count = {row_count} {'>' if passed else '<='} {min_count}",
            )

            group_results.append(GroupResult(
                group_key=group_key,
                row_count=row_count,
                passed=passed,
                check_results=[check_result],
            ))

            if passed:
                passed_count += 1

        total_groups = len(group_results)
        all_passed = passed_count == total_groups

        return GroupByResult(
            passed=all_passed,
            total_groups=total_groups,
            passed_groups=passed_count,
            failed_groups=total_groups - passed_count,
            group_results=group_results,
            group_columns=self._group_columns,
        )

    def validate(
        self,
        check_fn,
        column: str | None = None,
    ) -> GroupByResult:
        """
        Run a custom validation function on each group.

        Args:
            check_fn: Function that takes a group's column and returns ValidationResult
            column: Column to validate (required for column-level checks)

        Returns:
            GroupByResult with per-group validation results

        Example:
            # Check null percent per group
            result = orders.group_by("region").validate(
                lambda col: col.null_percent < 5,
                column="customer_id"
            )

            # Check amount range per group
            result = orders.group_by("date").validate(
                lambda col: col.between(0, 10000),
                column="amount"
            )
        """
        from duckguard.core.result import GroupByResult, GroupResult, ValidationResult

        group_results: list[GroupResult] = []
        passed_count = 0

        for group_key in self.groups:
            # Build WHERE clause for this group
            conditions = " AND ".join(
                f'"{k}" = {self._format_value(v)}'
                for k, v in group_key.items()
            )

            # Create a filtered view of the data for this group
            ref = self._dataset.engine.get_source_reference(self._dataset.source)

            # Get row count for this group
            sql_count = f"SELECT COUNT(*) FROM {ref} WHERE {conditions}"
            row_count = self._dataset.engine.fetch_value(sql_count) or 0

            # Create a temporary filtered column for validation
            if column:
                group_col = _GroupColumn(
                    name=column,
                    dataset=self._dataset,
                    filter_condition=conditions,
                )
                try:
                    result = check_fn(group_col)
                    if not isinstance(result, ValidationResult):
                        # If check_fn returns a boolean (e.g., col.null_percent < 5)
                        result = ValidationResult(
                            passed=bool(result),
                            actual_value=result,
                            message=f"Custom check {'passed' if result else 'failed'}",
                        )
                except Exception as e:
                    result = ValidationResult(
                        passed=False,
                        actual_value=None,
                        message=f"Check error: {e}",
                    )
            else:
                result = ValidationResult(
                    passed=True,
                    actual_value=row_count,
                    message="No column check specified",
                )

            group_results.append(GroupResult(
                group_key=group_key,
                row_count=row_count,
                passed=result.passed,
                check_results=[result],
            ))

            if result.passed:
                passed_count += 1

        total_groups = len(group_results)
        all_passed = passed_count == total_groups

        return GroupByResult(
            passed=all_passed,
            total_groups=total_groups,
            passed_groups=passed_count,
            failed_groups=total_groups - passed_count,
            group_results=group_results,
            group_columns=self._group_columns,
        )

    def _format_value(self, value: Any) -> str:
        """Format a value for SQL WHERE clause."""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        else:
            return str(value)


class _GroupColumn:
    """
    A column wrapper that applies a filter condition.

    Used internally by GroupedDataset to validate columns within groups.
    """

    def __init__(self, name: str, dataset: Dataset, filter_condition: str):
        self._name = name
        self._dataset = dataset
        self._filter_condition = filter_condition

    @property
    def null_percent(self) -> float:
        """Get null percentage for this column within the group."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT
            (COUNT(*) - COUNT({col})) * 100.0 / NULLIF(COUNT(*), 0) as null_pct
        FROM {ref}
        WHERE {self._filter_condition}
        """

        result = self._dataset.engine.fetch_value(sql)
        return float(result) if result is not None else 0.0

    @property
    def count(self) -> int:
        """Get non-null count for this column within the group."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT({col})
        FROM {ref}
        WHERE {self._filter_condition}
        """

        return self._dataset.engine.fetch_value(sql) or 0

    def between(self, min_val: Any, max_val: Any) -> ValidationResult:
        """Check if all values are between min and max within the group."""
        ref = self._dataset.engine.get_source_reference(self._dataset.source)
        col = f'"{self._name}"'

        sql = f"""
        SELECT COUNT(*) FROM {ref}
        WHERE {self._filter_condition}
          AND {col} IS NOT NULL
          AND ({col} < {min_val} OR {col} > {max_val})
        """

        out_of_range = self._dataset.engine.fetch_value(sql) or 0
        passed = out_of_range == 0

        return ValidationResult(
            passed=passed,
            actual_value=out_of_range,
            expected_value=0,
            message=f"{out_of_range} values outside [{min_val}, {max_val}]",
        )
