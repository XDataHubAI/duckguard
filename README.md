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

orders = connect("orders.csv")                               # CSV, Parquet, JSON, S3, databases...
assert orders.customer_id.is_not_null()                      # Just like pytest!
assert orders.amount.between(0, 10000)                       # Readable validations
assert orders.status.isin(["pending", "shipped", "delivered"])

quality = orders.score()
print(f"Grade: {quality.grade}")  # A, B, C, D, or F
```

**That's it.** No context. No datasource. No validator. No expectation suite. Just data quality.

---

## Demo

<div align="center">
  <img src="docs/assets/demo.gif" alt="DuckGuard Demo" width="750">
</div>

---

## Why DuckGuard?

Every data quality tool asks you to write **50+ lines of boilerplate** before you can validate a single column. DuckGuard gives you a **pytest-like API** powered by **DuckDB's speed**.

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

assert orders.customer_id.is_not_null()
assert orders.amount.between(0, 10000)
```

<br><br><br><br><br><br><br><br><br><br><br><br>

**4 seconds | 200MB RAM | 7 dependencies**

</td>
</tr>
</table>

| Feature | DuckGuard | Great Expectations | Soda Core | Pandera |
|---------|:---------:|:------------------:|:---------:|:-------:|
| **Lines of code to start** | 3 | 50+ | 10+ | 5+ |
| **Time for 1GB CSV*** | ~4 sec | ~45 sec | ~20 sec | ~15 sec |
| **Memory for 1GB CSV*** | ~200 MB | ~4 GB | ~1.5 GB | ~1.5 GB |
| **Learning curve** | Minutes | Days | Hours | Minutes |
| **Pytest-like API** | **Yes** | - | - | - |
| **DuckDB-powered** | **Yes** | - | Partial | - |
| **Cloud storage (S3/GCS/Azure)** | **Yes** | Yes | Yes | - |
| **Database connectors** | **11+** | Yes | Yes | - |
| **PII detection** | **Built-in** | - | - | - |
| **Anomaly detection (7 methods)** | **Built-in** | - | Partial | - |
| **Schema evolution tracking** | **Built-in** | - | Yes | - |
| **Freshness monitoring** | **Built-in** | - | Yes | - |
| **Data contracts** | **Yes** | - | Yes | Yes |
| **Row-level error details** | **Yes** | Yes | - | Yes |
| **Cross-dataset & FK checks** | **Built-in** | Partial | Yes | - |
| **Reconciliation** | **Built-in** | - | - | - |
| **Distribution drift** | **Built-in** | - | - | - |
| **Conditional checks** | **Built-in** | - | - | - |
| **Query-based checks** | **Built-in** | - | Yes | - |
| **YAML rules** | **Yes** | Yes | Yes | - |
| **dbt integration** | **Yes** | Yes | Yes | - |
| **Slack/Teams/Email alerts** | **Yes** | Yes | Yes | - |
| **HTML/PDF reports** | **Yes** | Yes | Yes | - |

<sub>*Performance varies by hardware and data characteristics. Based on typical usage patterns with DuckDB's columnar engine.</sub>

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

## Feature Overview

<table>
<tr>
<td align="center" width="25%">
<h3>&#127919;</h3>
<b>Quality Scoring</b><br>
<sub>A-F grades with 4 quality dimensions</sub>
</td>
<td align="center" width="25%">
<h3>&#128274;</h3>
<b>PII Detection</b><br>
<sub>Auto-detect emails, SSNs, phones</sub>
</td>
<td align="center" width="25%">
<h3>&#128200;</h3>
<b>Anomaly Detection</b><br>
<sub>Z-score, IQR, KS-test, ML baselines</sub>
</td>
<td align="center" width="25%">
<h3>&#128276;</h3>
<b>Alerts</b><br>
<sub>Slack, Teams, Email</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>&#9200;</h3>
<b>Freshness Monitoring</b><br>
<sub>Detect stale data automatically</sub>
</td>
<td align="center">
<h3>&#128208;</h3>
<b>Schema Evolution</b><br>
<sub>Track and detect breaking changes</sub>
</td>
<td align="center">
<h3>&#128220;</h3>
<b>Data Contracts</b><br>
<sub>Schema + SLA enforcement</sub>
</td>
<td align="center">
<h3>&#128270;</h3>
<b>Row-Level Errors</b><br>
<sub>See exactly which rows failed</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>&#128196;</h3>
<b>HTML/PDF Reports</b><br>
<sub>Beautiful shareable reports</sub>
</td>
<td align="center">
<h3>&#128200;</h3>
<b>Historical Tracking</b><br>
<sub>Quality trends over time</sub>
</td>
<td align="center">
<h3>&#128279;</h3>
<b>Cross-Dataset Checks</b><br>
<sub>FK, reconciliation, drift</sub>
</td>
<td align="center">
<h3>&#128640;</h3>
<b>CI/CD Ready</b><br>
<sub>dbt, Airflow, GitHub Actions</sub>
</td>
</tr>
<tr>
<td align="center">
<h3>&#128203;</h3>
<b>YAML Rules</b><br>
<sub>Declarative validation rules</sub>
</td>
<td align="center">
<h3>&#128269;</h3>
<b>Auto-Profiling</b><br>
<sub>Semantic types & rule suggestions</sub>
</td>
<td align="center">
<h3>&#9889;</h3>
<b>Conditional Checks</b><br>
<sub>Validate when conditions are met</sub>
</td>
<td align="center">
<h3>&#128202;</h3>
<b>Group-By Validation</b><br>
<sub>Segmented per-group checks</sub>
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

# Modern Formats
orders = connect("delta://path/to/delta_table")
orders = connect("iceberg://path/to/iceberg_table")

# pandas DataFrame
import pandas as pd
orders = connect(pd.read_csv("orders.csv"))
```

**Supported:** CSV, Parquet, JSON, Excel | S3, GCS, Azure Blob | PostgreSQL, MySQL, SQLite, Snowflake, BigQuery, Redshift, Databricks, SQL Server, Oracle, MongoDB | Delta Lake, Apache Iceberg | pandas DataFrames

---

## Cookbook

### Column Validation

```python
orders = connect("orders.csv")

# Null & uniqueness
orders.order_id.is_not_null()          # No nulls allowed
orders.order_id.is_unique()            # All values distinct
orders.order_id.has_no_duplicates()    # Alias for is_unique

# Range & comparison
orders.amount.between(0, 10000)        # Inclusive range
orders.amount.greater_than(0)          # Minimum (exclusive)
orders.amount.less_than(100000)        # Maximum (exclusive)

# Pattern & enum
orders.email.matches(r'^[\w.+-]+@[\w-]+\.[\w.]+$')
orders.status.isin(["pending", "shipped", "delivered"])

# String length
orders.order_id.value_lengths_between(5, 10)
```

Every validation returns a `ValidationResult` with `.passed`, `.message`, `.summary()`, and `.failed_rows`.

### Row-Level Error Debugging

```python
result = orders.quantity.between(1, 100)

if not result.passed:
    print(result.summary())
    # Column 'quantity' has 3 values outside [1, 100]
    #
    # Sample of 3 failing rows (total: 3):
    #   Row 5: quantity=500 - Value outside range [1, 100]
    #   Row 23: quantity=-2 - Value outside range [1, 100]
    #   Row 29: quantity=0 - Value outside range [1, 100]

    for row in result.failed_rows:
        print(f"Row {row.row_number}: {row.value} ({row.reason})")

    print(result.get_failed_values())        # [500, -2, 0]
    print(result.get_failed_row_indices())   # [5, 23, 29]
```

### Quality Scoring

```python
score = orders.score()

print(score.grade)          # A, B, C, D, or F
print(score.overall)        # 0-100 composite score
print(score.completeness)   # % non-null across all columns
print(score.uniqueness)     # % unique across key columns
print(score.validity)       # % values passing type/range checks
print(score.consistency)    # % consistent formatting
```

### Cross-Dataset Validation

```python
orders = connect("orders.csv")
customers = connect("customers.csv")

# Foreign key check
result = orders.customer_id.exists_in(customers.customer_id)

# FK with null handling
result = orders.customer_id.references(customers.customer_id, allow_nulls=True)

# Get orphan values for debugging
orphans = orders.customer_id.find_orphans(customers.customer_id)
print(f"Invalid IDs: {orphans}")

# Compare value sets
result = orders.status.matches_values(lookup.code)

# Compare row counts with tolerance
result = orders.row_count_matches(backup, tolerance=10)
```

### Reconciliation

```python
source = connect("orders_source.parquet")
target = connect("orders_migrated.parquet")

recon = source.reconcile(
    target,
    key_columns=["order_id"],
    compare_columns=["amount", "status", "customer_id"],
)

print(recon.match_percentage)    # 95.5
print(recon.missing_in_target)   # 3
print(recon.extra_in_target)     # 1
print(recon.value_mismatches)    # {'amount': 5, 'status': 2}
print(recon.summary())
```

### Distribution Drift Detection

```python
baseline = connect("orders_jan.parquet")
current  = connect("orders_feb.parquet")

drift = current.amount.detect_drift(baseline.amount)

print(drift.is_drifted)    # True/False
print(drift.p_value)       # 0.0023
print(drift.statistic)     # KS statistic
print(drift.message)       # Human-readable summary
```

### Group-By Validation

```python
grouped = orders.group_by("region")

print(grouped.groups)        # [{'region': 'North'}, ...]
print(grouped.group_count)   # 4

for stat in grouped.stats():
    print(stat)              # {'region': 'North', 'row_count': 150}

# Ensure every group has at least 10 rows
result = grouped.row_count_greater_than(10)
for g in result.get_failed_groups():
    print(f"{g.key_string}: only {g.row_count} rows")
```

---

## What's New in 3.0

DuckGuard 3.0 introduces **conditional checks**, **multi-column validation**, **query-based expectations**, **distributional tests**, and **7 anomaly detection methods**.

### Conditional Checks

Apply validation rules only when a SQL condition is met:

```python
# Email required only for shipped orders
orders.email.not_null_when("status = 'shipped'")

# Quantity must be 1-100 for US orders
orders.quantity.between_when(1, 100, "country = 'US'")

# Status must be shipped or delivered for UK
orders.status.isin_when(["shipped", "delivered"], "country = 'UK'")

# Also: unique_when(), matches_when()
```

### Multi-Column Checks

Validate relationships across columns:

```python
# Ship date must come after created date
orders.expect_column_pair_satisfy(
    column_a="ship_date",
    column_b="created_at",
    expression="ship_date >= created_at",
)

# Composite key uniqueness
orders.expect_columns_unique(columns=["order_id", "customer_id"])

# Multi-column sum check
orders.expect_multicolumn_sum_to_equal(
    columns=["subtotal", "tax", "shipping"],
    expected_sum=59.50,
)
```

### Query-Based Checks

Run custom SQL for unlimited flexibility:

```python
# No rows should have negative quantities
orders.expect_query_to_return_no_rows(
    "SELECT * FROM table WHERE quantity < 0"
)

# Verify data exists
orders.expect_query_to_return_rows(
    "SELECT * FROM table WHERE status = 'shipped'"
)

# Exact value check on aggregate
orders.expect_query_result_to_equal(
    "SELECT COUNT(*) FROM table", expected=1000
)

# Range check on aggregate
orders.expect_query_result_to_be_between(
    "SELECT AVG(amount) FROM table", min_value=50, max_value=500
)
```

### Distributional Checks

Statistical tests for distribution shape (requires `scipy`):

```python
# Test for normal distribution
orders.amount.expect_distribution_normal(significance_level=0.05)

# Kolmogorov-Smirnov test
orders.quantity.expect_ks_test(distribution="norm")

# Chi-square goodness of fit
orders.status.expect_chi_square_test()
```

### Anomaly Detection (7 Methods)

```python
from duckguard import detect_anomalies, AnomalyDetector
from duckguard.anomaly import BaselineMethod, KSTestMethod, SeasonalMethod

# High-level API: detect anomalies across columns
report = detect_anomalies(orders, method="zscore", columns=["quantity", "amount"])
print(report.has_anomalies, report.anomaly_count)
for a in report.anomalies:
    print(f"{a.column}: score={a.score:.2f}, anomaly={a.is_anomaly}")

# AnomalyDetector with IQR
detector = AnomalyDetector(method="iqr", threshold=1.5)
report = detector.detect(orders, columns=["quantity"])

# ML Baseline: fit on historical data, score new values
baseline = BaselineMethod(sensitivity=2.0)
baseline.fit([100, 102, 98, 105, 97, 103])
print(baseline.baseline_mean, baseline.baseline_std)

score = baseline.score(250)  # Single value
print(score.is_anomaly, score.score)

scores = baseline.score(orders.amount)  # Entire column
print(max(scores))

# KS-Test: detect distribution drift
ks = KSTestMethod(p_value_threshold=0.05)
ks.fit([1, 2, 3, 4, 5])
comparison = ks.compare_distributions([10, 11, 12, 13, 14])
print(comparison.is_drift, comparison.p_value, comparison.message)

# Seasonal: time-aware anomaly detection
seasonal = SeasonalMethod(period="daily", sensitivity=2.0)
seasonal.fit([10, 12, 11, 13, 9, 14])
```

**Available methods:** `zscore`, `iqr`, `modified_zscore`, `percent_change`, `baseline`, `ks_test`, `seasonal`

---

## YAML Rules & Data Contracts

### Declarative Rules

```yaml
# duckguard.yaml
name: orders_validation
description: Quality checks for the orders dataset

columns:
  order_id:
    checks:
      - type: not_null
      - type: unique
  quantity:
    checks:
      - type: between
        value: [1, 1000]
  status:
    checks:
      - type: allowed_values
        value: [pending, shipped, delivered, cancelled, returned]
```

```python
from duckguard import load_rules, execute_rules

rules = load_rules("duckguard.yaml")
result = execute_rules(rules, "orders.csv")

print(f"Passed: {result.passed_count}/{result.total_checks}")
for r in result.results:
    tag = "PASS" if r.passed else "FAIL"
    print(f"  [{tag}] {r.message}")
```

### Auto-Discover Rules

```python
from duckguard import connect, generate_rules

orders = connect("orders.csv")
yaml_rules = generate_rules(orders, dataset_name="orders")
print(yaml_rules)  # Ready-to-use YAML
```

### Data Contracts

```python
from duckguard import generate_contract, validate_contract, diff_contracts
from duckguard.contracts import contract_to_yaml

# Generate a contract from existing data
contract = generate_contract(orders, name="orders_v1", owner="data-team")
print(contract.name, contract.version, len(contract.schema))

# Validate data against a contract
validation = validate_contract(contract, "orders.csv")
print(validation.passed)

# Export to YAML
print(contract_to_yaml(contract))

# Detect breaking changes between versions
diff = diff_contracts(contract_v1, contract_v2)
if diff.has_breaking_changes:
    for change in diff.changes:
        print(change)
```

---

## Auto-Profiling & Semantic Analysis

```python
from duckguard import AutoProfiler, SemanticAnalyzer, detect_type, detect_types_for_dataset

# Profile entire dataset — quality scores, pattern detection, and rule suggestions included
profiler = AutoProfiler()
profile = profiler.profile(orders)
print(f"Columns: {profile.column_count}, Rows: {profile.row_count}")
print(f"Quality: {profile.overall_quality_grade} ({profile.overall_quality_score:.1f}/100)")

# Per-column quality grades and percentiles
for col in profile.columns:
    print(f"  {col.name}: grade={col.quality_grade}, nulls={col.null_percent:.1f}%")
    if col.median_value is not None:
        print(f"    p25={col.p25_value}, median={col.median_value}, p75={col.p75_value}")

# Suggested rules (25+ pattern types: email, SSN, UUID, credit card, etc.)
print(f"Suggested rules: {len(profile.suggested_rules)}")
for rule in profile.suggested_rules[:5]:
    print(f"  {rule}")

# Deep profiling — distribution analysis + outlier detection (numeric columns)
deep_profiler = AutoProfiler(deep=True)
deep_profile = deep_profiler.profile(orders)
for col in deep_profile.columns:
    if col.distribution_type:
        print(f"  {col.name}: {col.distribution_type}, skew={col.skewness:.2f}")
    if col.outlier_count is not None:
        print(f"    outliers: {col.outlier_count} ({col.outlier_percentage:.1f}%)")

# Configurable thresholds
strict = AutoProfiler(null_threshold=0.0, unique_threshold=100.0, pattern_min_confidence=95.0)
strict_profile = strict.profile(orders)
```

```python
# Detect semantic type for a single column
print(detect_type(orders, "email"))     # SemanticType.EMAIL
print(detect_type(orders, "country"))   # SemanticType.COUNTRY_CODE

# Detect types for all columns at once
type_map = detect_types_for_dataset(orders)
for col, stype in type_map.items():
    print(f"  {col}: {stype}")

# Full PII analysis
analysis = SemanticAnalyzer().analyze(orders)
print(f"PII columns: {analysis.pii_columns}")  # ['email', 'phone']
for col in analysis.columns:
    if col.is_pii:
        print(f"  {col.name}: {col.semantic_type.value} (confidence: {col.confidence:.0%})")
```

**Supported semantic types:** `email`, `phone`, `url`, `ip_address`, `ssn`, `credit_card`, `person_name`, `address`, `country`, `state`, `city`, `zipcode`, `latitude`, `longitude`, `date`, `datetime`, `currency`, `percentage`, `boolean`, `uuid`, `identifier`, and more.

---

## Freshness, Schema & History

### Freshness Monitoring

```python
from datetime import timedelta
from duckguard.freshness import FreshnessMonitor

# Quick check
print(orders.freshness.last_modified)   # 2024-01-30 14:22:01
print(orders.freshness.age_human)       # "2 hours ago"
print(orders.freshness.is_fresh)        # True

# Custom threshold
print(orders.is_fresh(timedelta(hours=6)))

# Structured monitoring
monitor = FreshnessMonitor(threshold=timedelta(hours=1))
result = monitor.check(orders)
print(result.is_fresh, result.age_human)
```

### Schema Evolution

```python
from duckguard.schema_history import SchemaTracker, SchemaChangeAnalyzer

# Capture a snapshot
tracker = SchemaTracker()
snapshot = tracker.capture(orders)
for col in snapshot.columns[:5]:
    print(f"  {col.name}: {col.dtype}")

# View history
history = tracker.get_history(orders.source)
print(f"Snapshots: {len(history)}")

# Detect breaking changes
analyzer = SchemaChangeAnalyzer()
report = analyzer.detect_changes(orders)
print(report.has_breaking_changes, len(report.changes))
```

### Historical Tracking & Trends

```python
from duckguard.history import HistoryStorage, TrendAnalyzer

# Store validation results
storage = HistoryStorage()
storage.store(exec_result)

# Query past runs
runs = storage.get_runs("orders.csv", limit=10)
for run in runs:
    print(f"  {run.run_id}: passed={run.passed}, checks={run.total_checks}")

# Analyze quality trends
trends = TrendAnalyzer(storage).analyze("orders.csv", days=30)
print(trends.summary())
```

---

## Reports & Notifications

```python
from duckguard.reports import generate_html_report, generate_pdf_report
from duckguard.notifications import (
    SlackNotifier, TeamsNotifier, EmailNotifier,
    format_results_text, format_results_markdown,
)

# HTML/PDF reports
generate_html_report(exec_result, "report.html")
generate_pdf_report(exec_result, "report.pdf")    # requires weasyprint

# Notifications
slack = SlackNotifier(webhook_url="https://hooks.slack.com/services/XXX")
teams = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/XXX")
email = EmailNotifier(
    smtp_host="smtp.example.com", smtp_port=587,
    smtp_user="user", smtp_password="pass",
    to_addresses=["team@example.com"],
)

# Format for custom integrations
print(format_results_text(exec_result))
print(format_results_markdown(exec_result))
```

---

## Integrations

### dbt

```python
from duckguard.integrations.dbt import rules_to_dbt_tests

dbt_tests = rules_to_dbt_tests(rules)
```

### Airflow

```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def validate_orders():
    from duckguard import connect, load_rules, execute_rules
    rules = load_rules("duckguard.yaml")
    result = execute_rules(rules, "s3://bucket/orders.parquet")
    if not result.passed:
        raise Exception(f"Quality check failed: {result.failed_count} failures")

dag = DAG("data_quality", schedule_interval="@daily", ...)
PythonOperator(task_id="validate", python_callable=validate_orders, dag=dag)
```

### GitHub Actions

```yaml
name: Data Quality
on: [push]
jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install duckguard
      - run: duckguard check data/orders.csv --rules duckguard.yaml
```

### pytest

```python
# tests/test_data_quality.py
from duckguard import connect

def test_orders_quality():
    orders = connect("data/orders.csv")
    assert orders.row_count > 0
    assert orders.order_id.is_not_null()
    assert orders.order_id.is_unique()
    assert orders.quantity.between(0, 10000)
    assert orders.status.isin(["pending", "shipped", "delivered", "cancelled"])
```

---

## CLI

```bash
# Validate data against rules
duckguard check orders.csv --config duckguard.yaml

# Auto-discover rules from data
duckguard discover orders.csv > duckguard.yaml

# Generate reports
duckguard report orders.csv --output report.html

# Anomaly detection
duckguard anomaly orders.csv --method zscore

# Freshness check
duckguard freshness orders.csv --max-age 6h

# Schema tracking
duckguard schema orders.csv --action capture
duckguard schema orders.csv --action changes

# Data contracts
duckguard contract generate orders.csv
duckguard contract validate orders.csv

# Dataset info
duckguard info orders.csv

# Profile dataset with quality scoring
duckguard profile orders.csv
duckguard profile orders.csv --deep --format json
```

---

## Performance

Built on DuckDB for fast, memory-efficient validation:

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

### Scaling Guide

| Data Size | Recommendation |
|-----------|----------------|
| < 10M rows | DuckGuard directly |
| 10-100M rows | Use Parquet, configure `memory_limit` |
| 100GB+ | Use database connectors (Snowflake, BigQuery, Databricks) |

```python
from duckguard import DuckGuardEngine, connect

engine = DuckGuardEngine(memory_limit="8GB")
dataset = connect("large_data.parquet", engine=engine)
```

---

## API Quick Reference

### Column Properties

```python
col.null_count        # Number of null values
col.null_percent      # Percentage of null values
col.unique_count      # Number of distinct values
col.min, col.max      # Min/max values (numeric)
col.mean, col.median  # Mean and median (numeric)
col.stddev            # Standard deviation (numeric)
```

### Column Validation Methods

| Method | Description |
|--------|-------------|
| `col.is_not_null()` | No nulls allowed |
| `col.is_unique()` | All values distinct |
| `col.between(min, max)` | Range check (inclusive) |
| `col.greater_than(val)` | Minimum (exclusive) |
| `col.less_than(val)` | Maximum (exclusive) |
| `col.matches(regex)` | Regex pattern check |
| `col.isin(values)` | Allowed values |
| `col.has_no_duplicates()` | No duplicate values |
| `col.value_lengths_between(min, max)` | String length range |
| `col.exists_in(ref_col)` | FK: values exist in reference |
| `col.references(ref_col, allow_nulls)` | FK with null handling |
| `col.find_orphans(ref_col)` | List orphan values |
| `col.matches_values(other_col)` | Compare value sets |
| `col.detect_drift(ref_col)` | KS-test drift detection |
| `col.not_null_when(condition)` | Conditional not-null |
| `col.unique_when(condition)` | Conditional uniqueness |
| `col.between_when(min, max, condition)` | Conditional range |
| `col.isin_when(values, condition)` | Conditional enum |
| `col.matches_when(pattern, condition)` | Conditional pattern |
| `col.expect_distribution_normal()` | Normality test |
| `col.expect_ks_test(distribution)` | KS distribution test |
| `col.expect_chi_square_test()` | Chi-square test |

### Dataset Methods

| Method | Description |
|--------|-------------|
| `ds.score()` | Quality score (completeness, uniqueness, validity, consistency) |
| `ds.reconcile(target, key_columns, compare_columns)` | Full reconciliation |
| `ds.row_count_matches(other, tolerance)` | Row count comparison |
| `ds.group_by(columns)` | Group-level validation |
| `ds.expect_column_pair_satisfy(a, b, expr)` | Column pair check |
| `ds.expect_columns_unique(columns)` | Composite key uniqueness |
| `ds.expect_multicolumn_sum_to_equal(columns, sum)` | Multi-column sum |
| `ds.expect_query_to_return_no_rows(sql)` | Custom SQL: no violations |
| `ds.expect_query_to_return_rows(sql)` | Custom SQL: data exists |
| `ds.expect_query_result_to_equal(sql, val)` | Custom SQL: exact value |
| `ds.expect_query_result_to_be_between(sql, min, max)` | Custom SQL: range |
| `ds.is_fresh(max_age)` | Data freshness check |
| `ds.head(n)` | Preview first n rows |

---

## Enhanced Error Messages

DuckGuard provides helpful, actionable error messages with suggestions:

```python
try:
    orders.nonexistent_column
except ColumnNotFoundError as e:
    print(e)
    # Column 'nonexistent_column' not found.
    # Available columns: order_id, customer_id, product_name, ...

try:
    connect("ftp://data.example.com/file.xyz")
except UnsupportedConnectorError as e:
    print(e)
    # No connector found for: ftp://data.example.com/file.xyz
    # Supported formats: CSV, Parquet, JSON, PostgreSQL, MySQL, ...
```

---

## Community

We'd love to hear from you! Whether you have a question, idea, or want to share how you're using DuckGuard:

- **[GitHub Discussions](https://github.com/XDataHubAI/duckguard/discussions)** — Ask questions, share ideas, show what you've built
- **[GitHub Issues](https://github.com/XDataHubAI/duckguard/issues)** — Report bugs or request features
- **[Contributing Guide](CONTRIBUTING.md)** — Learn how to contribute code, tests, or docs

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/XDataHubAI/duckguard.git
cd duckguard
pip install -e ".[dev]"

pytest                    # Run tests
black src tests           # Format code
ruff check src tests      # Lint
```

---

## License

Elastic License 2.0 - see [LICENSE](LICENSE)

---

<div align="center">
  <p>
    <strong>Built with &#10084;&#65039; by the DuckGuard Team</strong>
  </p>
  <p>
    <a href="https://github.com/XDataHubAI/duckguard/discussions">Discussions</a>
    &middot;
    <a href="https://github.com/XDataHubAI/duckguard/issues">Report Bug</a>
    &middot;
    <a href="https://github.com/XDataHubAI/duckguard/issues">Request Feature</a>
    &middot;
    <a href="CONTRIBUTING.md">Contribute</a>
  </p>
</div>
