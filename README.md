# DuckGuard

Data quality that just works. Python-native, DuckDB-powered, 10x faster.

[![PyPI version](https://img.shields.io/pypi/v/duckguard.svg)](https://pypi.org/project/duckguard/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic--2.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)

```bash
pip install duckguard
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

## License

Elastic License 2.0 - see [LICENSE](LICENSE)
