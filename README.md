<div align="center">
  <img src="docs/assets/duckguard-logo.svg" alt="DuckGuard" width="420">

  <h3>Data Quality That Just Works</h3>
  <p><strong>3 lines of code</strong> &bull; <strong>10x faster</strong> &bull; <strong>20x less memory</strong></p>

  <p><em>Stop wrestling with 50+ lines of boilerplate. Start validating data in seconds.</em></p>

  [![PyPI version](https://img.shields.io/pypi/v/duckguard.svg)](https://pypi.org/project/duckguard/)
  [![Downloads](https://static.pepy.tech/badge/duckguard)](https://pepy.tech/project/duckguard)
  [![GitHub stars](https://img.shields.io/github/stars/XDataHubAI/duckguard?style=social)](https://github.com/XDataHubAI/duckguard/stargazers)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic--2.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
  [![CI](https://github.com/XDataHubAI/duckguard/actions/workflows/ci.yml/badge.svg)](https://github.com/XDataHubAI/duckguard/actions/workflows/ci.yml)

  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/XDataHubAI/duckguard/blob/main/examples/getting_started.ipynb)
  [![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/XDataHubAI/duckguard/blob/main/examples/getting_started.ipynb)
</div>

---

## From Zero to Validated in 30 Seconds

```bash
pip install duckguard
```

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.null_percent == 0   # Just like pytest!
assert orders.amount.between(0, 10000)        # Readable validations
assert orders.status.isin(['pending', 'shipped', 'delivered'])
```

**That's it.** No context. No datasource. No validator. No expectation suite. Just data quality.

---

## Why DuckGuard?

### The Problem

Every data quality tool makes you write **50+ lines of boilerplate** before you can validate a single column. Setting up contexts, datasources, batch requests, validators, expectation suites... just to check if a column has nulls.

### The Solution

DuckGuard gives you a **pytest-like API** powered by **DuckDB's speed**. Write assertions that read like English. Get results in seconds, not minutes.

<table>
<tr>
<td width="50%">

**Great Expectations**
```python
# 50+ lines of setup required
from great_expectations import get_context

context = get_context()
datasource = context.sources.add_pandas("my_ds")
asset = datasource.add_dataframe_asset(
    name="orders", dataframe=df
)
batch_request = asset.build_batch_request()
expectation_suite = context.add_expectation_suite(
    "orders_suite"
)
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name="orders_suite"
)
validator.expect_column_values_to_not_be_null(
    "customer_id"
)
validator.expect_column_values_to_be_between(
    "amount", min_value=0, max_value=10000
)
# ... and more configuration
```
**45 seconds | 4GB RAM | 20+ dependencies**

</td>
<td width="50%">

**DuckGuard**
```python
from duckguard import connect

orders = connect("orders.csv")

assert orders.customer_id.null_percent == 0
assert orders.amount.between(0, 10000)
```

<br><br><br><br><br><br><br><br><br><br><br><br>

**4 seconds | 200MB RAM | 7 dependencies**

</td>
</tr>
</table>

---

## Comparison Table

| Feature | DuckGuard | Great Expectations | Soda Core | Pandera |
|---------|:---------:|:------------------:|:---------:|:-------:|
| **Lines of code to start** | 3 | 50+ | 10+ | 5+ |
| **Time for 1GB CSV*** | ~4 sec | ~45 sec | ~20 sec | ~15 sec |
| **Memory for 1GB CSV*** | ~200 MB | ~4 GB | ~1.5 GB | ~1.5 GB |
| **Direct dependencies** | 7 | 20+ | 11 | 5 |
| **Learning curve** | Minutes | Days | Hours | Minutes |
| **Pytest-like API** | ✅ | ❌ | ❌ | ❌ |
| **DuckDB-powered** | ✅ | ❌ | ✅ (v4) | ❌ |
| **Cloud storage (S3/GCS/Azure)** | ✅ | ✅ | ✅ | ❌ |
| **Database connectors** | 11+ | ✅ | ✅ | ❌ |
| **PII detection** | ✅ Built-in | ❌ | ❌ | ❌ |
| **Anomaly detection (ML)** | ✅ Built-in | ❌ | ✅ (v4) | ❌ |
| **Schema evolution tracking** | ✅ Built-in | ❌ | ✅ | ❌ |
| **Freshness monitoring** | ✅ Built-in | ❌ | ✅ | ❌ |
| **Data contracts** | ✅ | ❌ | ✅ | ✅ |
| **Row-level error details** | ✅ | ✅ | ❌ | ✅ |
| **Reference/FK checks** | ✅ Built-in | ✅ | ✅ | ❌ |
| **Cross-dataset validation** | ✅ Built-in | ⚠️ | ✅ | ❌ |
| **YAML rules** | ✅ | ✅ | ✅ | ❌ |
| **dbt integration** | ✅ | ✅ | ✅ | ❌ |
| **Slack/Teams alerts** | ✅ | ✅ | ✅ | ❌ |
| **HTML/PDF reports** | ✅ | ✅ | ✅ | ❌ |

<sub>*Performance varies by hardware and data characteristics. Based on typical usage patterns with DuckDB's columnar engine.</sub>

---

## Demo

<div align="center">
  <img src="docs/assets/demo.gif" alt="DuckGuard Demo" width="750">
</div>

```python
from duckguard import connect

orders = connect("data/orders.csv")

# Assertions that read like English
assert orders.row_count > 0
assert orders.customer_id.null_percent < 5
assert orders.amount.between(0, 10000)
assert orders.status.isin(['pending', 'shipped', 'delivered'])

# Get a quality score
quality = orders.score()
print(f"Grade: {quality.grade}")  # A, B, C, D, or F
```

---

## Installation

```bash
pip install duckguard

# With optional features
pip install duckguard[reports]     # HTML/PDF reports
pip install duckguard[snowflake]   # Snowflake connector
pip install duckguard[databricks]  # Databricks connector
pip install duckguard[airflow]     # Airflow integration
pip install duckguard[all]         # Everything
```

---

## Features

<table>
<tr>
<td align="center" width="25%">
<h3>🎯</h3>
<b>Quality Scoring</b><br>
<sub>A-F grades based on ISO 8000</sub>
</td>
<td align="center" width="25%">
<h3>🔒</h3>
<b>PII Detection</b><br>
<sub>Auto-detect emails, SSNs, phones</sub>
</td>
<td align="center" width="25%">
<h3>📊</h3>
<b>Anomaly Detection</b><br>
<sub>Z-score, IQR, ML baselines</sub>
</td>
<td align="center" width="25%">
<h3>🔔</h3>
<b>Alerts</b><br>
<sub>Slack, Teams, Email notifications</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>⏰</h3>
<b>Freshness Monitoring</b><br>
<sub>Detect stale data automatically</sub>
</td>
<td align="center">
<h3>📐</h3>
<b>Schema Evolution</b><br>
<sub>Track & detect breaking changes</sub>
</td>
<td align="center">
<h3>📜</h3>
<b>Data Contracts</b><br>
<sub>Schema + SLAs enforcement</sub>
</td>
<td align="center">
<h3>🔍</h3>
<b>Row-Level Errors</b><br>
<sub>See exactly which rows failed</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>📄</h3>
<b>HTML/PDF Reports</b><br>
<sub>Beautiful shareable reports</sub>
</td>
<td align="center">
<h3>📈</h3>
<b>Historical Tracking</b><br>
<sub>Quality trends over time</sub>
</td>
<td align="center">
<h3>🔧</h3>
<b>dbt Integration</b><br>
<sub>Export rules as dbt tests</sub>
</td>
<td align="center">
<h3>🚀</h3>
<b>CI/CD Ready</b><br>
<sub>GitHub Actions & Airflow</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>🔗</h3>
<b>Reference/FK Checks</b><br>
<sub>Cross-dataset FK validation</sub>
</td>
<td align="center">
<h3>🔀</h3>
<b>Cross-Dataset Validation</b><br>
<sub>Compare datasets & columns</sub>
</td>
<td align="center">
<h3>⚖️</h3>
<b>Reconciliation</b><br>
<sub>Migration & sync validation</sub>
</td>
<td align="center">
<h3>📊</h3>
<b>Distribution Drift</b><br>
<sub>KS-test based drift detection</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>📁</h3>
<b>Group By Checks</b><br>
<sub>Segmented validation</sub>
</td>
<td align="center" colspan="3">
</td>
</tr>
</table>

---

## Connect to Anything

```python
from duckguard import connect

# Files
orders = connect("orders.csv")
orders = connect("orders.parquet")
orders = connect("orders.json")

# Cloud Storage
orders = connect("s3://bucket/orders.parquet")
orders = connect("gs://bucket/orders.parquet")
orders = connect("az://container/orders.parquet")

# Databases
orders = connect("postgres://localhost/db", table="orders")
orders = connect("mysql://localhost/db", table="orders")
orders = connect("snowflake://account/db", table="orders")
orders = connect("bigquery://project/dataset", table="orders")
orders = connect("databricks://workspace/catalog/schema", table="orders")
orders = connect("redshift://cluster/db", table="orders")

# Streaming
orders = connect("kafka://broker:9092/orders-topic", sample_size=1000)

# Modern Formats
orders = connect("delta://path/to/delta_table")
orders = connect("iceberg://path/to/iceberg_table")
```

**Supported:** CSV, Parquet, JSON, Excel | S3, GCS, Azure Blob | PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, Redshift, Databricks, SQL Server, Oracle, MongoDB | Kafka | Delta Lake, Apache Iceberg

---

## Quick Examples

<details open>
<summary><b>🎯 Quality Score</b></summary>

```python
quality = orders.score()
print(f"Grade: {quality.grade}")        # A, B, C, D, or F
print(f"Score: {quality.score}/100")    # Numeric score
print(f"Completeness: {quality.completeness}%")
```
</details>

<details>
<summary><b>📋 YAML Rules</b></summary>

```yaml
# duckguard.yaml
dataset: orders
rules:
  - order_id is not null
  - order_id is unique
  - amount >= 0
  - status in ['pending', 'shipped', 'delivered']
  - customer_email matches '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
```

```python
from duckguard import load_rules, execute_rules

result = execute_rules(load_rules("duckguard.yaml"), dataset=orders)
print(f"Passed: {result.passed_count}/{result.total_checks}")
```
</details>

<details>
<summary><b>🔒 PII Detection</b></summary>

```python
from duckguard.semantic import SemanticAnalyzer

analysis = SemanticAnalyzer().analyze(orders)
print(f"PII columns: {analysis.pii_columns}")
# PII columns: ['email', 'phone', 'ssn']

for col in analysis.columns:
    if col.is_pii:
        print(f"⚠️  {col.name}: {col.pii_type} detected!")
```
</details>

<details>
<summary><b>📊 Anomaly Detection</b></summary>

```python
from duckguard import detect_anomalies

# Statistical methods
report = detect_anomalies(orders, method="zscore")
report = detect_anomalies(orders, method="iqr")

# ML-based baseline learning
report = detect_anomalies(orders, method="baseline", learn_baseline=True)

# Later: compare new data against baseline
report = detect_anomalies(new_orders, method="baseline")
if report.has_anomalies:
    for anomaly in report.anomalies:
        print(f"🚨 {anomaly.column}: {anomaly.message}")
```
</details>

<details>
<summary><b>⏰ Freshness Monitoring</b></summary>

```python
from datetime import timedelta

# Quick check
print(data.freshness.age_human)  # "2 hours ago"
print(data.freshness.is_fresh)   # True

# Custom threshold
if not data.is_fresh(timedelta(hours=6)):
    print("🚨 Data is stale!")
```
</details>

<details>
<summary><b>📐 Schema Evolution</b></summary>

```python
from duckguard.schema_history import SchemaTracker, SchemaChangeAnalyzer

tracker = SchemaTracker()
tracker.capture(data)  # Save snapshot

# Later: detect changes
analyzer = SchemaChangeAnalyzer()
report = analyzer.detect_changes(data)

if report.has_breaking_changes:
    print("🚨 Breaking schema changes!")
    for change in report.breaking_changes:
        print(f"  - {change}")
```
</details>

<details>
<summary><b>📜 Data Contracts</b></summary>

```python
from duckguard import generate_contract, validate_contract

# Generate from existing data
contract = generate_contract(orders)
contract.save("orders_contract.yaml")

# Validate new data
result = validate_contract(contract, new_orders)
if not result.passed:
    print("❌ Contract violation!")
```
</details>

<details>
<summary><b>🔍 Row-Level Errors</b></summary>

```python
result = orders.quantity.between(1, 100)
if not result.passed:
    print(result.summary())
    # Sample of 10 failing rows (total: 25):
    #   Row 5: quantity=150 - Value outside range [1, 100]
    #   Row 12: quantity=-5 - Value outside range [1, 100]

    # Export failed rows for debugging
    failed_df = result.to_dataframe()
```
</details>

<details>
<summary><b>🔔 Slack/Teams/Email Alerts</b></summary>

```python
from duckguard.notifications import SlackNotifier, EmailNotifier

slack = SlackNotifier(webhook_url="https://hooks.slack.com/...")
# Or: email = EmailNotifier(smtp_host="smtp.gmail.com", ...)

result = execute_rules(rules, dataset=orders)
if not result.passed:
    slack.send_failure_alert(result)
```
</details>

<details>
<summary><b>📄 HTML/PDF Reports</b></summary>

```python
from duckguard.reports import generate_html_report, generate_pdf_report

result = execute_rules(load_rules("duckguard.yaml"), dataset=orders)

generate_html_report(result, "report.html")
generate_pdf_report(result, "report.pdf")  # requires weasyprint
```
</details>

<details>
<summary><b>🔧 dbt Integration</b></summary>

```python
from duckguard.integrations import dbt

# Export DuckGuard rules to dbt
rules = load_rules("duckguard.yaml")
dbt.export_to_schema(rules, "models/schema.yml")

# Import dbt tests as DuckGuard rules
rules = dbt.import_from_dbt("models/schema.yml")
```
</details>

<details>
<summary><b>🚀 Airflow Integration</b></summary>

```python
from duckguard.integrations.airflow import DuckGuardOperator

validate_orders = DuckGuardOperator(
    task_id="validate_orders",
    source="s3://bucket/orders.parquet",
    config="duckguard.yaml",
    fail_on_error=True,
)
```
</details>

<details>
<summary><b>⚡ GitHub Actions</b></summary>

```yaml
# .github/workflows/data-quality.yml
- uses: XDataHubAI/duckguard/.github/actions/duckguard-check@main
  with:
    source: data/orders.csv
    config: duckguard.yaml
```
</details>

<details>
<summary><b>🔗 Reference/FK Checks</b></summary>

```python
from duckguard import connect

orders = connect("orders.parquet")
customers = connect("customers.parquet")

# Check that all customer_ids exist in customers table
result = orders["customer_id"].exists_in(customers["id"])
if not result.passed:
    print(f"Found {result.actual_value} orphan records!")
    for row in result.failed_rows:
        print(f"  Row {row.row_number}: {row.value}")

# FK check with null handling options
result = orders["customer_id"].references(
    customers["id"],
    allow_nulls=True  # Nulls are OK (optional FK)
)

# Get list of orphan values for debugging
orphans = orders["customer_id"].find_orphans(customers["id"])
print(f"Invalid customer IDs: {orphans}")
```
</details>

<details>
<summary><b>🔀 Cross-Dataset Validation</b></summary>

```python
from duckguard import connect

orders = connect("orders.parquet")
backup = connect("orders_backup.parquet")
status_lookup = connect("status_codes.csv")

# Compare row counts between datasets
result = orders.row_count_matches(backup)
result = orders.row_count_matches(backup, tolerance=10)  # Allow small diff

# Validate that column values match a lookup table
result = orders["status"].matches_values(status_lookup["code"])
if not result.passed:
    print(f"Missing in lookup: {result.details['missing_in_other']}")
    print(f"Extra in lookup: {result.details['extra_in_other']}")
```
</details>

<details>
<summary><b>⚖️ Reconciliation</b></summary>

```python
from duckguard import connect

source = connect("orders_source.parquet")
target = connect("orders_migrated.parquet")

# Reconcile datasets using primary key
result = source.reconcile(
    target,
    key_columns=["order_id"],
    compare_columns=["amount", "status", "customer_id"]
)

if not result.passed:
    print(f"Missing in target: {result.missing_in_target}")
    print(f"Extra in target: {result.extra_in_target}")
    print(f"Value mismatches: {result.value_mismatches}")
    print(result.summary())

# With numeric tolerance for floating point comparison
result = source.reconcile(
    target,
    key_columns=["order_id"],
    compare_columns=["amount"],
    tolerance=0.01  # Allow 1% difference
)
```
</details>

<details>
<summary><b>📊 Distribution Drift Detection</b></summary>

```python
from duckguard import connect

baseline = connect("orders_baseline.parquet")
current = connect("orders_current.parquet")

# Detect distribution drift using KS-test
result = current["amount"].detect_drift(baseline["amount"])

if result.is_drifted:
    print(f"Distribution drift detected!")
    print(f"P-value: {result.p_value:.4f}")
    print(f"KS statistic: {result.statistic:.4f}")

# Custom threshold (default: 0.05)
result = current["score"].detect_drift(
    baseline["score"],
    threshold=0.01  # More sensitive detection
)
```
</details>

<details>
<summary><b>📁 Group By Checks</b></summary>

```python
from duckguard import connect

orders = connect("orders.parquet")

# Get group statistics
stats = orders.group_by("region").stats()
for g in stats:
    print(f"{g['region']}: {g['row_count']} rows")

# Validate row count per group
result = orders.group_by("region").row_count_greater_than(100)
if not result.passed:
    for g in result.get_failed_groups():
        print(f"Region {g.group_key} has only {g.row_count} rows")

# Group by multiple columns
result = orders.group_by(["date", "region"]).row_count_greater_than(0)
print(f"Passed: {result.passed_groups}/{result.total_groups} groups")
```
</details>

---

## CLI

```bash
# Validate data
duckguard check orders.csv
duckguard check orders.csv --config duckguard.yaml

# Auto-generate rules from data
duckguard discover orders.csv > duckguard.yaml

# Generate reports
duckguard report orders.csv --output report.html

# Anomaly detection
duckguard anomaly orders.csv --method zscore
duckguard anomaly orders.csv --learn-baseline
duckguard anomaly orders.csv --method baseline

# Freshness monitoring
duckguard freshness orders.csv --max-age 6h

# Schema tracking
duckguard schema orders.csv --action capture
duckguard schema orders.csv --action changes

# Data contracts
duckguard contract generate orders.csv
duckguard contract validate orders.csv
```

---

## Performance

Built on DuckDB for blazing fast validation:

| Dataset | Great Expectations | DuckGuard | Speedup |
|---------|:------------------:|:---------:|:-------:|
| 1GB CSV | 45 sec, 4GB RAM | **4 sec, 200MB RAM** | **10x faster** |
| 10GB Parquet | 8 min, 32GB RAM | **45 sec, 2GB RAM** | **10x faster** |
| 100M rows | Minutes | **Seconds** | **10x faster** |

### Why So Fast?

- **DuckDB engine**: Columnar, vectorized, SIMD-optimized
- **Zero copy**: Direct file access, no DataFrame conversion
- **Lazy evaluation**: Only compute what's needed
- **Memory efficient**: Stream large files without loading entirely

---

## Scaling Guide

| Data Size | Recommendation |
|-----------|----------------|
| < 10M rows | DuckGuard directly |
| 10-100M rows | Use Parquet, configure `memory_limit` |
| 100GB+ | Use database connectors (Snowflake, BigQuery, Databricks) |
| Delta Tables | Use Databricks connector for query pushdown |

```python
from duckguard import DuckGuardEngine, connect

# Configure for large datasets
engine = DuckGuardEngine(memory_limit="8GB")
dataset = connect("large_data.parquet", engine=engine)
```

---

## Column Methods Reference

```python
# Statistics (properties)
col.null_percent      # Percentage of null values
col.unique_percent    # Percentage of unique values
col.min, col.max      # Min/max values
col.mean, col.stddev  # Mean and standard deviation
col.count             # Non-null count

# Validations (return ValidationResult with .passed, .summary(), etc.)
col.not_null()                # No nulls allowed
col.is_unique()               # All values unique
col.between(0, 100)           # Range check
col.greater_than(0)           # Minimum value
col.less_than(1000)           # Maximum value
col.matches(r'^\d{5}$')       # Regex pattern
col.isin(['a', 'b', 'c'])     # Allowed values
col.not_in(['x', 'y'])        # Forbidden values
col.has_no_duplicates()       # No duplicate values
col.value_lengths_between(1, 50)  # String length

# Cross-dataset validation (return ValidationResult)
col.exists_in(other_col)             # FK check: values exist in reference
col.references(other_col)            # FK check with null handling options
col.find_orphans(other_col)          # Get list of orphan values
col.matches_values(other_col)        # Value sets match between columns

# Distribution drift detection (returns DriftResult)
col.detect_drift(other_col)          # KS-test based drift detection
col.detect_drift(other_col, threshold=0.01)  # Custom p-value threshold
```

## Dataset Methods Reference

```python
# Properties
dataset.row_count      # Number of rows
dataset.columns        # List of column names
dataset.column_count   # Number of columns
dataset.freshness      # FreshnessResult with age info

# Validation methods
dataset.is_fresh(timedelta)              # Check data freshness
dataset.row_count_matches(other)         # Compare row counts
dataset.row_count_equals(other)          # Exact row count match
dataset.score()                          # Calculate quality score

# Reconciliation (returns ReconciliationResult)
dataset.reconcile(other, key_columns)    # Full dataset comparison
dataset.reconcile(other, key_columns, compare_columns, tolerance)

# Group By (returns GroupedDataset)
dataset.group_by("column")               # Group by single column
dataset.group_by(["col1", "col2"])       # Group by multiple columns
grouped.stats()                          # Get per-group statistics
grouped.row_count_greater_than(100)      # Validate per-group row counts
```

---

## Migrating from Great Expectations?

```python
# Before: Great Expectations (50+ lines)
context = get_context()
datasource = context.sources.add_pandas("my_datasource")
asset = datasource.add_dataframe_asset(name="orders", dataframe=df)
batch_request = asset.build_batch_request()
expectation_suite = context.add_expectation_suite("orders_suite")
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name="orders_suite"
)
validator.expect_column_values_to_not_be_null("customer_id")
validator.expect_column_values_to_be_between("amount", 0, 10000)
results = validator.validate()

# After: DuckGuard (3 lines)
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.null_percent == 0
assert orders.amount.between(0, 10000)
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Clone and install
git clone https://github.com/XDataHubAI/duckguard.git
cd duckguard
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check src tests
```

---

## License

Elastic License 2.0 - see [LICENSE](LICENSE)

---

<div align="center">
  <p>
    <strong>Built with ❤️ by the DuckGuard Team</strong>
  </p>
  <p>
    <a href="https://github.com/XDataHubAI/duckguard/issues">Report Bug</a>
    ·
    <a href="https://github.com/XDataHubAI/duckguard/issues">Request Feature</a>
    ·
    <a href="https://github.com/XDataHubAI/duckguard/discussions">Discussions</a>
  </p>
</div>
