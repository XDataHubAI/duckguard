---
title: DuckGuard for Databricks
description: Data quality for Unity Catalog — pytest-like syntax, zero Spark overhead. Validate from any Python environment.
---

# DuckGuard for Databricks

## Data quality for Unity Catalog — pytest-like syntax, zero Spark overhead

```python
from duckguard import connect

dg = connect("databricks://workspace.databricks.com", table="catalog.schema.orders")
dg.validate()
```

No Spark cluster. No notebook dependency. No 10-minute startup.

---

## The Problem

You want to validate data in Databricks. Current options:

- **Great Expectations** — Needs a running Spark cluster to execute checks. Your `XS` cluster takes 5 minutes to start. Your validation checks take 8 seconds. You're paying for 5 minutes of idle compute.
- **dbt tests** — Only works inside dbt. Can't run from CI without a full dbt setup.
- **Custom PySpark** — You're writing SQL with extra steps.

DuckGuard connects to Databricks via SQL endpoints. No Spark. No cluster. Runs from your laptop, CI runner, or a $5 VM.

!!! tip "Cost savings"
    A Databricks SQL warehouse (serverless) costs ~$0.07/query for validation aggregations. A Spark cluster costs ~$0.50/hour minimum just to exist. DuckGuard uses SQL warehouses by default.

---

## Quick Start

### Install

```bash
pip install duckguard[databricks]
```

### Connect

=== "Connection String"

    ```python
    from duckguard import connect

    dg = connect(
        "databricks://my-workspace.cloud.databricks.com",
        table="catalog.schema.orders",
    )
    ```

=== "Explicit Parameters"

    ```python
    from duckguard import connect

    dg = connect(
        "databricks://",
        server_hostname="my-workspace.cloud.databricks.com",
        http_path="/sql/1.0/warehouses/abc123",
        access_token="dapi1234567890",
        catalog="main",
        schema="default",
        table="orders",
    )
    ```

=== "Environment Variables"

    ```python
    import os
    from duckguard import connect

    # Reads DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN
    dg = connect("databricks://", table="main.default.orders")
    ```

### Connection Requirements

| Parameter | Environment Variable | Example |
|-----------|---------------------|---------|
| `server_hostname` | `DATABRICKS_HOST` | `my-workspace.cloud.databricks.com` |
| `http_path` | `DATABRICKS_HTTP_PATH` | `/sql/1.0/warehouses/abc123` |
| `access_token` | `DATABRICKS_TOKEN` | `dapi...` |

!!! info "Where to find these"
    1. **server_hostname** — Your workspace URL (without `https://`)
    2. **http_path** — SQL Warehouse → Connection Details → HTTP Path
    3. **access_token** — Settings → Developer → Access Tokens → Generate

---

## Databricks Notebooks

Use DuckGuard directly in notebook cells:

### Cell 1: Install

```python
%pip install duckguard[databricks]
dbutils.library.restartPython()
```

### Cell 2: Connect and Validate

```python
from duckguard import connect

# In a Databricks notebook, DuckGuard auto-detects the environment
# and uses the notebook's authentication context
dg = connect("databricks://auto", table="main.default.orders")

result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "amount": {"min": 0},
    "status": {"in": ["pending", "shipped", "delivered"]},
})

result.show()  # Rich display in notebook output
```

### Cell 3: Profile

```python
profile = dg.profile()
profile.show()  # Interactive profiling widget
```

!!! tip "Notebook auto-detection"
    When running inside a Databricks notebook, `connect("databricks://auto")` uses the notebook's built-in authentication. No tokens or hostnames needed.

---

## Delta Lake Support

Connect directly to Delta tables on storage:

```python
from duckguard import connect

# Read Delta table from cloud storage — no Databricks cluster needed
dg = connect("delta://s3://my-bucket/delta/orders")
result = dg.validate()
```

=== "S3"

    ```python
    dg = connect("delta://s3://my-bucket/warehouse/orders")
    ```

=== "ADLS"

    ```python
    dg = connect("delta://abfss://container@account.dfs.core.windows.net/orders")
    ```

=== "GCS"

    ```python
    dg = connect("delta://gs://my-bucket/warehouse/orders")
    ```

=== "Local"

    ```python
    dg = connect("delta:///tmp/delta/orders")
    ```

!!! warning "Delta direct access"
    Reading Delta tables directly from storage bypasses Databricks access controls. Use the `databricks://` connector for Unity Catalog-governed access.

---

## Unity Catalog Integration

### Three-Level Namespace

DuckGuard uses Unity Catalog's `catalog.schema.table` convention:

```python
dg = connect("databricks://workspace.databricks.com", table="main.sales.orders")
#                                                             ^^^^ ^^^^^ ^^^^^^
#                                                          catalog schema table
```

### Validate Across Catalogs

```python
from duckguard import connect

conn = connect("databricks://workspace.databricks.com")

# Validate production
prod = conn.table("prod.sales.orders")
prod_result = prod.expect({"order_id": {"not_null": True, "unique": True}})

# Validate staging with same rules
staging = conn.table("staging.sales.orders")
staging_result = staging.expect({"order_id": {"not_null": True, "unique": True}})

# Compare
print(f"Prod: {prod_result.stats['rows_checked']} rows, passed={prod_result.passed}")
print(f"Staging: {staging_result.stats['rows_checked']} rows, passed={staging_result.passed}")
```

### Information Schema Checks

Validate table metadata via Unity Catalog:

```python
dg = connect("databricks://workspace.databricks.com", table="prod.sales.orders")

# Check table exists and has expected columns
meta = dg.inspect()
assert "order_id" in meta.columns
assert meta.columns["order_id"].type == "BIGINT"
assert meta.row_count > 0
```

---

## Workflows

### CI Pipeline — No Cluster Required

```yaml
# .github/workflows/data-quality.yml
name: Data Quality
on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install duckguard[databricks]
      - run: pytest tests/data_quality/ -v
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_HTTP_PATH: ${{ secrets.DATABRICKS_HTTP_PATH }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

The CI runner is a basic Ubuntu VM. No Spark. No JVM. No cluster startup. Tests run in seconds.

### After dbt Runs on Databricks

```python
# tests/test_databricks_output.py
from duckguard import connect

def test_fact_orders():
    dg = connect("databricks://", table="prod.analytics.fct_orders")
    result = dg.expect({
        "order_id": {"not_null": True, "unique": True},
        "customer_id": {"not_null": True},
        "order_total": {"min": 0},
        "order_date": {"not_null": True},
    })
    assert result.passed, result.failures()

def test_dim_customers():
    dg = connect("databricks://", table="prod.analytics.dim_customers")
    result = dg.expect({
        "customer_id": {"not_null": True, "unique": True},
        "email": {"not_null": True, "pattern": r".+@.+\..+"},
        "created_at": {"not_null": True},
    })
    assert result.passed, result.failures()
```

### Databricks Workflow Job

```python
# validate_job.py — run as a Databricks Workflow task (Python script)
from duckguard import connect

dg = connect("databricks://auto", table="prod.sales.orders")

result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "amount": {"min": 0, "max": 1000000},
})

if not result.passed:
    raise Exception(f"Validation failed:\n{result.failures()}")

print(f"✓ Validated {result.stats['rows_checked']} rows")
```

Add this as a task in your Databricks Workflow, chained after your ETL task. Uses the job cluster's auth context automatically.

---

## Migration from Great Expectations on Databricks

### Before: GE + Spark

```python
# Requires: running Spark cluster, GE config, YAML files
import great_expectations as gx
from great_expectations.datasource.fluent import SparkDatasource

context = gx.get_context()

datasource = context.sources.add_spark("my_spark")
asset = datasource.add_dataframe_asset("orders")

df = spark.table("prod.sales.orders")
batch = asset.build_batch_request(dataframe=df)

context.add_or_update_expectation_suite("orders_suite")
validator = context.get_validator(
    batch_request=batch,
    expectation_suite_name="orders_suite",
)
validator.expect_column_values_to_not_be_null("order_id")
validator.expect_column_values_to_be_unique("order_id")
validator.expect_column_values_to_be_between("amount", min_value=0)
validator.save_expectation_suite()

checkpoint = context.add_or_update_checkpoint(
    name="orders_cp",
    validations=[{
        "batch_request": batch,
        "expectation_suite_name": "orders_suite",
    }],
)
result = checkpoint.run()
```

**Requirements:** Spark cluster running, `great_expectations/` directory with YAML configs, checkpoint YAML.

### After: DuckGuard

```python
from duckguard import connect

dg = connect("databricks://workspace.databricks.com", table="prod.sales.orders")
result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "amount": {"min": 0},
})
assert result.passed
```

**Requirements:** `pip install duckguard[databricks]`. That's it.

### Migration Steps

1. `pip install duckguard[databricks]`
2. Replace GE datasource config → one `connect()` call
3. Convert `expect_column_*` calls → dict format
4. Replace checkpoints → `pytest`
5. Delete `great_expectations/` directory and all YAML
6. Stop paying for a Spark cluster to run validation

!!! success "What you save"
    - **No Spark cluster** for validation — use SQL warehouse or direct Delta access
    - **No YAML** — expectations live in Python code
    - **No GE context** — no config directory, no checkpoint files
    - **Faster CI** — no JVM startup, no cluster provisioning

---

## Architecture

```
┌──────────────────┐
│  Your Code       │
│  (laptop / CI)   │
│                  │
│  duckguard       │
└────────┬─────────┘
         │ SQL over HTTPS
         │ (Databricks SQL connector)
         ▼
┌──────────────────┐
│  Databricks      │
│  SQL Warehouse   │
│  (serverless)    │
│                  │
│  ┌────────────┐  │
│  │ Unity      │  │
│  │ Catalog    │  │
│  │            │  │
│  │ Delta Lake │  │
│  └────────────┘  │
└──────────────────┘
```

DuckGuard sends aggregation queries to a SQL warehouse. No data leaves Databricks. No Spark driver needed on your side. Authentication goes through Databricks tokens over HTTPS.
