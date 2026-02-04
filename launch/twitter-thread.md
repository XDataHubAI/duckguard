# Twitter/X Thread

## Tweet 1 (Hook)
Every data quality tool makes you write 50+ lines of boilerplate before you can validate a single column.

So I built one where it takes 3 lines. Works on any source — S3, Snowflake, Databricks, Fabric, or CSV.

Meet DuckGuard 🦆🛡️

🧵👇

## Tweet 2 (The Problem)
Here's what it takes to check if a column has nulls in Great Expectations:

- Create a context
- Add a datasource
- Create an asset
- Build a batch request
- Add an expectation suite
- Get a validator
- Finally: validate

That's insane for a null check.

## Tweet 3 (The Solution)
Here's DuckGuard:

```python
from duckguard import connect

orders = connect("s3://warehouse/orders.parquet")
assert orders.customer_id.is_not_null()
```

Same 3 lines whether your data is in S3, Snowflake, Databricks, Fabric, BigQuery, or a local CSV.

## Tweet 4 (Connectors)
16+ connectors out of the box:

☁️ S3, GCS, Azure Blob
🏔️ Snowflake, Databricks, BigQuery, Redshift
🟦 Microsoft Fabric (OneLake + SQL)
🗄️ Postgres, MySQL, SQL Server, Oracle
📄 Parquet, CSV, JSON, Delta Lake, Iceberg
🐼 pandas DataFrames

One API. Any source.

## Tweet 5 (Features)
What's built-in (no extra setup):

✅ Quality scoring (A-F grades)
✅ Row-level error details
✅ PII auto-detection
✅ 7 anomaly detection methods
✅ AI-powered explain/suggest/fix
✅ Data contracts + schema tracking
✅ Drift detection + reconciliation
✅ YAML rules + auto-discovery

## Tweet 6 (Azure story)
Full Azure ecosystem integration:

🔷 ADF pipeline quality gates
🔷 Purview metadata push
🔷 Azure Monitor alerting
🔷 Power BI quality dashboards
🔷 DevOps pipeline tasks
🔷 Fabric notebooks

One quality layer across your entire Azure data stack.

## Tweet 7 (Integrations)
Works with your existing stack:

🧪 pytest (validations ARE assertions)
🔧 dbt
🌊 Airflow
🤖 GitHub Actions
📱 Slack / Teams / Email

## Tweet 8 (CTA)
Open source. Apache 2.0. Built for data engineers who are tired of ceremony.

⭐ github.com/XDataHubAI/duckguard
📦 pip install duckguard
📖 xdatahubai.github.io/duckguard

Star it if you've ever been frustrated by data quality tooling. I know you have.

#DataEngineering #DataQuality #Python #DuckDB #OpenSource
