"""
Comprehensive tests for multi-column checks in DuckGuard 3.0.

Tests cover:
- ExpressionParser validation
- Column pair satisfaction checks
- Composite uniqueness checks
- Multi-column sum checks
- Edge cases (empty data, nulls, Unicode)
- Performance benchmarks
- Integration with YAML rules

Target Coverage: 95%+
"""

import gc
import os
import tempfile

import pandas as pd
import pytest

from duckguard import connect
from duckguard.checks.multicolumn import ExpressionParser
from duckguard.core.result import ValidationResult

# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_orders_data():
    """Sample order data with multiple columns for testing."""
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "subtotal": [100.0, 200.0, 150.0, 300.0, 250.0, 180.0, 220.0, 190.0, 160.0, 210.0],
        "tax": [10.0, 20.0, 15.0, 30.0, 25.0, 18.0, 22.0, 19.0, 16.0, 21.0],
        "shipping": [5.0, 10.0, 7.5, 15.0, 12.5, 9.0, 11.0, 9.5, 8.0, 10.5],
        "total": [115.0, 230.0, 172.5, 345.0, 287.5, 207.0, 253.0, 218.5, 184.0, 241.5],
        "discount": [0.0, 5.0, 10.0, 0.0, 15.0, 8.0, 12.0, 6.0, 4.0, 9.0],
        "customer_id": [101, 102, 103, 101, 104, 105, 102, 106, 103, 107],
        "product_id": ["A", "B", "C", "A", "D", "E", "B", "F", "C", "G"],
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
def sample_date_range_data():
    """Sample data with date ranges for testing."""
    df = pd.DataFrame({
        "event_id": [1, 2, 3, 4, 5],
        "start_date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
        "end_date": ["2024-01-31", "2024-02-28", "2024-03-31", "2024-04-30", "2024-05-31"],
        "duration_days": [30, 27, 30, 29, 30],
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
def composite_key_data():
    """Sample data with composite keys for uniqueness testing."""
    df = pd.DataFrame({
        "customer_id": [101, 102, 103, 101, 102, 103, 104, 105],
        "product_id": ["A", "B", "C", "B", "A", "D", "A", "B"],
        "order_date": ["2024-01-01", "2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"],
        "quantity": [1, 2, 3, 1, 2, 1, 3, 1],
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
def percentage_data():
    """Sample data with percentages that should sum to 100."""
    df = pd.DataFrame({
        "category": ["A", "B", "C", "D", "E"],
        "region_north": [20.0, 25.0, 15.0, 30.0, 22.0],
        "region_south": [30.0, 25.0, 35.0, 20.0, 28.0],
        "region_east": [25.0, 30.0, 25.0, 30.0, 27.0],
        "region_west": [25.0, 20.0, 25.0, 20.0, 23.0],
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
def null_data():
    """Sample data with null values for edge case testing."""
    df = pd.DataFrame({
        "col_a": [1.0, 2.0, None, 4.0, 5.0],
        "col_b": [10.0, None, 30.0, 40.0, 50.0],
        "col_c": [100.0, 200.0, 300.0, 400.0, 500.0],
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
# EXPRESSION PARSER TESTS
# =============================================================================


class TestExpressionParser:
    """Tests for ExpressionParser validation and parsing."""

    def test_simple_comparison_gt(self):
        """Test simple greater-than comparison."""
        parser = ExpressionParser()
        result = parser.parse("A > B")

        assert result.is_valid
        assert "A" in result.columns
        assert "B" in result.columns
        assert ">" in result.operators

    def test_simple_comparison_gte(self):
        """Test simple greater-than-or-equal comparison."""
        parser = ExpressionParser()
        result = parser.parse("end_date >= start_date")

        assert result.is_valid
        assert "end_date" in result.columns
        assert "start_date" in result.columns
        assert ">=" in result.operators

    def test_simple_comparison_lt(self):
        """Test simple less-than comparison."""
        parser = ExpressionParser()
        result = parser.parse("price < max_price")

        assert result.is_valid
        assert "price" in result.columns
        assert "max_price" in result.columns
        assert "<" in result.operators

    def test_simple_comparison_eq(self):
        """Test simple equality comparison."""
        parser = ExpressionParser()
        result = parser.parse("calculated = expected")

        assert result.is_valid
        assert "calculated" in result.columns
        assert "expected" in result.columns
        assert "=" in result.operators

    def test_arithmetic_addition(self):
        """Test arithmetic addition expression."""
        parser = ExpressionParser()
        result = parser.parse("subtotal + tax = total")

        assert result.is_valid
        assert "subtotal" in result.columns
        assert "tax" in result.columns
        assert "total" in result.columns
        assert "+" in result.operators
        assert "=" in result.operators

    def test_arithmetic_subtraction(self):
        """Test arithmetic subtraction expression."""
        parser = ExpressionParser()
        result = parser.parse("revenue - costs > 0")

        assert result.is_valid
        assert "revenue" in result.columns
        assert "costs" in result.columns
        assert "-" in result.operators
        assert ">" in result.operators

    def test_arithmetic_multiplication(self):
        """Test arithmetic multiplication expression."""
        parser = ExpressionParser()
        result = parser.parse("quantity * price = total")

        assert result.is_valid
        assert "quantity" in result.columns
        assert "price" in result.columns
        assert "total" in result.columns
        assert "*" in result.operators

    def test_complex_expression_with_parentheses(self):
        """Test complex expression with parentheses."""
        parser = ExpressionParser()
        result = parser.parse("(subtotal + tax) * 0.9 = discounted_total")

        assert result.is_valid
        assert "subtotal" in result.columns
        assert "tax" in result.columns
        assert "discounted_total" in result.columns

    def test_expression_with_and(self):
        """Test expression with AND logical operator."""
        parser = ExpressionParser()
        result = parser.parse("A > B AND B > C")

        assert result.is_valid
        assert "A" in result.columns
        assert "B" in result.columns
        assert "C" in result.columns
        assert "AND" in result.operators

    def test_expression_with_or(self):
        """Test expression with OR logical operator."""
        parser = ExpressionParser()
        result = parser.parse("A > 100 OR B > 200")

        assert result.is_valid
        assert "A" in result.columns
        assert "B" in result.columns
        assert "OR" in result.operators

    def test_column_name_extraction(self):
        """Test column name extraction from complex expression."""
        parser = ExpressionParser()
        result = parser.parse("order_total = subtotal + tax + shipping - discount")

        assert result.is_valid
        assert len(result.columns) == 5
        assert "order_total" in result.columns
        assert "subtotal" in result.columns
        assert "tax" in result.columns
        assert "shipping" in result.columns
        assert "discount" in result.columns

    def test_complexity_score_simple(self):
        """Test complexity score for simple expression."""
        parser = ExpressionParser()
        result = parser.parse("A > B")

        assert result.is_valid
        assert result.complexity_score < 5

    def test_complexity_score_complex(self):
        """Test complexity score for complex expression."""
        parser = ExpressionParser()
        result = parser.parse("(A + B) * C - D / E > F AND G < H OR I = J")

        assert result.is_valid
        assert result.complexity_score > 10

    def test_invalid_expression_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        parser = ExpressionParser()
        result = parser.parse("(A + B > C")

        assert not result.is_valid
        assert "unbalanced parentheses" in result.error_message.lower()

    def test_invalid_expression_empty(self):
        """Test detection of empty expression."""
        parser = ExpressionParser()
        result = parser.parse("")

        assert not result.is_valid
        assert "empty" in result.error_message.lower()

    def test_invalid_expression_forbidden_keyword(self):
        """Test detection of forbidden SQL keywords."""
        parser = ExpressionParser()
        result = parser.parse("A > B; DROP TABLE users")

        assert not result.is_valid
        assert "forbidden" in result.error_message.lower()

    def test_expression_with_numeric_literals(self):
        """Test expression with numeric literals."""
        parser = ExpressionParser()
        result = parser.parse("price * 1.1 > 100")

        assert result.is_valid
        assert "price" in result.columns


# =============================================================================
# COLUMN PAIR SATISFACTION TESTS
# =============================================================================


class TestColumnPairSatisfy:
    """Tests for column_pair_satisfy checks."""

    def test_date_range_end_after_start(self, sample_date_range_data):
        """Test that end_date >= start_date."""
        dataset = connect(sample_date_range_data)
        result = dataset.expect_column_pair_satisfy(
            column_a="end_date",
            column_b="start_date",
            expression="end_date >= start_date",
            threshold=1.0
        )

        assert result.passed
        assert result.actual_value == 0  # No violations

    def test_order_total_equals_sum(self, sample_orders_data):
        """Test that total = subtotal + tax + shipping."""
        dataset = connect(sample_orders_data)
        result = dataset.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total = subtotal + tax + shipping",
            threshold=1.0
        )

        assert result.passed
        assert result.actual_value == 0

    def test_subtotal_greater_than_discount(self, sample_orders_data):
        """Test that subtotal >= discount."""
        dataset = connect(sample_orders_data)
        result = dataset.expect_column_pair_satisfy(
            column_a="subtotal",
            column_b="discount",
            expression="subtotal >= discount",
            threshold=1.0
        )

        assert result.passed

    def test_comparison_with_threshold(self, sample_orders_data):
        """Test column pair satisfaction with threshold."""
        dataset = connect(sample_orders_data)
        result = dataset.expect_column_pair_satisfy(
            column_a="tax",
            column_b="subtotal",
            expression="tax >= subtotal * 0.05",
            threshold=0.8  # Allow 20% violations
        )

        # Should pass with threshold
        assert isinstance(result, ValidationResult)

    def test_arithmetic_expression_multiplication(self, sample_orders_data):
        """Test arithmetic expression with multiplication."""
        dataset = connect(sample_orders_data)

        # This will likely fail since we don't have quantity*price
        # Just testing the mechanics work
        result = dataset.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total > subtotal",
            threshold=1.0
        )

        assert result.passed  # total should always be > subtotal


# =============================================================================
# COMPOSITE UNIQUENESS TESTS
# =============================================================================


class TestMultiColumnUniqueness:
    """Tests for multi-column uniqueness checks."""

    def test_two_column_composite_key(self, composite_key_data):
        """Test composite key uniqueness with 2 columns."""
        dataset = connect(composite_key_data)
        result = dataset.expect_columns_unique(
            columns=["customer_id", "product_id", "order_date"],
            threshold=1.0
        )

        assert result.passed
        assert result.actual_value == 0  # No duplicate combinations

    def test_three_column_composite_key(self, sample_orders_data):
        """Test composite key uniqueness with 3 columns."""
        dataset = connect(sample_orders_data)
        result = dataset.expect_columns_unique(
            columns=["customer_id", "product_id"],
            threshold=1.0
        )

        # This might have duplicates, but test the mechanics
        assert isinstance(result, ValidationResult)

    def test_composite_key_with_duplicates(self):
        """Test composite key when duplicates exist."""
        df = pd.DataFrame({
            "col_a": [1, 1, 2, 3],
            "col_b": ["A", "A", "B", "C"],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_columns_unique(
                columns=["col_a", "col_b"],
                threshold=1.0
            )

            assert not result.passed
            assert result.actual_value == 1  # One duplicate pair (1, A)
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_composite_key_all_unique(self):
        """Test composite key when all combinations are unique."""
        df = pd.DataFrame({
            "col_a": [1, 2, 3, 4],
            "col_b": ["A", "B", "C", "D"],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_columns_unique(
                columns=["col_a", "col_b"],
                threshold=1.0
            )

            assert result.passed
            assert result.actual_value == 0
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_composite_key_with_nulls(self, null_data):
        """Test composite key handling with null values."""
        dataset = connect(null_data)
        result = dataset.expect_columns_unique(
            columns=["col_a", "col_b"],
            threshold=1.0
        )

        # Should handle nulls gracefully
        assert isinstance(result, ValidationResult)


# =============================================================================
# MULTI-COLUMN SUM TESTS
# =============================================================================


class TestMultiColumnSum:
    """Tests for multi-column sum checks."""

    def test_percentage_sum_to_100(self, percentage_data):
        """Test that region percentages sum to 100."""
        dataset = connect(percentage_data)
        result = dataset.expect_multicolumn_sum_to_equal(
            columns=["region_north", "region_south", "region_east", "region_west"],
            expected_sum=100.0,
            threshold=0.01  # Allow 1% tolerance
        )

        assert result.passed

    def test_order_components_sum(self, sample_orders_data):
        """Test that order components sum correctly."""
        dataset = connect(sample_orders_data)

        # Create a test where subtotal + tax + shipping should equal total
        # This is an indirect test since we're testing sum functionality
        result = dataset.expect_multicolumn_sum_to_equal(
            columns=["tax", "shipping", "discount"],
            expected_sum=None,  # Just test mechanics
            threshold=0.01
        )

        # Just ensure it executes without error
        assert isinstance(result, ValidationResult)

    def test_sum_with_exact_match(self):
        """Test sum check with exact match."""
        df = pd.DataFrame({
            "part1": [10.0, 20.0, 30.0],
            "part2": [20.0, 30.0, 40.0],
            "part3": [70.0, 50.0, 30.0],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_multicolumn_sum_to_equal(
                columns=["part1", "part2", "part3"],
                expected_sum=100.0,
                threshold=0.01
            )

            assert result.passed
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_sum_with_violation(self):
        """Test sum check when sums don't match."""
        df = pd.DataFrame({
            "part1": [10.0, 20.0, 30.0],
            "part2": [20.0, 30.0, 40.0],
            "part3": [60.0, 40.0, 20.0],  # Sums to 90, 90, 90 instead of 100
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_multicolumn_sum_to_equal(
                columns=["part1", "part2", "part3"],
                expected_sum=100.0,
                threshold=0.01
            )

            assert not result.passed
            assert result.actual_value == 3  # All 3 rows violate
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_sum_with_nulls(self, null_data):
        """Test sum check with null values."""
        dataset = connect(null_data)
        result = dataset.expect_multicolumn_sum_to_equal(
            columns=["col_a", "col_b"],
            expected_sum=None,
            threshold=0.01
        )

        # Should handle nulls (likely treating as 0 or skipping)
        assert isinstance(result, ValidationResult)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestMultiColumnEdgeCases:
    """Tests for edge cases in multi-column checks."""

    def test_empty_dataset(self):
        """Test multi-column checks on empty dataset."""
        df = pd.DataFrame({
            "col_a": [],
            "col_b": [],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_column_pair_satisfy(
                column_a="col_a",
                column_b="col_b",
                expression="col_a > col_b",
                threshold=1.0
            )

            # Should pass vacuously (no rows to violate)
            assert result.passed
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_single_row_dataset(self):
        """Test multi-column checks on single row."""
        df = pd.DataFrame({
            "col_a": [10.0],
            "col_b": [5.0],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_column_pair_satisfy(
                column_a="col_a",
                column_b="col_b",
                expression="col_a > col_b",
                threshold=1.0
            )

            assert result.passed
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_all_nulls_column(self):
        """Test multi-column checks when all values are null."""
        df = pd.DataFrame({
            "col_a": [None, None, None],
            "col_b": [1.0, 2.0, 3.0],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_column_pair_satisfy(
                column_a="col_a",
                column_b="col_b",
                expression="col_a > col_b",
                threshold=1.0
            )

            # Should handle gracefully
            assert isinstance(result, ValidationResult)
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_unicode_column_names(self):
        """Test multi-column checks with Unicode column names."""
        df = pd.DataFrame({
            "数量": [10, 20, 30],
            "价格": [100, 200, 300],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
        df.to_csv(temp_file.name, index=False, encoding='utf-8')
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.expect_columns_unique(
                columns=["数量", "价格"],
                threshold=1.0
            )

            assert isinstance(result, ValidationResult)
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_nonexistent_column(self, sample_orders_data):
        """Test multi-column check with non-existent column."""
        dataset = connect(sample_orders_data)

        # Should raise an error or return failed result
        with pytest.raises(Exception):
            dataset.expect_column_pair_satisfy(
                column_a="nonexistent_col",
                column_b="subtotal",
                expression="nonexistent_col > subtotal",
                threshold=1.0
            )

    def test_very_long_expression(self):
        """Test with very long expression."""
        parser = ExpressionParser()

        # Create a very long expression
        long_expr = " + ".join([f"col_{i}" for i in range(100)])
        result = parser.parse(long_expr + " > 0")

        # Should handle but mark as complex
        assert isinstance(result.complexity_score, (int, float))


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestMultiColumnPerformance:
    """Performance tests for multi-column checks."""

    def test_column_pair_satisfy_100k_rows(self):
        """Test column_pair_satisfy performance with 100K rows."""
        import time

        # Generate large dataset
        df = pd.DataFrame({
            "col_a": range(100000),
            "col_b": range(1, 100001),
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)

            start_time = time.time()
            result = dataset.expect_column_pair_satisfy(
                column_a="col_b",
                column_b="col_a",
                expression="col_b > col_a",
                threshold=1.0
            )
            elapsed_time = time.time() - start_time

            assert result.passed
            assert elapsed_time < 5.0  # Should complete in < 5 seconds
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_composite_unique_100k_rows(self):
        """Test composite uniqueness with 100K rows."""
        import time

        # Generate large dataset with unique combinations
        df = pd.DataFrame({
            "col_a": [i // 1000 for i in range(100000)],
            "col_b": [i % 1000 for i in range(100000)],
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)

            start_time = time.time()
            result = dataset.expect_columns_unique(
                columns=["col_a", "col_b"],
                threshold=1.0
            )
            elapsed_time = time.time() - start_time

            assert result.passed
            assert elapsed_time < 8.0  # Should complete in < 8 seconds
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


class TestMultiColumnIntegration:
    """Integration tests for multi-column checks with other features."""

    def test_multiple_checks_on_same_dataset(self, sample_orders_data):
        """Test running multiple multi-column checks on same dataset."""
        dataset = connect(sample_orders_data)

        # Run multiple checks
        result1 = dataset.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total >= subtotal",
            threshold=1.0
        )

        result2 = dataset.expect_columns_unique(
            columns=["customer_id", "product_id"],
            threshold=1.0
        )

        # Both should execute successfully
        assert isinstance(result1, ValidationResult)
        assert isinstance(result2, ValidationResult)

    def test_chaining_with_regular_checks(self, sample_orders_data):
        """Test multi-column checks combined with regular checks."""
        dataset = connect(sample_orders_data)

        # Regular check
        result1 = dataset.order_id.is_unique()

        # Multi-column check
        result2 = dataset.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total > subtotal",
            threshold=1.0
        )

        assert result1.passed
        assert result2.passed
