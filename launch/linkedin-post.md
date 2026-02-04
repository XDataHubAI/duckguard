# LinkedIn Post

Data quality tools haven't kept up with how we actually work.

Great Expectations requires 50+ lines of setup before you can validate a single column. Soda pushes everything through YAML. Both assume your data lives in one place.

I built DuckGuard to fix this.

One API that works on any data source — S3, Snowflake, Databricks, Microsoft Fabric, BigQuery, or a local CSV:

```python
from duckguard import connect

orders = connect("snowflake://account/db", table="orders")
assert orders.customer_id.is_not_null()
assert orders.total_amount.between(0, 10000)
```

3 lines. Same API everywhere. No boilerplate.

16+ connectors: Snowflake, Databricks, Microsoft Fabric, BigQuery, Redshift, S3/GCS/Azure, Postgres, MySQL, Delta Lake, Iceberg, Parquet, and more.

What's built-in:
• Quality scoring (A-F grades across 4 dimensions)
• Row-level error details (not just "3% failed" — you see exactly which rows and why)
• PII auto-detection (emails, SSNs, credit cards, phones)
• 7 anomaly detection methods
• AI-powered explain, suggest, and fix (OpenAI/Anthropic/Ollama)
• Data contracts and schema evolution tracking
• Drift detection and cross-dataset reconciliation

For Azure shops: full integration with ADF pipelines, Microsoft Purview (quality metadata), Azure Monitor (alerting), Power BI (dashboards), and Azure DevOps (CI/CD).

For everyone: works with pytest, dbt, Airflow, GitHub Actions, Slack, and Teams.

Apache 2.0. Python 3.10+. v3.2.0 on PyPI.

If you're a data engineer, analytics engineer, or ML engineer tired of data quality ceremony — give it a try.

GitHub: https://github.com/XDataHubAI/duckguard
Docs: https://xdatahubai.github.io/duckguard/
Install: pip install duckguard

#DataEngineering #DataQuality #Python #DuckDB #OpenSource #MicrosoftFabric #Snowflake #Databricks
