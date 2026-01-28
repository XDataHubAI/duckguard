"""Example pytest tests using DuckGuard.

Run with: pytest examples/pytest_example.py -v
"""

import pytest

from duckguard import connect


@pytest.fixture
def orders():
    """Load the orders dataset."""
    return connect("examples/sample_data/orders.csv")


class TestOrdersDataQuality:
    """Data quality tests for orders dataset."""

    def test_dataset_not_empty(self, orders):
        """Ensure the dataset has rows."""
        assert orders.row_count > 0

    def test_order_id_unique(self, orders):
        """Order IDs should be unique."""
        assert orders.order_id.has_no_duplicates()

    def test_order_id_not_null(self, orders):
        """Order IDs should never be null."""
        assert orders.order_id.null_percent == 0

    def test_customer_id_not_null(self, orders):
        """Customer IDs should not be null."""
        assert orders.customer_id.null_percent == 0

    def test_quantity_positive(self, orders):
        """Quantity should be positive."""
        assert orders.quantity.min >= 1

    def test_quantity_reasonable(self, orders):
        """Quantity should be within reasonable range."""
        assert orders.quantity.between(1, 1000)

    def test_total_amount_positive(self, orders):
        """Total amount should be positive."""
        assert orders.total_amount.min > 0

    def test_status_valid_values(self, orders):
        """Status should only contain valid values."""
        assert orders.status.isin(['pending', 'shipped', 'delivered'])

    def test_email_format(self, orders):
        """Email should be valid format."""
        assert orders.email.matches(r'^[\w\.-]+@[\w\.-]+\.\w+$')

    def test_created_at_format(self, orders):
        """Created date should be in YYYY-MM-DD format."""
        assert orders.created_at.matches(r'^\d{4}-\d{2}-\d{2}$')


class TestColumnStatistics:
    """Tests for column statistics."""

    def test_unique_customer_count(self, orders):
        """Should have multiple unique customers."""
        assert orders.customer_id.unique_count > 5

    def test_product_variety(self, orders):
        """Should have multiple products."""
        assert orders.product_name.unique_count >= 5

    def test_price_range(self, orders):
        """Unit price should be in reasonable range."""
        assert orders.unit_price.min >= 10
        assert orders.unit_price.max <= 200
