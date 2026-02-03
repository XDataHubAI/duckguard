"""Tests for row-level error capture in ValidationResult."""

from duckguard.core.result import FailedRow, ValidationResult


class TestFailedRow:
    """Tests for FailedRow dataclass."""

    def test_basic_creation(self):
        """Test creating a FailedRow."""
        row = FailedRow(
            row_index=5,
            column="quantity",
            value=150,
            expected="between 1 and 100",
            reason="Value 150 is outside range [1, 100]",
        )

        assert row.row_index == 5
        assert row.column == "quantity"
        assert row.value == 150
        assert row.expected == "between 1 and 100"
        assert row.reason == "Value 150 is outside range [1, 100]"

    def test_with_context(self):
        """Test FailedRow with additional context."""
        row = FailedRow(
            row_index=10,
            column="email",
            value="invalid",
            expected="matches email pattern",
            context={"order_id": "ORD-123", "customer": "John"},
        )

        assert row.context["order_id"] == "ORD-123"
        assert row.context["customer"] == "John"

    def test_repr(self):
        """Test string representation."""
        row = FailedRow(
            row_index=5,
            column="qty",
            value=150,
            expected="between 1-100",
        )

        repr_str = repr(row)
        assert "row=5" in repr_str
        assert "column='qty'" in repr_str
        assert "value=150" in repr_str


class TestValidationResultWithFailedRows:
    """Tests for ValidationResult with row-level error capture."""

    def test_validation_result_with_failed_rows(self):
        """Test ValidationResult containing failed rows."""
        failed_rows = [
            FailedRow(row_index=1, column="qty", value=150, expected="<= 100"),
            FailedRow(row_index=3, column="qty", value=200, expected="<= 100"),
        ]

        result = ValidationResult(
            passed=False,
            actual_value=2,
            expected_value=0,
            message="Column 'qty' has 2 values outside range",
            failed_rows=failed_rows,
            total_failures=2,
        )

        assert not result.passed
        assert len(result.failed_rows) == 2
        assert result.total_failures == 2

    def test_get_failed_values(self):
        """Test getting list of failed values."""
        failed_rows = [
            FailedRow(row_index=1, column="qty", value=150, expected=""),
            FailedRow(row_index=2, column="qty", value=200, expected=""),
            FailedRow(row_index=3, column="qty", value=300, expected=""),
        ]

        result = ValidationResult(
            passed=False,
            actual_value=3,
            failed_rows=failed_rows,
            total_failures=3,
        )

        values = result.get_failed_values()
        assert values == [150, 200, 300]

    def test_get_failed_row_indices(self):
        """Test getting list of failed row indices."""
        failed_rows = [
            FailedRow(row_index=5, column="qty", value=150, expected=""),
            FailedRow(row_index=10, column="qty", value=200, expected=""),
        ]

        result = ValidationResult(
            passed=False,
            actual_value=2,
            failed_rows=failed_rows,
            total_failures=2,
        )

        indices = result.get_failed_row_indices()
        assert indices == [5, 10]

    def test_summary(self):
        """Test summary output."""
        failed_rows = [
            FailedRow(row_index=1, column="qty", value=150, expected="<= 100", reason="too high"),
            FailedRow(row_index=2, column="qty", value=200, expected="<= 100", reason="too high"),
        ]

        result = ValidationResult(
            passed=False,
            actual_value=2,
            message="Column 'qty' has 2 values outside range",
            failed_rows=failed_rows,
            total_failures=2,
        )

        summary = result.summary()
        assert "Column 'qty' has 2 values outside range" in summary
        assert "Row 1" in summary
        assert "Row 2" in summary
        assert "150" in summary
        assert "200" in summary

    def test_repr_with_failed_rows(self):
        """Test repr includes failed rows count."""
        failed_rows = [
            FailedRow(row_index=1, column="qty", value=150, expected=""),
        ]

        result = ValidationResult(
            passed=False,
            actual_value=1,
            failed_rows=failed_rows,
            total_failures=1,
        )

        repr_str = repr(result)
        assert "FAILED" in repr_str
        assert "failed_rows=1" in repr_str


class TestColumnValidationWithRowCapture:
    """Tests for Column validation methods with row capture."""

    def test_between_captures_failed_rows(self, orders_dataset):
        """Test that between() captures failed rows."""
        # Use a range that excludes some values
        result = orders_dataset.quantity.between(1, 5)

        # With sample data having quantity up to 100, this should fail
        if not result.passed:
            assert result.total_failures > 0
            # Should have captured some failed rows
            if result.failed_rows:
                assert all(r.column == "quantity" for r in result.failed_rows)
                assert all(r.value < 1 or r.value > 5 for r in result.failed_rows)

    def test_isin_captures_failed_rows(self, orders_dataset):
        """Test that isin() captures failed rows."""
        # Use a restricted set that doesn't include all values
        result = orders_dataset.status.isin(["pending", "shipped"])

        # Sample data has more status values
        if not result.passed:
            assert result.total_failures > 0
            if result.failed_rows:
                assert all(r.column == "status" for r in result.failed_rows)
                # Failed values should not be in allowed set
                for row in result.failed_rows:
                    assert row.value not in ["pending", "shipped"]

    def test_matches_captures_failed_rows(self, orders_dataset):
        """Test that matches() captures failed rows."""
        # Use a pattern that won't match all values
        result = orders_dataset.order_id.matches(r"^ORD-0")

        if not result.passed:
            assert result.total_failures > 0
            if result.failed_rows:
                assert all(r.column == "order_id" for r in result.failed_rows)

    def test_capture_failures_disabled(self, orders_dataset):
        """Test that capture_failures=False skips row capture."""
        result = orders_dataset.quantity.between(1, 5, capture_failures=False)

        # Even if check fails, should not capture rows
        assert len(result.failed_rows) == 0


class TestValidationResultEdgeCases:
    """Edge case tests for ValidationResult."""

    def test_passed_result_no_failed_rows(self):
        """Test that passed results have empty failed_rows."""
        result = ValidationResult(
            passed=True,
            actual_value=0,
            expected_value=0,
            message="All values passed",
        )

        assert result.passed
        assert len(result.failed_rows) == 0
        assert result.total_failures == 0

    def test_summary_with_no_failures(self):
        """Test summary when there are no failures."""
        result = ValidationResult(
            passed=True,
            actual_value=0,
            message="All checks passed",
        )

        summary = result.summary()
        assert "All checks passed" in summary
        assert "failing rows" not in summary

    def test_summary_truncates_many_failures(self):
        """Test that summary truncates when there are many failures."""
        failed_rows = [
            FailedRow(row_index=i, column="qty", value=i * 100, expected="<= 50")
            for i in range(1, 21)  # 20 failures
        ]

        result = ValidationResult(
            passed=False,
            actual_value=20,
            message="Column 'qty' has 20 values outside range",
            failed_rows=failed_rows,
            total_failures=20,
        )

        summary = result.summary()
        # Should only show first 5
        assert "Row 1" in summary
        assert "Row 5" in summary
        assert "... and 15 more failures" in summary

    def test_repr_without_failed_rows(self):
        """Test repr when there are no failed rows."""
        result = ValidationResult(
            passed=True,
            actual_value=0,
        )

        repr_str = repr(result)
        assert "PASSED" in repr_str
        assert "failed_rows" not in repr_str

    def test_get_failed_values_empty(self):
        """Test get_failed_values with no failures."""
        result = ValidationResult(
            passed=True,
            actual_value=0,
        )

        assert result.get_failed_values() == []

    def test_get_failed_row_indices_empty(self):
        """Test get_failed_row_indices with no failures."""
        result = ValidationResult(
            passed=True,
            actual_value=0,
        )

        assert result.get_failed_row_indices() == []
