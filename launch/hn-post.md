# Hacker News Submission

## Title
Show HN: DuckGuard – Data quality validation in 3 lines of Python, powered by DuckDB

## URL
https://github.com/XDataHubAI/duckguard

## Text (for Show HN)
I built DuckGuard because every data quality tool (Great Expectations, Soda) requires 50+ lines of boilerplate before you can validate a single column.

DuckGuard gives you a pytest-like API that works on any data source:

```python
from duckguard import connect

orders = connect("s3://warehouse/orders.parquet")  # or Snowflake, Databricks, CSV...
assert orders.customer_id.is_not_null()
assert orders.total_amount.between(0, 10000)
assert orders.status.isin(["pending", "shipped", "delivered"])
```

Same 3 lines whether your data lives in S3, Snowflake, Databricks, BigQuery, or a local CSV.

Built on DuckDB — connects to 15+ data sources including Parquet on cloud storage, data warehouses (Snowflake, Databricks, BigQuery, Redshift), databases (Postgres, MySQL), and modern formats (Delta Lake, Iceberg).

What's included out of the box:
- Quality scoring (A-F grades across 4 dimensions)
- Row-level error details (shows exactly which rows failed and why)
- PII detection (auto-detect emails, SSNs, credit cards, phones)
- 7 anomaly detection methods (z-score, IQR, ML baselines, seasonal)
- AI features — LLM-powered explain, suggest, and fix (OpenAI/Anthropic/Ollama)
- Data contracts and schema evolution tracking
- Drift detection and cross-dataset reconciliation
- Auto-profiling with semantic type detection
- YAML rules + auto-discovery (generate rules from your data)
- Integrations: pytest, dbt, Airflow, GitHub Actions, Slack/Teams/Email

v3.2.0 is on PyPI. Python 3.10+, Apache 2.0.

Try it: `pip install duckguard`
Docs: https://xdatahubai.github.io/duckguard/

Would love feedback from anyone doing data quality at scale.

---

## Posting Instructions
1. Go to https://news.ycombinator.com/submit
2. Title: `Show HN: DuckGuard – Data quality validation in 3 lines of Python, powered by DuckDB`
3. URL: `https://github.com/XDataHubAI/duckguard`
4. Text: Copy everything between the first ``` and the `---` above
5. **Timing**: Tuesday 8-10 AM ET (5-7 AM PST) is optimal
6. **Critical**: Respond to EVERY comment within 30 min. Be honest, don't be defensive.
