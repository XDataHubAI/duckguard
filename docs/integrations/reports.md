# Reports

Generate beautiful HTML and PDF data quality reports.

## Quick Start

```bash
# HTML report (default)
duckguard report data.csv --output report.html

# PDF report
duckguard report data.csv --format pdf --output report.pdf

# With custom title and YAML rules
duckguard report data.csv \
  --config duckguard.yaml \
  --title "Orders Quality Report" \
  --output report.html
```

## CLI Options

```bash
duckguard report <source> [options]

Options:
  --config, -c      Path to duckguard.yaml rules file
  --table, -t       Table name (for databases)
  --format, -f      Output format: html (default), pdf
  --output, -o      Output file path (default: report.html)
  --title           Report title
  --include-passed  Include passed checks (default: true)
  --no-passed       Exclude passed checks
  --store, -s       Store results in history database
  --trends          Include quality trend charts from history
  --trend-days      Number of days for trend charts (default: 30)
  --dark-mode       Theme: auto, light, dark
  --logo            Logo URL for report header
```

## Features

| Feature | HTML | PDF |
|---------|------|-----|
| Dark/light mode | ✅ | ✅ |
| Interactive tables | ✅ | — |
| Quality score | ✅ | ✅ |
| Check results | ✅ | ✅ |
| Trend charts | ✅ | ✅ |
| Shareable | ✅ | ✅ |

## Python API

```python
from duckguard import connect
from duckguard.rules import load_rules, execute_rules
from duckguard.reports import HTMLReporter, PDFReporter, ReportConfig

# Run checks
data = connect("orders.csv")
rules = load_rules("duckguard.yaml")
result = execute_rules(rules, dataset=data)

# Configure report
config = ReportConfig(
    title="Orders Quality Report",
    include_passed=True,
    include_trends=False,
    dark_mode="auto",
    logo_url="https://example.com/logo.png",
)

# Generate HTML
reporter = HTMLReporter(config=config)
reporter.generate(
    result, "report.html",
    row_count=data.row_count,
    column_count=data.column_count,
)

# Generate PDF (requires weasyprint)
reporter = PDFReporter(config=config)
reporter.generate(result, "report.pdf")
```

## Trend Charts

Include historical quality trends by enabling history storage:

```bash
# First, run checks with --store to build history
duckguard report data.csv --config rules.yaml --store

# Later, include trends in reports
duckguard report data.csv --config rules.yaml --trends --trend-days 30
```

## Dark Mode

Reports support three theme modes:

- `auto` — matches the viewer's system preference
- `light` — always light theme
- `dark` — always dark theme

```bash
duckguard report data.csv --dark-mode dark
```

## PDF Requirements

PDF generation requires `weasyprint`:

```bash
pip install 'duckguard[reports]'
```

## Example Workflow

```bash
# 1. Profile data
duckguard profile data.csv

# 2. Generate rules
duckguard discover data.csv --output duckguard.yaml

# 3. Run checks and generate report
duckguard report data.csv \
  --config duckguard.yaml \
  --store \
  --trends \
  --title "Daily Quality Report" \
  --output reports/quality-$(date +%F).html
```
