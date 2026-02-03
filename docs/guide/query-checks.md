# Query-Based Checks

Write custom SQL to validate complex business logic that can't be expressed with standard checks.

## Quick Start

```python
from duckguard import connect

data = connect("orders.csv")

# Find violations — query should return no rows
result = data.expect_query_to_return_no_rows(
    query="SELECT * FROM table WHERE total < subtotal"
)
assert result.passed

# Ensure expected data exists
result = data.expect_query_to_return_rows(
    query="SELECT * FROM table WHERE status = 'active'"
)
assert result.passed
```

## Available Methods

### No Rows (Find Violations)

Write a query that finds bad rows. Passes if zero rows returned:

```python
# No future dates
result = data.expect_query_to_return_no_rows(
    query="SELECT * FROM table WHERE order_date > CURRENT_DATE"
)

# No orphaned records
result = data.expect_query_to_return_no_rows(
    query="SELECT * FROM table WHERE status = 'shipped' AND tracking_number IS NULL"
)
```

### Returns Rows (Data Exists)

Ensure a query returns at least one row:

```python
result = data.expect_query_to_return_rows(
    query="SELECT * FROM table WHERE created_at >= CURRENT_DATE - 7"
)
```

### Result Equals

Check a scalar query result against an expected value:

```python
# Exact match
result = data.expect_query_result_to_equal(
    query="SELECT COUNT(*) FROM table WHERE status = 'pending'",
    expected=0
)

# With numeric tolerance
result = data.expect_query_result_to_equal(
    query="SELECT AVG(price) FROM table",
    expected=100.0,
    tolerance=5.0
)
```

### Result Between

Validate a query result falls within a range:

```python
result = data.expect_query_result_to_be_between(
    query="SELECT AVG(price) FROM table",
    min_value=10.0,
    max_value=1000.0
)

# Null rate validation
result = data.expect_query_result_to_be_between(
    query="""
        SELECT (COUNT(*) FILTER (WHERE price IS NULL)) * 100.0 / COUNT(*)
        FROM table
    """,
    min_value=0.0,
    max_value=5.0  # Max 5% nulls
)
```

## Table Reference

Use `table` in your queries to reference the dataset — DuckGuard replaces it with the actual source:

```python
# ✅ Correct
query = "SELECT * FROM table WHERE amount < 0"

# ❌ Don't hardcode file paths
query = "SELECT * FROM 'data/orders.csv' WHERE amount < 0"
```

## Security

Query-based checks enforce multiple security layers:

| Control | Detail |
|---------|--------|
| **Read-only** | Only `SELECT` statements allowed |
| **Forbidden keywords** | `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, etc. blocked |
| **Injection patterns** | `OR 1=1`, `UNION SELECT`, stacked queries blocked |
| **Complexity limit** | Score capped at 50 (JOINs, subqueries, aggregates add points) |
| **Timeout** | 30-second execution limit |
| **Row limit** | Results capped at 10,000 rows |

## YAML Rules

```yaml
checks:
  _query:
    - query_no_rows:
        query: "SELECT * FROM table WHERE total < subtotal"
    - query_result_equals:
        query: "SELECT COUNT(*) FROM table WHERE status = 'error'"
        expected: 0
    - query_result_between:
        query: "SELECT AVG(amount) FROM table"
        min_value: 10
        max_value: 500
```
