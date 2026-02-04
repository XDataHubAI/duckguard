---
title: DuckGuard for Snowflake
description: Validate your Snowflake data in 3 lines of Python. Query pushdown, dbt integration, and zero boilerplate.
---

# DuckGuard for Snowflake

## Validate your Snowflake data in 3 lines of Python

```python
from duckguard import connect

dg = connect("snowflake://account/db", table="orders")
dg.validate()
```

That's it. No YAML. No context objects. No 200-line config files.

---

## The Problem

You're running dbt models in Snowflake. Data lands in tables. You need to know if it's correct.

With Great Expectations, that looks like this:

```python
# Great Expectations — ~50 lines to validate one table
import great_expectations as gx

context = gx.get_context()

datasource = context.sources.add_snowflake(
    name="my_snowflake",
    connection_string="snowflake://user:pass@account/database/schema?warehouse=WH&role=ROLE",
)
asset = datasource.add_table_asset(name="orders", table_name="orders")
batch_request = asset.build_batch_request()

context.add_or_update_expectation_suite("orders_suite")
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name="orders_suite",
)

validator.expect_column_to_exist("order_id")
validator.expect_column_values_to_not_be_null("order_id")
validator.expect_column_values_to_be_between("amount", min_value=0)
validator.expect_column_values_to_be_in_set("status", ["pending", "shipped", "delivered"])

validator.save_expectation_suite(discard_failed_expectations=False)

checkpoint = context.add_or_update_checkpoint(
    name="orders_checkpoint",
    validations=[{
        "batch_request": batch_request,
        "expectation_suite_name": "orders_suite",
    }],
)
result = checkpoint.run()
```

With DuckGuard:

```python
from duckguard import connect

dg = connect("snowflake://user:pass@account/database/schema", table="orders")
result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "amount": {"min": 0},
    "status": {"in": ["pending", "shipped", "delivered"]},
})
```

Same checks. Fraction of the code.

---

## Quick Start

### Install

```bash
pip install duckguard[snowflake]
```

### Connect

=== "Connection String"

    ```python
    from duckguard import connect

    dg = connect("snowflake://user:pass@account/database/schema", table="orders")
    ```

=== "Explicit Parameters"

    ```python
    from duckguard import connect

    dg = connect(
        "snowflake://myaccount.us-east-1",
        database="analytics",
        schema="public",
        warehouse="COMPUTE_WH",
        role="DATA_ENGINEER",
        table="orders",
    )
    ```

=== "Environment Variables"

    ```python
    import os
    from duckguard import connect

    # DuckGuard reads SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT
    dg = connect("snowflake://", table="orders")
    ```

### Connection String Format

```
snowflake://user:pass@account/database/schema?warehouse=WH&role=ROLE
```

| Component    | Example                | Required |
|-------------|------------------------|----------|
| `user`      | `data_engineer`        | Yes      |
| `pass`      | `s3cret`               | Yes      |
| `account`   | `xy12345.us-east-1`    | Yes      |
| `database`  | `analytics`            | Yes      |
| `schema`    | `public`               | No       |
| `warehouse` | `COMPUTE_WH` (query param) | No  |
| `role`      | `DATA_ENGINEER` (query param) | No |

---

## Query Pushdown

DuckGuard doesn't pull your data out of Snowflake. It pushes computation **into** Snowflake.

When you run:

```python
dg.expect({"amount": {"min": 0, "max": 10000}})
```

DuckGuard generates and executes:

```sql
SELECT
    MIN(amount) AS amount_min,
    MAX(amount) AS amount_max,
    COUNT(*) FILTER (WHERE amount IS NULL) AS amount_null_count,
    COUNT(*) AS total_rows
FROM orders
```

One query. One round trip. No data leaves Snowflake.

!!! info "What gets pushed down"
    - Null checks → `COUNT(*) FILTER (WHERE col IS NULL)`
    - Min/max/range → `MIN()`, `MAX()`
    - Uniqueness → `COUNT(DISTINCT col) = COUNT(col)`
    - Value sets → `COUNT(*) FILTER (WHERE col NOT IN (...))`
    - Pattern matching → `COUNT(*) FILTER (WHERE col NOT RLIKE ...)`
    - Row counts → `COUNT(*)`

    DuckGuard batches all checks for a table into a **single query** when possible.

!!! tip "Warehouse sizing"
    Validation queries are lightweight aggregations. An `XS` warehouse handles most workloads. Don't spin up `XLARGE` for DuckGuard — you're wasting credits.

---

## Key Workflows

### After dbt Runs

Add DuckGuard as a post-hook or a downstream test:

```python
# tests/test_dbt_output.py
from duckguard import connect

def test_orders_output():
    dg = connect("snowflake://account/analytics", table="fct_orders")
    result = dg.expect({
        "order_id": {"not_null": True, "unique": True},
        "customer_id": {"not_null": True},
        "amount": {"min": 0},
        "order_date": {"not_null": True, "max": "today"},
    })
    assert result.passed
```

Run with pytest after `dbt run`:

```bash
dbt run --select fct_orders
pytest tests/test_dbt_output.py -v
```

### CI Pipeline

```yaml
# .github/workflows/data-quality.yml
name: Data Quality
on:
  workflow_run:
    workflows: ["dbt Run"]
    types: [completed]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install duckguard[snowflake]
      - run: pytest tests/data_quality/ -v
        env:
          SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
          SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
          SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
```

### Airflow DAG Task

```python
from airflow.decorators import task

@task
def validate_orders():
    from duckguard import connect

    dg = connect("snowflake://account/analytics", table="fct_orders")
    result = dg.expect({
        "order_id": {"not_null": True, "unique": True},
        "amount": {"min": 0},
    })
    if not result.passed:
        raise ValueError(f"Data quality failed: {result.summary()}")
```

```python
# In your DAG
run_dbt >> validate_orders() >> notify_downstream
```

---

## Snowflake Feature Integration

### Stages

Validate files in a Snowflake stage before loading:

```python
dg = connect("snowflake://account/db", stage="@my_stage/data/", file_format="csv")
result = dg.profile()
print(result.summary())
```

### Streams

Validate only **new/changed** rows using Snowflake streams:

```python
dg = connect("snowflake://account/db", stream="orders_stream")
result = dg.expect({
    "order_id": {"not_null": True},
    "amount": {"min": 0},
})
# Only validates rows captured by the stream — not the full table
```

### Tasks

Schedule DuckGuard validation as a Snowflake task using the Python connector:

```python
# Create a stored procedure that runs DuckGuard
CREATE OR REPLACE PROCEDURE validate_orders()
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
PACKAGES = ('duckguard', 'snowflake-connector-python')
HANDLER = 'run'
AS
$$
def run(session):
    from duckguard import connect
    dg = connect(session=session, table="orders")  # Use existing session
    result = dg.expect({"order_id": {"not_null": True}})
    return result.summary()
$$;

-- Run every hour
CREATE TASK validate_orders_task
  WAREHOUSE = XS_WH
  SCHEDULE = 'USING CRON 0 * * * * UTC'
AS
  CALL validate_orders();
```

---

## Real-World Example: Pipeline Output Validation

You have a daily pipeline that loads order data from an API into Snowflake via dbt. Here's the full validation pattern:

```python
# validate_pipeline.py
from duckguard import connect
from datetime import date, timedelta

def validate_daily_orders():
    dg = connect(
        "snowflake://account/analytics/public",
        warehouse="COMPUTE_WH",
        table="fct_orders",
    )

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Profile first — understand what you're working with
    profile = dg.profile(where=f"order_date = '{yesterday}'")
    print(profile.summary())

    # Validate structure
    result = dg.expect({
        "order_id": {"not_null": True, "unique": True},
        "customer_id": {"not_null": True},
        "order_date": {"not_null": True, "equals": str(yesterday)},
        "amount": {"not_null": True, "min": 0, "max": 100000},
        "currency": {"in": ["USD", "EUR", "GBP", "CAD"]},
        "status": {"in": ["pending", "processing", "shipped", "delivered", "cancelled"]},
        "email": {"not_null": True, "pattern": r"^[^@]+@[^@]+\.[^@]+$"},
    }, where=f"order_date = '{yesterday}'")

    # Check row count is reasonable (not empty, not duplicated)
    row_check = dg.expect_table({
        "row_count": {"min": 100, "max": 1000000},
    }, where=f"order_date = '{yesterday}'")

    if not result.passed or not row_check.passed:
        # Send alert, block downstream
        raise ValueError(
            f"Pipeline validation failed for {yesterday}:\n"
            f"{result.failures()}\n{row_check.failures()}"
        )

    print(f"✓ {yesterday}: {result.stats['rows_checked']} rows, all checks passed")

if __name__ == "__main__":
    validate_daily_orders()
```

---

## Migration from Great Expectations

### Concepts Mapping

| Great Expectations | DuckGuard | Notes |
|-------------------|-----------|-------|
| Data Context | `connect()` | No YAML config needed |
| Datasource | Connection string | One line |
| Data Asset | `table` parameter | Just a name |
| Expectation Suite | `expect()` dict | Inline or file |
| Validator | Return value of `expect()` | Automatic |
| Checkpoint | `pytest` | Standard testing |
| Data Docs | `dg.report()` | Built-in HTML report |

### Side-by-Side

=== "Great Expectations"

    ```python
    import great_expectations as gx

    context = gx.get_context()
    ds = context.sources.add_snowflake("sf", connection_string="...")
    asset = ds.add_table_asset("orders", table_name="orders")
    batch = asset.build_batch_request()

    context.add_or_update_expectation_suite("orders_suite")
    v = context.get_validator(batch_request=batch, expectation_suite_name="orders_suite")

    v.expect_column_values_to_not_be_null("order_id")
    v.expect_column_values_to_be_unique("order_id")
    v.expect_column_values_to_be_between("amount", min_value=0)
    v.save_expectation_suite()

    cp = context.add_or_update_checkpoint("cp", validations=[{
        "batch_request": batch,
        "expectation_suite_name": "orders_suite",
    }])
    result = cp.run()
    ```

=== "DuckGuard"

    ```python
    from duckguard import connect

    dg = connect("snowflake://account/db", table="orders")
    result = dg.expect({
        "order_id": {"not_null": True, "unique": True},
        "amount": {"min": 0},
    })
    ```

### Migration Steps

1. **Install:** `pip install duckguard[snowflake]`
2. **Replace connection setup** with a single `connect()` call
3. **Convert expectations** to DuckGuard's dict format (see mapping above)
4. **Replace checkpoints** with `pytest` tests
5. **Replace Data Docs** with `dg.report()` or CI output
6. **Delete** `great_expectations/` directory, YAML files, and checkpoint configs

!!! success "Migration time"
    Most teams migrate a full GE suite in under an hour. The hardest part is deleting all that YAML.
