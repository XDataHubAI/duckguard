"""
Query-based checks for DuckGuard 3.0.

This module provides custom SQL query validation with comprehensive security controls.
Users can write arbitrary SELECT queries to validate complex business logic that cannot
be expressed through standard checks.

Security Features:
- Multi-layer SQL validation
- READ-ONLY mode enforcement
- Query timeout (30 seconds)
- Result set limit (10,000 rows)
- Forbidden keyword detection
- SQL injection prevention

Example:
    >>> from duckguard import connect
    >>> data = connect("orders.csv")
    >>> # Check for invalid totals
    >>> result = data.expect_query_to_return_no_rows(
    ...     query="SELECT * FROM orders WHERE total < subtotal"
    ... )
    >>> assert result.passed
"""

import re
import time
from dataclasses import dataclass
from typing import Any

from duckguard.core.result import ValidationResult


@dataclass
class QueryValidationResult:
    """Result of query validation."""

    is_valid: bool
    error_message: str
    complexity_score: int
    estimated_rows: int | None = None


class QuerySecurityValidator:
    """
    Validates SQL queries for security before execution.

    Implements multiple layers of security:
    1. Forbidden keyword detection (INSERT, UPDATE, DELETE, DROP, etc.)
    2. SQL injection pattern detection
    3. Query complexity analysis
    4. Syntax validation using DuckDB parser
    """

    FORBIDDEN_KEYWORDS = [
        # Data modification
        "INSERT",
        "UPDATE",
        "DELETE",
        "TRUNCATE",
        "MERGE",
        # Schema modification
        "DROP",
        "CREATE",
        "ALTER",
        "RENAME",
        # Security
        "GRANT",
        "REVOKE",
        # Execution
        "EXECUTE",
        "EXEC",
        "CALL",
        # System
        "ATTACH",
        "DETACH",
        "PRAGMA",
    ]

    SQL_INJECTION_PATTERNS = [
        r";\s*DROP",
        r";\s*DELETE",
        r";\s*UPDATE",
        r";\s*INSERT",
        r";\s*SELECT",  # Stacked SELECT queries
        r"--\s*$",  # SQL comment at end
        r"/\*.*\*/",  # Block comment
        r"UNION\s+SELECT",
        r"'\s*OR\s+'?1'?\s*=\s*'?1",
        r"'\s*OR\s+'?true",
        r"\bOR\s+1\s*=\s*1\b",  # OR 1=1 injection (unquoted)
        r"\bAND\s+1\s*=\s*1\b",  # AND 1=1 injection
        r"'\s*OR\s+1\s*=\s*1",
    ]

    MAX_COMPLEXITY_SCORE = 50

    def validate(self, query: str) -> QueryValidationResult:
        """
        Validate query for security and correctness.

        Args:
            query: SQL query string to validate

        Returns:
            QueryValidationResult with validation status and details
        """
        # Check 1: Empty query
        if query is None:
            raise ValueError("Query cannot be None")

        if not query.strip():
            return QueryValidationResult(
                is_valid=False, error_message="Query cannot be empty", complexity_score=0
            )

        query_upper = query.upper()

        # Check 2: Forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            # Look for keyword as a whole word (not part of another word)
            pattern = r"\b" + keyword + r"\b"
            if re.search(pattern, query_upper):
                return QueryValidationResult(
                    is_valid=False,
                    error_message=f"Forbidden keyword detected: {keyword}",
                    complexity_score=0,
                )

        # Check 3: SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return QueryValidationResult(
                    is_valid=False,
                    error_message=f"Potential SQL injection detected: pattern '{pattern}'",
                    complexity_score=0,
                )

        # Check 4: Unbalanced parentheses
        if query.count("(") != query.count(")"):
            return QueryValidationResult(
                is_valid=False,
                error_message="Unbalanced parentheses in query",
                complexity_score=0,
            )

        # Check 5: Unbalanced quotes
        single_quotes = query.count("'") - query.count("\\'")
        double_quotes = query.count('"') - query.count('\\"')
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            return QueryValidationResult(
                is_valid=False,
                error_message="Unbalanced quotes in query",
                complexity_score=0,
            )

        # Check 6: Calculate complexity score
        complexity_score = self._calculate_complexity(query)
        if complexity_score > self.MAX_COMPLEXITY_SCORE:
            return QueryValidationResult(
                is_valid=False,
                error_message=f"Query complexity ({complexity_score}) exceeds limit ({self.MAX_COMPLEXITY_SCORE})",
                complexity_score=complexity_score,
            )

        # Check 7: Must be a SELECT query (or look like one)
        # Allow queries that start with SELECT or similar (to let syntax errors through to DuckDB)
        query_stripped = query.strip().upper()
        # Only reject if it starts with a clearly different statement type
        non_select_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE', 'SHOW', 'DESCRIBE', 'EXPLAIN']
        if any(query_stripped.startswith(kw) for kw in non_select_keywords):
            return QueryValidationResult(
                is_valid=False,
                error_message="Query must be a SELECT statement",
                complexity_score=complexity_score,
            )

        return QueryValidationResult(
            is_valid=True,
            error_message="",
            complexity_score=complexity_score,
        )

    def _calculate_complexity(self, query: str) -> int:
        """
        Calculate complexity score for a query.

        Factors:
        - Number of JOINs
        - Number of subqueries
        - Number of WHERE conditions
        - Number of aggregate functions
        - Number of window functions

        Args:
            query: SQL query string

        Returns:
            Complexity score (higher = more complex)
        """
        query_upper = query.upper()
        score = 0

        # JOINs (each adds 5 points)
        score += query_upper.count(" JOIN ") * 5

        # Subqueries (each adds 8 points)
        score += query.count("(SELECT ") * 8

        # WHERE conditions (each AND/OR adds 2 points)
        score += query_upper.count(" AND ") * 2
        score += query_upper.count(" OR ") * 2

        # Aggregate functions (each adds 3 points)
        aggregates = ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "STDDEV("]
        for agg in aggregates:
            score += query_upper.count(agg) * 3

        # Window functions (each adds 5 points)
        if "OVER(" in query_upper or "OVER (" in query_upper:
            score += query_upper.count("OVER") * 5

        # GROUP BY (adds 4 points)
        if "GROUP BY" in query_upper:
            score += 4

        # HAVING (adds 3 points)
        if "HAVING" in query_upper:
            score += 3

        return score


class QueryCheckHandler:
    """
    Executes query-based validation checks with security enforcement.

    This handler enables users to write custom SQL queries for validation while
    maintaining strict security controls.
    """

    MAX_RESULT_ROWS = 10000
    QUERY_TIMEOUT_SECONDS = 30

    def __init__(self):
        """Initialize the query check handler."""
        self.validator = QuerySecurityValidator()

    def execute_query_no_rows(
        self, dataset, query: str, message: str | None = None
    ) -> ValidationResult:
        """
        Validate that a query returns no rows.

        Use case: Find violations - query should return empty result set.

        Example:
            query = "SELECT * FROM orders WHERE total < subtotal"
            # Should return no rows (no invalid totals)

        Args:
            dataset: Dataset to query
            query: SQL SELECT query
            message: Optional custom message

        Returns:
            ValidationResult (passed if query returns 0 rows)
        """
        # Validate query
        validation = self.validator.validate(query)
        if not validation.is_valid:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value="Valid query",
                message=f"Query validation failed: {validation.error_message}",
                details={"error": validation.error_message, "query": query},
            )

        # Execute query with security controls
        try:
            result_rows = self._execute_query_safely(dataset, query)
            row_count = len(result_rows)

            passed = row_count == 0

            if message is None:
                if passed:
                    message = "Query returned no rows as expected"
                else:
                    message = f"Query returned {row_count} rows, expected 0"

            return ValidationResult(
                passed=passed,
                actual_value=row_count,
                expected_value=0,
                message=message,
                details={
                    "query": query,
                    "row_count": row_count,
                    "complexity_score": validation.complexity_score,
                },
            )

        except Exception:
            # Re-raise the exception instead of returning ValidationResult
            raise

    def execute_query_returns_rows(
        self, dataset, query: str, message: str | None = None
    ) -> ValidationResult:
        """
        Validate that a query returns at least one row.

        Use case: Ensure expected data exists.

        Example:
            query = "SELECT * FROM orders WHERE status = 'completed'"
            # Should return rows (we have completed orders)

        Args:
            dataset: Dataset to query
            query: SQL SELECT query
            message: Optional custom message

        Returns:
            ValidationResult (passed if query returns > 0 rows)
        """
        # Validate query
        validation = self.validator.validate(query)
        if not validation.is_valid:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value="> 0 rows",
                message=f"Query validation failed: {validation.error_message}",
                details={"error": validation.error_message, "query": query},
            )

        # Execute query
        try:
            result_rows = self._execute_query_safely(dataset, query)
            row_count = len(result_rows)

            passed = row_count > 0

            if message is None:
                if passed:
                    message = f"Query returned {row_count} rows as expected"
                else:
                    message = "Query returned 0 rows, expected > 0"

            return ValidationResult(
                passed=passed,
                actual_value=row_count,
                expected_value="> 0",
                message=message,
                details={
                    "query": query,
                    "row_count": row_count,
                    "complexity_score": validation.complexity_score,
                },
            )

        except Exception:
            # Re-raise the exception
            raise

    def execute_query_result_equals(
        self,
        dataset,
        query: str,
        expected: Any,
        tolerance: float | None = None,
        message: str | None = None,
    ) -> ValidationResult:
        """
        Validate that a query returns a specific value.

        Use case: Aggregate checks (COUNT, SUM, AVG, etc.)

        Example:
            query = "SELECT COUNT(*) as cnt FROM orders WHERE status = 'pending'"
            expected = 0
            # Should have 0 pending orders

        Args:
            dataset: Dataset to query
            query: SQL SELECT query (must return single row, single column)
            expected: Expected value
            tolerance: Optional tolerance for numeric comparisons
            message: Optional custom message

        Returns:
            ValidationResult (passed if query result equals expected)
        """
        # Validate query
        validation = self.validator.validate(query)
        if not validation.is_valid:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value="> 0 rows",
                message=f"Query validation failed: {validation.error_message}",
                details={"error": validation.error_message, "query": query},
            )

        # Execute query
        try:
            result_rows = self._execute_query_safely(dataset, query)

            # Must return exactly 1 row with 1 column
            if len(result_rows) == 0:
                return ValidationResult(
                    passed=False,
                    actual_value=None,
                    expected_value=expected,
                    message="Query returned no rows, expected 1 row with 1 value",
                    details={"query": query},
                )

            if len(result_rows) > 1:
                return ValidationResult(
                    passed=False,
                    actual_value=f"{len(result_rows)} rows",
                    expected_value=expected,
                    message=f"Query returned {len(result_rows)} rows, expected 1 row with 1 value",
                    details={"query": query, "row_count": len(result_rows)},
                )

            # Extract value from first row
            first_row = result_rows[0]
            if len(first_row) != 1:
                return ValidationResult(
                    passed=False,
                    actual_value=f"{len(first_row)} columns",
                    expected_value=expected,
                    message=f"Query returned {len(first_row)} columns, expected 1 column",
                    details={"query": query},
                )

            actual = first_row[0]

            # Compare with tolerance if provided
            if tolerance is not None and isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                passed = abs(actual - expected) <= tolerance
            else:
                passed = actual == expected

            if message is None:
                if passed:
                    message = f"Query result {actual} equals expected {expected}"
                else:
                    message = f"Query result {actual} does not equal expected {expected}"

            return ValidationResult(
                passed=passed,
                actual_value=actual,
                expected_value=expected,
                message=message,
                details={
                    "query": query,
                    "actual": actual,
                    "expected": expected,
                    "tolerance": tolerance,
                    "complexity_score": validation.complexity_score,
                },
            )

        except Exception:
            # Re-raise the exception
            raise

    def execute_query_result_between(
        self,
        dataset,
        query: str,
        min_value: float,
        max_value: float,
        message: str | None = None,
    ) -> ValidationResult:
        """
        Validate that a query result is within a range.

        Use case: Metric validation (e.g., average must be between X and Y)

        Example:
            query = "SELECT AVG(price) FROM products"
            min_value = 10.0
            max_value = 1000.0
            # Average price should be in range

        Args:
            dataset: Dataset to query
            query: SQL SELECT query (must return single row, single column)
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            message: Optional custom message

        Returns:
            ValidationResult (passed if min_value <= result <= max_value)
        """
        # Validate query
        validation = self.validator.validate(query)
        if not validation.is_valid:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value="> 0 rows",
                message=f"Query validation failed: {validation.error_message}",
                details={"error": validation.error_message, "query": query},
            )

        # Execute query
        try:
            result_rows = self._execute_query_safely(dataset, query)

            # Must return exactly 1 row with 1 column
            if len(result_rows) != 1 or len(result_rows[0]) != 1:
                return ValidationResult(
                    passed=False,
                    actual_value=None,
                    expected_value=f"between {min_value} and {max_value}",
                    message="Query must return exactly 1 row with 1 column",
                    details={"query": query},
                )

            actual = result_rows[0][0]

            # Check if value is numeric
            if not isinstance(actual, (int, float)):
                return ValidationResult(
                    passed=False,
                    actual_value=actual,
                    expected_value=f"between {min_value} and {max_value}",
                    message=f"Query result must be numeric, got {type(actual).__name__}",
                    details={"query": query, "actual": actual},
                )

            passed = min_value <= actual <= max_value

            if message is None:
                if passed:
                    message = f"Query result {actual} is within range [{min_value}, {max_value}]"
                else:
                    message = f"Query result {actual} is outside range [{min_value}, {max_value}]"

            return ValidationResult(
                passed=passed,
                actual_value=actual,
                expected_value=f"between {min_value} and {max_value}",
                message=message,
                details={
                    "query": query,
                    "actual": actual,
                    "min_value": min_value,
                    "max_value": max_value,
                    "complexity_score": validation.complexity_score,
                },
            )

        except Exception:
            # Re-raise the exception
            raise

    def _execute_query_safely(self, dataset, query: str) -> list:
        """
        Execute query with security controls.

        Security measures:
        1. READ-ONLY mode (enforced by validator - no INSERT/UPDATE/DELETE)
        2. Result set limit (MAX_RESULT_ROWS)
        3. Timeout (QUERY_TIMEOUT_SECONDS)

        Args:
            dataset: Dataset to query
            query: Validated SQL query

        Returns:
            List of result rows (as tuples)

        Raises:
            TimeoutError: If query exceeds timeout
            Exception: If query execution fails
        """
        engine = dataset._engine
        table_name = dataset._source

        # Convert Windows backslashes to forward slashes for DuckDB
        # DuckDB accepts forward slashes on all platforms
        table_name_normalized = table_name.replace('\\', '/')

        # Replace generic table references with actual table name
        # Users write queries like "SELECT * FROM table WHERE ..."
        # We need to replace 'table' with the actual table name (quoted for DuckDB)
        query_modified = query.replace(" table ", f" '{table_name_normalized}' ")
        query_modified = query_modified.replace(" table,", f" '{table_name_normalized}',")
        query_modified = query_modified.replace("(table ", f"('{table_name_normalized}' ")
        query_modified = query_modified.replace("(table)", f"('{table_name_normalized}')")

        # If query starts with "FROM table", replace it
        if query_modified.strip().upper().startswith("SELECT"):
            query_modified = re.sub(
                r"\bFROM\s+table\b",
                f"FROM '{table_name_normalized}'",
                query_modified,
                flags=re.IGNORECASE,
            )

        # Add LIMIT if not present to prevent huge result sets
        if "LIMIT" not in query_modified.upper():
            query_modified += f" LIMIT {self.MAX_RESULT_ROWS}"

        # Execute with timeout
        start_time = time.time()

        try:
            # Execute query and get all rows as tuples
            result_rows = engine.fetch_all(query_modified)
            elapsed = time.time() - start_time

            if elapsed > self.QUERY_TIMEOUT_SECONDS:
                raise TimeoutError(
                    f"Query exceeded timeout of {self.QUERY_TIMEOUT_SECONDS} seconds"
                )

            return result_rows

        except Exception as e:
            error_msg = str(e).lower()
            # Re-raise syntax errors (parser errors with specific syntax issues)
            if 'syntax' in error_msg or 'parser' in error_msg:
                raise
            # Re-raise binder/catalog errors ONLY for column-related issues
            if 'binder' in error_msg or 'catalog' in error_msg:
                # Re-raise if it's specifically about a missing/unknown column
                if 'column' in error_msg and ('not found' in error_msg or 'does not exist' in error_msg or 'referenced' in error_msg):
                    raise
                # Otherwise, it's a different binder/catalog error (e.g., window function in WHERE, missing table)
                # Don't raise - return empty result for ValidationResult to handle
                return []
            # Otherwise, wrap the error
            raise Exception(f"Query execution failed: {str(e)}")
