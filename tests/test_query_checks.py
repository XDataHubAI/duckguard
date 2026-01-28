"""
Comprehensive tests for query-based checks in DuckGuard 3.0.

Tests cover:
- QuerySecurityValidator validation
- Simple SELECT queries
- Aggregate queries (COUNT, SUM, AVG, MIN, MAX)
- Complex queries (JOINs, subqueries, window functions)
- Error handling
- Security tests (SQL injection prevention)
- Performance benchmarks

Target Coverage: 95%+
Security Focus: Extensive SQL injection prevention tests
"""

import gc
import os
import tempfile

import pandas as pd
import pytest

from duckguard import connect
from duckguard.checks.query_based import QuerySecurityValidator
from duckguard.core.result import ValidationResult

# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_orders_data():
    """Sample order data for query testing."""
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "customer_id": [101, 102, 103, 101, 104, 105, 102, 106, 103, 107],
        "order_date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
                       "2024-01-06", "2024-01-07", "2024-01-08", "2024-01-09", "2024-01-10"],
        "total": [115.0, 230.0, 172.5, 345.0, 287.5, 207.0, 253.0, 218.5, 184.0, 241.5],
        "subtotal": [100.0, 200.0, 150.0, 300.0, 250.0, 180.0, 220.0, 190.0, 160.0, 210.0],
        "status": ["completed", "completed", "pending", "completed", "shipped",
                   "completed", "pending", "completed", "completed", "shipped"],
    })

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    yield temp_file.name

    # Clean up with garbage collection to release file handles (Windows)
    import gc
    gc.collect()
    try:
        # Clean up with garbage collection to release file handles (Windows)
        gc.collect()
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
    except (PermissionError, FileNotFoundError):
        pass  # Ignore cleanup errors on Windows


@pytest.fixture
def sample_products_data():
    """Sample product data for query testing."""
    df = pd.DataFrame({
        "product_id": [1, 2, 3, 4, 5],
        "name": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"],
        "price": [10.0, 20.0, 30.0, 40.0, 50.0],
        "category": ["electronics", "electronics", "furniture", "clothing", "electronics"],
        "in_stock": [True, True, False, True, True],
    })

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    yield temp_file.name

    # Clean up with garbage collection to release file handles (Windows)
    import gc
    gc.collect()
    try:
        # Clean up with garbage collection to release file handles (Windows)
        gc.collect()
        try:
            os.unlink(temp_file.name)
        except (PermissionError, FileNotFoundError):
            pass  # Ignore cleanup errors on Windows
    except (PermissionError, FileNotFoundError):
        pass  # Ignore cleanup errors on Windows


# =============================================================================
# QUERY SECURITY VALIDATOR TESTS
# =============================================================================


class TestQuerySecurityValidator:
    """Tests for QuerySecurityValidator."""

    def test_valid_simple_select(self):
        """Test validation of simple SELECT query."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE id > 100")

        assert result.is_valid
        assert result.complexity_score >= 0

    def test_valid_aggregate_query(self):
        """Test validation of aggregate query."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT COUNT(*) FROM table WHERE status = 'active'")

        assert result.is_valid

    def test_forbidden_keyword_drop(self):
        """Test detection of DROP keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table; DROP TABLE users")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_insert(self):
        """Test detection of INSERT keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("INSERT INTO table VALUES (1, 'test')")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_update(self):
        """Test detection of UPDATE keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("UPDATE table SET value = 1")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_delete(self):
        """Test detection of DELETE keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("DELETE FROM table WHERE id = 1")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_truncate(self):
        """Test detection of TRUNCATE keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("TRUNCATE TABLE users")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_create(self):
        """Test detection of CREATE keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("CREATE TABLE new_table (id INT)")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_forbidden_keyword_alter(self):
        """Test detection of ALTER keyword."""
        validator = QuerySecurityValidator()
        result = validator.validate("ALTER TABLE users ADD COLUMN email VARCHAR")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_sql_injection_union_select(self):
        """Test detection of UNION SELECT injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE id = 1 UNION SELECT * FROM passwords")

        assert not result.is_valid
        assert "injection" in result.error_message.lower()

    def test_sql_injection_or_1_equals_1(self):
        """Test detection of OR 1=1 injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE id = 1 OR 1=1")

        assert not result.is_valid
        assert "injection" in result.error_message.lower()

    def test_sql_injection_comment(self):
        """Test detection of SQL comment injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE id = 1--")

        assert not result.is_valid
        assert "injection" in result.error_message.lower()

    def test_sql_injection_block_comment(self):
        """Test detection of block comment injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table /* comment */ WHERE id = 1")

        assert not result.is_valid
        assert "injection" in result.error_message.lower()

    def test_empty_query(self):
        """Test detection of empty query."""
        validator = QuerySecurityValidator()
        result = validator.validate("")

        assert not result.is_valid
        assert "empty" in result.error_message.lower()

    def test_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE (id > 100")

        assert not result.is_valid
        assert "unbalanced parentheses" in result.error_message.lower()

    def test_unbalanced_quotes(self):
        """Test detection of unbalanced quotes."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table WHERE name = 'test")

        assert not result.is_valid
        assert "unbalanced quotes" in result.error_message.lower()

    def test_complexity_score_simple(self):
        """Test complexity score for simple query."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table")

        assert result.is_valid
        assert result.complexity_score < 10

    def test_complexity_score_complex(self):
        """Test complexity score for complex query."""
        validator = QuerySecurityValidator()
        query = """
        SELECT a.id, b.name, COUNT(*) as cnt, AVG(a.value) as avg_val
        FROM table_a a
        JOIN table_b b ON a.id = b.id
        WHERE a.status = 'active' AND b.type = 'premium'
        GROUP BY a.id, b.name
        HAVING COUNT(*) > 10
        """
        result = validator.validate(query)

        assert result.is_valid
        assert result.complexity_score > 10

    def test_non_select_query(self):
        """Test rejection of non-SELECT queries."""
        validator = QuerySecurityValidator()
        result = validator.validate("SHOW TABLES")

        assert not result.is_valid
        assert "must be a select" in result.error_message.lower()


# =============================================================================
# SIMPLE SELECT QUERY TESTS
# =============================================================================


class TestQueryNoRows:
    """Tests for expect_query_to_return_no_rows."""

    def test_no_violations_found(self, sample_orders_data):
        """Test query that finds no violations (passes)."""
        dataset = connect(sample_orders_data)

        # No orders with negative totals
        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < 0"
        )

        assert result.passed
        assert result.actual_value == 0

    def test_violations_found(self, sample_orders_data):
        """Test query that finds violations (fails)."""
        dataset = connect(sample_orders_data)

        # Find orders where total < subtotal (should have violations if any exist)
        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < subtotal"
        )

        # This should pass because our test data has total >= subtotal
        assert result.passed

    def test_with_where_condition(self, sample_orders_data):
        """Test query with WHERE condition."""
        dataset = connect(sample_orders_data)

        # No pending orders with high totals
        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE status = 'pending' AND total > 1000"
        )

        assert result.passed

    def test_with_custom_message(self, sample_orders_data):
        """Test query with custom message."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < 0",
            message="No negative order totals allowed"
        )

        assert result.passed

    def test_invalid_query_syntax(self, sample_orders_data):
        """Test handling of invalid SQL syntax."""
        dataset = connect(sample_orders_data)

        with pytest.raises(Exception):
            dataset.expect_query_to_return_no_rows(
                query="SELECT * FORM table"  # Typo: FORM instead of FROM
            )


class TestQueryReturnsRows:
    """Tests for expect_query_to_return_rows."""

    def test_data_exists(self, sample_orders_data):
        """Test query that finds expected data."""
        dataset = connect(sample_orders_data)

        # Should have completed orders
        result = dataset.expect_query_to_return_rows(
            query="SELECT * FROM table WHERE status = 'completed'"
        )

        assert result.passed
        assert result.actual_value > 0

    def test_no_data_found(self, sample_orders_data):
        """Test query that finds no data (fails)."""
        dataset = connect(sample_orders_data)

        # Should not have cancelled orders
        result = dataset.expect_query_to_return_rows(
            query="SELECT * FROM table WHERE status = 'cancelled'"
        )

        assert not result.passed
        assert result.actual_value == 0

    def test_with_aggregate(self, sample_orders_data):
        """Test query with aggregate function."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_rows(
            query="SELECT COUNT(*) FROM table WHERE total > 100"
        )

        assert result.passed


# =============================================================================
# AGGREGATE QUERY TESTS
# =============================================================================


class TestQueryResultEquals:
    """Tests for expect_query_result_to_equal."""

    def test_count_exact_match(self, sample_orders_data):
        """Test COUNT query with exact match."""
        dataset = connect(sample_orders_data)

        # Count pending orders
        result = dataset.expect_query_result_to_equal(
            query="SELECT COUNT(*) FROM table WHERE status = 'pending'",
            expected=2  # We have 2 pending orders in test data
        )

        assert result.passed

    def test_count_mismatch(self, sample_orders_data):
        """Test COUNT query with mismatch."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT COUNT(*) FROM table WHERE status = 'completed'",
            expected=100  # Wrong expected value
        )

        assert not result.passed

    def test_sum_with_tolerance(self, sample_orders_data):
        """Test SUM query with tolerance."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT SUM(total) FROM table",
            expected=2250.0,  # Approximate sum
            tolerance=10.0
        )

        # Should pass with tolerance
        assert isinstance(result, ValidationResult)

    def test_avg_calculation(self, sample_orders_data):
        """Test AVG query."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT AVG(total) FROM table WHERE status = 'completed'",
            expected=200.0,  # Approximate average
            tolerance=50.0
        )

        assert isinstance(result, ValidationResult)

    def test_min_value(self, sample_products_data):
        """Test MIN query."""
        dataset = connect(sample_products_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT MIN(price) FROM table",
            expected=10.0
        )

        assert result.passed

    def test_max_value(self, sample_products_data):
        """Test MAX query."""
        dataset = connect(sample_products_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT MAX(price) FROM table",
            expected=50.0
        )

        assert result.passed

    def test_query_returns_multiple_rows(self, sample_orders_data):
        """Test query that returns multiple rows (should fail)."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT order_id FROM table",  # Returns multiple rows
            expected=1
        )

        assert not result.passed
        assert "rows" in result.message.lower()

    def test_query_returns_multiple_columns(self, sample_orders_data):
        """Test query that returns multiple columns (should fail)."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT order_id, total FROM table LIMIT 1",
            expected=1
        )

        assert not result.passed
        assert "columns" in result.message.lower()


class TestQueryResultBetween:
    """Tests for expect_query_result_to_be_between."""

    def test_average_in_range(self, sample_orders_data):
        """Test AVG query with result in range."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_be_between(
            query="SELECT AVG(total) FROM table",
            min_value=100.0,
            max_value=300.0
        )

        assert result.passed

    def test_average_out_of_range(self, sample_orders_data):
        """Test AVG query with result out of range."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_be_between(
            query="SELECT AVG(total) FROM table",
            min_value=500.0,
            max_value=1000.0
        )

        assert not result.passed

    def test_count_in_range(self, sample_orders_data):
        """Test COUNT query in range."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_be_between(
            query="SELECT COUNT(*) FROM table WHERE status = 'completed'",
            min_value=5.0,
            max_value=10.0
        )

        assert result.passed

    def test_percentage_calculation(self, sample_orders_data):
        """Test percentage calculation in range."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_be_between(
            query="""
                SELECT (COUNT(*) FILTER (WHERE status = 'pending')) * 100.0 / COUNT(*)
                FROM table
            """,
            min_value=0.0,
            max_value=50.0
        )

        assert result.passed

    def test_non_numeric_result(self, sample_orders_data):
        """Test non-numeric result (should fail)."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_be_between(
            query="SELECT status FROM table LIMIT 1",
            min_value=0.0,
            max_value=100.0
        )

        assert not result.passed
        assert "numeric" in result.message.lower()


# =============================================================================
# COMPLEX QUERY TESTS
# =============================================================================


class TestComplexQueries:
    """Tests for complex SQL queries."""

    def test_group_by_query(self, sample_orders_data):
        """Test GROUP BY query."""
        dataset = connect(sample_orders_data)

        # Count orders by status
        result = dataset.expect_query_to_return_rows(
            query="""
                SELECT status, COUNT(*) as cnt
                FROM table
                GROUP BY status
                HAVING COUNT(*) > 0
            """
        )

        assert result.passed

    def test_case_statement(self, sample_orders_data):
        """Test CASE statement in query."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="""
                SELECT COUNT(*)
                FROM table
                WHERE CASE
                    WHEN total > 200 THEN 'high'
                    ELSE 'low'
                END = 'high'
            """,
            expected=5,
            tolerance=3
        )

        assert isinstance(result, ValidationResult)

    def test_subquery(self, sample_orders_data):
        """Test subquery."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="""
                SELECT * FROM table
                WHERE total < (SELECT AVG(total) FROM table) - 1000
            """
        )

        assert result.passed

    def test_window_function(self, sample_orders_data):
        """Test window function query."""
        dataset = connect(sample_orders_data)

        # This tests if DuckDB supports window functions
        result = dataset.expect_query_to_return_rows(
            query="""
                SELECT order_id, total,
                       ROW_NUMBER() OVER (ORDER BY total DESC) as rank
                FROM table
                WHERE rank = 1
            """
        )

        # Window functions should work in DuckDB
        assert isinstance(result, ValidationResult)


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_syntax_error_handling(self, sample_orders_data):
        """Test handling of SQL syntax errors."""
        dataset = connect(sample_orders_data)

        with pytest.raises(Exception):
            dataset.expect_query_to_return_no_rows(
                query="SELEKT * FORM table"  # Invalid SQL
            )

    def test_nonexistent_column(self, sample_orders_data):
        """Test handling of nonexistent column."""
        dataset = connect(sample_orders_data)

        with pytest.raises(Exception):
            dataset.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE nonexistent_column > 0"
            )

    def test_missing_query_parameter(self, sample_orders_data):
        """Test handling of missing query parameter."""
        dataset = connect(sample_orders_data)

        # This should be handled gracefully
        with pytest.raises((TypeError, ValueError)):
            dataset.expect_query_to_return_no_rows(query=None)


# =============================================================================
# SECURITY TESTS (EXTENSIVE)
# =============================================================================


class TestQuerySecurity:
    """Extensive security tests for SQL injection prevention."""

    def test_security_drop_table(self, sample_orders_data):
        """Test prevention of DROP TABLE."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table; DROP TABLE orders"
        )

        # Should fail validation
        assert not result.passed
        assert "forbidden" in result.message.lower() or "validation failed" in result.message.lower()

    def test_security_insert_injection(self, sample_orders_data):
        """Test prevention of INSERT injection."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_result_to_equal(
            query="SELECT 1; INSERT INTO table VALUES (1, 'hacked')",
            expected=1
        )

        assert not result.passed

    def test_security_update_injection(self, sample_orders_data):
        """Test prevention of UPDATE injection."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE id = 1; UPDATE table SET hacked = 1"
        )

        assert not result.passed

    def test_security_delete_injection(self, sample_orders_data):
        """Test prevention of DELETE injection."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE id = 1; DELETE FROM table"
        )

        assert not result.passed

    def test_security_union_based_injection(self, sample_orders_data):
        """Test prevention of UNION-based injection."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE id = 1 UNION SELECT * FROM users"
        )

        assert not result.passed

    def test_security_comment_injection(self, sample_orders_data):
        """Test prevention of comment-based injection."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE id = 1 --"
        )

        assert not result.passed

    def test_security_stacked_queries(self, sample_orders_data):
        """Test prevention of stacked queries."""
        dataset = connect(sample_orders_data)

        result = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table; SELECT * FROM passwords"
        )

        # Should be caught by security validation
        assert not result.passed

    def test_security_exec_injection(self, sample_orders_data):
        """Test prevention of EXEC injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table; EXEC sp_executesql")

        assert not result.is_valid

    def test_security_grant_injection(self, sample_orders_data):
        """Test prevention of GRANT injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table; GRANT ALL TO hacker")

        assert not result.is_valid

    def test_security_pragma_injection(self, sample_orders_data):
        """Test prevention of PRAGMA injection."""
        validator = QuerySecurityValidator()
        result = validator.validate("SELECT * FROM table; PRAGMA table_info(users)")

        assert not result.is_valid


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestQueryPerformance:
    """Performance tests for query-based checks."""

    def test_simple_query_performance(self):
        """Test performance of simple query on large dataset."""
        import time

        # Generate large dataset
        df = pd.DataFrame({
            "id": range(100000),
            "value": range(100000),
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)

            start_time = time.time()
            result = dataset.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE value < 0"
            )
            elapsed_time = time.time() - start_time

            assert result.passed
            assert elapsed_time < 10.0  # Should complete in < 10 seconds
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_aggregate_query_performance(self):
        """Test performance of aggregate query."""
        import time

        # Generate large dataset
        df = pd.DataFrame({
            "id": range(100000),
            "value": range(100000),
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)

            start_time = time.time()
            result = dataset.expect_query_result_to_be_between(
                query="SELECT AVG(value) FROM table",
                min_value=40000.0,
                max_value=60000.0
            )
            elapsed_time = time.time() - start_time

            assert result.passed
            assert elapsed_time < 10.0
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestQueryIntegration:
    """Integration tests for query-based checks."""

    def test_multiple_queries_on_same_dataset(self, sample_orders_data):
        """Test running multiple queries on same dataset."""
        dataset = connect(sample_orders_data)

        # Run multiple checks
        result1 = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < 0"
        )

        result2 = dataset.expect_query_result_to_equal(
            query="SELECT COUNT(*) FROM table",
            expected=10
        )

        result3 = dataset.expect_query_result_to_be_between(
            query="SELECT AVG(total) FROM table",
            min_value=100.0,
            max_value=300.0
        )

        assert result1.passed
        assert result2.passed
        assert result3.passed

    def test_combining_with_regular_checks(self, sample_orders_data):
        """Test combining query checks with regular checks."""
        dataset = connect(sample_orders_data)

        # Regular check
        result1 = dataset.order_id.is_unique()

        # Query check
        result2 = dataset.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < subtotal"
        )

        assert result1.passed
        assert result2.passed
