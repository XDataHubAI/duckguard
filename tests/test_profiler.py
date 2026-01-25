"""Tests for the auto-profiler."""

import pytest
from duckguard import connect
from duckguard.profiler import AutoProfiler, profile


class TestAutoProfiler:
    """Tests for AutoProfiler class."""

    def test_profile_dataset(self, orders_dataset):
        """Test profiling a dataset."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert result.row_count == 20
        assert result.column_count == 9
        assert len(result.columns) == 9

    def test_profile_column_stats(self, orders_dataset):
        """Test column statistics in profile."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        # Find order_id column
        order_id_col = next(c for c in result.columns if c.name == "order_id")
        assert order_id_col.null_percent == 0
        assert order_id_col.unique_percent == 100

    def test_suggested_rules_generated(self, orders_dataset):
        """Test that rules are suggested."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert len(result.suggested_rules) > 0

    def test_unique_column_rule_suggested(self, orders_dataset):
        """Test that unique columns get uniqueness rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        # Should suggest uniqueness rule for order_id
        order_id_col = next(c for c in result.columns if c.name == "order_id")
        assert any("has_no_duplicates" in r for r in order_id_col.suggested_rules)

    def test_enum_column_rule_suggested(self, orders_dataset):
        """Test that low-cardinality columns get enum rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        # Should suggest isin rule for status
        status_col = next(c for c in result.columns if c.name == "status")
        assert any("isin" in r for r in status_col.suggested_rules)

    def test_generate_test_file(self, orders_dataset):
        """Test generating a test file."""
        profiler = AutoProfiler()
        code = profiler.generate_test_file(orders_dataset, output_var="orders")

        assert "from duckguard import connect" in code
        assert "def test_" in code
        assert "assert orders.row_count > 0" in code

    def test_profile_convenience_function(self, orders_dataset):
        """Test the profile() convenience function."""
        result = profile(orders_dataset)
        assert result.row_count == 20


class TestPatternDetection:
    """Tests for pattern detection in profiler."""

    def test_email_pattern_detection(self, orders_dataset):
        """Test that email pattern is detected."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        email_col = next(c for c in result.columns if c.name == "email")
        # Should have a pattern suggestion for email
        assert any("matches" in r for r in email_col.suggested_rules)

    def test_date_column_has_rules(self, orders_dataset):
        """Test that date columns get validation rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        date_col = next(c for c in result.columns if c.name == "created_at")
        # Date column should have at least some suggested rules
        # (e.g., null checks, uniqueness checks)
        assert len(date_col.suggested_rules) > 0
