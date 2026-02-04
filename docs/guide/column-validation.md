# Column Validation

DuckGuard's column validation API is designed to read like English. Every method returns a `ValidationResult` with `.passed`, `.message`, `.summary()`, and `.failed_rows`.

## Null & Uniqueness

```python
from duckguard import connect

orders = connect("orders.csv")

# No nulls allowed
assert orders.order_id.is_not_null()

# All values must be distinct
assert orders.order_id.is_unique()

# Alias for is_unique
assert orders.order_id.has_no_duplicates()
```

## Column Properties

Access statistics directly on any column:

```python
col = orders.total_amount

col.null_count       # Number of null values
col.null_percent     # Percentage of nulls
col.unique_count     # Number of distinct values
col.min              # Minimum value
col.max              # Maximum value
col.mean             # Mean (numeric columns)
col.median           # Median (numeric columns)
col.stddev           # Standard deviation
```

## Range Checks

```python
# Inclusive range
assert orders.total_amount.between(0, 10000)

# Exclusive bounds
assert orders.total_amount.greater_than(0)
assert orders.total_amount.less_than(100000)
```

## Pattern Matching

```python
# Regex validation
assert orders.email.matches(r'^[\w.+-]+@[\w-]+\.[\w.]+$')

# String length
assert orders.order_id.value_lengths_between(5, 10)
```

## Enum Checks

```python
assert orders.status.isin(["pending", "shipped", "delivered"])
```

## Working with Results

Every validation returns a `ValidationResult`:

```python
result = orders.quantity.between(1, 100)

# Check pass/fail
result.passed          # True or False

# Human-readable message
result.message         # "Column 'quantity' has 3 values outside [1, 100]"

# Detailed summary with row-level errors
print(result.summary())

# Access failed rows directly
for row in result.failed_rows:
    print(f"Row {row.row_number}: {row.value} ({row.reason})")

# Get just the values or indices
result.get_failed_values()        # [500, -2, 0]
result.get_failed_row_indices()   # [5, 23, 29]
```

## Using with pytest

```python
# test_data_quality.py
from duckguard import connect

def test_orders_quality():
    orders = connect("data/orders.csv")
    assert orders.row_count > 0
    assert orders.order_id.is_not_null()
    assert orders.order_id.is_unique()
    assert orders.quantity.between(0, 10000)
    assert orders.status.isin(["pending", "shipped", "delivered"])
```

Run with `pytest`:

```bash
pytest test_data_quality.py -v
```

## Next

- [Quality Scoring →](quality-scoring.md)
- [Cross-Dataset Checks →](cross-dataset.md)
- [Conditional Checks →](conditional-checks.md)
