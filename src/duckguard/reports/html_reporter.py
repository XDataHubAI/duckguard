"""HTML report generation for DuckGuard.

Generates beautiful, standalone HTML reports from validation results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from duckguard.history.storage import StoredRun
    from duckguard.rules.executor import ExecutionResult


@dataclass
class ReportConfig:
    """Configuration for report generation.

    Attributes:
        title: Report title
        include_passed: Include passed checks in report
        include_failed_rows: Include sample of failed rows
        max_failed_rows: Maximum failed rows to show per check
        include_charts: Generate quality score charts
        include_trends: Include trend charts (requires history)
        custom_css: Custom CSS to include
        logo_url: URL or data URI for logo
    """

    title: str = "DuckGuard Data Quality Report"
    include_passed: bool = True
    include_failed_rows: bool = True
    max_failed_rows: int = 10
    include_charts: bool = True
    include_trends: bool = False
    custom_css: str | None = None
    logo_url: str | None = None


# Embedded HTML template (no external dependencies for basic reports)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        :root {
            --color-pass: #10b981;
            --color-fail: #ef4444;
            --color-warn: #f59e0b;
            --color-info: #6b7280;
            --color-bg: #f9fafb;
            --color-card: #ffffff;
            --color-border: #e5e7eb;
            --color-text: #111827;
            --color-text-secondary: #6b7280;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.5;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--color-border);
        }
        .header h1 { font-size: 1.75rem; font-weight: 600; }
        .header .meta { color: var(--color-text-secondary); font-size: 0.875rem; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 0.875rem;
        }
        .status-pass { background: #d1fae5; color: #065f46; }
        .status-fail { background: #fee2e2; color: #991b1b; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card {
            background: var(--color-card);
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .card-label { font-size: 0.75rem; text-transform: uppercase; color: var(--color-text-secondary); letter-spacing: 0.05em; margin-bottom: 0.25rem; }
        .card-value { font-size: 2rem; font-weight: 700; }
        .card-value.pass { color: var(--color-pass); }
        .card-value.fail { color: var(--color-fail); }
        .card-value.warn { color: var(--color-warn); }
        .section { background: var(--color-card); border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section-title { font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .section-title .icon { width: 1.25rem; height: 1.25rem; }
        table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-border); }
        th { font-weight: 600; color: var(--color-text-secondary); background: var(--color-bg); }
        tr:hover { background: var(--color-bg); }
        .status-icon { display: inline-flex; align-items: center; gap: 0.25rem; }
        .status-icon.pass { color: var(--color-pass); }
        .status-icon.fail { color: var(--color-fail); }
        .status-icon.warn { color: var(--color-warn); }
        .gauge-container { display: flex; justify-content: center; margin: 1rem 0; }
        .gauge { width: 200px; height: 100px; position: relative; }
        .gauge svg { width: 100%; height: 100%; }
        .gauge-value { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); font-size: 2rem; font-weight: 700; }
        .grade { font-size: 1rem; color: var(--color-text-secondary); }
        .failed-rows { margin-top: 0.5rem; padding: 0.75rem; background: #fef2f2; border-radius: 0.375rem; font-size: 0.8rem; }
        .failed-rows-title { font-weight: 600; color: #991b1b; margin-bottom: 0.25rem; }
        .failed-rows code { background: #fee2e2; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-family: monospace; }
        .footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--color-border); text-align: center; color: var(--color-text-secondary); font-size: 0.75rem; }
        .footer a { color: inherit; text-decoration: none; }
        @media print {
            body { padding: 0; }
            .section { break-inside: avoid; }
        }
        {{ custom_css }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>{{ title }}</h1>
                <div class="meta">
                    Source: <strong>{{ source }}</strong> |
                    Generated: {{ generated_at }}
                </div>
            </div>
            <div class="status-badge {{ 'status-pass' if passed else 'status-fail' }}">
                {{ '✓ PASSED' if passed else '✗ FAILED' }}
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <div class="card-label">Quality Score</div>
                <div class="card-value {{ 'pass' if quality_score >= 80 else 'warn' if quality_score >= 60 else 'fail' }}">
                    {{ "%.1f"|format(quality_score) }}%
                </div>
                <div class="grade">Grade: {{ grade }}</div>
            </div>
            <div class="card">
                <div class="card-label">Checks Passed</div>
                <div class="card-value pass">{{ passed_count }}</div>
                <div class="grade">of {{ total_checks }} total</div>
            </div>
            <div class="card">
                <div class="card-label">Failures</div>
                <div class="card-value {{ 'fail' if failed_count > 0 else 'pass' }}">{{ failed_count }}</div>
            </div>
            <div class="card">
                <div class="card-label">Warnings</div>
                <div class="card-value {{ 'warn' if warning_count > 0 else 'pass' }}">{{ warning_count }}</div>
            </div>
        </div>

        {% if include_charts %}
        <div class="section">
            <div class="section-title">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                Quality Score
            </div>
            <div class="gauge-container">
                <div class="gauge">
                    <svg viewBox="0 0 200 100">
                        <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="#e5e7eb" stroke-width="12" stroke-linecap="round"/>
                        <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none"
                              stroke="{{ '#10b981' if quality_score >= 80 else '#f59e0b' if quality_score >= 60 else '#ef4444' }}"
                              stroke-width="12" stroke-linecap="round"
                              stroke-dasharray="{{ quality_score * 2.51 }} 251"/>
                    </svg>
                    <div class="gauge-value">{{ "%.0f"|format(quality_score) }}</div>
                </div>
            </div>
        </div>
        {% endif %}

        {% if failures %}
        <div class="section">
            <div class="section-title" style="color: var(--color-fail);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Failures ({{ failures|length }})
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Check</th>
                        <th>Column</th>
                        <th>Message</th>
                        <th>Actual</th>
                        <th>Expected</th>
                    </tr>
                </thead>
                <tbody>
                    {% for f in failures %}
                    <tr>
                        <td><span class="status-icon fail">✗</span> {{ f.check.type.value }}</td>
                        <td>{{ f.column or '-' }}</td>
                        <td>{{ f.message }}</td>
                        <td><code>{{ f.actual_value }}</code></td>
                        <td><code>{{ f.expected_value }}</code></td>
                    </tr>
                    {% if include_failed_rows and f.details and f.details.get('failed_rows') %}
                    <tr>
                        <td colspan="5">
                            <div class="failed-rows">
                                <div class="failed-rows-title">Sample Failed Rows ({{ f.details.get('failed_rows')|length }} shown)</div>
                                {% for row in f.details.get('failed_rows')[:max_failed_rows] %}
                                <code>{{ row }}</code>{% if not loop.last %}, {% endif %}
                                {% endfor %}
                            </div>
                        </td>
                    </tr>
                    {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if warnings %}
        <div class="section">
            <div class="section-title" style="color: var(--color-warn);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                Warnings ({{ warnings|length }})
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Check</th>
                        <th>Column</th>
                        <th>Message</th>
                        <th>Actual</th>
                    </tr>
                </thead>
                <tbody>
                    {% for w in warnings %}
                    <tr>
                        <td><span class="status-icon warn">⚠</span> {{ w.check.type.value }}</td>
                        <td>{{ w.column or '-' }}</td>
                        <td>{{ w.message }}</td>
                        <td><code>{{ w.actual_value }}</code></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if include_passed and passed_results %}
        <div class="section">
            <div class="section-title" style="color: var(--color-pass);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Passed Checks ({{ passed_results|length }})
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Check</th>
                        <th>Column</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in passed_results %}
                    <tr>
                        <td><span class="status-icon pass">✓</span> {{ p.check.type.value }}</td>
                        <td>{{ p.column or '-' }}</td>
                        <td>{{ p.message }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="footer">
            Generated by <a href="https://github.com/XDataHubAI/duckguard">DuckGuard</a> |
            Data quality that just works
        </div>
    </div>
</body>
</html>
"""


class HTMLReporter:
    """Generates HTML reports from DuckGuard validation results.

    Creates beautiful, standalone HTML reports that can be shared
    or viewed in any browser.

    Usage:
        from duckguard.reports import HTMLReporter
        from duckguard import connect, load_rules, execute_rules

        result = execute_rules(load_rules("rules.yaml"), connect("data.csv"))

        reporter = HTMLReporter()
        reporter.generate(result, "report.html")

    Attributes:
        config: Report configuration
    """

    def __init__(self, config: ReportConfig | None = None):
        """Initialize the reporter.

        Args:
            config: Report configuration (uses defaults if None)
        """
        self.config = config or ReportConfig()

    def generate(
        self,
        result: ExecutionResult,
        output_path: str | Path,
        *,
        history: list[StoredRun] | None = None,
    ) -> Path:
        """Generate an HTML report.

        Args:
            result: ExecutionResult to report on
            output_path: Path to write HTML file
            history: Optional historical results for trends

        Returns:
            Path to generated report

        Raises:
            ImportError: If jinja2 is not installed
        """
        try:
            from jinja2 import BaseLoader, Environment
        except ImportError:
            # Fall back to basic string formatting if jinja2 not available
            return self._generate_basic(result, output_path)

        output_path = Path(output_path)

        # Create Jinja2 environment
        env = Environment(loader=BaseLoader(), autoescape=True)
        template = env.from_string(HTML_TEMPLATE)

        # Build context
        context = self._build_context(result, history)

        # Render and write
        html = template.render(**context)
        output_path.write_text(html, encoding="utf-8")

        return output_path

    def _generate_basic(
        self,
        result: ExecutionResult,
        output_path: str | Path,
    ) -> Path:
        """Generate a basic HTML report without Jinja2.

        Args:
            result: ExecutionResult to report on
            output_path: Path to write HTML file

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)

        # Simple HTML generation
        status = "PASSED" if result.passed else "FAILED"
        status_class = "status-pass" if result.passed else "status-fail"
        grade = self._score_to_grade(result.quality_score)

        failures_html = ""
        for f in result.get_failures():
            failures_html += f"""
            <tr>
                <td>✗ {f.check.type.value}</td>
                <td>{f.column or '-'}</td>
                <td>{f.message}</td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{self.config.title}</title>
    <style>
        body {{ font-family: sans-serif; padding: 2rem; max-width: 1000px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #eee; padding-bottom: 1rem; }}
        .{status_class} {{ padding: 0.5rem 1rem; border-radius: 9999px; font-weight: bold; }}
        .status-pass {{ background: #d1fae5; color: #065f46; }}
        .status-fail {{ background: #fee2e2; color: #991b1b; }}
        .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 2rem 0; }}
        .card {{ background: #f9fafb; padding: 1rem; border-radius: 0.5rem; }}
        .card-value {{ font-size: 2rem; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f9fafb; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{self.config.title}</h1>
            <p>Source: {result.source} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        <span class="{status_class}">{status}</span>
    </div>
    <div class="cards">
        <div class="card">
            <div>Quality Score</div>
            <div class="card-value">{result.quality_score:.1f}%</div>
            <div>Grade: {grade}</div>
        </div>
        <div class="card">
            <div>Checks Passed</div>
            <div class="card-value">{result.passed_count}</div>
            <div>of {result.total_checks}</div>
        </div>
        <div class="card">
            <div>Failures</div>
            <div class="card-value">{result.failed_count}</div>
        </div>
        <div class="card">
            <div>Warnings</div>
            <div class="card-value">{result.warning_count}</div>
        </div>
    </div>
    {f'<h2>Failures</h2><table><tr><th>Check</th><th>Column</th><th>Message</th></tr>{failures_html}</table>' if failures_html else ''}
    <footer style="margin-top: 2rem; text-align: center; color: #888;">Generated by DuckGuard</footer>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")
        return output_path

    def _build_context(
        self,
        result: ExecutionResult,
        history: list[StoredRun] | None = None,
    ) -> dict[str, Any]:
        """Build template context from result."""
        return {
            "title": self.config.title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": result.source,
            "quality_score": result.quality_score,
            "grade": self._score_to_grade(result.quality_score),
            "passed": result.passed,
            "total_checks": result.total_checks,
            "passed_count": result.passed_count,
            "failed_count": result.failed_count,
            "warning_count": result.warning_count,
            "failures": result.get_failures(),
            "warnings": result.get_warnings(),
            "passed_results": [r for r in result.results if r.passed]
            if self.config.include_passed
            else [],
            "include_passed": self.config.include_passed,
            "include_charts": self.config.include_charts,
            "include_failed_rows": self.config.include_failed_rows,
            "max_failed_rows": self.config.max_failed_rows,
            "include_trends": self.config.include_trends and history,
            "history": history,
            "custom_css": self.config.custom_css or "",
        }

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"


def generate_html_report(
    result: ExecutionResult,
    output_path: str | Path,
    **kwargs: Any,
) -> Path:
    """Convenience function to generate HTML report.

    Args:
        result: ExecutionResult to report on
        output_path: Path to write HTML file
        **kwargs: Additional ReportConfig options

    Returns:
        Path to generated report
    """
    config = ReportConfig(**kwargs) if kwargs else None
    reporter = HTMLReporter(config=config)
    return reporter.generate(result, output_path)
