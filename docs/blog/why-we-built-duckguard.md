# Why We Built DuckGuard

*January 2026*

## The Frustration

I've been a data engineer for years. Every project, the same ritual: set up data quality checks. Every time, the same pain.

Great Expectations wants you to understand contexts, datasources, assets, batch requests, expectation suites, and validators before you can check if a column has nulls. That's not quality engineering — that's ceremony.

Soda Core is better but pushes you into YAML-first configuration. Want to do something beyond the built-in checks? Good luck.

Pandera is clean but pandas-only. The moment your data doesn't fit in memory, you're stuck.

Every tool in this space makes the same mistake: they're designed for the tool's architecture, not for the engineer's workflow.

## The Insight

I write tests every day. `pytest` doesn't ask me to configure a test context, register a test source, build a test batch, and initialize a test validator. I just write:

```python
def test_something():
    assert result == expected
```

Why can't data quality work the same way?

And separately: every data tool loads everything into pandas DataFrames. For a 1 GB CSV, that means 4 GB of RAM and 45 seconds of waiting. But DuckDB can scan that same file in 4 seconds using 200 MB. The technology exists — nobody's wiring it up for data quality.

## The Result

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.is_not_null()
assert orders.amount.between(0, 10000)
```

That's DuckGuard. Three lines. Reads like English. Runs on DuckDB.

No boilerplate. No configuration ceremony. No memory explosion. Just connect and validate.

## What We Learned Building It

### 1. The API is the product

We spent more time on the API surface than on the engine. Every method name was debated. `is_not_null()` not `expect_column_values_to_not_be_null()`. `between(0, 100)` not `expect_column_values_to_be_between(column, 0, 100)`.

Data quality checks should read like assertions, not Java method signatures from 2005.

### 2. Speed changes behavior

When validation takes 45 seconds, engineers run it in CI and forget about it. When it takes 4 seconds, they run it interactively. They explore. They add more checks. Speed isn't just a feature — it changes how people work with data quality.

### 3. Batteries matter

PII detection, anomaly detection, data contracts, drift detection, reconciliation — these aren't nice-to-haves. They're the things engineers build themselves (badly) because their data quality tool doesn't include them. We built them in from the start.

### 4. Row-level errors change everything

"3% of values failed" is useless. "Row 5: quantity=500, Row 23: quantity=-2" is actionable. Every DuckGuard validation returns the specific rows that failed. This alone saves hours of debugging.

## The Numbers

| Metric | Great Expectations | DuckGuard |
|--------|:-----------------:|:---------:|
| Lines to start | 50+ | **3** |
| 1 GB CSV | 45 sec / 4 GB | **4 sec / 200 MB** |
| 10 GB Parquet | 8 min / 32 GB | **45 sec / 2 GB** |
| Dependencies | 20+ | **7** |
| Learning curve | Days | **Minutes** |

## What's Next

DuckGuard 3.0 shipped with conditional checks, multi-column validation, query-based expectations, and 7 anomaly detection methods. We're working on:

- **AI-powered rule suggestion** — point DuckGuard at your data, get validation rules automatically
- **Streaming validation** — check data quality in real-time pipelines
- **Deeper integrations** — native dbt tests, Dagster assets, Prefect flows

We're building DuckGuard in the open. Star us on [GitHub](https://github.com/XDataHubAI/duckguard), try it on your data, and tell us what sucks.

```bash
pip install duckguard
```

---

*DuckGuard is open-source under the Elastic License 2.0. Built by the [XDataHubAI](https://github.com/XDataHubAI) team.*
