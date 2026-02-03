"""Tests for enhanced error messages."""


from duckguard.errors import (
    ColumnNotFoundError,
    ContractViolationError,
    DuckGuardError,
    RuleParseError,
    UnsupportedConnectorError,
    ValidationError,
    format_multiple_failures,
    format_validation_failure,
)


class TestDuckGuardError:
    """Tests for base DuckGuardError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = DuckGuardError("Something went wrong")
        assert "Something went wrong" in str(error)

    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        error = DuckGuardError(
            "Something went wrong",
            suggestion="Try doing X instead",
        )
        msg = str(error)
        assert "Something went wrong" in msg
        assert "Suggestion: Try doing X instead" in msg

    def test_error_with_docs_url(self):
        """Test error with documentation URL."""
        error = DuckGuardError(
            "Something went wrong",
            docs_url="https://docs.example.com/help",
        )
        msg = str(error)
        assert "Docs: https://docs.example.com/help" in msg

    def test_error_with_context(self):
        """Test error with context dict."""
        error = DuckGuardError(
            "Something went wrong",
            context={"file": "test.csv", "line": 42},
        )
        msg = str(error)
        assert "Context:" in msg
        assert "file: test.csv" in msg
        assert "line: 42" in msg


class TestColumnNotFoundError:
    """Tests for ColumnNotFoundError."""

    def test_basic_error(self):
        """Test basic column not found error."""
        error = ColumnNotFoundError(
            column="order_id",
            available_columns=["id", "customer_id", "amount"],
        )
        msg = str(error)
        assert "Column 'order_id' not found" in msg
        assert "Available columns:" in msg

    def test_suggests_similar_column(self):
        """Test that similar column names are suggested."""
        error = ColumnNotFoundError(
            column="order",
            available_columns=["order_id", "customer_id", "amount"],
        )
        msg = str(error)
        # Should suggest order_id as it contains "order"
        assert "order_id" in msg

    def test_suggests_partial_match(self):
        """Test suggestion for partial matches."""
        error = ColumnNotFoundError(
            column="ord",
            available_columns=["order_id", "customer_id", "amount"],
        )
        msg = str(error)
        assert "Did you mean: order_id?" in msg


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError(
            check_name="not_null",
            column="email",
            actual_value=5,
            expected_value=0,
        )
        msg = str(error)
        assert "Validation check 'not_null' failed" in msg
        assert "column 'email'" in msg

    def test_validation_error_with_failed_rows(self):
        """Test validation error with failed rows."""
        error = ValidationError(
            check_name="between",
            column="amount",
            actual_value=3,
            expected_value="[0, 100]",
            failed_rows=[150, 200, 300],
        )
        msg = str(error)
        assert "Sample failing values:" in msg
        assert "150" in msg

    def test_table_level_validation_error(self):
        """Test table-level validation error (no column)."""
        error = ValidationError(
            check_name="row_count",
            actual_value=0,
            expected_value=">= 1",
        )
        msg = str(error)
        assert "Validation check 'row_count' failed" in msg
        # Should not have "for column" since no column is specified
        assert "for column" not in msg


class TestRuleParseError:
    """Tests for RuleParseError."""

    def test_basic_parse_error(self):
        """Test basic parse error."""
        error = RuleParseError("Invalid check type")
        msg = str(error)
        assert "Failed to parse rules" in msg
        assert "Invalid check type" in msg

    def test_parse_error_with_location(self):
        """Test parse error with file location."""
        error = RuleParseError(
            "Unknown field 'foo'",
            file_path="duckguard.yaml",
            line_number=15,
        )
        msg = str(error)
        assert "in duckguard.yaml" in msg
        assert "at line 15" in msg

    def test_includes_example(self):
        """Test that parse error includes example YAML."""
        error = RuleParseError("Invalid syntax")
        msg = str(error)
        assert "Example valid rule:" in msg
        assert "columns:" in msg


class TestContractViolationError:
    """Tests for ContractViolationError."""

    def test_basic_violation(self):
        """Test basic contract violation."""
        error = ContractViolationError(
            violations=["Column 'email' removed", "Column 'phone' type changed"],
        )
        msg = str(error)
        assert "Data contract violated with 2 issue(s)" in msg
        assert "Column 'email' removed" in msg
        assert "Column 'phone' type changed" in msg

    def test_with_contract_path(self):
        """Test violation with contract path."""
        error = ContractViolationError(
            violations=["Missing column"],
            contract_path="contracts/orders_v1.yaml",
        )
        msg = str(error)
        assert "contracts/orders_v1.yaml" in msg

    def test_truncates_many_violations(self):
        """Test that many violations are truncated."""
        violations = [f"Violation {i}" for i in range(20)]
        error = ContractViolationError(violations=violations)
        msg = str(error)
        assert "... and 15 more" in msg


class TestUnsupportedConnectorError:
    """Tests for UnsupportedConnectorError."""

    def test_basic_error(self):
        """Test basic unsupported connector error."""
        error = UnsupportedConnectorError(source="data.xyz")
        msg = str(error)
        assert "No connector found for: data.xyz" in msg

    def test_lists_supported_formats(self):
        """Test that error lists supported formats."""
        error = UnsupportedConnectorError(source="data.xyz")
        msg = str(error)
        assert "Supported formats:" in msg
        assert "CSV (.csv)" in msg
        assert "Parquet" in msg
        assert "PostgreSQL" in msg


class TestFormatFunctions:
    """Tests for formatting utility functions."""

    def test_format_validation_failure(self):
        """Test format_validation_failure function."""
        output = format_validation_failure(
            check_name="between",
            column="amount",
            actual=5,
            expected="[0, 100]",
        )
        assert "Check 'between' failed for column 'amount'" in output
        assert "Expected: [0, 100]" in output
        assert "Actual: 5" in output

    def test_format_validation_failure_with_rows(self):
        """Test format_validation_failure with failed rows."""
        from duckguard.core.result import FailedRow

        failed_rows = [
            FailedRow(row_index=1, column="amount", value=150, expected="<= 100"),
            FailedRow(row_index=2, column="amount", value=200, expected="<= 100"),
        ]
        output = format_validation_failure(
            check_name="max",
            column="amount",
            actual=2,
            expected="0",
            failed_rows=failed_rows,
        )
        assert "Sample failing rows:" in output
        assert "Row 1: 150" in output
        assert "Row 2: 200" in output

    def test_format_multiple_failures(self):
        """Test format_multiple_failures function."""
        from unittest.mock import Mock

        failures = [
            Mock(column="order_id", message="5 null values"),
            Mock(column="amount", message="3 values out of range"),
        ]
        output = format_multiple_failures(failures)
        assert "2 validation check(s) failed" in output
        assert "[order_id]" in output
        assert "[amount]" in output

    def test_format_multiple_failures_empty(self):
        """Test format_multiple_failures with no failures."""
        output = format_multiple_failures([])
        assert "All checks passed!" in output
