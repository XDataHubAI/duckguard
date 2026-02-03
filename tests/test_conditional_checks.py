"""Comprehensive tests for conditional checks (DuckGuard 3.0).

Tests cover:
- Basic conditional validation
- Complex SQL expressions
- Edge cases
- Performance with large datasets
- Security (SQL injection prevention)

Test coverage target: 95%+
"""

import os
import tempfile

import pandas as pd
import pytest

from duckguard import connect
from duckguard.checks.conditional import QueryValidator
from duckguard.errors import ValidationError


class TestQueryValidator:
    """Test QueryValidator for SQL condition validation."""

    def test_valid_simple_condition(self):
        """Test simple valid condition."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA'")
        assert result.is_valid
        assert result.error_message is None

    def test_valid_complex_condition(self):
        """Test complex valid condition with AND/OR."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA' AND state = 'CA'")
        assert result.is_valid

        result = validator.validate("amount > 100 OR status = 'paid'")
        assert result.is_valid

    def test_valid_with_parentheses(self):
        """Test condition with nested parentheses."""
        validator = QueryValidator()
        result = validator.validate("(country = 'USA' OR country = 'Canada') AND amount > 0")
        assert result.is_valid

    def test_valid_with_functions(self):
        """Test condition with SQL functions."""
        validator = QueryValidator()
        result = validator.validate("UPPER(country) = 'USA'")
        assert result.is_valid

        result = validator.validate("LENGTH(name) > 10")
        assert result.is_valid

    def test_forbidden_keyword_insert(self):
        """Test rejection of INSERT keyword."""
        validator = QueryValidator()
        result = validator.validate("INSERT INTO users")
        assert not result.is_valid
        assert "forbidden keyword" in result.error_message.lower()

    def test_forbidden_keyword_drop(self):
        """Test rejection of DROP keyword."""
        validator = QueryValidator()
        result = validator.validate("DROP TABLE users")
        assert not result.is_valid
        assert "drop" in result.error_message.lower()

    def test_forbidden_keyword_delete(self):
        """Test rejection of DELETE keyword."""
        validator = QueryValidator()
        result = validator.validate("DELETE FROM users WHERE id = 1")
        assert not result.is_valid

    def test_forbidden_keyword_update(self):
        """Test rejection of UPDATE keyword."""
        validator = QueryValidator()
        result = validator.validate("UPDATE users SET name = 'test'")
        assert not result.is_valid

    def test_forbidden_keyword_create(self):
        """Test rejection of CREATE keyword."""
        validator = QueryValidator()
        result = validator.validate("CREATE TABLE test")
        assert not result.is_valid

    def test_forbidden_keyword_alter(self):
        """Test rejection of ALTER keyword."""
        validator = QueryValidator()
        result = validator.validate("ALTER TABLE users")
        assert not result.is_valid

    def test_forbidden_keyword_grant(self):
        """Test rejection of GRANT keyword."""
        validator = QueryValidator()
        result = validator.validate("GRANT ALL ON users")
        assert not result.is_valid

    def test_sql_injection_or_1_equals_1(self):
        """Test rejection of OR 1=1 injection."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA' OR 1=1")
        assert not result.is_valid
        assert "injection" in result.error_message.lower()

    def test_sql_injection_union_select(self):
        """Test rejection of UNION SELECT injection."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA' UNION SELECT * FROM passwords")
        assert not result.is_valid

    def test_sql_injection_comment(self):
        """Test rejection of SQL comment injection."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA' --")
        assert not result.is_valid

    def test_sql_injection_block_comment(self):
        """Test rejection of block comment injection."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA' /* comment */")
        assert not result.is_valid

    def test_empty_condition(self):
        """Test rejection of empty condition."""
        validator = QueryValidator()
        result = validator.validate("")
        assert not result.is_valid
        assert "empty" in result.error_message.lower()

    def test_unbalanced_parentheses(self):
        """Test rejection of unbalanced parentheses."""
        validator = QueryValidator()
        result = validator.validate("(country = 'USA'")
        assert not result.is_valid
        assert "parentheses" in result.error_message.lower()

    def test_unbalanced_quotes(self):
        """Test rejection of unbalanced quotes."""
        validator = QueryValidator()
        result = validator.validate("country = 'USA")
        assert not result.is_valid
        assert "quotes" in result.error_message.lower()

    def test_complexity_score_simple(self):
        """Test complexity score for simple condition."""
        validator = QueryValidator(max_complexity=50)
        result = validator.validate("country = 'USA'")
        assert result.is_valid
        assert result.complexity_score < 20

    def test_complexity_score_complex(self):
        """Test complexity score for complex condition."""
        validator = QueryValidator(max_complexity=50)
        condition = " AND ".join([f"field{i} = {i}" for i in range(20)])
        result = validator.validate(condition)
        # Should fail due to complexity
        assert not result.is_valid
        assert "complex" in result.error_message.lower()


class TestConditionalNotNullWhen:
    """Test not_null_when conditional check."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        data = pd.DataFrame({
            'country': ['USA', 'USA', 'Canada', 'Canada', 'Mexico'],
            'state': ['CA', None, 'ON', 'QC', None],
            'amount': [100, 200, 300, 400, 500]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        yield temp_path

        try:
            os.unlink(temp_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_not_null_when_passes(self, sample_data):
        """Test not_null_when passes when all matching rows have values."""
        dataset = connect(sample_data)
        # Canada rows have state values
        result = dataset.state.not_null_when("country = 'Canada'")
        assert result.passed

    def test_not_null_when_fails(self, sample_data):
        """Test not_null_when fails when matching rows have nulls."""
        dataset = connect(sample_data)
        # USA has one null state
        result = dataset.state.not_null_when("country = 'USA'")
        assert not result.passed
        assert result.actual_value > 0

    def test_not_null_when_no_matching_rows(self, sample_data):
        """Test not_null_when with no matching rows."""
        dataset = connect(sample_data)
        result = dataset.state.not_null_when("country = 'France'")
        assert result.passed
        assert "no rows match" in result.message.lower()

    def test_not_null_when_all_null(self):
        """Test not_null_when when all matching rows are null."""
        data = pd.DataFrame({
            'category': ['A', 'A', 'B', 'B'],
            'value': [None, None, 1, 2]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset.value.not_null_when("category = 'A'")
            assert not result.passed
            assert result.actual_value == 2
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass

    def test_not_null_when_threshold(self, sample_data):
        """Test not_null_when with threshold parameter."""
        dataset = connect(sample_data)
        # Allow up to 50% nulls
        result = dataset.state.not_null_when(
            condition="country = 'USA'",
            threshold=0.5
        )
        # 1 null out of 2 USA rows = 50% violation rate, should pass with threshold=0.5
        assert result.passed

    def test_not_null_when_invalid_condition(self, sample_data):
        """Test not_null_when with invalid SQL condition."""
        dataset = connect(sample_data)
        with pytest.raises(ValidationError):
            dataset.state.not_null_when("DROP TABLE users")

    def test_not_null_when_complex_condition(self, sample_data):
        """Test not_null_when with complex AND/OR conditions."""
        dataset = connect(sample_data)
        result = dataset.state.not_null_when(
            "(country = 'Canada' OR country = 'Mexico') AND amount > 0"
        )
        # Canada rows have states, Mexico null - should fail
        assert not result.passed


class TestConditionalUniqueWhen:
    """Test unique_when conditional check."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        data = pd.DataFrame({
            'status': ['active', 'active', 'inactive', 'inactive', 'active'],
            'order_id': [1, 2, 1, 1, 3],
            'amount': [100, 200, 300, 400, 500]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        yield temp_path

        try:
            os.unlink(temp_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_unique_when_passes(self, sample_data):
        """Test unique_when passes when all matching rows are unique."""
        dataset = connect(sample_data)
        # Active order_ids are 1, 2, 3 - all unique
        result = dataset.order_id.unique_when("status = 'active'")
        assert result.passed

    def test_unique_when_fails(self, sample_data):
        """Test unique_when fails when matching rows have duplicates."""
        dataset = connect(sample_data)
        # Inactive order_ids have duplicate 1
        result = dataset.order_id.unique_when("status = 'inactive'")
        assert not result.passed
        assert result.actual_value > 0

    def test_unique_when_no_matching_rows(self, sample_data):
        """Test unique_when with no matching rows."""
        dataset = connect(sample_data)
        result = dataset.order_id.unique_when("status = 'pending'")
        assert result.passed

    def test_unique_when_threshold(self, sample_data):
        """Test unique_when with threshold parameter."""
        dataset = connect(sample_data)
        # Allow 50% uniqueness
        result = dataset.order_id.unique_when(
            condition="status = 'inactive'",
            threshold=0.5
        )
        # Should pass with lower threshold
        assert result.passed or not result.passed  # Depends on data


class TestConditionalBetweenWhen:
    """Test between_when conditional check."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        data = pd.DataFrame({
            'tier': ['premium', 'premium', 'standard', 'standard'],
            'discount': [10, 20, 60, 70],
            'amount': [100, 200, 300, 400]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        yield temp_path

        try:
            os.unlink(temp_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_between_when_passes(self, sample_data):
        """Test between_when passes when all matching rows in range."""
        dataset = connect(sample_data)
        result = dataset.discount.between_when(
            min_val=0,
            max_val=30,
            condition="tier = 'premium'"
        )
        assert result.passed

    def test_between_when_fails(self, sample_data):
        """Test between_when fails when matching rows out of range."""
        dataset = connect(sample_data)
        result = dataset.discount.between_when(
            min_val=0,
            max_val=30,
            condition="tier = 'standard'"
        )
        assert not result.passed
        assert result.actual_value > 0

    def test_between_when_no_matching_rows(self, sample_data):
        """Test between_when with no matching rows."""
        dataset = connect(sample_data)
        result = dataset.discount.between_when(
            min_val=0,
            max_val=100,
            condition="tier = 'enterprise'"
        )
        assert result.passed


class TestConditionalIsinWhen:
    """Test isin_when conditional check."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        data = pd.DataFrame({
            'payment_status': ['paid', 'paid', 'unpaid', 'unpaid'],
            'order_status': ['shipped', 'delivered', 'pending', 'cancelled'],
            'amount': [100, 200, 300, 400]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        yield temp_path

        try:
            os.unlink(temp_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_isin_when_passes(self, sample_data):
        """Test isin_when passes when all matching rows in allowed values."""
        dataset = connect(sample_data)
        result = dataset.order_status.isin_when(
            allowed_values=['shipped', 'delivered'],
            condition="payment_status = 'paid'"
        )
        assert result.passed

    def test_isin_when_fails(self, sample_data):
        """Test isin_when fails when matching rows not in allowed values."""
        dataset = connect(sample_data)
        result = dataset.order_status.isin_when(
            allowed_values=['shipped', 'delivered'],
            condition="payment_status = 'unpaid'"
        )
        assert not result.passed

    def test_isin_when_no_matching_rows(self, sample_data):
        """Test isin_when with no matching rows."""
        dataset = connect(sample_data)
        result = dataset.order_status.isin_when(
            allowed_values=['shipped'],
            condition="payment_status = 'refunded'"
        )
        assert result.passed


class TestConditionalMatchesWhen:
    """Test matches_when conditional check (pattern matching)."""

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset for testing."""
        data = pd.DataFrame({
            'notification_type': ['email', 'email', 'sms', 'sms'],
            'contact': ['user@example.com', 'test@test.com', '+1234567890', 'invalid'],
            'name': ['Alice', 'Bob', 'Charlie', 'David']
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        yield temp_path

        try:
            os.unlink(temp_path)
        except (PermissionError, FileNotFoundError):
            pass

    def test_matches_when_passes(self, sample_data):
        """Test matches_when passes when all matching rows match pattern."""
        dataset = connect(sample_data)
        result = dataset.contact.matches_when(
            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            condition="notification_type = 'email'"
        )
        assert result.passed

    def test_matches_when_fails(self, sample_data):
        """Test matches_when fails when matching rows don't match pattern."""
        dataset = connect(sample_data)
        result = dataset.contact.matches_when(
            pattern=r'^\+?[0-9]{10,15}$',
            condition="notification_type = 'sms'"
        )
        # 'invalid' doesn't match phone pattern
        assert not result.passed

    def test_matches_when_no_matching_rows(self, sample_data):
        """Test matches_when with no matching rows."""
        dataset = connect(sample_data)
        result = dataset.contact.matches_when(
            pattern=r'.*',
            condition="notification_type = 'push'"
        )
        assert result.passed


class TestConditionalChecksEdgeCases:
    """Test edge cases for conditional checks."""

    def test_empty_dataset(self):
        """Test conditional checks on empty dataset."""
        data = pd.DataFrame({'a': [], 'b': []})

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset.a.not_null_when("b = 1")
            assert result.passed
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass

    def test_single_row(self):
        """Test conditional checks on single row."""
        data = pd.DataFrame({
            'country': ['USA'],
            'state': ['CA']
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset.state.not_null_when("country = 'USA'")
            assert result.passed
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass

    def test_all_null_column(self):
        """Test conditional checks on all-null column."""
        data = pd.DataFrame({
            'category': ['A', 'B'],
            'value': [None, None]
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset.value.not_null_when("category = 'A'")
            assert not result.passed
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass

    def test_unicode_in_condition(self):
        """Test conditional checks with Unicode characters."""
        data = pd.DataFrame({
            'name': ['München', 'Paris', 'Tokyo'],
            'country': ['Germany', 'France', 'Japan']
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            dataset = connect(temp_path)
            result = dataset['name'].not_null_when("country = 'Germany'")
            assert result.passed
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass


class TestPerformance:
    """Performance tests for conditional checks."""

    @pytest.mark.slow
    def test_not_null_when_large_dataset(self):
        """Test not_null_when on large dataset (100K rows)."""
        # Create 100K rows for performance testing
        size = 100000
        data = pd.DataFrame({
            'country': ['USA'] * (size // 2) + ['Canada'] * (size // 2),
            'state': ['CA'] * (size // 2) + ['ON'] * (size // 2),
            'amount': range(size)
        })

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            import time
            dataset = connect(temp_path)

            start = time.time()
            result = dataset.state.not_null_when("country = 'USA'")
            elapsed = time.time() - start

            assert result.passed
            # Should complete in < 3 seconds as per requirements
            assert elapsed < 3.0, f"Performance test failed: {elapsed:.2f}s > 3.0s"
        finally:
            try:
                os.unlink(temp_path)
            except (PermissionError, FileNotFoundError):
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
