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
assert orders.status.isin(["pending", "shipped", "delivered"])

quality = orders.score()
print(f"Grade: {quality.grade}")  # A, B, C, D, or F
```

It runs on DuckDB, so it's 10x faster and uses 20x less memory than pandas-based alternatives. A 1GB CSV validates in ~4 seconds using ~200MB RAM.

What's included out of the box:
- Quality scoring (A-F grades across 4 dimensions)
- Row-level error details (shows which rows failed, not just percentages)
- PII detection (auto-detect emails, SSNs, credit cards)
- 7 anomaly detection methods (z-score, IQR, ML baselines, seasonal)
- Data contracts and schema evolution tracking
- Drift detection and cross-dataset reconciliation
- Conditional checks, multi-column validation, distributional tests
- YAML rules + auto-discovery
- Integrations: pytest, dbt, Airflow, GitHub Actions, Slack/Teams

v3.1 is current. Python 3.10+, no pandas dependency.

Docs: https://xdatahubai.github.io/duckguard/

Open source under Elastic License 2.0 (same as Elasticsearch). Would love feedback from anyone doing data quality at scale.

## Notes
- Post between 8-10 AM ET on a weekday (best HN times)
- Tuesday or Wednesday preferred
- Respond to every comment within 30 minutes
- Be honest about limitations
- Don't be defensive
