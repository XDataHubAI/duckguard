---
hide:
  - navigation
---

# DuckGuard

## Data Quality That Just Works

**3 lines of code** · **Any data source** · **10x faster**

One API for CSV, Parquet, Snowflake, Databricks, BigQuery, and 15+ sources. No boilerplate.

```bash
pip install duckguard
```

```python
from duckguard import connect

orders = connect("s3://warehouse/orders.parquet")       # or Snowflake, Databricks, CSV...
assert orders.customer_id.is_not_null()                 # Just like pytest!
assert orders.total_amount.between(0, 10000)
assert orders.status.isin(["pending", "shipped", "delivered"])

quality = orders.score()
print(f"Grade: {quality.grade}")  # A, B, C, D, or F
```

Same 3 lines whether your data lives in S3, Snowflake, Databricks, or a local CSV.

---

## Why DuckGuard?

Every data quality tool asks you to write **50+ lines of boilerplate** before you validate a single column. DuckGuard gives you a **pytest-like API** powered by **DuckDB's speed**.

| Feature | DuckGuard | Great Expectations | Soda Core | Pandera |
|---------|:---------:|:------------------:|:---------:|:-------:|
| Lines of code to start | **3** | 50+ | 10+ | 5+ |
| Time for 1GB CSV | **~4 sec** | ~45 sec | ~20 sec | ~15 sec |
| Memory for 1GB CSV | **~200 MB** | ~4 GB | ~1.5 GB | ~1.5 GB |
| Learning curve | **Minutes** | Days | Hours | Minutes |
| Pytest-like API | **✓** | — | — | — |
| DuckDB-powered | **✓** | — | Partial | — |
| PII detection | **Built-in** | — | — | — |
| Anomaly detection | **7 methods** | — | Partial | — |
| Data contracts | **✓** | — | ✓ | ✓ |

---

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started/quickstart.md)**

    Install and validate your first dataset in 30 seconds

- :material-check-circle: **[Validation Guide](guide/column-validation.md)**

    Column checks, cross-dataset validation, conditional rules

- :material-database: **[Connectors](connectors/overview.md)**

    CSV, Parquet, S3, PostgreSQL, Snowflake, BigQuery, and more

- :material-snowflake: **[Snowflake](platforms/snowflake.md)** · :material-fire: **[Databricks](platforms/databricks.md)** · :material-notebook: **[Kaggle](platforms/kaggle.md)**

    Platform-specific guides for your data stack

- :material-puzzle: **[Integrations](integrations/pytest.md)**

    pytest, dbt, Airflow, GitHub Actions, Slack, Teams

- :material-console: **[CLI Reference](cli.md)**

    Command-line tools for validation, profiling, and reports

- :material-api: **[API Reference](api/index.md)**

    Complete Python API documentation

</div>

---

## What's New in 3.0

DuckGuard 3.0 adds **23 new check types** while maintaining 100% backward compatibility:

- **Conditional checks** — validate only when conditions are met
- **Multi-column checks** — composite keys, column pair relationships
- **Query-based checks** — custom SQL with built-in security
- **Distributional checks** — KS test, chi-square, normality testing
- **7 anomaly detection methods** — Z-score, IQR, ML baselines, seasonal
- **Enterprise security** — multi-layer SQL injection prevention

[Read the full changelog →](changelog.md)
