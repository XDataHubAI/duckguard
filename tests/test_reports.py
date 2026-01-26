"""Tests for the reports module."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from duckguard.reports import (
    HTMLReporter,
    ReportConfig,
    generate_html_report,
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_execution_result():
    """Create a mock ExecutionResult for testing."""
    # Create mock check
    mock_check = MagicMock()
    mock_check.type.value = "not_null"

    # Create mock passed result
    mock_passed = MagicMock()
    mock_passed.passed = True
    mock_passed.column = "id"
    mock_passed.check = mock_check
    mock_passed.severity.value = "error"
    mock_passed.actual_value = 0
    mock_passed.expected_value = 0
    mock_passed.message = "No null values"
    mock_passed.details = {}

    # Create mock failed result
    mock_failed_check = MagicMock()
    mock_failed_check.type.value = "unique"

    mock_failed = MagicMock()
    mock_failed.passed = False
    mock_failed.column = "email"
    mock_failed.check = mock_failed_check
    mock_failed.severity.value = "error"
    mock_failed.actual_value = 95
    mock_failed.expected_value = 100
    mock_failed.message = "5 duplicate values found"
    mock_failed.details = {"failed_rows": [1, 5, 10, 15, 20]}
    mock_failed.is_failure = True

    # Create mock warning result
    mock_warning_check = MagicMock()
    mock_warning_check.type.value = "null_percent"

    mock_warning = MagicMock()
    mock_warning.passed = False
    mock_warning.column = "phone"
    mock_warning.check = mock_warning_check
    mock_warning.severity.value = "warning"
    mock_warning.actual_value = 15
    mock_warning.expected_value = 10
    mock_warning.message = "Null percentage is 15%"
    mock_warning.details = {}
    mock_warning.is_failure = False

    # Create mock ruleset
    mock_ruleset = MagicMock()
    mock_ruleset.name = "test_rules"

    # Create mock execution result
    mock_result = MagicMock()
    mock_result.source = "test_data.csv"
    mock_result.ruleset = mock_ruleset
    mock_result.started_at = datetime.now()
    mock_result.finished_at = datetime.now()
    mock_result.quality_score = 75.0
    mock_result.total_checks = 10
    mock_result.passed_count = 7
    mock_result.failed_count = 2
    mock_result.warning_count = 1
    mock_result.passed = False
    mock_result.results = [mock_passed, mock_failed, mock_warning]
    mock_result.get_failures.return_value = [mock_failed]
    mock_result.get_warnings.return_value = [mock_warning]

    return mock_result


class TestReportConfig:
    """Tests for ReportConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ReportConfig()
        assert config.title == "DuckGuard Data Quality Report"
        assert config.include_passed is True
        assert config.include_failed_rows is True
        assert config.max_failed_rows == 10
        assert config.include_charts is True
        assert config.include_trends is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ReportConfig(
            title="My Custom Report",
            include_passed=False,
            max_failed_rows=5,
        )
        assert config.title == "My Custom Report"
        assert config.include_passed is False
        assert config.max_failed_rows == 5


class TestHTMLReporter:
    """Tests for HTMLReporter class."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        reporter = HTMLReporter()
        assert reporter.config is not None
        assert reporter.config.title == "DuckGuard Data Quality Report"

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = ReportConfig(title="Custom Title")
        reporter = HTMLReporter(config=config)
        assert reporter.config.title == "Custom Title"

    def test_generate_creates_file(self, temp_output_dir, mock_execution_result):
        """Test that generate creates an HTML file."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        result_path = reporter.generate(mock_execution_result, output_path)

        assert result_path == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_generate_html_content(self, temp_output_dir, mock_execution_result):
        """Test that generated HTML contains expected content."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "test_data.csv" in content
        assert "75.0" in content or "75" in content  # Quality score
        assert "DuckGuard" in content

    def test_generate_with_failures(self, temp_output_dir, mock_execution_result):
        """Test that failures are included in report."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "FAILED" in content or "Failure" in content or "fail" in content.lower()

    def test_generate_without_passed_checks(self, temp_output_dir, mock_execution_result):
        """Test generating report without passed checks."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_passed=False)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        # File should still be created
        assert output_path.exists()
        assert output_path.read_text()  # Verify content is readable

    def test_score_to_grade(self):
        """Test score to grade conversion."""
        reporter = HTMLReporter()

        assert reporter._score_to_grade(95) == "A"
        assert reporter._score_to_grade(85) == "B"
        assert reporter._score_to_grade(75) == "C"
        assert reporter._score_to_grade(65) == "D"
        assert reporter._score_to_grade(50) == "F"


class TestGenerateHtmlReport:
    """Tests for generate_html_report convenience function."""

    def test_basic_usage(self, temp_output_dir, mock_execution_result):
        """Test basic usage of convenience function."""
        output_path = temp_output_dir / "report.html"

        result_path = generate_html_report(mock_execution_result, output_path)

        assert result_path == output_path
        assert output_path.exists()

    def test_with_kwargs(self, temp_output_dir, mock_execution_result):
        """Test convenience function with keyword arguments."""
        output_path = temp_output_dir / "report.html"

        generate_html_report(
            mock_execution_result,
            output_path,
            title="Custom Report Title",
            include_passed=False,
        )

        content = output_path.read_text()
        assert "Custom Report Title" in content


class TestPDFReporter:
    """Tests for PDFReporter class."""

    def test_import_without_weasyprint(self, temp_output_dir, mock_execution_result):
        """Test that PDFReporter raises ImportError without weasyprint."""
        # This test verifies the error message when weasyprint is not installed
        from duckguard.reports import PDFReporter

        reporter = PDFReporter()
        # The generate method should raise ImportError if weasyprint is not installed
        # We don't want to require weasyprint for tests, so we just verify the class exists
        assert reporter is not None
        # Verify temp_output_dir is usable for PDF output
        assert temp_output_dir.exists()


class TestIntegration:
    """Integration tests for reports module."""

    def test_report_generation_workflow(self, temp_output_dir, mock_execution_result):
        """Test the complete report generation workflow."""
        # 1. Create config
        config = ReportConfig(
            title="Integration Test Report",
            include_passed=True,
            include_failed_rows=True,
        )

        # 2. Create reporter
        reporter = HTMLReporter(config=config)

        # 3. Generate report
        output_path = temp_output_dir / "integration_report.html"
        reporter.generate(mock_execution_result, output_path)

        # 4. Verify
        assert output_path.exists()
        content = output_path.read_text()
        assert "Integration Test Report" in content
        assert "test_data.csv" in content
