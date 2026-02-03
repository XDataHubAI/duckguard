"""Tests for cross-dataset validation (Reference/FK checks)."""

import gc
import os
import tempfile

import pytest

from duckguard import connect
from duckguard.core.engine import DuckGuardEngine

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_engine():
    """Reset engine singleton before each test."""
    DuckGuardEngine.reset_instance()
    yield
    DuckGuardEngine.reset_instance()
    gc.collect()


@pytest.fixture
def customers_csv():
    """Create a customers reference table."""
    content = """id,name,email
CUST-001,Alice,alice@example.com
CUST-002,Bob,bob@example.com
CUST-003,Charlie,charlie@example.com
CUST-004,Diana,diana@example.com
CUST-005,Eve,eve@example.com
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def orders_valid_csv():
    """Create orders with all valid customer references."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-003,150.00,shipped
ORD-004,CUST-001,50.00,delivered
ORD-005,CUST-004,300.00,pending
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def orders_with_orphans_csv():
    """Create orders with some invalid customer references."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-999,150.00,shipped
ORD-004,,50.00,delivered
ORD-005,CUST-888,300.00,pending
ORD-006,CUST-003,75.00,shipped
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def status_lookup_csv():
    """Create a status lookup table."""
    content = """code,description
shipped,Order has been shipped
pending,Order is pending
delivered,Order has been delivered
cancelled,Order was cancelled
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def backup_orders_csv():
    """Create a backup orders table with same row count."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-003,150.00,shipped
ORD-004,CUST-001,50.00,delivered
ORD-005,CUST-004,300.00,pending
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


@pytest.fixture
def backup_orders_different_count_csv():
    """Create a backup orders table with different row count."""
    content = """order_id,customer_id,amount,status
ORD-001,CUST-001,100.00,shipped
ORD-002,CUST-002,200.00,pending
ORD-003,CUST-003,150.00,shipped
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    gc.collect()
    try:
        os.unlink(temp_path)
    except PermissionError:
        pass


# ============================================================================
# Tests for exists_in()
# ============================================================================


class TestExistsIn:
    """Tests for Column.exists_in() method."""

    def test_all_values_exist(self, orders_valid_csv, customers_csv):
        """Test when all FK values are valid."""
        orders = connect(orders_valid_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])

        assert result.passed is True
        assert result.actual_value == 0  # 0 orphans
        assert len(result.failed_rows) == 0

    def test_orphan_values_detected(self, orders_with_orphans_csv, customers_csv):
        """Test detection of invalid FK values."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])

        assert result.passed is False
        assert result.actual_value == 2  # CUST-999 and CUST-888
        assert len(result.failed_rows) == 2
        assert result.total_failures == 2

    def test_nulls_are_ignored(self, orders_with_orphans_csv, customers_csv):
        """Test that null FK values are ignored by default."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])

        # Orphan count should be 2 (CUST-999 and CUST-888), not 3 (null is ignored)
        assert result.actual_value == 2

    def test_failed_rows_contain_orphan_values(self, orders_with_orphans_csv, customers_csv):
        """Test that failed rows contain the actual orphan values."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])

        orphan_values = [row.value for row in result.failed_rows]
        assert "CUST-999" in orphan_values
        assert "CUST-888" in orphan_values

    def test_result_details(self, orders_with_orphans_csv, customers_csv):
        """Test that result contains useful details."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])

        assert "orphan_count" in result.details
        assert "reference_column" in result.details
        assert result.details["orphan_count"] == 2
        assert result.details["reference_column"] == "id"

    def test_capture_failures_disabled(self, orders_with_orphans_csv, customers_csv):
        """Test that capture_failures=False skips row capture."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(
            customers["id"], capture_failures=False
        )

        assert result.passed is False
        assert result.actual_value == 2
        assert len(result.failed_rows) == 0  # No rows captured


# ============================================================================
# Tests for references()
# ============================================================================


class TestReferences:
    """Tests for Column.references() method."""

    def test_allow_nulls_true_ignores_nulls(self, orders_with_orphans_csv, customers_csv):
        """Test that allow_nulls=True (default) ignores null values."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].references(customers["id"], allow_nulls=True)

        # Only orphans counted, not nulls
        assert result.actual_value == 2

    def test_allow_nulls_false_counts_nulls(self, orders_with_orphans_csv, customers_csv):
        """Test that allow_nulls=False counts nulls as failures."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].references(customers["id"], allow_nulls=False)

        # Should count 2 orphans + 1 null = 3 failures
        assert result.actual_value == 3
        assert result.passed is False
        assert "null_count" in result.details
        assert result.details["null_count"] == 1
        assert result.details["orphan_count"] == 2

    def test_references_passes_with_valid_data(self, orders_valid_csv, customers_csv):
        """Test that references passes with valid FK data."""
        orders = connect(orders_valid_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].references(customers["id"])

        assert result.passed is True


# ============================================================================
# Tests for find_orphans()
# ============================================================================


class TestFindOrphans:
    """Tests for Column.find_orphans() method."""

    def test_returns_orphan_values(self, orders_with_orphans_csv, customers_csv):
        """Test that orphan values are returned."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        orphans = orders["customer_id"].find_orphans(customers["id"])

        assert len(orphans) == 2
        assert "CUST-999" in orphans
        assert "CUST-888" in orphans

    def test_returns_empty_when_all_valid(self, orders_valid_csv, customers_csv):
        """Test that empty list returned when all values are valid."""
        orders = connect(orders_valid_csv)
        customers = connect(customers_csv)

        orphans = orders["customer_id"].find_orphans(customers["id"])

        assert len(orphans) == 0

    def test_respects_limit(self, orders_with_orphans_csv, customers_csv):
        """Test that limit parameter is respected."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        orphans = orders["customer_id"].find_orphans(customers["id"], limit=1)

        assert len(orphans) == 1


# ============================================================================
# Tests for matches_values()
# ============================================================================


class TestMatchesValues:
    """Tests for Column.matches_values() method."""

    def test_identical_value_sets_pass(self, orders_valid_csv, status_lookup_csv):
        """Test that identical value sets pass."""
        orders = connect(orders_valid_csv)
        status_lookup = connect(status_lookup_csv)

        # Orders has: shipped, pending, delivered
        # Status lookup has: shipped, pending, delivered, cancelled
        # So orders.status should have all its values in status_lookup
        result = orders["status"].matches_values(status_lookup["code"])

        # This will fail because status_lookup has "cancelled" which orders doesn't have
        assert result.passed is False
        assert result.details["extra_in_other"] == 1  # "cancelled"
        assert result.details["missing_in_other"] == 0

    def test_missing_values_detected(self, orders_with_orphans_csv, status_lookup_csv):
        """Test detection of missing values."""
        orders = connect(orders_with_orphans_csv)
        status_lookup = connect(status_lookup_csv)

        result = orders["status"].matches_values(status_lookup["code"])

        # Orders has same status values, status_lookup has "cancelled" extra
        assert result.passed is False
        assert "missing_in_other" in result.details
        assert "extra_in_other" in result.details


# ============================================================================
# Tests for row_count_matches()
# ============================================================================


class TestRowCountMatches:
    """Tests for Dataset.row_count_matches() method."""

    def test_matching_counts_pass(self, orders_valid_csv, backup_orders_csv):
        """Test that matching row counts pass."""
        orders = connect(orders_valid_csv)
        backup = connect(backup_orders_csv)

        result = orders.row_count_matches(backup)

        assert result.passed is True
        assert result.actual_value == 0  # 0 difference
        assert result.details["source_count"] == 5
        assert result.details["other_count"] == 5

    def test_different_counts_fail(self, orders_valid_csv, backup_orders_different_count_csv):
        """Test that different row counts fail."""
        orders = connect(orders_valid_csv)
        backup = connect(backup_orders_different_count_csv)

        result = orders.row_count_matches(backup)

        assert result.passed is False
        assert result.actual_value == 2  # Difference of 2
        assert result.details["source_count"] == 5
        assert result.details["other_count"] == 3

    def test_tolerance_allows_small_difference(
        self, orders_valid_csv, backup_orders_different_count_csv
    ):
        """Test that tolerance parameter allows small differences."""
        orders = connect(orders_valid_csv)
        backup = connect(backup_orders_different_count_csv)

        result = orders.row_count_matches(backup, tolerance=5)

        assert result.passed is True
        assert result.actual_value == 2

    def test_tolerance_exact_boundary(
        self, orders_valid_csv, backup_orders_different_count_csv
    ):
        """Test tolerance at exact boundary."""
        orders = connect(orders_valid_csv)
        backup = connect(backup_orders_different_count_csv)

        # Difference is 2
        result_pass = orders.row_count_matches(backup, tolerance=2)
        result_fail = orders.row_count_matches(backup, tolerance=1)

        assert result_pass.passed is True
        assert result_fail.passed is False


class TestRowCountEquals:
    """Tests for Dataset.row_count_equals() method."""

    def test_equals_is_alias_for_matches_zero_tolerance(
        self, orders_valid_csv, backup_orders_csv
    ):
        """Test that row_count_equals is an alias for row_count_matches(tolerance=0)."""
        orders = connect(orders_valid_csv)
        backup = connect(backup_orders_csv)

        result_equals = orders.row_count_equals(backup)
        result_matches = orders.row_count_matches(backup, tolerance=0)

        assert result_equals.passed == result_matches.passed
        assert result_equals.actual_value == result_matches.actual_value


# ============================================================================
# Integration Tests
# ============================================================================


class TestCrossDatasetIntegration:
    """Integration tests for cross-dataset validation."""

    def test_multiple_fk_checks_same_reference(self, orders_with_orphans_csv, customers_csv):
        """Test multiple FK checks against the same reference."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result1 = orders["customer_id"].exists_in(customers["id"])
        result2 = orders["customer_id"].references(customers["id"])

        # Both should detect the same orphans
        assert result1.actual_value == result2.actual_value

    def test_chained_validations(
        self, orders_with_orphans_csv, customers_csv, status_lookup_csv
    ):
        """Test chaining multiple cross-dataset validations."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)
        status_lookup = connect(status_lookup_csv)

        # Check FK reference
        fk_result = orders["customer_id"].exists_in(customers["id"])

        # Check status values
        status_result = orders["status"].matches_values(status_lookup["code"])

        assert fk_result.passed is False  # Has orphans
        assert status_result.passed is False  # Has mismatches

    def test_validation_result_summary(self, orders_with_orphans_csv, customers_csv):
        """Test that validation result summary is readable."""
        orders = connect(orders_with_orphans_csv)
        customers = connect(customers_csv)

        result = orders["customer_id"].exists_in(customers["id"])
        summary = result.summary()

        assert "customer_id" in summary
        assert "2" in summary  # Should mention 2 orphans
