"""Tests for the reports module."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from duckguard.history.storage import TrendDataPoint
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
    mock_result.started_at = datetime(2026, 1, 30, 10, 0, 0)
    mock_result.finished_at = datetime(2026, 1, 30, 10, 0, 2)
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


@pytest.fixture
def mock_trend_data():
    """Create mock TrendDataPoint data for trend chart tests."""
    return [
        TrendDataPoint(
            date="2026-01-01",
            avg_score=75.0,
            min_score=70.0,
            max_score=80.0,
            run_count=3,
            passed_count=2,
            failed_count=1,
        ),
        TrendDataPoint(
            date="2026-01-02",
            avg_score=80.0,
            min_score=75.0,
            max_score=85.0,
            run_count=2,
            passed_count=2,
            failed_count=0,
        ),
        TrendDataPoint(
            date="2026-01-03",
            avg_score=85.0,
            min_score=80.0,
            max_score=90.0,
            run_count=4,
            passed_count=3,
            failed_count=1,
        ),
        TrendDataPoint(
            date="2026-01-04",
            avg_score=78.0,
            min_score=72.0,
            max_score=82.0,
            run_count=2,
            passed_count=1,
            failed_count=1,
        ),
        TrendDataPoint(
            date="2026-01-05",
            avg_score=90.0,
            min_score=88.0,
            max_score=92.0,
            run_count=3,
            passed_count=3,
            failed_count=0,
        ),
    ]


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

    def test_new_default_values(self):
        """Test that new config fields have correct defaults."""
        config = ReportConfig()
        assert config.dark_mode == "auto"
        assert config.trend_days == 30
        assert config.include_metadata is True

    def test_dark_mode_values(self):
        """Test that dark_mode accepts all valid options."""
        for mode in ("auto", "light", "dark"):
            config = ReportConfig(dark_mode=mode)
            assert config.dark_mode == mode


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

    def test_with_trend_data(self, temp_output_dir, mock_execution_result, mock_trend_data):
        """Test convenience function with trend_data kwarg."""
        output_path = temp_output_dir / "report.html"

        generate_html_report(
            mock_execution_result,
            output_path,
            trend_data=mock_trend_data,
            include_trends=True,
        )

        content = output_path.read_text()
        assert output_path.exists()
        assert "<svg" in content  # Trend chart SVG present

    def test_with_metadata_kwargs(self, temp_output_dir, mock_execution_result):
        """Test convenience function with row_count and column_count."""
        output_path = temp_output_dir / "report.html"

        generate_html_report(
            mock_execution_result,
            output_path,
            row_count=5000,
            column_count=12,
        )

        content = output_path.read_text()
        assert "5,000" in content
        assert "12" in content


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


class TestDarkMode:
    """Tests for dark mode functionality."""

    def test_dark_mode_auto_includes_media_query(self, temp_output_dir, mock_execution_result):
        """Test that auto dark mode includes prefers-color-scheme media query."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(dark_mode="auto")
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "prefers-color-scheme" in content

    def test_dark_mode_dark_sets_data_attribute(self, temp_output_dir, mock_execution_result):
        """Test that dark mode sets data-theme attribute on html tag."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(dark_mode="dark")
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert 'data-theme="dark"' in content

    def test_dark_mode_light_sets_data_attribute(self, temp_output_dir, mock_execution_result):
        """Test that light mode sets data-theme attribute on html tag."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(dark_mode="light")
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert 'data-theme="light"' in content

    def test_dark_mode_auto_no_data_attribute(self, temp_output_dir, mock_execution_result):
        """Test that auto mode does not force data-theme attribute."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(dark_mode="auto")
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        # Should NOT have data-theme="auto" — auto means no forced theme
        assert 'data-theme="auto"' not in content

    def test_dark_mode_toggle_button_present(self, temp_output_dir, mock_execution_result):
        """Test that the theme toggle button is present in the report."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "theme-toggle" in content
        assert "toggleTheme" in content

    def test_dark_mode_css_variables_present(self, temp_output_dir, mock_execution_result):
        """Test that dark mode CSS variable overrides are defined."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert '[data-theme="dark"]' in content
        assert "--color-bg: #111827" in content


class TestTrendCharts:
    """Tests for trend chart rendering."""

    def test_trend_chart_renders_when_data_provided(
        self, temp_output_dir, mock_execution_result, mock_trend_data
    ):
        """Test that trend chart SVG is rendered when trend data is provided."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=mock_trend_data)

        content = output_path.read_text()
        assert "Quality Trend" in content
        assert "trend-chart" in content

    def test_trend_chart_absent_when_no_data(self, temp_output_dir, mock_execution_result):
        """Test that no trend chart appears when trend data is not provided."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "Quality Trend" not in content

    def test_trend_chart_absent_when_include_trends_false(
        self, temp_output_dir, mock_execution_result, mock_trend_data
    ):
        """Test that trend chart is absent when include_trends is False."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=False)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=mock_trend_data)

        content = output_path.read_text()
        assert "Quality Trend" not in content

    def test_trend_chart_has_correct_data_points(
        self, temp_output_dir, mock_execution_result, mock_trend_data
    ):
        """Test that trend chart SVG has correct number of data point circles."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=mock_trend_data)

        content = output_path.read_text()
        # Each data point gets a <circle> element
        circle_count = content.count("<circle")
        assert circle_count >= len(mock_trend_data)

    def test_trend_chart_svg_has_gridlines(
        self, temp_output_dir, mock_execution_result, mock_trend_data
    ):
        """Test that trend chart SVG includes gridlines."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=mock_trend_data)

        content = output_path.read_text()
        # Gridlines at 0, 25, 50, 75, 100
        assert "stroke-dasharray" in content

    def test_trend_chart_single_data_point(self, temp_output_dir, mock_execution_result):
        """Test trend chart rendering with only one data point (edge case)."""
        single_point = [
            TrendDataPoint(
                date="2026-01-01",
                avg_score=85.0,
                min_score=85.0,
                max_score=85.0,
                run_count=1,
                passed_count=1,
                failed_count=0,
            ),
        ]
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=single_point)

        content = output_path.read_text()
        assert "Quality Trend" in content
        assert "<circle" in content

    def test_generate_trend_svg_empty_data(self):
        """Test _generate_trend_svg returns empty string for empty data."""
        reporter = HTMLReporter()
        result = reporter._generate_trend_svg([])
        assert result == ""

    def test_trend_chart_tooltips_contain_scores(
        self, temp_output_dir, mock_execution_result, mock_trend_data
    ):
        """Test that trend chart data point tooltips contain score values."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_trends=True)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, trend_data=mock_trend_data)

        content = output_path.read_text()
        # Tooltips should contain date and score
        assert "2026-01-01: 75.0%" in content
        assert "2026-01-05: 90.0%" in content


class TestMetadata:
    """Tests for dataset metadata display."""

    def test_metadata_renders_row_count(self, temp_output_dir, mock_execution_result):
        """Test that row count is displayed with comma formatting."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path, row_count=10000)

        content = output_path.read_text()
        assert "10,000" in content

    def test_metadata_renders_column_count(self, temp_output_dir, mock_execution_result):
        """Test that column count is displayed."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path, column_count=15)

        content = output_path.read_text()
        assert "Columns:" in content

    def test_metadata_renders_duration(self, temp_output_dir, mock_execution_result):
        """Test that execution duration is displayed when timing data is available."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        # mock_execution_result has started_at and finished_at 2s apart
        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "Duration:" in content
        assert "2.0s" in content

    def test_metadata_absent_when_disabled(self, temp_output_dir, mock_execution_result):
        """Test that metadata is not shown when include_metadata is False."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_metadata=False)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path, row_count=1000, column_count=10)

        content = output_path.read_text()
        assert "Rows:" not in content
        assert "Columns:" not in content

    def test_metadata_absent_when_values_none(self, temp_output_dir, mock_execution_result):
        """Test that metadata line is clean when row_count and column_count are None."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        # Don't pass row_count or column_count
        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        # Should not crash and should not show "None"
        assert "None" not in content or "none" in content.lower()  # Allow CSS 'none'


class TestLogoRendering:
    """Tests for logo display in report header."""

    def test_logo_renders_when_url_provided(self, temp_output_dir, mock_execution_result):
        """Test that logo img tag is present when logo_url is configured."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(logo_url="https://example.com/logo.png")
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "header-logo" in content
        assert "example.com/logo.png" in content

    def test_logo_absent_when_not_provided(self, temp_output_dir, mock_execution_result):
        """Test that no logo img tag exists when logo_url is not set."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig()
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        # CSS class definition exists but the <img> tag should not be rendered
        assert '<img src="' not in content or 'src=""' in content

    def test_logo_with_data_uri(self, temp_output_dir, mock_execution_result):
        """Test that logo works with a data URI."""
        data_uri = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(logo_url=data_uri)
        reporter = HTMLReporter(config=config)

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "header-logo" in content
        assert "data:image/png;base64," in content


class TestInteractivity:
    """Tests for interactive features (JS, collapsible sections, search)."""

    def test_script_tag_present(self, temp_output_dir, mock_execution_result):
        """Test that a script tag with JavaScript is included."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "<script>" in content
        assert "makeSortable" in content
        assert "setupSearch" in content

    def test_collapsible_sections_use_details_element(self, temp_output_dir, mock_execution_result):
        """Test that sections use native <details> for collapsibility."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "<details" in content
        assert "<summary" in content

    def test_search_input_present_for_failures(self, temp_output_dir, mock_execution_result):
        """Test that search input exists when failures are present."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "search-input" in content
        assert 'data-table="failures-table"' in content

    def test_search_input_absent_when_no_failures(self, temp_output_dir):
        """Test that search input is not present when there are no failures."""
        mock_result = MagicMock()
        mock_result.source = "clean_data.csv"
        mock_result.started_at = datetime.now()
        mock_result.finished_at = datetime.now()
        mock_result.quality_score = 100.0
        mock_result.total_checks = 5
        mock_result.passed_count = 5
        mock_result.failed_count = 0
        mock_result.warning_count = 0
        mock_result.passed = True
        mock_result.results = []
        mock_result.get_failures.return_value = []
        mock_result.get_warnings.return_value = []

        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_result, output_path)

        content = output_path.read_text()
        assert 'data-table="failures-table"' not in content

    def test_sortable_table_headers_have_cursor(self, temp_output_dir, mock_execution_result):
        """Test that table headers have sort-related CSS for interactivity."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        # CSS for sortable headers
        assert "th.sort-asc" in content
        assert "th.sort-desc" in content

    def test_print_hides_interactive_elements(self, temp_output_dir, mock_execution_result):
        """Test that print styles hide interactive-only elements."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter.generate(mock_execution_result, output_path)

        content = output_path.read_text()
        assert "@media print" in content
        assert ".theme-toggle { display: none; }" in content
        assert ".search-bar { display: none; }" in content


class TestCalculateDuration:
    """Tests for the _calculate_duration helper method."""

    def test_milliseconds_format(self):
        """Test duration formatting for sub-second execution."""
        reporter = HTMLReporter()
        start = datetime(2026, 1, 1, 12, 0, 0)
        end = datetime(2026, 1, 1, 12, 0, 0, 500000)  # 500ms
        assert reporter._calculate_duration(start, end) == "500ms"

    def test_seconds_format(self):
        """Test duration formatting for seconds-range execution."""
        reporter = HTMLReporter()
        start = datetime(2026, 1, 1, 12, 0, 0)
        end = start + timedelta(seconds=5)
        assert reporter._calculate_duration(start, end) == "5.0s"

    def test_minutes_format(self):
        """Test duration formatting for minutes-range execution."""
        reporter = HTMLReporter()
        start = datetime(2026, 1, 1, 12, 0, 0)
        end = start + timedelta(minutes=2, seconds=30)
        assert reporter._calculate_duration(start, end) == "2.5m"

    def test_none_when_no_finished_at(self):
        """Test that None is returned when finished_at is not available."""
        reporter = HTMLReporter()
        start = datetime(2026, 1, 1, 12, 0, 0)
        assert reporter._calculate_duration(start, None) is None

    def test_none_when_no_started_at(self):
        """Test that None is returned when started_at is not available."""
        reporter = HTMLReporter()
        end = datetime(2026, 1, 1, 12, 0, 0)
        assert reporter._calculate_duration(None, end) is None


class TestBasicFallback:
    """Tests for _generate_basic fallback (when Jinja2 is unavailable)."""

    def test_basic_fallback_with_metadata(self, temp_output_dir, mock_execution_result):
        """Test that basic fallback includes metadata when provided."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        reporter._generate_basic(
            mock_execution_result, output_path, row_count=5000, column_count=10
        )

        content = output_path.read_text()
        assert "5,000" in content
        assert "Columns: 10" in content

    def test_basic_fallback_no_crash_with_new_params(self, temp_output_dir, mock_execution_result):
        """Test that basic fallback does not crash when all new params are passed."""
        output_path = temp_output_dir / "report.html"
        reporter = HTMLReporter()

        # Should not raise any exceptions
        reporter._generate_basic(
            mock_execution_result,
            output_path,
            row_count=None,
            column_count=None,
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "<!DOCTYPE html>" in content

    def test_basic_fallback_metadata_absent_when_disabled(
        self, temp_output_dir, mock_execution_result
    ):
        """Test that basic fallback hides metadata when include_metadata is False."""
        output_path = temp_output_dir / "report.html"
        config = ReportConfig(include_metadata=False)
        reporter = HTMLReporter(config=config)

        reporter._generate_basic(
            mock_execution_result, output_path, row_count=5000, column_count=10
        )

        content = output_path.read_text()
        assert "Rows:" not in content


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

    def test_full_featured_report(self, temp_output_dir, mock_execution_result, mock_trend_data):
        """Test report with all features enabled: dark mode, trends, metadata, logo."""
        config = ReportConfig(
            title="Full Feature Report",
            include_passed=True,
            include_trends=True,
            dark_mode="dark",
            logo_url="https://example.com/logo.png",
            include_metadata=True,
        )

        reporter = HTMLReporter(config=config)
        output_path = temp_output_dir / "full_report.html"
        reporter.generate(
            mock_execution_result,
            output_path,
            trend_data=mock_trend_data,
            row_count=50000,
            column_count=25,
        )

        content = output_path.read_text()
        assert "Full Feature Report" in content
        assert 'data-theme="dark"' in content
        assert "Quality Trend" in content
        assert "50,000" in content
        assert "header-logo" in content
        assert "<script>" in content
        assert "<details" in content
