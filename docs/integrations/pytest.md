# pytest Integration

Write data quality tests as standard pytest tests — no plugins needed.

## Quick Start

```python
# tests/test_data_quality.py
from duckguard import connect

def test_orders_quality():
    data = connect("data/orders.csv")

    assert data.row_count > 0
    assert data.order_id.null_percent == 0
    assert data.order_id.has_no_duplicates()
    assert data.amount.between(0, 10000)
    assert data.status.isin(["pending", "shipped", "delivered"])
```

```bash
pytest tests/test_data_quality.py -v
```

## Why It Works

DuckGuard's `ValidationResult` implements `__bool__`, so it works directly with `assert`:

```python
result = data.amount.between(0, 10000)
assert result  # Passes if all values in range
```

On failure, pytest shows the result details automatically.

## Better Error Messages

Include the summary in assertions for detailed failure output:

```python
def test_amount_range():
    data = connect("orders.csv")
    result = data.amount.between(0, 10000)
    assert result, result.summary()
    # On failure:
    # AssertionError: Column 'amount' has 47 values outside range [0, 10000]
    # Sample of 5 failing rows (total: 47):
    #   Row 23: amount=-5 ...
```

## Fixtures

Use pytest fixtures for shared dataset connections:

```python
import pytest
from duckguard import connect

@pytest.fixture
def orders():
    return connect("data/orders.csv")

@pytest.fixture
def customers():
    return connect("data/customers.csv")

def test_orders_completeness(orders):
    assert orders.order_id.null_percent == 0
    assert orders.customer_id.null_percent == 0

def test_orders_values(orders):
    assert orders.total_amount.between(0, 100000)
    assert orders.status.isin(["pending", "shipped", "delivered"])

def test_customer_uniqueness(customers):
    assert customers.email.has_no_duplicates()
```

## Parameterized Tests

Test multiple columns with `@pytest.mark.parametrize`:

```python
@pytest.mark.parametrize("column", ["order_id", "customer_id", "product_id"])
def test_required_columns(orders, column):
    assert orders[column].null_percent == 0

@pytest.mark.parametrize("column,min_val,max_val", [
    ("amount", 0, 100000),
    ("quantity", 1, 10000),
    ("discount", 0, 100),
])
def test_ranges(orders, column, min_val, max_val):
    assert orders[column].between(min_val, max_val)
```

## Auto-Generate Tests

Let DuckGuard write your tests:

```python
from duckguard import connect
from duckguard.profiler import AutoProfiler

data = connect("orders.csv")
profiler = AutoProfiler()
test_code = profiler.generate_test_file(data, output_var="orders")

with open("tests/test_orders.py", "w") as f:
    f.write(test_code)
```

## YAML-Based Tests

Run YAML rules inside pytest:

```python
from duckguard import load_rules, execute_rules

def test_yaml_rules():
    rules = load_rules("duckguard.yaml")
    result = execute_rules(rules)
    assert result.passed, f"{result.failed_count} checks failed"
```

## Quality Gate Pattern

```python
def test_quality_gate():
    data = connect("data/orders.csv")
    score = data.score()
    assert score.overall >= 80, f"Quality {score.overall:.0f}/100 below threshold"
    assert score.grade in ("A", "B"), f"Grade {score.grade} below acceptable"
```

## CI Integration

```bash
# Run data quality tests in CI
pytest tests/test_data_quality.py -v --tb=short --junitxml=results.xml
```

See [GitHub Actions](github-actions.md) for CI/CD setup.
