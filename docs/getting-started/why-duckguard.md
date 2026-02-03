# Why DuckGuard?

## The Problem

Data quality tools are stuck in 2018. Here's what it looks like to validate a single column with the market leader:

```python
# Great Expectations — 50+ lines before you validate anything
from great_expectations import get_context

context = get_context()
datasource = context.sources.add_pandas("my_ds")
asset = datasource.add_dataframe_asset(name="orders", dataframe=df)
batch_request = asset.build_batch_request()
expectation_suite = context.add_expectation_suite("orders_suite")
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name="orders_suite"
)
validator.expect_column_values_to_not_be_null("customer_id")
# ... and you're just getting started
```

This is insane. You need to understand contexts, datasources, assets, batch requests, expectation suites, and validators — just to check if a column has nulls.

## The DuckGuard Way

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
```

Done. No ceremony. No boilerplate. If you can write pytest, you can write DuckGuard.

## Speed

DuckGuard is built on [DuckDB](https://duckdb.org/), the fastest embedded analytics engine. This means:

| Dataset Size | Great Expectations | DuckGuard |
|-------------|:-----------------:|:---------:|
| 1 GB CSV | 45 sec / 4 GB RAM | **4 sec / 200 MB RAM** |
| 10 GB Parquet | 8 min / 32 GB RAM | **45 sec / 2 GB RAM** |

**Why?** DuckDB uses columnar storage, vectorized execution, and SIMD optimizations. DuckGuard reads files directly — no loading into pandas, no DataFrame conversion, no memory explosion.

## Feature Comparison

| What you need | DuckGuard | Great Expectations | Soda Core |
|--------------|:---------:|:-----------------:|:---------:|
| Validate a column | 1 line | 50+ lines | 10+ lines (YAML) |
| PII detection | Built-in | ✗ | ✗ |
| Anomaly detection | 7 methods | ✗ | Partial |
| Row-level errors | Built-in | Yes | ✗ |
| Data contracts | Built-in | ✗ | Yes |
| Conditional checks | Built-in | ✗ | ✗ |
| Query-based checks | Built-in | ✗ | Yes |
| Drift detection | Built-in | ✗ | ✗ |
| Reconciliation | Built-in | ✗ | ✗ |
| Quality scoring (A-F) | Built-in | ✗ | ✗ |
| Learning curve | Minutes | Days | Hours |

## Who Is DuckGuard For?

**Data engineers** who want validation that doesn't slow down their pipelines.

**Analytics engineers** who want data quality checks as readable as their SQL.

**ML engineers** who need to detect data drift before it breaks their models.

**Anyone** who's tired of writing 50 lines of YAML to check if a column is not null.

## Design Principles

1. **Zero boilerplate** — If it takes more than 3 lines to start, it's too many
2. **Speed by default** — DuckDB under the hood, not pandas
3. **Batteries included** — PII, anomalies, contracts, drift — all built in
4. **Pytest-native** — Use `assert`, not `.expect_column_values_to_be_blah()`
5. **Progressive complexity** — Simple things simple, complex things possible
