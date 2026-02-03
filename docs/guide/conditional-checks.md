# Conditional Checks

Apply validation rules only when a SQL condition is met. Perfect for business rules that depend on context.

## Basic Usage

```python
from duckguard import connect

orders = connect("orders.csv")

# Email required only for shipped orders
orders.email.not_null_when("status = 'shipped'")

# Quantity must be 1-100 for US orders
orders.quantity.between_when(1, 100, "country = 'US'")

# Status must be shipped or delivered for UK
orders.status.isin_when(["shipped", "delivered"], "country = 'UK'")
```

## Available Methods

| Method | Description |
|--------|-------------|
| `col.not_null_when(condition)` | Not null when condition is true |
| `col.unique_when(condition)` | Unique when condition is true |
| `col.between_when(min, max, condition)` | Range check when condition is true |
| `col.isin_when(values, condition)` | Enum check when condition is true |
| `col.matches_when(pattern, condition)` | Pattern match when condition is true |

## Conditions

Conditions are SQL WHERE clauses. Use any valid SQL expression:

```python
# Simple equality
orders.email.not_null_when("status = 'active'")

# Multiple conditions
orders.phone.not_null_when("country = 'US' AND type = 'business'")

# Numeric comparisons
orders.discount.between_when(0, 50, "amount > 1000")

# Date conditions
orders.tracking_number.not_null_when("ship_date IS NOT NULL")
```

## Thresholds

By default, all rows matching the condition must pass. Use `threshold` for partial pass rates:

```python
# At least 95% of shipped orders must have tracking numbers
result = orders.tracking.not_null_when("status = 'shipped'", threshold=0.95)
```

## Security

Conditions go through multi-layer SQL injection prevention:

- Forbidden keyword detection (INSERT, UPDATE, DELETE, DROP, etc.)
- Injection pattern blocking (OR 1=1, UNION SELECT, comment injection)
- Complexity scoring and validation
- READ-ONLY enforcement

You cannot modify data through conditions — only filter rows for validation.

## Real-World Examples

```python
# E-commerce: validate based on order type
orders.gift_message.not_null_when("is_gift = true")
orders.tax_amount.between_when(0, 1000, "country = 'US'")

# Finance: conditional compliance
txns.kyc_verified.not_null_when("amount > 10000")
txns.currency.isin_when(['USD', 'EUR'], "region = 'EMEA'")

# Healthcare: conditional requirements
records.insurance_id.not_null_when("visit_type = 'inpatient'")
records.diagnosis_code.matches_when(r'^[A-Z]\d{2}', "status = 'discharged'")
```
