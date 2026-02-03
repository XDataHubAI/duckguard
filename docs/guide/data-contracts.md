# Data Contracts

Define schema, quality SLAs, and ownership for your data in YAML — then validate automatically.

## Quick Start

```yaml
# orders.contract.yaml
contract:
  name: orders
  version: "1.2.0"

  schema:
    - name: order_id
      type: string
      required: true
      unique: true
    - name: amount
      type: decimal
      required: true
      constraints:
        - type: range
          value: [0, 100000]
    - name: email
      type: string
      semantic_type: email
      pii: true

  quality:
    completeness: 99.5
    freshness: "24h"
    row_count_min: 1000

  metadata:
    owner: platform-team
    description: Order transactions from checkout
    consumers: [analytics, finance]
```

```python
from duckguard import load_contract, validate_contract

contract = load_contract("orders.contract.yaml")
result = validate_contract(contract, "orders.parquet")

assert result.passed
print(result.summary())
```

## Schema Validation

Contracts validate that your data matches the expected schema:

- **Missing fields** — required fields that don't exist → error; optional → warning
- **Extra fields** — fields in data not in contract → info (or error in strict mode)
- **Required (not null)** — fields marked `required: true` must have zero nulls
- **Unique** — fields marked `unique: true` must have 100% unique values

### Field Types

`string`, `integer`, `float`, `decimal`, `boolean`, `date`, `datetime`, `timestamp`, `time`, `uuid`, `json`, `array`, `object`, `binary`, `any`

### Field Constraints

```yaml
constraints:
  - type: range
    value: [0, 100000]
  - type: min
    value: 0
  - type: max
    value: 999
  - type: pattern
    value: "^[A-Z]{3}-\\d{4}$"
  - type: allowed_values
    value: [pending, shipped, delivered]
```

## Quality SLAs

```yaml
quality:
  completeness: 99.5        # Min % of non-null cells
  freshness: "24h"           # Max data age
  row_count_min: 1000        # Minimum rows
  row_count_max: 10000000    # Maximum rows
  uniqueness:
    order_id: 100.0          # 100% unique
    email: 95.0              # 95%+ unique
```

## Auto-Generate Contracts

Generate a contract from your existing data:

```python
from duckguard import generate_contract

contract = generate_contract("orders.parquet", name="orders", owner="data-team")

# Save to YAML
generate_contract("orders.parquet", output="orders.contract.yaml")
```

The generator infers types, constraints, PII flags, and quality SLAs from the data.

## Compare Contract Versions

Detect breaking changes between contract versions:

```python
from duckguard import load_contract, diff_contracts

old = load_contract("orders.v1.yaml")
new = load_contract("orders.v2.yaml")

diff = diff_contracts(old, new)

print(diff.has_breaking_changes)  # True/False
print(diff.suggest_version_bump())  # 'major', 'minor', 'patch'
print(diff.summary())

for change in diff.breaking_changes:
    print(f"❌ {change.message}")
```

**Breaking changes:** field removed, type changed, new required field, constraint added.

## Strict Mode

In strict mode, extra fields in data (not defined in contract) are errors:

```python
result = validate_contract(contract, "orders.parquet", strict_mode=True)
```

## CLI

```bash
# Generate contract
duckguard contract generate data.csv --output orders.contract.yaml

# Validate data against contract
duckguard contract validate data.csv --contract orders.contract.yaml

# Diff two versions
duckguard contract diff old.contract.yaml new.contract.yaml
```

## Validation Result

```python
result = validate_contract(contract, source)

result.passed          # True if no errors
result.schema_valid    # Schema checks only
result.quality_valid   # Quality SLA checks only
result.error_count     # Number of errors
result.warning_count   # Number of warnings
result.errors          # List of error messages
result.warnings        # List of warning messages
result.violations      # Full list of ContractViolation objects
```
