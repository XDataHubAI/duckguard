# DuckGuard

Data quality that just works. Python-native, DuckDB-powered, 10x faster.

[![PyPI version](https://img.shields.io/pypi/v/duckguard.svg)](https://pypi.org/project/duckguard/)
[![Downloads](https://static.pepy.tech/badge/duckguard)](https://pepy.tech/project/duckguard)
[![GitHub stars](https://img.shields.io/github/stars/XDataHubAI/duckguard?style=social)](https://github.com/XDataHubAI/duckguard/stargazers)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic--2.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![CI](https://github.com/XDataHubAI/duckguard/actions/workflows/ci.yml/badge.svg)](https://github.com/XDataHubAI/duckguard/actions/workflows/ci.yml)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/XDataHubAI/duckguard/blob/main/examples/getting_started.ipynb)
[![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/XDataHubAI/duckguard/blob/main/examples/getting_started.ipynb)

```bash
pip install duckguard

# With optional features
pip install duckguard[reports]   # HTML/PDF reports
pip install duckguard[airflow]   # Airflow integration
pip install duckguard[all]       # All features
```

## 60-Second Demo

```bash
# CLI - instant data quality check
duckguard check data.csv

# Auto-generate validation rules
duckguard discover data.csv --output duckguard.yaml
```

```python
# Python - feels like pytest
from duckguard import connect

orders = connect("data/orders.csv")

assert orders.row_count > 0
assert orders.customer_id.null_percent < 5
assert orders.amount.between(0, 10000)
assert orders.status.isin(['pending', 'shipped', 'delivered'])
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Quality Scoring** | Get A-F grades for your data |
| **YAML Rules** | Define checks in simple YAML files |
| **Semantic Detection** | Auto-detect emails, phones, SSNs, PII |
| **Data Contracts** | Schema + SLAs with breaking change detection |
| **Anomaly Detection** | Z-score, IQR, and percent change methods |
| **pytest Integration** | Data tests alongside unit tests |
| **Slack/Teams Alerts** | Get notified when checks fail |
| **Row-Level Errors** | See exactly which rows failed |
| **dbt Integration** | Export rules as dbt tests |
| **HTML/PDF Reports** | Generate beautiful shareable reports |
| **Historical Tracking** | Store and analyze quality trends over time |
| **Airflow Operator** | Native integration for data pipelines |
| **GitHub Action** | CI/CD data quality gates |

## Quick Examples

### Quality Score
```python
quality = orders.score()
print(f"Grade: {quality.grade}")  # A, B, C, D, or F
```

### YAML Rules
```yaml
# duckguard.yaml
dataset: orders
rules:
  - order_id is not null
  - order_id is unique
  - amount >= 0
  - status in ['pending', 'shipped', 'delivered']
```

```python
from duckguard import load_rules, execute_rules
result = execute_rules(load_rules("duckguard.yaml"), dataset=orders)
```

### PII Detection
```python
from duckguard.semantic import SemanticAnalyzer
analysis = SemanticAnalyzer().analyze(orders)
print(f"PII found: {analysis.pii_columns}")
```

### Anomaly Detection
```python
from duckguard import detect_anomalies
report = detect_anomalies(orders, method="zscore")
```

### Data Contracts
```python
from duckguard import generate_contract, validate_contract
contract = generate_contract(orders)
result = validate_contract(contract, new_orders)
```

### Slack/Teams Notifications
```python
from duckguard.notifications import SlackNotifier

slack = SlackNotifier(webhook_url="https://hooks.slack.com/...")
# Or set DUCKGUARD_SLACK_WEBHOOK env var

result = execute_rules(rules, dataset=orders)
if not result.passed:
    slack.send_failure_alert(result)
```

### Row-Level Error Debugging
```python
# See exactly which rows failed validation
result = orders.quantity.between(1, 100)
if not result.passed:
    print(result.summary())
    # Sample of 10 failing rows (total: 25):
    #   Row 5: quantity=150 - Value 150 is outside range [1, 100]
    #   Row 12: quantity=200 - Value 200 is outside range [1, 100]

    # Get failed values as list
    print(result.get_failed_values())  # [150, 200, ...]
```

### dbt Integration
```python
from duckguard import load_rules
from duckguard.integrations import dbt

# Export DuckGuard rules to dbt schema.yml
rules = load_rules("duckguard.yaml")
dbt.export_to_schema(rules, "models/schema.yml")

# Generate dbt singular tests
dbt.generate_singular_tests(rules, "tests/")

# Import dbt tests as DuckGuard rules
rules = dbt.import_from_dbt("models/schema.yml")
```

### HTML/PDF Reports
```python
from duckguard import execute_rules, load_rules
from duckguard.reports import generate_html_report, generate_pdf_report

result = execute_rules(load_rules("duckguard.yaml"), dataset=orders)

# Generate beautiful HTML report
generate_html_report(result, "report.html", title="Orders Quality Report")

# Generate PDF report (requires weasyprint)
generate_pdf_report(result, "report.pdf")
```

### Historical Tracking
```python
from duckguard.history import HistoryStorage, TrendAnalyzer

# Store validation results
storage = HistoryStorage()  # Uses ~/.duckguard/history.db
run_id = storage.store(result)

# Query historical runs
runs = storage.get_runs("orders.csv", limit=10)

# Analyze quality trends
analyzer = TrendAnalyzer(storage)
trend = analyzer.analyze("orders.csv", days=30)
print(f"Trend: {trend.score_trend}, Pass rate: {trend.pass_rate}%")
```

### Airflow Integration
```python
from duckguard.integrations.airflow import DuckGuardOperator

# Use in your Airflow DAG
validate_orders = DuckGuardOperator(
    task_id="validate_orders",
    source="s3://bucket/orders.parquet",
    config="duckguard.yaml",
    fail_on_error=True,
    store_history=True,
)
```

### GitHub Action
```yaml
# .github/workflows/data-quality.yml
- uses: XDataHubAI/duckguard/.github/actions/duckguard-check@main
  with:
    source: data/orders.csv
    config: duckguard.yaml
    fail-on-warning: false
```

## Supported Sources

**Files:** CSV, Parquet, JSON, Excel
**Cloud:** S3, GCS, Azure Blob
**Databases:** PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, Redshift, Databricks, SQL Server, Oracle, MongoDB
**Formats:** Delta Lake, Apache Iceberg

```python
# Connect to anything
orders = connect("s3://bucket/orders.parquet")
orders = connect("postgres://localhost/db", table="orders")
orders = connect("snowflake://account/db", table="orders")
```

## CLI Commands

```bash
duckguard check <file>       # Run quality checks
duckguard discover <file>    # Auto-generate rules
duckguard contract generate  # Create data contract
duckguard contract validate  # Validate against contract
duckguard anomaly <file>     # Detect anomalies
duckguard report <file>      # Generate HTML/PDF report
duckguard history            # View validation history
duckguard history --trend    # Analyze quality trends
```

## Column Methods

```python
# Statistics
col.null_percent, col.unique_percent
col.min, col.max, col.mean, col.stddev

# Validations
col.between(0, 100)
col.matches(r'^\d{5}$')
col.isin(['a', 'b', 'c'])
col.has_no_duplicates()
```

## Performance

Built on DuckDB for speed:

| | Pandas/GX | DuckGuard |
|---|---|---|
| 1GB CSV | 45s, 4GB RAM | 4s, 200MB RAM |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Elastic License 2.0 - see [LICENSE](LICENSE)
