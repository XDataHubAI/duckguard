# dbt Integration

Use DuckGuard alongside dbt to validate models after transformation.

## Quick Start

Add a post-hook or write a Python script that validates dbt output:

```python
# tests/test_dbt_models.py
from duckguard import connect

def test_stg_orders():
    """Validate the stg_orders dbt model."""
    data = connect("target/stg_orders.parquet")

    assert data.row_count > 0
    assert data.order_id.null_percent == 0
    assert data.order_id.has_no_duplicates()
    assert data.amount.between(0, 100000)
```

## Validate dbt Models

### After `dbt run`

Point DuckGuard at the output of your dbt models:

```python
from duckguard import connect

# If dbt outputs to a database
data = connect("postgres://localhost/analytics", table="stg_orders")

# If dbt outputs to files (dbt-duckdb)
data = connect("target/stg_orders.parquet")
```

### With dbt-duckdb

If you use `dbt-duckdb`, models are stored as DuckDB tables or Parquet files:

```python
data = connect("target/dev.duckdb", table="stg_orders")
```

## Data Contracts for dbt Models

Define contracts for each model:

```yaml
# contracts/stg_orders.contract.yaml
contract:
  name: stg_orders
  version: "1.0.0"

  schema:
    - name: order_id
      type: string
      required: true
      unique: true
    - name: amount
      type: decimal
      required: true
      constraints:
        - type: range
          value: [0, 100000]
    - name: status
      type: string
      required: true
      constraints:
        - type: allowed_values
          value: [pending, shipped, delivered, cancelled]

  quality:
    completeness: 99.0
    row_count_min: 100
```

```python
from duckguard import load_contract, validate_contract

contract = load_contract("contracts/stg_orders.contract.yaml")
result = validate_contract(contract, "postgres://localhost/analytics",
                           table="stg_orders")
assert result.passed, result.summary()
```

## dbt Test Replacement

DuckGuard can replace or supplement dbt tests:

| dbt Test | DuckGuard Equivalent |
|----------|---------------------|
| `unique` | `col.has_no_duplicates()` |
| `not_null` | `col.null_percent == 0` |
| `accepted_values` | `col.isin([...])` |
| `relationships` | `data.reconcile(other, key_columns=[...])` |

DuckGuard adds capabilities dbt tests don't have: anomaly detection, distribution tests, quality scoring, PII detection, and profiling.

## Pipeline Pattern

```python
import subprocess
from duckguard import connect, load_rules, execute_rules

# 1. Run dbt
subprocess.run(["dbt", "run"], check=True)

# 2. Validate output
rules = load_rules("duckguard.yaml")
result = execute_rules(rules, source="target/dev.duckdb")

if not result.passed:
    print(f"Quality gate failed: {result.failed_count} checks")
    exit(1)

print(f"Quality score: {result.quality_score:.0f}%")
```

## Quality Reports

Generate HTML reports for dbt model quality:

```bash
duckguard report target/stg_orders.parquet \
  --config duckguard.yaml \
  --title "stg_orders Quality Report" \
  --output reports/stg_orders.html
```
