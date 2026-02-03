# Hacker News Submission

## Title
Show HN: DuckGuard – Data quality validation in 3 lines, powered by DuckDB

## URL
https://github.com/XDataHubAI/duckguard

## Text (for Show HN)
I built DuckGuard because every data quality tool (Great Expectations, Soda) requires 50+ lines of boilerplate before you can validate a single column.

DuckGuard gives you a pytest-like API:

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
assert orders.amount.between(0, 10000)
```

It runs on DuckDB, so it's 10x faster and uses 20x less memory than pandas-based alternatives. A 1GB CSV validates in ~4 seconds using ~200MB RAM.

Features: quality scoring (A-F grades), PII detection, 7 anomaly detection methods, data contracts, drift detection, reconciliation, YAML rules, and integrations with pytest/dbt/Airflow.

v3.0 just shipped with conditional checks, multi-column validation, query-based expectations, and distributional tests — all with multi-layer SQL injection prevention.

Open source under Elastic License 2.0. Would love feedback from anyone doing data quality at scale.

## Notes
- Post between 8-10 AM ET on a weekday (best HN times)
- Tuesday or Wednesday preferred
- Respond to every comment within 30 minutes
- Be honest about limitations
- Don't be defensive
