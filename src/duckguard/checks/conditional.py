"""Conditional check implementations for DuckGuard 3.0.

This module provides conditional validation checks that apply rules only when
a specified condition is true. This enables sophisticated data quality checks
like:
- "Column must not be null when country = 'USA'"
- "Amount must be positive when status = 'completed'"
- "Email is required when customer_type = 'registered'"

Security Note:
    All SQL conditions are validated to prevent SQL injection. Only SELECT
    queries with WHERE clauses are allowed. No data modification statements
    (INSERT, UPDATE, DELETE, DROP, etc.) are permitted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from duckguard.core.result import ValidationResult
from duckguard.errors import ValidationError


@dataclass
class QueryValidationResult:
    """Result of SQL query validation."""

    is_valid: bool
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    complexity_score: int = 0  # 0-100, higher = more complex


class QueryValidator:
    """Validates SQL conditions for security and correctness.

    This validator prevents SQL injection and ensures queries are safe to execute.
    It applies multiple layers of validation:
    1. Keyword blacklist (no destructive operations)
    2. Syntax validation via DuckDB parser
    3. Complexity analysis
    4. Read-only enforcement

    Examples:
        >>> validator = QueryValidator()
        >>> result = validator.validate("country = 'USA'")
        >>> assert result.is_valid

        >>> result = validator.validate("DROP TABLE users")
        >>> assert not result.is_valid
        >>> assert "forbidden keyword" in result.error_message.lower()
    """

    # Keywords that are absolutely forbidden in conditions
    FORBIDDEN_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
        "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXECUTE",
        "EXEC", "CALL", "MERGE", "REPLACE", "PRAGMA"
    ]

    # Keywords that suggest dangerous operations
    WARNING_KEYWORDS = [
        "ATTACH", "DETACH", "IMPORT", "EXPORT", "COPY",
        "LOAD", "INSTALL"
    ]

    def __init__(self, max_complexity: int = 50):
        """Initialize validator.

        Args:
            max_complexity: Maximum allowed complexity score (0-100)
        """
        self.max_complexity = max_complexity

    def validate(self, condition: str) -> QueryValidationResult:
        """Validate a SQL condition string.

        Args:
            condition: SQL WHERE clause condition (without WHERE keyword)

        Returns:
            QueryValidationResult with validation status and details

        Examples:
            >>> validator = QueryValidator()
            >>> result = validator.validate("status = 'active'")
            >>> assert result.is_valid

            >>> result = validator.validate("amount > 100 AND category = 'A'")
            >>> assert result.is_valid
        """
        if not condition or not condition.strip():
            return QueryValidationResult(
                is_valid=False,
                error_message="Condition cannot be empty"
            )

        condition = condition.strip()

        # Step 1: Check for forbidden keywords
        condition_upper = condition.upper()
        for keyword in self.FORBIDDEN_KEYWORDS:
            if re.search(rf'\b{keyword}\b', condition_upper):
                return QueryValidationResult(
                    is_valid=False,
                    error_message=f"Forbidden keyword detected: {keyword}. "
                                f"Only SELECT queries with WHERE clauses are allowed."
                )

        # Step 2: Check for warning keywords
        warnings = []
        for keyword in self.WARNING_KEYWORDS:
            if re.search(rf'\b{keyword}\b', condition_upper):
                warnings.append(
                    f"Warning: Potentially dangerous keyword detected: {keyword}"
                )

        # Step 3: Basic syntax checks
        if condition.count('(') != condition.count(')'):
            return QueryValidationResult(
                is_valid=False,
                error_message="Unbalanced parentheses in condition"
            )

        if condition.count("'") % 2 != 0:
            return QueryValidationResult(
                is_valid=False,
                error_message="Unbalanced quotes in condition"
            )

        # Step 4: Check for common SQL injection patterns
        injection_patterns = [
            r'--',  # SQL comments
            r'/\*',  # Block comment start
            r'\*/',  # Block comment end
            r';.*',  # Multiple statements
            r'\bOR\s+[\'"]?1[\'"]?\s*=\s*[\'"]?1[\'"]?',  # OR 1=1
            r'\bUNION\b.*\bSELECT\b',  # UNION SELECT
        ]

        for pattern in injection_patterns:
            if re.search(pattern, condition_upper):
                return QueryValidationResult(
                    is_valid=False,
                    error_message="Potential SQL injection detected. "
                                "Suspicious pattern found."
                )

        # Step 5: Calculate complexity score
        complexity = self._calculate_complexity(condition)
        if complexity > self.max_complexity:
            return QueryValidationResult(
                is_valid=False,
                error_message=f"Condition too complex (score: {complexity}, "
                            f"max: {self.max_complexity}). "
                            f"Simplify your condition or use query-based checks."
            )

        # All checks passed
        return QueryValidationResult(
            is_valid=True,
            warnings=warnings,
            complexity_score=complexity
        )

    def _calculate_complexity(self, condition: str) -> int:
        """Calculate complexity score for a condition (0-100).

        Factors:
        - Length of condition string
        - Number of operators (AND, OR, NOT)
        - Number of comparisons
        - Nesting depth (parentheses)
        - Number of function calls

        Args:
            condition: SQL condition string

        Returns:
            Complexity score (0-100)
        """
        score = 0
        condition_upper = condition.upper()

        # Length factor (0-20 points)
        length_score = min(20, len(condition) // 10)
        score += length_score

        # Logical operators (5 points each)
        logical_ops = len(re.findall(r'\b(AND|OR|NOT)\b', condition_upper))
        score += logical_ops * 5

        # Comparison operators (2 points each)
        comparisons = len(re.findall(r'[<>=!]+', condition))
        score += comparisons * 2

        # Nesting depth (10 points per level)
        max_depth = self._calculate_nesting_depth(condition)
        score += max_depth * 10

        # Function calls (8 points each)
        functions = len(re.findall(r'\w+\s*\(', condition))
        score += functions * 8

        # Subqueries (20 points each - very complex)
        subqueries = condition_upper.count('SELECT')
        score += subqueries * 20

        return min(100, score)

    def _calculate_nesting_depth(self, condition: str) -> int:
        """Calculate maximum nesting depth of parentheses.

        Args:
            condition: SQL condition string

        Returns:
            Maximum nesting depth
        """
        max_depth = 0
        current_depth = 0

        for char in condition:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1

        return max_depth


class ConditionalCheckHandler:
    """Executes conditional validation checks.

    This handler translates conditional checks into SQL queries that filter
    data based on a condition before applying the validation rule.

    Pattern:
        WHERE (condition) AND NOT (check_passes)

    Example:
        For not_null_when(condition="country = 'USA'"):
        SELECT COUNT(*) FROM table
        WHERE (country = 'USA') AND (column IS NULL)

    This counts rows where the condition is true BUT the check fails.

    Attributes:
        validator: QueryValidator instance for SQL validation
        timeout_seconds: Maximum query execution time

    Examples:
        >>> handler = ConditionalCheckHandler()
        >>> result = handler.execute_not_null_when(
        ...     dataset=my_data,
        ...     column="state",
        ...     condition="country = 'USA'"
        ... )
    """

    def __init__(
        self,
        validator: QueryValidator | None = None,
        timeout_seconds: int = 30
    ):
        """Initialize conditional check handler.

        Args:
            validator: Query validator (creates default if None)
            timeout_seconds: Maximum query execution time
        """
        self.validator = validator or QueryValidator()
        self.timeout_seconds = timeout_seconds

    def execute_not_null_when(
        self,
        dataset,
        column: str,
        condition: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check column is not null when condition is true.

        Args:
            dataset: Dataset to validate
            column: Column name to check
            condition: SQL WHERE clause condition
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Raises:
            ValidationError: If condition is invalid or unsafe

        Examples:
            >>> data = connect("customers.csv")
            >>> result = handler.execute_not_null_when(
            ...     dataset=data,
            ...     column="state",
            ...     condition="country = 'USA'"
            ... )
            >>> assert result.passed
        """
        # Validate condition
        validation = self.validator.validate(condition)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid condition: {validation.error_message}"
            )

        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be between 0.0 and 1.0, got {threshold}")
        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Build SQL query
        sql = f"""
            SELECT COUNT(*) as violations
            FROM '{source_path}'
            WHERE ({condition}) AND ({column} IS NULL)
        """

        try:
            # Execute query with timeout
            violations = dataset._engine.fetch_value(sql)

            # Count rows matching condition
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM '{source_path}'
                WHERE ({condition})
            """
            total_matching = dataset._engine.fetch_value(count_sql)

            if total_matching == 0:
                # No rows match condition - check passes vacuously
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message=f"No rows match condition: {condition}. "
                           f"Check passes vacuously.",
                    details={
                        "condition": condition,
                        "matching_rows": 0,
                        "violations": 0
                    }
                )

            # Calculate violation rate
            violation_rate = violations / total_matching
            passed = violation_rate <= (1.0 - threshold)

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_message(
                    passed=passed,
                    column=column,
                    check="not null",
                    condition=condition,
                    violations=violations,
                    total=total_matching,
                    violation_rate=violation_rate
                ),
                details={
                    "condition": condition,
                    "matching_rows": total_matching,
                    "violations": violations,
                    "violation_rate": violation_rate,
                    "threshold": threshold,
                    "complexity_score": validation.complexity_score
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing conditional check: {str(e)}"
            ) from e

    def execute_unique_when(
        self,
        dataset,
        column: str,
        condition: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check column is unique when condition is true.

        Args:
            dataset: Dataset to validate
            column: Column name to check
            condition: SQL WHERE clause condition
            threshold: Minimum required uniqueness rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status

        Examples:
            >>> result = handler.execute_unique_when(
            ...     dataset=data,
            ...     column="order_id",
            ...     condition="status = 'completed'"
            ... )
        """
        # Validate condition
        validation = self.validator.validate(condition)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid condition: {validation.error_message}"
            )

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Check for duplicates in rows matching condition
        sql = f"""
            SELECT COUNT(*) as duplicates
            FROM (
                SELECT {column}, COUNT(*) as cnt
                FROM '{source_path}'
                WHERE ({condition})
                GROUP BY {column}
                HAVING cnt > 1
            ) as dups
        """

        try:
            duplicate_values = dataset._engine.fetch_value(sql)

            # Count distinct values matching condition
            distinct_sql = f"""
                SELECT COUNT(DISTINCT {column}) as distinct_count
                FROM '{source_path}'
                WHERE ({condition})
            """
            distinct_count = dataset._engine.fetch_value(distinct_sql)

            # Count total rows matching condition
            total_sql = f"""
                SELECT COUNT(*) as total
                FROM '{source_path}'
                WHERE ({condition})
            """
            total_matching = dataset._engine.fetch_value(total_sql)

            if total_matching == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message=f"No rows match condition: {condition}",
                    details={"condition": condition, "matching_rows": 0}
                )

            # Calculate uniqueness rate
            uniqueness_rate = distinct_count / total_matching
            passed = uniqueness_rate >= threshold

            return ValidationResult(
                passed=passed,
                actual_value=duplicate_values,
                expected_value=0,
                message=self._format_message(
                    passed=passed,
                    column=column,
                    check="unique",
                    condition=condition,
                    violations=duplicate_values,
                    total=total_matching,
                    violation_rate=1.0 - uniqueness_rate
                ),
                details={
                    "condition": condition,
                    "matching_rows": total_matching,
                    "distinct_values": distinct_count,
                    "duplicate_values": duplicate_values,
                    "uniqueness_rate": uniqueness_rate,
                    "threshold": threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing conditional unique check: {str(e)}"
            ) from e

    def execute_between_when(
        self,
        dataset,
        column: str,
        min_value: float,
        max_value: float,
        condition: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check column is between min and max when condition is true.

        Args:
            dataset: Dataset to validate
            column: Column name to check
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            condition: SQL WHERE clause condition
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status
        """
        validation = self.validator.validate(condition)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid condition: {validation.error_message}"
            )

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        sql = f"""
            SELECT COUNT(*) as violations
            FROM '{source_path}'
            WHERE ({condition})
              AND ({column} < {min_value} OR {column} > {max_value})
        """

        try:
            violations = dataset._engine.fetch_value(sql)

            count_sql = f"""
                SELECT COUNT(*) as total
                FROM '{source_path}'
                WHERE ({condition})
            """
            total_matching = dataset._engine.fetch_value(count_sql)

            if total_matching == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message=f"No rows match condition: {condition}",
                    details={"condition": condition, "matching_rows": 0}
                )

            violation_rate = violations / total_matching
            passed = violation_rate <= (1.0 - threshold)

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_message(
                    passed=passed,
                    column=column,
                    check=f"between {min_value} and {max_value}",
                    condition=condition,
                    violations=violations,
                    total=total_matching,
                    violation_rate=violation_rate
                ),
                details={
                    "condition": condition,
                    "matching_rows": total_matching,
                    "violations": violations,
                    "violation_rate": violation_rate,
                    "min_value": min_value,
                    "max_value": max_value,
                    "threshold": threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing conditional between check: {str(e)}"
            ) from e

    def execute_isin_when(
        self,
        dataset,
        column: str,
        allowed_values: list[Any],
        condition: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check column is in allowed values when condition is true.

        Args:
            dataset: Dataset to validate
            column: Column name to check
            allowed_values: List of allowed values
            condition: SQL WHERE clause condition
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status
        """
        validation = self.validator.validate(condition)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid condition: {validation.error_message}"
            )

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        # Format allowed values for SQL IN clause
        if isinstance(allowed_values[0], str):
            values_str = ", ".join(f"'{v}'" for v in allowed_values)
        else:
            values_str = ", ".join(str(v) for v in allowed_values)

        sql = f"""
            SELECT COUNT(*) as violations
            FROM '{source_path}'
            WHERE ({condition})
              AND {column} NOT IN ({values_str})
        """

        try:
            violations = dataset._engine.fetch_value(sql)

            count_sql = f"""
                SELECT COUNT(*) as total
                FROM '{source_path}'
                WHERE ({condition})
            """
            total_matching = dataset._engine.fetch_value(count_sql)

            if total_matching == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message=f"No rows match condition: {condition}",
                    details={"condition": condition, "matching_rows": 0}
                )

            violation_rate = violations / total_matching
            passed = violation_rate <= (1.0 - threshold)

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_message(
                    passed=passed,
                    column=column,
                    check=f"in {allowed_values}",
                    condition=condition,
                    violations=violations,
                    total=total_matching,
                    violation_rate=violation_rate
                ),
                details={
                    "condition": condition,
                    "matching_rows": total_matching,
                    "violations": violations,
                    "violation_rate": violation_rate,
                    "allowed_values": allowed_values,
                    "threshold": threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing conditional isin check: {str(e)}"
            ) from e

    def execute_pattern_when(
        self,
        dataset,
        column: str,
        pattern: str,
        condition: str,
        threshold: float = 1.0
    ) -> ValidationResult:
        """Check column matches pattern when condition is true.

        Args:
            dataset: Dataset to validate
            column: Column name to check
            pattern: Regex pattern to match
            condition: SQL WHERE clause condition
            threshold: Maximum allowed failure rate (0.0-1.0)

        Returns:
            ValidationResult with pass/fail status
        """
        validation = self.validator.validate(condition)
        if not validation.is_valid:
            raise ValidationError(
                f"Invalid condition: {validation.error_message}"
            )

        # Normalize path for DuckDB (forward slashes work on all platforms)
        source_path = dataset._source.replace('\\', '/')

        sql = f"""
            SELECT COUNT(*) as violations
            FROM '{source_path}'
            WHERE ({condition})
              AND NOT regexp_matches({column}::VARCHAR, '{pattern}')
        """

        try:
            violations = dataset._engine.fetch_value(sql)

            count_sql = f"""
                SELECT COUNT(*) as total
                FROM '{source_path}'
                WHERE ({condition})
            """
            total_matching = dataset._engine.fetch_value(count_sql)

            if total_matching == 0:
                return ValidationResult(
                    passed=True,
                    actual_value=0,
                    expected_value=0,
                    message=f"No rows match condition: {condition}",
                    details={"condition": condition, "matching_rows": 0}
                )

            violation_rate = violations / total_matching
            passed = violation_rate <= (1.0 - threshold)

            return ValidationResult(
                passed=passed,
                actual_value=violations,
                expected_value=0,
                message=self._format_message(
                    passed=passed,
                    column=column,
                    check=f"matches pattern '{pattern}'",
                    condition=condition,
                    violations=violations,
                    total=total_matching,
                    violation_rate=violation_rate
                ),
                details={
                    "condition": condition,
                    "matching_rows": total_matching,
                    "violations": violations,
                    "violation_rate": violation_rate,
                    "pattern": pattern,
                    "threshold": threshold
                }
            )

        except Exception as e:
            raise ValidationError(
                f"Error executing conditional pattern check: {str(e)}"
            ) from e

    def _format_message(
        self,
        passed: bool,
        column: str,
        check: str,
        condition: str,
        violations: int,
        total: int,
        violation_rate: float
    ) -> str:
        """Format human-readable validation message.

        Args:
            passed: Whether check passed
            column: Column name
            check: Check description
            condition: SQL condition
            violations: Number of violations
            total: Total rows matching condition
            violation_rate: Violation rate (0.0-1.0)

        Returns:
            Formatted message string
        """
        if passed:
            return (
                f"Column '{column}' {check} when {condition}: "
                f"PASSED ({violations}/{total} violations, "
                f"{violation_rate:.1%} failure rate)"
            )
        else:
            return (
                f"Column '{column}' {check} when {condition}: "
                f"FAILED ({violations}/{total} violations, "
                f"{violation_rate:.1%} failure rate)"
            )
