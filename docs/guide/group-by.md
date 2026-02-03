# Group-By Validation

Run validation checks on each group separately — per-region, per-date, per-status.

## Quick Start

```python
from duckguard import connect

data = connect("orders.csv")

# Every region must have >100 rows
result = data.group_by("region").row_count_greater_than(100)
assert result.passed

# Check null percent per group
result = data.group_by("region").validate(
    lambda col: col.null_percent < 5,
    column="customer_id"
)
assert result.passed
```

## Creating Groups

Use `group_by()` with a single column or a list:

```python
# Single column
grouped = data.group_by("status")

# Multiple columns
grouped = data.group_by(["date", "region"])
```

## Group Properties

```python
grouped = data.group_by("status")

# List all group keys
print(grouped.groups)
# [{'status': 'active'}, {'status': 'pending'}, ...]

# Count of distinct groups
print(grouped.group_count)  # 3
```

## Group Statistics

Get row counts per group:

```python
stats = data.group_by("status").stats()
for g in stats:
    print(f"{g['status']}: {g['row_count']} rows")
# active: 5000 rows
# pending: 1200 rows
# cancelled: 300 rows
```

## Row Count Validation

Ensure every group meets a minimum row count:

```python
result = data.group_by("region").row_count_greater_than(100)

if not result.passed:
    for g in result.get_failed_groups():
        print(f"Region {g.group_key} has only {g.row_count} rows")
```

## Custom Validation

Use `validate()` with a lambda for column-level checks per group:

```python
# Null percentage check per group
result = data.group_by("region").validate(
    lambda col: col.null_percent < 5,
    column="customer_id"
)

# Range check per group
result = data.group_by("date").validate(
    lambda col: col.between(0, 10000),
    column="amount"
)
```

## GroupByResult

The result object gives you full visibility:

```python
result = data.group_by("region").row_count_greater_than(50)

print(result.passed)          # True/False — all groups pass?
print(result.total_groups)    # Total number of groups
print(result.passed_groups)   # Groups that passed
print(result.failed_groups)   # Groups that failed
print(result.pass_rate)       # Percentage passed

# Inspect failures
for g in result.get_failed_groups():
    print(f"[{g.key_string}]: {g.row_count} rows")
    for cr in g.check_results:
        if not cr.passed:
            print(f"  - {cr.message}")

# Full summary
print(result.summary())
```

## Practical Patterns

### Per-partition quality gate

```python
# Every date partition must have data
result = data.group_by("date").row_count_greater_than(0)
assert result, f"Empty partitions found: {result.summary()}"
```

### Segment-level completeness

```python
# Amount must be non-null in each region
result = data.group_by("region").validate(
    lambda col: col.null_percent == 0,
    column="amount"
)
```

### Multi-level grouping

```python
result = data.group_by(["country", "city"]).row_count_greater_than(10)
print(f"{result.pass_rate:.0f}% of country/city combos have >10 rows")
```
