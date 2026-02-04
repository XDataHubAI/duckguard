# Reddit Posts

## r/dataengineering

### Title
I built a data quality tool that validates any source in 3 lines instead of 50

### Body
I've been frustrated with data quality tools for years. Great Expectations requires contexts, datasources, assets, batch requests, and expectation suites before you can check if a column has nulls. Soda pushes everything through YAML. Both use pandas under the hood, so they choke on anything over a few GB.

So I built DuckGuard. It works on any data source with the same 3-line API:

```python
from duckguard import connect

orders = connect("s3://warehouse/orders.parquet")  # or Snowflake, Databricks, CSV...
assert orders.customer_id.is_not_null()
assert orders.total_amount.between(0, 10000)
assert orders.status.isin(["pending", "shipped", "delivered"])
```

15+ connectors: S3/GCS/Azure, Snowflake, Databricks, BigQuery, Redshift, Postgres, MySQL, Delta Lake, Iceberg, Parquet, CSV, JSON, Excel, pandas DataFrames.

Built on DuckDB instead of pandas. For warehouse sources, it pushes queries down to Snowflake/Databricks directly.

What's included out of the box:
- Quality scoring (A-F grades across 4 dimensions)
- Row-level error details (shows exactly which rows failed, not just percentages)
- PII detection (auto-detect emails, SSNs, credit cards)
- 7 anomaly detection methods
- AI features — LLM-powered explain, suggest, and fix
- Data contracts + schema evolution tracking
- Cross-dataset validation, drift detection, reconciliation
- YAML rules + auto-discovery (generate rules from your data)
- Integrations: pytest, dbt, Airflow, GitHub Actions, Slack/Teams

v3.2.0 on PyPI. Apache 2.0. Python 3.10+.

GitHub: https://github.com/XDataHubAI/duckguard
Docs: https://xdatahubai.github.io/duckguard/
`pip install duckguard`

What would make you switch from your current data quality setup?

---

## r/Python

### Title
DuckGuard: pytest-like data quality validation powered by DuckDB — works on S3, Snowflake, Databricks & 15+ sources

### Body
I built a data quality library where validations read like pytest assertions:

```python
from duckguard import connect

orders = connect("s3://bucket/orders.parquet")
assert orders.customer_id.is_not_null()
assert orders.total_amount.between(0, 10000)
```

Instead of `expect_column_values_to_not_be_null("customer_id")`, you write `orders.customer_id.is_not_null()`.

Same API for CSV, Parquet, S3, Snowflake, Databricks, BigQuery, Delta Lake, and 15+ sources. Built on DuckDB. Includes quality scoring, PII detection, anomaly detection, AI-powered suggestions, data contracts, and integrations with pytest/dbt/Airflow.

GitHub: https://github.com/XDataHubAI/duckguard
Docs: https://xdatahubai.github.io/duckguard/
`pip install duckguard`

Would love to hear what Pythonistas think of the API design.

---

## r/snowflake

### Title
Open source tool to validate Snowflake data in 3 lines of Python (no GE boilerplate)

### Body
Built a data quality library that connects to Snowflake directly and pushes aggregation queries down — no data transfer needed:

```python
from duckguard import connect

data = connect("snowflake://account/db", table="orders")
assert data.customer_id.is_not_null()
assert data.total_amount.between(0, 10000)
```

`pip install duckguard[snowflake]`

If you're using Great Expectations on Snowflake and find the setup painful, this might interest you. Same validation power, fraction of the code.

GitHub: https://github.com/XDataHubAI/duckguard
Snowflake guide: https://xdatahubai.github.io/duckguard/platforms/snowflake/

---

## r/databricks

---

## r/azuredatafactory / r/MicrosoftFabric

### Title
Open source data quality tool with native Microsoft Fabric + ADF integration

### Body
Built a Python library for data validation that integrates with the Azure data stack:

```python
from duckguard import connect

# Fabric Lakehouse
data = connect("fabric://workspace/lakehouse/Tables/orders", token=token)

# Or via SQL endpoint
data = connect("fabric+sql://host.datawarehouse.fabric.microsoft.com",
               table="orders", token=token)

# Same 3-line validation everywhere
assert data.customer_id.is_not_null()
assert data.total_amount.between(0, 10000)
```

Also integrates with:
- ADF pipelines (Notebook, Function, or Custom Activity)
- Microsoft Purview (push quality metadata)
- Azure Monitor (custom metrics + alerting)
- Power BI (Python visual scorecards)
- Azure DevOps (pipeline YAML)
- ADLS Gen2 / Blob Storage (direct Parquet read)

`pip install duckguard[fabric]`

GitHub: https://github.com/XDataHubAI/duckguard
Azure guide: https://xdatahubai.github.io/duckguard/platforms/azure/

---

### Title
Data quality for Unity Catalog without Spark overhead — open source tool

### Body
Built a Python library that validates Databricks data via SQL endpoints — no Spark cluster needed:

```python
from duckguard import connect

data = connect("databricks://workspace.databricks.com", table="orders")
assert data.customer_id.is_not_null()
assert data.total_amount.between(0, 10000)
```

Works from your laptop, CI runner, or a $5 VM. Also reads Delta Lake tables directly.

`pip install duckguard[databricks]`

GitHub: https://github.com/XDataHubAI/duckguard
Databricks guide: https://xdatahubai.github.io/duckguard/platforms/databricks/
