# LinkedIn Post

Data quality tools haven't kept up with how we actually work.

Great Expectations requires 50+ lines of setup before you can validate a single column. Soda pushes everything through YAML. Both use pandas, so they choke on anything larger than a few GB.

I built DuckGuard to fix this.

The API reads like pytest:

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
assert orders.total_amount.between(0, 10000)
```

3 lines. No boilerplate. No ceremony.

It runs on DuckDB, so it's 10x faster and uses 20x less memory than pandas-based alternatives.

What's included out of the box:
• Quality scoring (A-F grades across 4 dimensions)
• Row-level error details (not just "3% failed" — you see which rows)
• PII detection (auto-detect emails, SSNs, credit cards)
• 7 anomaly detection methods
• Data contracts and schema evolution
• Cross-dataset validation and reconciliation
• Conditional and query-based checks
• Integrations with pytest, dbt, Airflow, and CI/CD

If you're a data engineer, analytics engineer, or ML engineer tired of data quality ceremony — give it a try.

GitHub: https://github.com/XDataHubAI/duckguard
Install: pip install duckguard

#DataEngineering #DataQuality #Python #DuckDB #OpenSource
