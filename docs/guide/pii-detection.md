# PII Detection

Automatically detect personally identifiable information (PII) in your data using column names and value patterns.

## Quick Start

```python
from duckguard import connect
from duckguard.semantic import SemanticAnalyzer

data = connect("customers.csv")
analyzer = SemanticAnalyzer()

# Find all PII columns
pii = analyzer.find_pii_columns(data)
for col_name, sem_type, warning in pii:
    print(f"⚠️ {col_name}: {sem_type.value} — {warning}")
```

## Semantic Type Detection

DuckGuard detects 40+ semantic types from column names and value patterns:

```python
from duckguard import detect_type, detect_types_for_dataset

# Single column
sem_type = detect_type(data, "email")
print(sem_type)  # SemanticType.EMAIL

# All columns at once
types = detect_types_for_dataset(data)
for col, stype in types.items():
    print(f"{col}: {stype.value}")
```

## Full Dataset Analysis

```python
analysis = analyzer.analyze(data)

print(f"PII columns: {analysis.pii_columns}")
print(f"Has PII: {analysis.has_pii}")

for col in analysis.columns:
    print(f"{col.name}: {col.semantic_type.value} "
          f"(confidence: {col.confidence:.0%})")
    if col.is_pii:
        print(f"  ⚠️ {col.pii_warning}")
    if col.suggested_validations:
        print(f"  Suggested: {col.suggested_validations}")
```

## PII Types Detected

| Type | Detection | Example |
|------|-----------|---------|
| **Email** | Name + regex pattern | `user@example.com` |
| **Phone** | Name + digit pattern | `+1-555-0123` |
| **SSN** | Name + `\d{3}-\d{2}-\d{4}` | `123-45-6789` |
| **Credit Card** | Name + 16-digit pattern | `4111-1111-1111-1111` |
| **Person Name** | Column name matching | `first_name`, `surname` |
| **Address** | Column name matching | `street_address` |

## Detection Methods

Detection uses a two-pass approach:

1. **Column name patterns** — matches against 40+ name patterns (e.g., `email`, `phone_number`, `ssn`)
2. **Value patterns** — regex matching on sampled values (e.g., email format, UUID format)

Confidence scores combine both signals (0.0–1.0).

## Generate Validation YAML

```python
analysis = analyzer.analyze(data)
yaml_rules = analysis.get_validations_yaml()
print(yaml_rules)
```

Output:

```yaml
checks:
  email:
    - pattern: email
    - unique
  phone:
    - pattern: phone
  order_id:
    - not_null
    - unique
```

## Quick Scan

For a fast type-only scan (no statistics):

```python
types = analyzer.quick_scan(data)
# {'order_id': SemanticType.PRIMARY_KEY, 'email': SemanticType.EMAIL, ...}
```

## Common Semantic Types

**Identity:** `primary_key`, `foreign_key`, `uuid`, `id`
**Contact:** `email`, `phone`, `url`, `ip_address`
**PII:** `ssn`, `credit_card`, `person_name`, `address`
**Location:** `country`, `state`, `city`, `zipcode`, `latitude`, `longitude`
**Time:** `date`, `datetime`, `timestamp`, `year`
**Numeric:** `currency`, `percentage`, `quantity`, `age`
**Categorical:** `boolean`, `enum`, `status`, `category`

## CLI Integration

The `discover` and `info` commands include semantic analysis:

```bash
duckguard discover data.csv    # Shows semantic types + PII warnings
duckguard info data.csv        # Shows column types and PII flags
```
