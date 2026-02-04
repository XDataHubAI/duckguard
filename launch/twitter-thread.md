# Twitter/X Thread

## Tweet 1 (Hook)
Every data quality tool makes you write 50+ lines of boilerplate before you can validate a single column.

So I built one where it takes 3 lines.

Meet DuckGuard. 🦆🛡️

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

That's insane.

## Tweet 3 (The Solution)
Here's DuckGuard:

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
```

Done. It reads like English. Runs like DuckDB.

## Tweet 4 (Speed)
Because it's built on @daboratoryorg's DuckDB, not pandas:

📊 1GB CSV
- Great Expectations: 45 sec, 4GB RAM
- DuckGuard: 4 sec, 200MB RAM

That's 10x faster, 20x less memory.

## Tweet 5 (Features)
What's included (no extra setup):

✅ Quality scoring (A-F grades)
✅ Row-level error details
✅ PII detection
✅ 7 anomaly detection methods
✅ Data contracts
✅ Drift detection
✅ Cross-dataset validation
✅ YAML rules + auto-discovery

## Tweet 6 (Integrations)
Works with your existing stack:

🧪 pytest (validations ARE pytest assertions)
🔧 dbt
🌊 Airflow
🤖 GitHub Actions
📱 Slack/Teams alerts

## Tweet 7 (CTA)
Open source. Built for data engineers who are tired of ceremony.

⭐ GitHub: github.com/XDataHubAI/duckguard
📦 Install: pip install duckguard
📖 Docs: xdatahubai.github.io/duckguard

Star it if you've ever been frustrated by Great Expectations. I know you have.
