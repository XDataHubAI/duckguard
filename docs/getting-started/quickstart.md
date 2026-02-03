# Quickstart

Get from zero to validated in 30 seconds.

## Connect to Your Data

```python
from duckguard import connect

# Files
orders = connect("orders.csv")           # CSV
orders = connect("orders.parquet")       # Parquet
orders = connect("orders.json")          # JSON

# Cloud
orders = connect("s3://bucket/orders.parquet")

# Databases
orders = connect("postgres://localhost/db", table="orders")

# pandas DataFrame
import pandas as pd
orders = connect(pd.read_csv("orders.csv"))
```

DuckGuard connects to anything — files, cloud storage, databases, DataFrames. [See all connectors →](../connectors/overview.md)

## Validate Columns

Validations work like pytest assertions — readable, composable, and they tell you exactly what failed.

```python
# Null & uniqueness
assert orders.order_id.is_not_null()
assert orders.order_id.is_unique()

# Range checks
assert orders.amount.between(0, 10000)
assert orders.quantity.greater_than(0)

# Patterns & enums
assert orders.email.matches(r'^[\w.+-]+@[\w-]+\.[\w.]+$')
assert orders.status.isin(["pending", "shipped", "delivered"])
```

## Debug Failures

When a check fails, you get row-level details:

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
```

## Score Your Data

Get an instant quality grade:

```python
score = orders.score()

print(score.grade)          # A, B, C, D, or F
print(score.completeness)   # % non-null
print(score.uniqueness)     # % unique keys
print(score.validity)       # % passing checks
print(score.consistency)    # % consistent format
```

## Use YAML Rules

Define checks declaratively:

```yaml
# duckguard.yaml
name: orders_validation

checks:
  order_id:
    - not_null
    - unique
  quantity:
    - between: [1, 1000]
  status:
    - allowed_values: [pending, shipped, delivered]
```

```python
from duckguard import load_rules, execute_rules

rules = load_rules("duckguard.yaml")
result = execute_rules(rules, "orders.csv")
print(f"Passed: {result.passed_count}/{result.total_checks}")
```

Or auto-discover rules from your data:

```bash
duckguard discover orders.csv > duckguard.yaml
```

## Run from CLI

```bash
# Validate
duckguard check orders.csv --config duckguard.yaml

# Profile
duckguard profile orders.csv

# Generate report
duckguard report orders.csv --output report.html
```

## What's Next?

- [Column Validation](../guide/column-validation.md) — All validation methods
- [Cross-Dataset Checks](../guide/cross-dataset.md) — FK validation, reconciliation
- [Anomaly Detection](../guide/anomaly-detection.md) — 7 detection methods
- [Data Contracts](../guide/data-contracts.md) — Schema enforcement
- [Integrations](../integrations/pytest.md) — pytest, dbt, Airflow, CI/CD
