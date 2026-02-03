"""HTML report generation for DuckGuard.

Generates beautiful, standalone HTML reports from validation results.
Features: dark mode, collapsible sections, sortable tables, search,
trend charts, and dataset metadata — all in a single self-contained file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from duckguard.history.storage import StoredRun, TrendDataPoint
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
        dark_mode: Theme mode — "auto" (OS preference), "light", or "dark"
        trend_days: Number of days of history for trend charts
        include_metadata: Show row count, column count, and duration in header
    """

    title: str = "DuckGuard Data Quality Report"
    include_passed: bool = True
    include_failed_rows: bool = True
    max_failed_rows: int = 10
    include_charts: bool = True
    include_trends: bool = False
    custom_css: str | None = None
    logo_url: str | None = None
    dark_mode: str = "auto"
    trend_days: int = 30
    include_metadata: bool = True


# Embedded HTML template (no external dependencies for basic reports)
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en"{% if dark_mode == 'dark' %} data-theme="dark"{% elif dark_mode == 'light' %} data-theme="light"{% endif %}>
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
        [data-theme="dark"] {
            --color-pass: #34d399;
            --color-fail: #f87171;
            --color-warn: #fbbf24;
            --color-info: #9ca3af;
            --color-bg: #111827;
            --color-card: #1f2937;
            --color-border: #374151;
            --color-text: #f9fafb;
            --color-text-secondary: #9ca3af;
        }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) {
                --color-pass: #34d399;
                --color-fail: #f87171;
                --color-warn: #fbbf24;
                --color-info: #9ca3af;
                --color-bg: #111827;
                --color-card: #1f2937;
                --color-border: #374151;
                --color-text: #f9fafb;
                --color-text-secondary: #9ca3af;
            }
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
        .header-left { display: flex; align-items: center; gap: 1rem; }
        .header-logo { max-height: 48px; max-width: 200px; object-fit: contain; }
        .header h1 { font-size: 1.75rem; font-weight: 600; }
        .header .meta { color: var(--color-text-secondary); font-size: 0.875rem; }
        .header-right { display: flex; align-items: center; gap: 0.75rem; }
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
        [data-theme="dark"] .status-pass { background: #064e3b; color: #34d399; }
        [data-theme="dark"] .status-fail { background: #7f1d1d; color: #f87171; }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) .status-pass { background: #064e3b; color: #34d399; }
            :root:not([data-theme="light"]) .status-fail { background: #7f1d1d; color: #f87171; }
        }
        .theme-toggle {
            background: none; border: 1px solid var(--color-border);
            border-radius: 0.375rem; padding: 0.5rem;
            cursor: pointer; color: var(--color-text-secondary);
            display: flex; align-items: center;
        }
        .theme-toggle:hover { background: var(--color-bg); }
        .icon-moon { display: none; }
        [data-theme="dark"] .icon-sun { display: none; }
        [data-theme="dark"] .icon-moon { display: block; }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) .icon-sun { display: none; }
            :root:not([data-theme="light"]) .icon-moon { display: block; }
        }
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
        details.section > summary { cursor: pointer; user-select: none; list-style: none; }
        details.section > summary::-webkit-details-marker { display: none; }
        .section-title { font-size: 1.125rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        .section-title .icon { width: 1.25rem; height: 1.25rem; }
        .collapse-hint { font-size: 0.75rem; color: var(--color-text-secondary); margin-left: auto; }
        details.section[open] .collapse-hint::after { content: '[-]'; }
        details.section:not([open]) .collapse-hint::after { content: '[+]'; }
        details.section:not([open]) .section-title { margin-bottom: 0; }
        table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-border); }
        th { font-weight: 600; color: var(--color-text-secondary); background: var(--color-bg); cursor: pointer; user-select: none; }
        th:hover { color: var(--color-text); }
        th.sort-asc::after { content: ' \\25B2'; font-size: 0.65rem; }
        th.sort-desc::after { content: ' \\25BC'; font-size: 0.65rem; }
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
        [data-theme="dark"] .failed-rows { background: #1c1917; }
        [data-theme="dark"] .failed-rows-title { color: #f87171; }
        [data-theme="dark"] .failed-rows code { background: #292524; color: #fca5a5; }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) .failed-rows { background: #1c1917; }
            :root:not([data-theme="light"]) .failed-rows-title { color: #f87171; }
            :root:not([data-theme="light"]) .failed-rows code { background: #292524; color: #fca5a5; }
        }
        .search-bar { margin-bottom: 0.75rem; }
        .search-input {
            width: 100%; padding: 0.5rem 0.75rem;
            border: 1px solid var(--color-border); border-radius: 0.375rem;
            background: var(--color-bg); color: var(--color-text);
            font-size: 0.875rem; font-family: inherit;
        }
        .search-input:focus { outline: 2px solid var(--color-pass); outline-offset: -1px; }
        .search-input::placeholder { color: var(--color-text-secondary); }
        .trend-chart { width: 100%; overflow-x: auto; }
        .trend-chart svg { display: block; margin: 0 auto; max-width: 100%; height: auto; }
        .footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--color-border); text-align: center; color: var(--color-text-secondary); font-size: 0.75rem; }
        .footer a { color: inherit; text-decoration: none; }
        @media print {
            body { padding: 0; }
            :root, [data-theme="dark"] {
                --color-pass: #10b981; --color-fail: #ef4444; --color-warn: #f59e0b;
                --color-info: #6b7280; --color-bg: #f9fafb; --color-card: #ffffff;
                --color-border: #e5e7eb; --color-text: #111827; --color-text-secondary: #6b7280;
            }
            .status-pass { background: #d1fae5 !important; color: #065f46 !important; }
            .status-fail { background: #fee2e2 !important; color: #991b1b !important; }
            .failed-rows { background: #fef2f2 !important; }
            .failed-rows-title { color: #991b1b !important; }
            .failed-rows code { background: #fee2e2 !important; color: inherit !important; }
            .section { break-inside: avoid; }
            details.section { display: block; }
            details.section > summary { pointer-events: none; }
            .collapse-hint { display: none; }
            .theme-toggle { display: none; }
            .search-bar { display: none; }
        }
        {{ custom_css }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                {% if logo_url %}
                <img src="{{ logo_url }}" alt="Logo" class="header-logo">
                {% endif %}
                <div>
                    <h1>{{ title }}</h1>
                    <div class="meta">
                        Source: <strong>{{ source }}</strong> |
                        Generated: {{ generated_at }}
                        {% if include_metadata %}
                        <br>
                        {% if row_count is not none %}Rows: <strong>{{ "{:,}".format(row_count) }}</strong>{% endif %}
                        {% if row_count is not none and column_count is not none %} | {% endif %}
                        {% if column_count is not none %}Columns: <strong>{{ column_count }}</strong>{% endif %}
                        {% if execution_duration and (row_count is not none or column_count is not none) %} | {% endif %}
                        {% if execution_duration %}Duration: <strong>{{ execution_duration }}</strong>{% endif %}
                        {% endif %}
                    </div>
                </div>
            </div>
            <div class="header-right">
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">
                    <svg class="icon-sun" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    <svg class="icon-moon" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
                </button>
                <div class="status-badge {{ 'status-pass' if passed else 'status-fail' }}">
                    {{ ('&#10003; PASSED' if passed else '&#10007; FAILED')|safe }}
                </div>
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

        {% if include_trends and trend_chart_svg %}
        <div class="section">
            <div class="section-title">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"/></svg>
                Quality Trend ({{ trend_data|length }} data points)
            </div>
            <div class="trend-chart">
                {{ trend_chart_svg|safe }}
            </div>
        </div>
        {% endif %}

        {% if failures %}
        <details class="section" open>
            <summary class="section-title" style="color: var(--color-fail);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Failures ({{ failures|length }})
                <span class="collapse-hint"></span>
            </summary>
            <div class="search-bar">
                <input type="text" class="search-input" data-table="failures-table" placeholder="Search failures..." aria-label="Filter failure rows">
            </div>
            <table id="failures-table">
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
                        <td><span class="status-icon fail">&#10007;</span> {{ f.check.type.value }}</td>
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
        </details>
        {% endif %}

        {% if warnings %}
        <details class="section" open>
            <summary class="section-title" style="color: var(--color-warn);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                Warnings ({{ warnings|length }})
                <span class="collapse-hint"></span>
            </summary>
            <table id="warnings-table">
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
                        <td><span class="status-icon warn">&#9888;</span> {{ w.check.type.value }}</td>
                        <td>{{ w.column or '-' }}</td>
                        <td>{{ w.message }}</td>
                        <td><code>{{ w.actual_value }}</code></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </details>
        {% endif %}

        {% if include_passed and passed_results %}
        <details class="section">
            <summary class="section-title" style="color: var(--color-pass);">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Passed Checks ({{ passed_results|length }})
                <span class="collapse-hint"></span>
            </summary>
            <table id="passed-table">
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
                        <td><span class="status-icon pass">&#10003;</span> {{ p.check.type.value }}</td>
                        <td>{{ p.column or '-' }}</td>
                        <td>{{ p.message }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </details>
        {% endif %}

        <div class="footer">
            Generated by <a href="https://github.com/XDataHubAI/duckguard">DuckGuard</a> |
            Data quality that just works
        </div>
    </div>
    <script>
    (function() {
        'use strict';
        function toggleTheme() {
            var html = document.documentElement;
            var current = html.getAttribute('data-theme');
            if (current === 'dark') {
                html.setAttribute('data-theme', 'light');
            } else {
                html.setAttribute('data-theme', 'dark');
            }
        }
        window.toggleTheme = toggleTheme;

        function makeSortable(table) {
            var headers = table.querySelectorAll('th');
            for (var i = 0; i < headers.length; i++) {
                (function(index) {
                    headers[index].addEventListener('click', function() {
                        sortTable(table, index, this);
                    });
                })(i);
            }
        }

        function sortTable(table, colIndex, header) {
            var tbody = table.querySelector('tbody');
            if (!tbody) return;
            var rows = [];
            var children = tbody.querySelectorAll('tr');
            for (var i = 0; i < children.length; i++) { rows.push(children[i]); }
            var dataRows = [];
            var detailMap = {};
            for (var j = 0; j < rows.length; j++) {
                if (rows[j].querySelector('td[colspan]')) {
                    if (dataRows.length > 0) {
                        detailMap[dataRows.length - 1] = rows[j];
                    }
                } else {
                    dataRows.push(rows[j]);
                }
            }
            var ascending = !header.classList.contains('sort-asc');
            var allHeaders = table.querySelectorAll('th');
            for (var h = 0; h < allHeaders.length; h++) {
                allHeaders[h].classList.remove('sort-asc', 'sort-desc');
            }
            dataRows.sort(function(a, b) {
                var aText = a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '';
                var bText = b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '';
                var aNum = parseFloat(aText);
                var bNum = parseFloat(bText);
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return ascending ? aNum - bNum : bNum - aNum;
                }
                return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
            });
            header.classList.add(ascending ? 'sort-asc' : 'sort-desc');
            while (tbody.firstChild) { tbody.removeChild(tbody.firstChild); }
            for (var k = 0; k < dataRows.length; k++) {
                tbody.appendChild(dataRows[k]);
                if (detailMap[k]) { tbody.appendChild(detailMap[k]); }
            }
        }

        function setupSearch() {
            var inputs = document.querySelectorAll('.search-input');
            for (var i = 0; i < inputs.length; i++) {
                (function(input) {
                    var tableId = input.getAttribute('data-table');
                    var table = document.getElementById(tableId);
                    if (!table) return;
                    input.addEventListener('input', function() {
                        filterTable(table, input.value.toLowerCase());
                    });
                })(inputs[i]);
            }
        }

        function filterTable(table, query) {
            var tbody = table.querySelector('tbody');
            if (!tbody) return;
            var rows = tbody.querySelectorAll('tr');
            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                if (row.querySelector('td[colspan]')) continue;
                var text = row.textContent.toLowerCase();
                var visible = !query || text.indexOf(query) >= 0;
                row.style.display = visible ? '' : 'none';
                var next = row.nextElementSibling;
                if (next && next.querySelector('td[colspan]')) {
                    next.style.display = visible ? '' : 'none';
                }
            }
        }

        var tables = document.querySelectorAll('table');
        for (var t = 0; t < tables.length; t++) { makeSortable(tables[t]); }
        setupSearch();
    })();
    </script>
</body>
</html>
"""


class HTMLReporter:
    """Generates HTML reports from DuckGuard validation results.

    Creates beautiful, standalone HTML reports that can be shared
    or viewed in any browser. Supports dark mode, collapsible sections,
    sortable tables, search, and quality trend charts.

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
        trend_data: list[TrendDataPoint] | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> Path:
        """Generate an HTML report.

        Args:
            result: ExecutionResult to report on
            output_path: Path to write HTML file
            history: Optional historical results for trends
            trend_data: Optional trend data points for chart rendering
            row_count: Optional dataset row count for metadata display
            column_count: Optional dataset column count for metadata display

        Returns:
            Path to generated report

        Raises:
            ImportError: If jinja2 is not installed
        """
        try:
            from jinja2 import BaseLoader, Environment
        except ImportError:
            # Fall back to basic string formatting if jinja2 not available
            return self._generate_basic(
                result, output_path, row_count=row_count, column_count=column_count
            )

        output_path = Path(output_path)

        # Create Jinja2 environment
        env = Environment(loader=BaseLoader(), autoescape=True)
        template = env.from_string(HTML_TEMPLATE)

        # Build context
        context = self._build_context(
            result,
            history,
            row_count=row_count,
            column_count=column_count,
            trend_data=trend_data,
        )

        # Render and write
        html = template.render(**context)
        output_path.write_text(html, encoding="utf-8")

        return output_path

    def _generate_basic(
        self,
        result: ExecutionResult,
        output_path: str | Path,
        *,
        row_count: int | None = None,
        column_count: int | None = None,
    ) -> Path:
        """Generate a basic HTML report without Jinja2.

        Args:
            result: ExecutionResult to report on
            output_path: Path to write HTML file
            row_count: Optional dataset row count
            column_count: Optional dataset column count

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)

        # Simple HTML generation
        status = "PASSED" if result.passed else "FAILED"
        status_class = "status-pass" if result.passed else "status-fail"
        grade = self._score_to_grade(result.quality_score)

        # Build metadata line
        metadata_parts: list[str] = []
        if row_count is not None:
            metadata_parts.append(f"Rows: {row_count:,}")
        if column_count is not None:
            metadata_parts.append(f"Columns: {column_count}")
        metadata_html = ""
        if metadata_parts and self.config.include_metadata:
            metadata_html = f"<br>{' | '.join(metadata_parts)}"

        failures_html = ""
        for f in result.get_failures():
            failures_html += f"""
            <tr>
                <td>&#10007; {f.check.type.value}</td>
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
            <p>Source: {result.source} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}{metadata_html}</p>
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
        *,
        row_count: int | None = None,
        column_count: int | None = None,
        trend_data: list[TrendDataPoint] | None = None,
    ) -> dict[str, Any]:
        """Build template context from result."""
        trend_dicts = self._serialize_trend_data(trend_data) if trend_data else None
        trend_svg = ""
        if self.config.include_trends and trend_dicts:
            trend_svg = self._generate_trend_svg(trend_dicts)

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
            "passed_results": (
                [r for r in result.results if r.passed] if self.config.include_passed else []
            ),
            "include_passed": self.config.include_passed,
            "include_charts": self.config.include_charts,
            "include_failed_rows": self.config.include_failed_rows,
            "max_failed_rows": self.config.max_failed_rows,
            "include_trends": self.config.include_trends and bool(trend_dicts),
            "trend_data": trend_dicts or [],
            "trend_chart_svg": trend_svg,
            "history": history,
            "custom_css": self.config.custom_css or "",
            "logo_url": self.config.logo_url or "",
            "dark_mode": self.config.dark_mode,
            "include_metadata": self.config.include_metadata,
            "row_count": row_count,
            "column_count": column_count,
            "execution_duration": self._calculate_duration(result.started_at, result.finished_at),
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

    def _calculate_duration(
        self, started_at: datetime | None, finished_at: datetime | None
    ) -> str | None:
        """Format execution duration as a human-readable string.

        Args:
            started_at: Validation start time
            finished_at: Validation end time

        Returns:
            Formatted duration string, or None if timing unavailable
        """
        if not started_at or not finished_at:
            return None
        delta = finished_at - started_at
        seconds = delta.total_seconds()
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = seconds / 60
        return f"{minutes:.1f}m"

    def _serialize_trend_data(self, trend_data: list[TrendDataPoint]) -> list[dict[str, Any]]:
        """Convert TrendDataPoint list to template-friendly dicts.

        Args:
            trend_data: List of TrendDataPoint objects

        Returns:
            List of dicts with date, avg_score, min_score, max_score, run_count
        """
        return [
            {
                "date": tp.date,
                "avg_score": tp.avg_score,
                "min_score": tp.min_score,
                "max_score": tp.max_score,
                "run_count": tp.run_count,
            }
            for tp in trend_data
        ]

    def _generate_trend_svg(
        self,
        trend_data: list[dict[str, Any]],
        width: int = 700,
        height: int = 200,
    ) -> str:
        """Generate an inline SVG line chart for quality score trends.

        The chart includes a line for avg_score, a shaded min/max band,
        gridlines, date labels, and data point tooltips.

        Args:
            trend_data: List of trend data dicts
            width: SVG width in pixels
            height: SVG height in pixels

        Returns:
            SVG markup string
        """
        if not trend_data:
            return ""

        pad_top = 20
        pad_right = 20
        pad_bottom = 35
        pad_left = 40
        plot_w = width - pad_left - pad_right
        plot_h = height - pad_top - pad_bottom

        n = len(trend_data)
        x_step = plot_w / max(n - 1, 1)
        x_positions = [pad_left + i * x_step for i in range(n)]

        def y_for_score(score: float) -> float:
            return pad_top + plot_h * (1 - score / 100)

        # Determine line color from latest score
        latest_score = trend_data[-1]["avg_score"]
        if latest_score >= 80:
            line_color = "#10b981"
            band_color = "#10b981"
        elif latest_score >= 60:
            line_color = "#f59e0b"
            band_color = "#f59e0b"
        else:
            line_color = "#ef4444"
            band_color = "#ef4444"

        parts: list[str] = []
        parts.append(
            f'<svg viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Quality score trend chart">'
        )

        # Background
        parts.append(
            f'<rect x="0" y="0" width="{width}" height="{height}" ' f'fill="none" rx="8"/>'
        )

        # Gridlines at 0, 25, 50, 75, 100
        for val in [0, 25, 50, 75, 100]:
            gy = y_for_score(val)
            parts.append(
                f'<line x1="{pad_left}" y1="{gy:.1f}" x2="{width - pad_right}" '
                f'y2="{gy:.1f}" stroke="#e5e7eb" stroke-width="1" '
                f'stroke-dasharray="4"/>'
            )
            parts.append(
                f'<text x="{pad_left - 5}" y="{gy + 4:.1f}" '
                f'text-anchor="end" fill="#9ca3af" font-size="11">{val}</text>'
            )

        # Min/Max band (polygon)
        if n > 1:
            band_points_top = " ".join(
                f"{x_positions[i]:.1f},{y_for_score(trend_data[i]['max_score']):.1f}"
                for i in range(n)
            )
            band_points_bottom = " ".join(
                f"{x_positions[i]:.1f},{y_for_score(trend_data[i]['min_score']):.1f}"
                for i in range(n - 1, -1, -1)
            )
            parts.append(
                f'<polygon points="{band_points_top} {band_points_bottom}" '
                f'fill="{band_color}" opacity="0.1"/>'
            )

        # Average score line
        line_points = " ".join(
            f"{x_positions[i]:.1f},{y_for_score(trend_data[i]['avg_score']):.1f}" for i in range(n)
        )
        parts.append(
            f'<polyline points="{line_points}" fill="none" '
            f'stroke="{line_color}" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

        # Data points with tooltips
        for i in range(n):
            cx = x_positions[i]
            cy = y_for_score(trend_data[i]["avg_score"])
            score = trend_data[i]["avg_score"]
            date = trend_data[i]["date"]
            parts.append(
                f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" '
                f'fill="{line_color}" stroke="white" stroke-width="2">'
                f"<title>{date}: {score:.1f}%</title></circle>"
            )

        # X-axis date labels (sample to avoid overlap)
        max_labels = max(1, plot_w // 80)
        step = max(1, n // max_labels)
        for i in range(0, n, step):
            date_label = trend_data[i]["date"]
            # Shorten date: "2026-01-15" -> "Jan 15"
            try:
                dt = datetime.strptime(date_label, "%Y-%m-%d")
                date_label = dt.strftime("%b %d")
            except (ValueError, TypeError):
                pass
            parts.append(
                f'<text x="{x_positions[i]:.1f}" y="{height - 5}" '
                f'text-anchor="middle" fill="#9ca3af" font-size="11">'
                f"{date_label}</text>"
            )
        # Always show last label if not already shown
        if (n - 1) % step != 0 and n > 1:
            date_label = trend_data[-1]["date"]
            try:
                dt = datetime.strptime(date_label, "%Y-%m-%d")
                date_label = dt.strftime("%b %d")
            except (ValueError, TypeError):
                pass
            parts.append(
                f'<text x="{x_positions[-1]:.1f}" y="{height - 5}" '
                f'text-anchor="middle" fill="#9ca3af" font-size="11">'
                f"{date_label}</text>"
            )

        parts.append("</svg>")
        return "\n".join(parts)


def generate_html_report(
    result: ExecutionResult,
    output_path: str | Path,
    *,
    history: list[StoredRun] | None = None,
    trend_data: list[TrendDataPoint] | None = None,
    row_count: int | None = None,
    column_count: int | None = None,
    **kwargs: Any,
) -> Path:
    """Convenience function to generate HTML report.

    Args:
        result: ExecutionResult to report on
        output_path: Path to write HTML file
        history: Optional historical results for trends
        trend_data: Optional trend data points for chart rendering
        row_count: Optional dataset row count
        column_count: Optional dataset column count
        **kwargs: Additional ReportConfig options

    Returns:
        Path to generated report
    """
    config = ReportConfig(**kwargs) if kwargs else None
    reporter = HTMLReporter(config=config)
    return reporter.generate(
        result,
        output_path,
        history=history,
        trend_data=trend_data,
        row_count=row_count,
        column_count=column_count,
    )
