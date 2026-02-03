"""PDF report generation for DuckGuard.

Uses WeasyPrint to convert HTML reports to PDF format.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from duckguard.reports.html_reporter import HTMLReporter, ReportConfig

if TYPE_CHECKING:
    from duckguard.history.storage import StoredRun, TrendDataPoint
    from duckguard.rules.executor import ExecutionResult


class PDFReporter(HTMLReporter):
    """Generates PDF reports from DuckGuard validation results.

    Uses WeasyPrint to convert HTML to PDF, producing high-quality
    PDF documents suitable for sharing and archiving.

    Usage:
        from duckguard.reports import PDFReporter
        from duckguard import connect, load_rules, execute_rules

        result = execute_rules(load_rules("rules.yaml"), connect("data.csv"))

        reporter = PDFReporter()
        reporter.generate(result, "report.pdf")

    Note:
        Requires weasyprint to be installed:
        pip install duckguard[reports]

    Attributes:
        config: Report configuration (inherited from HTMLReporter)
    """

    def generate(
        self,
        result: ExecutionResult,
        output_path: str | Path,
        *,
        history: list[StoredRun] | None = None,
        trend_data: list[TrendDataPoint] | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> Path:
        """Generate a PDF report.

        Args:
            result: ExecutionResult to report on
            output_path: Path to write PDF file
            history: Optional historical results for trends
            trend_data: Optional trend data points for chart rendering
            row_count: Optional dataset row count for metadata display
            column_count: Optional dataset column count for metadata display

        Returns:
            Path to generated PDF report

        Raises:
            ImportError: If weasyprint is not installed
        """
        try:
            from weasyprint import HTML
        except ImportError:
            raise ImportError(
                "PDF reports require weasyprint. " "Install with: pip install duckguard[reports]"
            )

        output_path = Path(output_path)

        # Generate HTML first to a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".html",
            delete=False,
            encoding="utf-8",
        ) as f:
            html_path = Path(f.name)

        try:
            # Generate HTML report
            super().generate(
                result,
                html_path,
                history=history,
                trend_data=trend_data,
                row_count=row_count,
                column_count=column_count,
            )

            # Convert to PDF
            HTML(filename=str(html_path)).write_pdf(str(output_path))
        finally:
            # Cleanup temporary HTML file
            try:
                html_path.unlink()
            except OSError:
                pass

        return output_path


def generate_pdf_report(
    result: ExecutionResult,
    output_path: str | Path,
    *,
    history: list[StoredRun] | None = None,
    trend_data: list[TrendDataPoint] | None = None,
    row_count: int | None = None,
    column_count: int | None = None,
    **kwargs: Any,
) -> Path:
    """Convenience function to generate PDF report.

    Args:
        result: ExecutionResult to report on
        output_path: Path to write PDF file
        history: Optional historical results for trends
        trend_data: Optional trend data points for chart rendering
        row_count: Optional dataset row count
        column_count: Optional dataset column count
        **kwargs: Additional ReportConfig options

    Returns:
        Path to generated PDF report
    """
    config = ReportConfig(**kwargs) if kwargs else None
    reporter = PDFReporter(config=config)
    return reporter.generate(
        result,
        output_path,
        history=history,
        trend_data=trend_data,
        row_count=row_count,
        column_count=column_count,
    )
