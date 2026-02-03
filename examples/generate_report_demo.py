"""Generate showcase HTML and PDF reports demonstrating all DuckGuard report features.

This script generates demo reports using the sample orders.csv data with:
- Dark mode support (auto theme)
- Quality trend charts with simulated history
- Dataset metadata (row count, column count, execution duration)
- Collapsible sections, sortable tables, search
- Failures, warnings, and passed checks for a realistic showcase

Usage:
    python examples/generate_report_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from duckguard.connectors import connect
from duckguard.history.storage import TrendDataPoint
from duckguard.reports import HTMLReporter, PDFReporter, ReportConfig
from duckguard.rules import execute_rules
from duckguard.rules.loader import load_rules_from_string

# Comprehensive rules that showcase PASS, FAIL, and WARNING results.
# The sample orders.csv has intentional data issues:
#   - Missing customer_id on row 22
#   - Missing emails on rows 14, 22
#   - Missing phones on rows 6, 19
#   - Negative quantity on row 23 (-2)
#   - Zero quantity on row 29
#   - Negative subtotal/total on row 23
DEMO_RULES_YAML = """
name: orders_quality_checks
description: Comprehensive quality checks for the orders dataset

checks:
  order_id:
    - not_null
    - unique

  customer_id:
    - not_null

  product_name:
    - not_null
    - allowed_values: [Widget A, Widget B, Widget C, Gadget X, Gadget Y, Premium Z]

  quantity:
    - between: [1, 1000]

  unit_price:
    - positive

  subtotal:
    - non_negative

  total_amount:
    - positive

  status:
    - not_null
    - allowed_values: [pending, shipped, delivered, cancelled, returned]

  country:
    - not_null
    - allowed_values: [US, UK, CA, DE, JP]

  email:
    - not_null:
        severity: warning

  phone:
    - not_null:
        severity: warning

  created_at:
    - not_null

table:
  - row_count: ">= 10"
"""


def generate_simulated_trend_data() -> list[TrendDataPoint]:
    """Create realistic-looking trend data for the demo report."""
    return [
        TrendDataPoint(
            "2026-01-10",
            avg_score=68.0,
            min_score=62.0,
            max_score=74.0,
            run_count=3,
            passed_count=2,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-12",
            avg_score=71.0,
            min_score=65.0,
            max_score=77.0,
            run_count=2,
            passed_count=1,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-14",
            avg_score=74.5,
            min_score=70.0,
            max_score=79.0,
            run_count=4,
            passed_count=3,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-16",
            avg_score=72.0,
            min_score=68.0,
            max_score=76.0,
            run_count=2,
            passed_count=1,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-18",
            avg_score=78.0,
            min_score=74.0,
            max_score=82.0,
            run_count=3,
            passed_count=2,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-20",
            avg_score=76.0,
            min_score=71.0,
            max_score=81.0,
            run_count=2,
            passed_count=2,
            failed_count=0,
        ),
        TrendDataPoint(
            "2026-01-22",
            avg_score=80.0,
            min_score=76.0,
            max_score=84.0,
            run_count=3,
            passed_count=3,
            failed_count=0,
        ),
        TrendDataPoint(
            "2026-01-24",
            avg_score=82.5,
            min_score=78.0,
            max_score=87.0,
            run_count=4,
            passed_count=3,
            failed_count=1,
        ),
        TrendDataPoint(
            "2026-01-26",
            avg_score=79.0,
            min_score=75.0,
            max_score=83.0,
            run_count=2,
            passed_count=2,
            failed_count=0,
        ),
        TrendDataPoint(
            "2026-01-28",
            avg_score=85.0,
            min_score=80.0,
            max_score=90.0,
            run_count=3,
            passed_count=3,
            failed_count=0,
        ),
        TrendDataPoint(
            "2026-01-30",
            avg_score=83.3,
            min_score=78.0,
            max_score=88.0,
            run_count=3,
            passed_count=2,
            failed_count=1,
        ),
    ]


def main() -> None:
    """Generate demo reports."""
    sample_csv = project_root / "examples" / "sample_data" / "orders.csv"
    output_dir = project_root / "examples" / "reports"
    output_dir.mkdir(exist_ok=True)

    print("Connecting to sample data...")
    dataset = connect(str(sample_csv))

    print("Loading rules and running validation...")
    ruleset = load_rules_from_string(DEMO_RULES_YAML)
    result = execute_rules(ruleset, dataset=dataset)

    print(f"Validation: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Quality Score: {result.quality_score:.1f}%")
    print(f"Checks: {result.passed_count}/{result.total_checks} passed")
    print(f"Failures: {result.failed_count} | Warnings: {result.warning_count}\n")

    trend_data = generate_simulated_trend_data()

    # --- HTML Report (auto theme — follows OS preference) ---
    config_light = ReportConfig(
        title="DuckGuard — Orders Quality Report",
        include_passed=True,
        include_trends=True,
        include_metadata=True,
        dark_mode="auto",
    )

    html_path = output_dir / "demo_report.html"
    reporter = HTMLReporter(config=config_light)
    reporter.generate(
        result,
        html_path,
        trend_data=trend_data,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
    )
    print(f"HTML report: {html_path}")

    # --- HTML Report (dark mode forced) ---
    config_dark = ReportConfig(
        title="DuckGuard — Orders Quality Report (Dark)",
        include_passed=True,
        include_trends=True,
        include_metadata=True,
        dark_mode="dark",
    )

    dark_path = output_dir / "demo_report_dark.html"
    reporter_dark = HTMLReporter(config=config_dark)
    reporter_dark.generate(
        result,
        dark_path,
        trend_data=trend_data,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
    )
    print(f"HTML report (dark): {dark_path}")

    # --- PDF Report ---
    try:
        config_pdf = ReportConfig(
            title="DuckGuard — Orders Quality Report",
            include_passed=True,
            include_trends=True,
            include_metadata=True,
            dark_mode="light",
        )

        pdf_path = output_dir / "demo_report.pdf"
        pdf_reporter = PDFReporter(config=config_pdf)
        pdf_reporter.generate(
            result,
            pdf_path,
            trend_data=trend_data,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
        )
        print(f"PDF report:  {pdf_path}")
    except (ImportError, OSError) as e:
        print(f"PDF report:  skipped ({e})")

    print("\nDone! Open the HTML files in a browser to see the reports.")


if __name__ == "__main__":
    main()
