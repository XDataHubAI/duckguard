"""Tests for the Dataset class."""

import pytest

from duckguard import connect


class TestDataset:
    """Tests for Dataset class."""

    def test_create_dataset_from_csv(self, orders_csv):
        """Test creating a dataset from CSV."""
        dataset = connect(orders_csv)
        assert dataset is not None
        assert dataset.row_count == 30

    def test_column_access_attribute(self, orders_dataset):
        """Test accessing columns as attributes."""
        col = orders_dataset.order_id
        assert col is not None
        assert col.name == "order_id"

    def test_column_access_bracket(self, orders_dataset):
        """Test accessing columns with bracket notation."""
        col = orders_dataset["order_id"]
        assert col is not None
        assert col.name == "order_id"

    def test_invalid_column_attribute(self, orders_dataset):
        """Test accessing non-existent column raises error."""
        with pytest.raises(AttributeError):
            _ = orders_dataset.nonexistent_column

    def test_invalid_column_bracket(self, orders_dataset):
        """Test accessing non-existent column with brackets raises error."""
        with pytest.raises(KeyError):
            _ = orders_dataset["nonexistent_column"]

    def test_columns_property(self, orders_dataset):
        """Test columns property returns column names."""
        columns = orders_dataset.columns
        assert isinstance(columns, list)
        assert "order_id" in columns
        assert "customer_id" in columns

    def test_column_count(self, orders_dataset):
        """Test column count."""
        assert orders_dataset.column_count == 15

    def test_has_column(self, orders_dataset):
        """Test has_column method."""
        assert orders_dataset.has_column("order_id")
        assert not orders_dataset.has_column("nonexistent")

    def test_contains(self, orders_dataset):
        """Test __contains__ method."""
        assert "order_id" in orders_dataset
        assert "nonexistent" not in orders_dataset

    def test_iter(self, orders_dataset):
        """Test iterating over column names."""
        columns = list(orders_dataset)
        assert "order_id" in columns
        assert len(columns) == 15

    def test_len(self, orders_dataset):
        """Test __len__ returns row count."""
        assert len(orders_dataset) == 30

    def test_sample(self, orders_dataset):
        """Test sample method."""
        samples = orders_dataset.sample(5)
        assert len(samples) == 5
        assert isinstance(samples[0], dict)
        assert "order_id" in samples[0]

    def test_head(self, orders_dataset):
        """Test head method."""
        head = orders_dataset.head(3)
        assert len(head) == 3

    def test_repr(self, orders_dataset):
        """Test string representation."""
        repr_str = repr(orders_dataset)
        assert "Dataset" in repr_str
        assert "rows=30" in repr_str


class TestColumn:
    """Tests for Column class."""

    def test_null_count(self, temp_csv_with_nulls):
        """Test null count."""
        dataset = connect(temp_csv_with_nulls)
        # 'user_name' has 1 null (row 4)
        assert dataset.user_name.null_count == 1

    def test_null_percent(self, temp_csv_with_nulls):
        """Test null percentage."""
        dataset = connect(temp_csv_with_nulls)
        # 1 null out of 5 = 20%
        assert dataset.user_name.null_percent == 20.0

    def test_unique_count(self, orders_dataset):
        """Test unique count."""
        # All order IDs should be unique (25 unique values)
        assert orders_dataset.order_id.unique_count == 30

    def test_unique_percent(self, orders_dataset):
        """Test unique percentage."""
        assert orders_dataset.order_id.unique_percent == 100.0

    def test_min_max(self, orders_dataset):
        """Test min and max values."""
        assert orders_dataset.quantity.min == -2
        assert orders_dataset.quantity.max == 500

    def test_mean(self, orders_dataset):
        """Test mean value."""
        mean = orders_dataset.quantity.mean
        assert mean is not None
        assert mean > 0

    def test_is_not_null(self, orders_dataset):
        """Test is_not_null validation."""
        result = orders_dataset.order_id.is_not_null()
        assert result.passed

    def test_is_unique(self, orders_dataset):
        """Test is_unique validation."""
        result = orders_dataset.order_id.is_unique()
        assert result.passed

    def test_between(self, orders_dataset):
        """Test between validation."""
        result = orders_dataset.quantity.between(-10, 1000)
        assert result.passed

        result = orders_dataset.quantity.between(200, 300)
        assert not result.passed

    def test_isin(self, orders_dataset):
        """Test isin validation."""
        # Updated: sample data now includes 'cancelled' status
        result = orders_dataset.status.isin(
            ["pending", "shipped", "delivered", "cancelled", "returned"]
        )
        assert result.passed

        result = orders_dataset.status.isin(["pending", "shipped"])
        assert not result.passed

    def test_matches(self, orders_dataset):
        """Test matches validation."""
        # Note: sample data has 1 null email, so matches may not be 100%
        result = orders_dataset.order_id.matches(r"^ORD-\d+$")
        assert result.passed

    def test_has_no_duplicates(self, orders_dataset):
        """Test has_no_duplicates validation."""
        result = orders_dataset.order_id.has_no_duplicates()
        assert result.passed

        # customer_id has duplicates
        result = orders_dataset.customer_id.has_no_duplicates()
        assert not result.passed

    def test_get_distinct_values(self, orders_dataset):
        """Test getting distinct values."""
        values = orders_dataset.status.get_distinct_values()
        # Updated: sample data now includes 'cancelled' status
        assert set(values) == {"pending", "shipped", "delivered", "cancelled", "returned"}

    def test_get_value_counts(self, orders_dataset):
        """Test getting value counts."""
        counts = orders_dataset.status.get_value_counts()
        assert isinstance(counts, dict)
        assert len(counts) == 5
