"""Report generation for DuckGuard.

Provides HTML and PDF report generation for validation results.

Usage:
    from duckguard.reports import HTMLReporter, PDFReporter

    # Generate HTML report
    reporter = HTMLReporter()
    reporter.generate(result, "report.html")

    # Generate PDF report (requires weasyprint)
    pdf_reporter = PDFReporter()
    pdf_reporter.generate(result, "report.pdf")

    # Or use convenience functions
    from duckguard.reports import generate_html_report, generate_pdf_report

    generate_html_report(result, "report.html", title="My Report")
    generate_pdf_report(result, "report.pdf")
"""

from duckguard.reports.html_reporter import (
    HTMLReporter,
    ReportConfig,
    generate_html_report,
)
from duckguard.reports.pdf_reporter import (
    PDFReporter,
    generate_pdf_report,
)

__all__ = [
    # Configuration
    "ReportConfig",
    # Reporters
    "HTMLReporter",
    "PDFReporter",
    # Convenience functions
    "generate_html_report",
    "generate_pdf_report",
]
