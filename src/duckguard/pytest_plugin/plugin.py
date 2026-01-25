"""pytest plugin for DuckGuard data quality testing.

This plugin provides fixtures and hooks for seamless pytest integration.

Usage in conftest.py:
    import pytest
    from duckguard import connect

    @pytest.fixture
    def orders():
        return connect("data/orders.csv")

Usage in tests:
    def test_orders_not_empty(orders):
        assert orders.row_count > 0

    def test_customer_id_valid(orders):
        assert orders.customer_id.null_percent < 5
"""

from __future__ import annotations

import pytest

from duckguard.connectors import connect as duckguard_connect
from duckguard.core.engine import DuckGuardEngine


@pytest.fixture(scope="session")
def duckguard_engine():
    """
    Provide a DuckGuard engine instance for the test session.

    This fixture provides a shared DuckDB engine that persists
    across all tests in the session.

    Usage:
        def test_something(duckguard_engine):
            result = duckguard_engine.execute("SELECT 1")
    """
    engine = DuckGuardEngine()
    yield engine
    engine.close()


@pytest.fixture
def duckguard_dataset(request):
    """
    Factory fixture for creating datasets from markers.

    Usage with marker:
        @pytest.mark.duckguard_source("data/orders.csv")
        def test_orders(duckguard_dataset):
            assert duckguard_dataset.row_count > 0

    Usage with parametrize:
        @pytest.mark.parametrize("source", ["data/orders.csv", "data/customers.csv"])
        def test_multiple_sources(duckguard_dataset, source):
            dataset = duckguard_dataset(source)
            assert dataset.row_count > 0
    """
    # Check for marker
    marker = request.node.get_closest_marker("duckguard_source")

    if marker:
        source = marker.args[0] if marker.args else None
        table = marker.kwargs.get("table")
        if source:
            return duckguard_connect(source, table=table)

    # Return factory function
    def _create_dataset(source: str, **kwargs):
        return duckguard_connect(source, **kwargs)

    return _create_dataset


def pytest_configure(config):
    """Register DuckGuard markers."""
    config.addinivalue_line(
        "markers",
        "duckguard_source(source, table=None): Mark test with a DuckGuard data source",
    )
    config.addinivalue_line(
        "markers",
        "duckguard_skip_slow: Skip slow DuckGuard tests",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on DuckGuard options."""
    # Check if slow tests should be skipped
    skip_slow = config.getoption("--duckguard-skip-slow", default=False)

    if skip_slow:
        skip_marker = pytest.mark.skip(reason="Skipping slow DuckGuard tests")
        for item in items:
            if "duckguard_skip_slow" in item.keywords:
                item.add_marker(skip_marker)


def pytest_addoption(parser):
    """Add DuckGuard-specific command line options."""
    group = parser.getgroup("duckguard", "DuckGuard data quality testing")
    group.addoption(
        "--duckguard-skip-slow",
        action="store_true",
        default=False,
        help="Skip slow DuckGuard tests",
    )


# Custom assertion helpers for better error messages
class DuckGuardAssertionHelper:
    """Helper class for custom DuckGuard assertions with better error messages."""

    @staticmethod
    def assert_not_null(column, threshold: float = 0.0):
        """Assert column null percentage is below threshold."""
        actual = column.null_percent
        if actual > threshold:
            pytest.fail(
                f"Column '{column.name}' has {actual:.2f}% null values, "
                f"expected <= {threshold}%"
            )

    @staticmethod
    def assert_unique(column, threshold: float = 100.0):
        """Assert column unique percentage is at or above threshold."""
        actual = column.unique_percent
        if actual < threshold:
            pytest.fail(
                f"Column '{column.name}' has {actual:.2f}% unique values, "
                f"expected >= {threshold}%"
            )

    @staticmethod
    def assert_in_range(column, min_val, max_val):
        """Assert all column values are within range."""
        result = column.between(min_val, max_val)
        if not result:
            pytest.fail(
                f"Column '{column.name}' has {result.actual_value} values "
                f"outside range [{min_val}, {max_val}]"
            )

    @staticmethod
    def assert_matches_pattern(column, pattern: str):
        """Assert all column values match pattern."""
        result = column.matches(pattern)
        if not result:
            pytest.fail(
                f"Column '{column.name}' has {result.actual_value} values "
                f"not matching pattern '{pattern}'"
            )


@pytest.fixture
def duckguard_assert():
    """Provide DuckGuard assertion helpers with better error messages."""
    return DuckGuardAssertionHelper()
