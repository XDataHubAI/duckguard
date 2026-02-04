# Reddit Posts

## r/dataengineering

### Title
I built a data quality tool that validates in 3 lines instead of 50. Here's why.

### Body
I've been frustrated with data quality tools for years. Great Expectations requires you to set up contexts, datasources, assets, batch requests, and expectation suites before you can check if a column has nulls. Soda pushes everything through YAML. Both use pandas under the hood, so they choke on anything over a few GB.

So I built DuckGuard. The API is designed to feel like pytest:

```python
from duckguard import connect

orders = connect("orders.csv")  # Also: Parquet, S3, Postgres, Snowflake, BigQuery...
assert orders.customer_id.is_not_null()
assert orders.amount.between(0, 10000)
assert orders.status.isin(["pending", "shipped", "delivered"])
```

It runs on DuckDB instead of pandas, so:
- 1GB CSV: 4 sec / 200MB RAM (vs 45 sec / 4GB with GE)
- 10GB Parquet: 45 sec / 2GB RAM (vs 8 min / 32GB)

What's included:
- Quality scoring (A-F grades)
- Row-level error details (not just "3% failed" — shows you which rows)
- PII detection (auto-detect emails, SSNs, credit cards)
- 7 anomaly detection methods (zscore, IQR, ML baselines, seasonal)
- Data contracts and schema evolution tracking
- Cross-dataset validation (FK checks, reconciliation, drift)
- Conditional checks (validate only when conditions are met)
- YAML rules + auto-discovery
- Integrations: pytest, dbt, Airflow, GitHub Actions, Slack/Teams

GitHub: https://github.com/XDataHubAI/duckguard
Docs: https://xdatahubai.github.io/duckguard/
PyPI: `pip install duckguard`

Curious what people think. What would make you switch from your current data quality setup?

---

## r/Python

### Title
DuckGuard: pytest-like data quality validation powered by DuckDB (10x faster than Great Expectations)

### Body
I built a data quality library where validations read like pytest assertions:

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
assert orders.amount.between(0, 10000)
```

Instead of `expect_column_values_to_not_be_null("customer_id")`, you write `orders.customer_id.is_not_null()`.

Built on DuckDB for speed (10x faster, 20x less memory than pandas-based tools). Includes quality scoring, PII detection, anomaly detection, data contracts, and integrations with pytest/dbt/Airflow.

GitHub: https://github.com/XDataHubAI/duckguard
`pip install duckguard`

Would love to hear what Pythonistas think of the API design.
