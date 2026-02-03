"""Tests for Group By Checks feature."""

import pytest

from duckguard import connect


class TestGroupBy:
    """Tests for Dataset.group_by() method."""

    def test_groups_property(self, grouped_orders_csv):
        """Test that groups are correctly identified."""
        orders = connect(grouped_orders_csv)
        grouped = orders.group_by("region")

        groups = grouped.groups
        assert len(groups) == 2
        group_regions = [g["region"] for g in groups]
        assert "US" in group_regions
        assert "EU" in group_regions

    def test_group_count(self, grouped_orders_csv):
        """Test group count property."""
        orders = connect(grouped_orders_csv)
        grouped = orders.group_by("region")

        assert grouped.group_count == 2

    def test_stats(self, grouped_orders_csv):
        """Test group statistics."""
        orders = connect(grouped_orders_csv)
        grouped = orders.group_by("region")

        stats = grouped.stats()
        assert len(stats) == 2
        for stat in stats:
            assert "region" in stat
            assert "row_count" in stat
            assert stat["row_count"] > 0

    def test_row_count_greater_than_passes(self, grouped_orders_csv):
        """Test row count validation that should pass."""
        orders = connect(grouped_orders_csv)

        result = orders.group_by("region").row_count_greater_than(0)

        assert result.passed is True
        assert result.passed_groups == 2
        assert result.failed_groups == 0

    def test_row_count_greater_than_fails(self, grouped_orders_csv):
        """Test row count validation that should fail."""
        orders = connect(grouped_orders_csv)

        # Require more than 5 rows per region - should fail
        result = orders.group_by("region").row_count_greater_than(5)

        assert result.passed is False
        assert result.failed_groups == 2  # Both regions have <= 5 rows

    def test_multiple_group_columns(self, grouped_orders_csv):
        """Test grouping by multiple columns."""
        orders = connect(grouped_orders_csv)
        grouped = orders.group_by(["region", "status"])

        groups = grouped.groups
        assert len(groups) > 2  # More combinations than single column

    def test_group_by_result_summary(self, grouped_orders_csv):
        """Test group by result summary."""
        orders = connect(grouped_orders_csv)
        result = orders.group_by("status").row_count_greater_than(0)

        summary = result.summary()
        assert "Group By Validation" in summary
        assert "Grouped by:" in summary

    def test_get_failed_groups(self, grouped_orders_csv):
        """Test getting failed groups."""
        orders = connect(grouped_orders_csv)

        result = orders.group_by("region").row_count_greater_than(5)
        failed = result.get_failed_groups()

        assert len(failed) == 2

    def test_invalid_group_column_raises_error(self, grouped_orders_csv):
        """Test that invalid column raises error."""
        orders = connect(grouped_orders_csv)

        with pytest.raises(KeyError):
            orders.group_by("nonexistent_column")

    def test_group_by_boolean_context(self, grouped_orders_csv):
        """Test that group by result works in boolean context."""
        orders = connect(grouped_orders_csv)

        result = orders.group_by("region").row_count_greater_than(0)

        assert bool(result) is True
        assert result.passed is True

    def test_group_by_pass_rate(self, grouped_orders_csv):
        """Test pass rate calculation."""
        orders = connect(grouped_orders_csv)

        # All groups pass
        result = orders.group_by("region").row_count_greater_than(0)
        assert result.pass_rate == 100.0

        # All groups fail
        result = orders.group_by("region").row_count_greater_than(100)
        assert result.pass_rate == 0.0

    def test_group_result_properties(self, grouped_orders_csv):
        """Test individual GroupResult properties."""
        orders = connect(grouped_orders_csv)

        result = orders.group_by("region").row_count_greater_than(0)

        for group_result in result.group_results:
            assert group_result.group_key is not None
            assert group_result.row_count > 0
            assert group_result.passed is True
            assert group_result.key_string is not None

    def test_group_by_with_string_column(self, grouped_orders_csv):
        """Test grouping by string column works correctly."""
        orders = connect(grouped_orders_csv)

        grouped = orders.group_by("status")
        stats = grouped.stats()

        # Should have 3 statuses: shipped, pending, delivered
        assert len(stats) == 3
        status_values = [s["status"] for s in stats]
        assert "shipped" in status_values
        assert "pending" in status_values
        assert "delivered" in status_values


class TestGroupByIntegration:
    """Integration tests for group by with other features."""

    def test_group_stats_with_multiple_checks(self, grouped_orders_csv):
        """Test running multiple group checks."""
        orders = connect(grouped_orders_csv)

        # Check multiple things per group
        result1 = orders.group_by("region").row_count_greater_than(0)
        result2 = orders.group_by("status").row_count_greater_than(0)

        assert result1.passed is True
        assert result2.passed is True

    def test_group_by_with_date_column(self, grouped_orders_csv):
        """Test grouping by date column."""
        orders = connect(grouped_orders_csv)

        grouped = orders.group_by("date")
        stats = grouped.stats()

        # Should have 3 dates
        assert len(stats) == 3

        result = orders.group_by("date").row_count_greater_than(0)
        assert result.passed is True
