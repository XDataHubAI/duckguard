# YAML Rules

Define validation rules in YAML — no Python needed. DuckGuard supports both structured and natural-language formats.

## Quick Start

```yaml
# duckguard.yaml
source: data/orders.csv

checks:
  customer_id:
    - not_null
    - unique

  amount:
    - positive
    - range: [0, 10000]

  email:
    - pattern: email
    - null_percent: "< 5"

  status:
    - allowed_values: [pending, shipped, delivered]

table:
  - row_count: "> 0"
```

```bash
duckguard check data/orders.csv --config duckguard.yaml
```

## Natural Language Format

Use the `rules:` key for plain-English expressions:

```yaml
source: data/orders.csv

rules:
  - order_id is not null
  - order_id is unique
  - amount >= 0
  - amount between 0 and 10000
  - status in ['pending', 'shipped', 'delivered']
  - row_count > 0
```

## Check Types

### Null Checks

```yaml
checks:
  name:
    - not_null               # Zero nulls
    - null_percent: "< 5"   # Less than 5% nulls
```

### Uniqueness

```yaml
checks:
  email:
    - unique                 # 100% unique
    - unique_percent: "> 95" # At least 95% unique
    - no_duplicates          # Same as unique
```

### Value Ranges

```yaml
checks:
  amount:
    - positive             # > 0
    - non_negative         # >= 0
    - min: 0               # All values >= 0
    - max: 10000           # All values <= 10000
    - range: [0, 10000]    # Between 0 and 10000
    - between: [0, 10000]  # Alias for range
```

### Patterns

```yaml
checks:
  email:
    - pattern: email       # Built-in email pattern
  phone:
    - pattern: phone       # Built-in phone pattern
  id:
    - pattern: uuid        # Built-in UUID pattern
  custom:
    - pattern: "^[A-Z]{3}-\\d{4}$"  # Custom regex
```

**Built-in patterns:** `email`, `phone`, `uuid`, `url`, `ip_address`, `date_iso`, `datetime_iso`, `ssn`, `zip_us`, `credit_card`, `slug`, `alpha`, `alphanumeric`, `numeric`

### Allowed Values

```yaml
checks:
  status:
    - allowed_values: [pending, shipped, delivered]
  # Aliases also work:
  country:
    - isin: [US, CA, UK, DE]
```

### String Length

```yaml
checks:
  name:
    - min_length: 1
    - max_length: 100
    - length: [1, 100]    # Combined min/max
```

### Table-Level Checks

```yaml
table:
  - row_count: "> 0"
  - row_count: "> 1000"
```

## Severity Levels

Override severity per check — `error` (default), `warning`, or `info`:

```yaml
checks:
  description:
    - not_null:
        severity: warning
        message: "Description is recommended"
```

## Conditional Checks (DuckGuard 3.0)

```yaml
checks:
  state:
    - not_null_when:
        condition: "country = 'USA'"
  tracking_number:
    - not_null_when:
        condition: "status = 'shipped'"
  price:
    - between_when:
        value: [0, 999999]
        condition: "status = 'COMPLETED'"
```

## Multi-Column & Query Checks

```yaml
checks:
  _multicolumn:
    - column_pair_satisfy:
        column_a: end_date
        column_b: start_date
        expression: "end_date >= start_date"
    - multicolumn_unique:
        columns: [user_id, session_id]

  _query:
    - query_no_rows:
        query: "SELECT * FROM table WHERE total < subtotal"
```

## Auto-Generate Rules

```bash
duckguard discover data.csv --output duckguard.yaml
```

Or in Python:

```python
from duckguard import generate_rules

rules = generate_rules("data.csv", as_yaml=True)
print(rules)
```

## Execute Programmatically

```python
from duckguard import load_rules, execute_rules

ruleset = load_rules("duckguard.yaml")
result = execute_rules(ruleset, source="data.csv")

print(result.passed)        # True/False
print(result.quality_score) # 0-100
print(result.failed_count)  # Number of failures

for failure in result.get_failures():
    print(f"[{failure.column}] {failure.message}")
```
