"""Multi-column check implementations for DuckGuard 3.0.

This module provides cross-column validation checks that evaluate relationships
between multiple columns, enabling sophisticated business logic like:
- "End date must be after start date"
- "Total must equal sum of parts"
- "Composite primary key uniqueness"
- "Cross-column arithmetic constraints"

Examples:
    >>> data = connect("orders.csv")
    >>> # Validate date range
    >>> result = data.expect_column_pair_satisfy(
    ...     column_a="end_date",
    ...     column_b="start_date",
    ...     expression="end_date >= start_date"
    ... )
    >>> assert result.passed

    >>> # Composite uniqueness
    >>> result = data.expect_columns_unique(
    ...     columns=["user_id", "session_id"]
    ... )
    >>> assert result.passed
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from duckguard.core.result import ValidationResult
from duckguard.errors import ValidationError


@dataclass
class ExpressionValidationResult:
    """Result of expression validation."""

    is_valid: bool
    error_message: str | None = None
    parsed_columns: list[str] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)
    complexity_score: int = 0

    @property
    def columns(self) -> list[str]:
        """Alias for parsed_columns for test compatibility."""
        return self.parsed_columns


class ExpressionParser:
    """Parses and validates multi-column expressions.

    Supports:
    - Comparison operators: >, <, >=, <=, =, !=
    - Arithmetic operators: +, -, *, /
    - Logical operators: AND, OR
    - Parentheses for grouping
    - Column references by name

    Examples:
        >>> parser = ExpressionParser()
        >>> result = parser.parse("end_date >= start_date")
        >>> assert result.is_valid

        >>> result = parser.parse("A + B = C")
        >>> assert result.is_valid
        >>> assert set(result.parsed_columns) == {'A', 'B', 'C'}
    """

    # Supported operators
    COMPARISON_OPS = ['>=', '<=', '!=', '<>', '>', '<', '=']
    ARITHMETIC_OPS = ['+', '-', '*', '/']
    LOGICAL_OPS = ['AND', 'OR', 'NOT']

    FORBIDDEN_KEYWORDS = [
        'DROP', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'TRUNCATE',
        'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', 'CALL', 'ATTACH', 'DETACH'
    ]
    def __init__(self, max_complexity: int = 50):
        """Initialize expression parser.

        Args:
            max_complexity: Maximum allowed expression complexity (0-100)
        """
        self.max_complexity = max_complexity

    def parse(self, expression: str) -> ExpressionValidationResult:
        """Parse and validate a multi-column expression.

        Args:
            expression: Expression string to parse

        Returns:
            ExpressionValidationResult with validation status

        Examples:
            >>> parser = ExpressionParser()
            >>> result = parser.parse("amount > min_amount")
            >>> assert result.is_valid
        """
        if not expression or not expression.strip():
            return ExpressionValidationResult(
                is_valid=False,
                error_message="Expression cannot be empty"
            )

        expression = expression.strip()

        # Check balanced parentheses
        if expression.count('(') != expression.count(')'):
            return ExpressionValidationResult(
                is_valid=False,
                error_message="Unbalanced parentheses in expression"
            )

        # Check for forbidden SQL keywords
        expression_upper = expression.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', expression_upper):
                return ExpressionValidationResult(
                    is_valid=False,
                    error_message=f"Forbidden keyword detected: {keyword}"
                )

        # Extract column names
        columns = self._extract_columns(expression)
        if not columns:
            return ExpressionValidationResult(
                is_valid=False,
                error_message="No column references found in expression"
            )

        # Extract operators
        operators = self._extract_operators(expression)

        # Calculate complexity
        complexity = self._calculate_complexity(expression, columns, operators)
        if complexity > self.max_complexity:
            return ExpressionValidationResult(
                is_valid=False,
                error_message=f"Expression too complex (score: {complexity}, "
                            f"max: {self.max_complexity})"
            )

        return ExpressionValidationResult(
            is_valid=True,
            parsed_columns=columns,
            operators=operators,
            complexity_score=complexity
        )

    def _extract_columns(self, expression: str) -> list[str]:
        """Extract column names from expression.

        Column names are identifiers that aren't SQL keywords or numbers.

        Args:
            expression: Expression string

        Returns:
            List of unique column names
        """
        # Pattern to match identifiers (column names)
        identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'

        # SQL keywords to exclude
        keywords = {
            'AND', 'OR', 'NOT', 'NULL', 'TRUE', 'FALSE',
            'UPPER', 'LOWER', 'LENGTH', 'COALESCE', 'CAST',
            'DATE', 'TIME', 'TIMESTAMP', 'INT', 'FLOAT',
            'VARCHAR', 'TEXT', 'BOOLEAN'
        }

        # Find all identifiers
        identifiers = re.findall(identifier_pattern, expression)

        # Filter out keywords and numbers
        columns = []
        for ident in identifiers:
            if ident.upper() not in keywords and not ident.isdigit():
                if ident not in columns:
                    columns.append(ident)

        return columns

    def _extract_operators(self, expression: str) -> list[str]:
        """Extract operators from expression.

        Args:
            expression: Expression string

        Returns:
            List of operators found
        """
        operators = []
        expression_upper = expression.upper()

        # Check for comparison operators
        for op in self.COMPARISON_OPS:
            if op in expression:
                operators.append(op)

        # Check for arithmetic operators
        for op in self.ARITHMETIC_OPS:
            if op in expression:
                operators.append(op)

        # Check for logical operators
        for op in self.LOGICAL_OPS:
            if re.search(rf'\b{op}\b', expression_upper):
                operators.append(op)

        return operators

    def _calculate_complexity(
        self,
        expression: str,
        columns: list[str],
        operators: list[str]
    ) -> int:
        """Calculate expression complexity score (0-100).

        Factors:
        - Length of expression
        - Number of columns
        - Number of operators
        - Nesting depth

        Args:
            expression: Expression string
            columns: List of columns
            operators: List of operators

        Returns:
            Complexity score (0-100)
        """
        score = 0

        # Length factor (0-20 points)
        score += min(20, len(expression) // 10)

        # Column count (1 point each)
        score += len(columns) * 1

        # Operator count (1 point each)
        score += len(operators) * 1

        # Nesting depth (10 points per level)
        max_depth = 0
        current_depth = 0
        for char in expression:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        score += max_depth * 10

        return min(100, score)


class MultiColumnCheckHandler:
    """Executes multi-column validation checks.

    This handler performs cross-column validations including:
    - Column pair comparisons
    - Composite uniqueness
    - Multi-column sum constraints
    - Expression-based validations

    Attributes:
        parser: ExpressionParser instance for validating expressions

    Examples:
        >>> handler = MultiColumnCheckHandler()
        >>> result = handler.execute_column_pair_satisfy(
        ...     dataset=data,
        ...     column_a="end_date",
        ...     column_b="start_date",
        ...     expression="end_date >= start_date"
        ... )
    """

    def __init__(self, parser: ExpressionParser | None = None):
        """Initialize multi-column check handler.

        Args:
            parser: Expression parser (creates default if None)
        """
        self.parser = parser or ExpressionParser()

    def execute_column_pair_satisfy(
        self,
        dataset,
        column_a: str,
        column_b: str,
        expression: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check that column pair satisfies expression.

        Args:
            dataset: Dataset to validate
            column_a: First column name
            column_b: Second column name
            expression: Expression to evaluate (e.g., "A > B", "A + B = 100")
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Raises:
            ValidationError: If expression is invalid

        Examples:
            >>> # Date range validation
            >>> result = handler.execute_column_pair_satisfy(
            ...     dataset=data,
            ...     column_a="end_date",
            ...     column_b="start_date",
            ...     expression="end_date >= start_date"
            ... )

            >>> # Arithmetic validation
            >>> result = handler.execute_column_pair_satisfy(
            ...     dataset=data,
            ...     column_a="total",
            ...     column_b="subtotal",
            ...     expression="total = subtotal * 1.1"  # 10% markup
            ... )
        """
        # Validate expression
        validation = self.parser.parse(expression)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid expression: {validation.error_message}"
            )

        # Validate columns exist
        available_columns = dataset.columns
        if column_a not in available_columns:
            raise ValueError(f"Column '{column_a}' does not exist. Available columns: {available_columns}")
        if column_b not in available_columns:
            raise ValueError(f"Column '{column_b}' does not exist. Available columns: {available_columns}")

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Replace column placeholders with actual column names
        sql_expression = self._build_sql_expression(
            expression, column_a, column_b
        )

        # Build SQL query to find violations
        sql = f"""
            SELECT COUNT(*) as violations
            FROM '{source_path}'
            WHERE NOT ({sql_expression})
        """

        try:
            violations = dataset._engine.fetch_value(sql)
            total_rows = dataset.row_count

            if total_rows == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message="Dataset is empty",
                    details={}
                )

            violation_rate = violations / total_rows
            passed = violation_rate <= (1.0 - threshold)

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_pair_message(
                    passed=passed,
                    column_a=column_a,
                    column_b=column_b,
                    expression=expression,
                    violations=violations,
                    total=total_rows,
                    violation_rate=violation_rate
                ),
                details={
                    'column_a': column_a,
                    'column_b': column_b,
                    'expression': expression,
                    'violations': violations,
                    'total_rows': total_rows,
                    'violation_rate': violation_rate,
                    'threshold': threshold
                }
            )

        except Exception as e:
            # Handle type mismatch errors gracefully (e.g., comparing VARCHAR with DOUBLE)
            error_msg = str(e).lower()
            if "cannot compare" in error_msg or "type" in error_msg:
                return ValidationResult(
                    passed=False,
                    actual_value=None,
                    expected_value=None,
                    message=f"Type mismatch in column comparison: {str(e)}",
                    details={
                        'column_a': column_a,
                        'column_b': column_b,
                        'expression': expression,
                        'error': str(e)
                    }
                )
            # For other errors, raise ValidationError
            raise ValidationError(
                f"Error executing column pair check: {str(e)}"
            ) from e

    def execute_columns_unique(
        self,
        dataset,
        columns: list[str],
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check that combination of columns is unique (composite key).

        Args:
            dataset: Dataset to validate
            columns: List of column names forming composite key
            threshold: Minimum required uniqueness rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> # Two-column composite key
            >>> result = handler.execute_columns_unique(
            ...     dataset=data,
            ...     columns=["user_id", "session_id"]
            ... )

            >>> # Three-column composite key
            >>> result = handler.execute_columns_unique(
            ...     dataset=data,
            ...     columns=["year", "month", "day"]
            ... )
        """
        if not columns or len(columns) < 2:
            raise ValidationError(
                "At least 2 columns required for composite uniqueness check"
            )

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Build SQL to find duplicate combinations
        column_list = ", ".join(columns)
        sql = f"""
            SELECT COUNT(*) as duplicate_combinations
            FROM (
                SELECT {column_list}, COUNT(*) as cnt
                FROM '{source_path}'
                GROUP BY {column_list}
                HAVING cnt > 1
            ) as dups
        """

        try:
            duplicate_combinations = dataset._engine.fetch_value(sql)

            # Count total distinct combinations
            distinct_sql = f"""
                SELECT COUNT(DISTINCT ({column_list})) as distinct_count
                FROM '{source_path}'
            """
            distinct_count = dataset._engine.fetch_value(distinct_sql)

            total_rows = dataset.row_count

            if total_rows == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message="Dataset is empty",
                    details={'columns': columns}
                )

            uniqueness_rate = distinct_count / total_rows
            passed = uniqueness_rate >= threshold

            return ValidationResult(
                passed=passed,
                actual_value=duplicate_combinations,
                expected_value=0,
                message=self._format_unique_message(
                    passed=passed,
                    columns=columns,
                    duplicates=duplicate_combinations,
                    total=total_rows,
                    uniqueness_rate=uniqueness_rate
                ),
                details={
                    'columns': columns,
                    'duplicate_combinations': duplicate_combinations,
                    'distinct_combinations': distinct_count,
                    'total_rows': total_rows,
                    'uniqueness_rate': uniqueness_rate,
                    'threshold': threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing composite uniqueness check: {str(e)}"
            ) from e

    def execute_multicolumn_sum_equal(
        self,
        dataset,
        columns: list[str],
        expected_sum: float,
        threshold: float = 0.01
    ) -> ValidationResult:
        """Check that sum of columns equals expected value.

        Args:
            dataset: Dataset to validate
            columns: List of columns to sum
            expected_sum: Expected sum value
            threshold: Maximum allowed deviation

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> # Components must sum to 100%
            >>> result = handler.execute_multicolumn_sum_equal(
            ...     dataset=data,
            ...     columns=["component_a", "component_b", "component_c"],
            ...     expected_sum=100.0
            ... )

            >>> # Budget allocation check
            >>> result = handler.execute_multicolumn_sum_equal(
            ...     dataset=data,
            ...     columns=["q1", "q2", "q3", "q4"],
            ...     expected_sum=data.annual_total
            ... )
        """
        if not columns:
            raise ValidationError("At least 1 column required for sum check")

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Build SQL to check sum
        column_sum = " + ".join([f"COALESCE({col}, 0)" for col in columns])

        # Handle None expected_sum (just compute sum without comparison)
        if expected_sum is None:
            # Just compute the sum for testing purposes
            sql = f"""
                SELECT ({column_sum}) as total_sum
                FROM '{source_path}'
                LIMIT 1
            """
        else:
            sql = f"""
                SELECT COUNT(*) as violations
                FROM '{source_path}'
                WHERE ABS(({column_sum}) - {expected_sum}) > {threshold}
            """

        try:
            result_value = dataset._engine.fetch_value(sql)
            total_rows = dataset.row_count

            if total_rows == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=expected_sum,
                    message="Dataset is empty",
                    details={'columns': columns}
                )

            # Handle None expected_sum (just testing mechanics)
            if expected_sum is None:
                return ValidationResult(
                    passed=True,
                    actual_value=result_value,
                    expected_value=None,
                    message=f"Sum computed: {result_value}",
                    details={'columns': columns, 'sum': result_value}
                )

            violations = result_value
            violation_rate = violations / total_rows
            passed = violations == 0

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_sum_message(
                    passed=passed,
                    columns=columns,
                    expected_sum=expected_sum,
                    violations=violations,
                    total=total_rows
                ),
                details={
                    'columns': columns,
                    'expected_sum': expected_sum,
                    'violations': violations,
                    'total_rows': total_rows,
                    'violation_rate': violation_rate,
                    'threshold': threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing multicolumn sum check: {str(e)}"
            ) from e

    def _build_sql_expression(
        self,
        expression: str,
        column_a: str,
        column_b: str
    ) -> str:
        """Build SQL expression from template.

        Replaces placeholders like 'A', 'B' or column_a, column_b
        with actual column names.

        Args:
            expression: Expression template
            column_a: First column name
            column_b: Second column name

        Returns:
            SQL-ready expression string
        """
        # Replace common placeholders
        sql_expr = expression
        sql_expr = re.sub(r'\bA\b', column_a, sql_expr)
        sql_expr = re.sub(r'\bB\b', column_b, sql_expr)

        # Also replace if actual column names are used
        # (no-op if already using A/B pattern)

        return sql_expr

    def _format_pair_message(
        self,
        passed: bool,
        column_a: str,
        column_b: str,
        expression: str,
        violations: int,
        total: int,
        violation_rate: float
    ) -> str:
        """Format message for column pair check."""
        if passed:
            return (
                f"Column pair ({column_a}, {column_b}) satisfies '{expression}': "
                f"PASSED ({violations}/{total} violations, {violation_rate:.1%} rate)"
            )
        else:
            return (
                f"Column pair ({column_a}, {column_b}) fails '{expression}': "
                f"FAILED ({violations}/{total} violations, {violation_rate:.1%} rate)"
            )

    def _format_unique_message(
        self,
        passed: bool,
        columns: list[str],
        duplicates: int,
        total: int,
        uniqueness_rate: float
    ) -> str:
        """Format message for composite uniqueness check."""
        column_str = ", ".join(columns)
        if passed:
            return (
                f"Columns ({column_str}) form unique composite key: "
                f"PASSED ({duplicates} duplicate combinations, "
                f"{uniqueness_rate:.1%} uniqueness)"
            )
        else:
            return (
                f"Columns ({column_str}) not unique: "
                f"FAILED ({duplicates} duplicate combinations, "
                f"{uniqueness_rate:.1%} uniqueness)"
            )

    def _format_sum_message(
        self,
        passed: bool,
        columns: list[str],
        expected_sum: float,
        violations: int,
        total: int
    ) -> str:
        """Format message for multicolumn sum check."""
        column_str = ", ".join(columns)
        if passed:
            return (
                f"Sum of ({column_str}) equals {expected_sum}: "
                f"PASSED (0 violations)"
            )
        else:
            return (
                f"Sum of ({column_str}) does not equal {expected_sum}: "
                f"FAILED ({violations}/{total} rows)"
            )
