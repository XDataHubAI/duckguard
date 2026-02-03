# Row-Level Errors

Pinpoint exactly which rows failed validation — with values, reasons, and context.

## Quick Start

```python
from duckguard import connect

data = connect("orders.csv")
result = data.amount.between(1, 1000)

if not result:
    print(result.summary())
    # Sample of 10 failing rows (total: 47):
    #   Row 23: amount=0 - expected between 1 and 1000
    #   Row 156: amount=-5 - expected between 1 and 1000
    #   ... and 42 more failures
```

## FailedRow Structure

Each failed row captures:

```python
for row in result.failed_rows:
    print(row.row_index)   # 1-based row number
    print(row.column)      # Column name
    print(row.value)       # Actual value that failed
    print(row.expected)    # What was expected
    print(row.reason)      # Human-readable explanation
    print(row.context)     # Additional row data (dict)
```

## Accessing Failed Data

```python
result = data.email.matches(r"^[\w.]+@[\w.]+$")

# Get just the bad values
bad_values = result.get_failed_values()
# ['not-an-email', '', 'missing@', ...]

# Get row indices
bad_rows = result.get_failed_row_indices()
# [12, 45, 78, ...]

# Total failure count (may exceed sample size)
print(result.total_failures)  # 47
```

## Convert to DataFrame

Export failed rows to pandas for analysis:

```python
df = result.to_dataframe()
print(df)
#    row_index  column       value              expected  reason
# 0         12   email  not-an-email   matches pattern    ...
# 1         45   email               matches pattern    ...
```

!!! note
    Requires pandas: `pip install pandas`

## Summary Output

The `summary()` method gives a concise overview:

```python
print(result.summary())
```

Output:

```
Column 'amount' has 47 values outside range [1, 1000]

Sample of 5 failing rows (total: 47):
  Row 23: amount=0 - expected between 1 and 1000
  Row 156: amount=-5 - expected between 1 and 1000
  Row 301: amount=1500 - expected between 1 and 1000
  Row 445: amount=-12.5 - expected between 1 and 1000
  Row 502: amount=0 - expected between 1 and 1000
  ... and 42 more failures
```

## ValidationResult in Detail

```python
result = data.amount.between(0, 100)

result.passed          # True/False
result.actual_value    # Count of failures
result.expected_value  # What was expected
result.message         # Human-readable summary
result.details         # Additional metadata dict
result.failed_rows     # List[FailedRow] — sample of failures
result.total_failures  # Total count (may exceed sample)
```

## Boolean Context

`ValidationResult` works directly in assertions and `if` statements:

```python
# Use in assert
assert data.customer_id.null_percent == 0

# Use in if
result = data.amount.between(0, 10000)
if not result:
    print(f"Failed: {result.message}")
```

## Practical Patterns

### Debugging pipeline failures

```python
result = data.price.between(0, 999)
if not result:
    df = result.to_dataframe()
    df.to_csv("failed_rows.csv")
    raise AssertionError(result.summary())
```

### Conditional alerting

```python
result = data.email.matches(r"^[\w.]+@[\w.]+\.\w{2,}$")
if result.total_failures > 100:
    send_alert(f"Email validation: {result.total_failures} failures")
elif result.total_failures > 0:
    log_warning(result.summary())
```

### Combining with quality score

```python
score = data.score()
results = [
    data.order_id.null_percent == 0,
    data.amount.between(0, 10000),
    data.email.matches(r"^[\w.]+@[\w.]+\.\w{2,}$"),
]

for r in results:
    if not r:
        print(r.summary())

print(f"Overall quality: {score.grade}")
```
