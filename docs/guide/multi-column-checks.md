# Multi-Column Checks

Validate relationships between columns — date ranges, composite keys, cross-column arithmetic.

## Quick Start

```python
from duckguard import connect

data = connect("orders.csv")

# Date range: end must be after start
result = data.expect_column_pair_satisfy(
    column_a="end_date",
    column_b="start_date",
    expression="end_date >= start_date"
)
assert result.passed

# Composite primary key
result = data.expect_columns_unique(columns=["user_id", "session_id"])
assert result.passed

# Components must sum to 100%
result = data.expect_multicolumn_sum_to_equal(
    columns=["q1_pct", "q2_pct", "q3_pct", "q4_pct"],
    expected_sum=100.0
)
assert result.passed
```

## Column Pair Expressions

`expect_column_pair_satisfy()` evaluates a SQL expression across two columns.

```python
# Arithmetic constraint
result = data.expect_column_pair_satisfy(
    column_a="total",
    column_b="subtotal",
    expression="total = subtotal * 1.1"  # 10% markup
)

# With threshold — allow up to 5% violations
result = data.expect_column_pair_satisfy(
    column_a="end_date",
    column_b="start_date",
    expression="end_date >= start_date",
    threshold=0.95
)
```

**Supported operators:** `>`, `<`, `>=`, `<=`, `=`, `!=`, `+`, `-`, `*`, `/`, `AND`, `OR`

The expression parser validates syntax, checks for SQL injection, and scores complexity (max 50 by default).

## Composite Uniqueness

Validate that a combination of columns forms a unique key:

```python
# Two-column composite key
result = data.expect_columns_unique(
    columns=["user_id", "session_id"]
)

# Three-column composite key with threshold
result = data.expect_columns_unique(
    columns=["year", "month", "day"],
    threshold=0.99  # Allow 1% duplicates
)

# Inspect results
print(result.details["duplicate_combinations"])
print(result.details["uniqueness_rate"])
```

!!! note
    At least 2 columns are required. For single-column uniqueness, use `column.has_no_duplicates()`.

## Multi-Column Sum

Check that columns sum to an expected value per row:

```python
# Budget allocation check
result = data.expect_multicolumn_sum_to_equal(
    columns=["marketing", "sales", "r_and_d"],
    expected_sum=1000000,
    threshold=0.01  # Allow $0.01 rounding error
)
```

## YAML Rules

All multi-column checks work in YAML rule files:

```yaml
checks:
  _multicolumn:
    - column_pair_satisfy:
        column_a: end_date
        column_b: start_date
        expression: "end_date >= start_date"

    - multicolumn_unique:
        columns: [user_id, session_id]

    - multicolumn_sum:
        columns: [q1, q2, q3, q4]
        expected_sum: 100.0
```

## Result Details

Every result includes detailed metadata:

```python
result = data.expect_column_pair_satisfy(
    column_a="end_date",
    column_b="start_date",
    expression="end_date >= start_date"
)

print(result.details["violations"])       # Count of failing rows
print(result.details["total_rows"])       # Total rows checked
print(result.details["violation_rate"])   # Fraction that failed
```
