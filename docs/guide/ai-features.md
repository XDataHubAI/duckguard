# AI-Powered Data Quality (Coming in v3.2)

!!! warning "Preview"
    This feature is under development. API may change.

## Overview

DuckGuard 3.2 will add AI-powered data quality capabilities — the first data quality tool with native LLM integration.

## Planned Features

### `duckguard explain`

Point DuckGuard at your data and get a plain-English quality summary:

```bash
duckguard explain orders.csv
```

```
📊 Orders Data Quality Summary

Your dataset has 29 rows across 14 columns. Overall quality: B+ (85/100)

Issues found:
• 2 rows have missing ship_date values — these appear to be pending orders,
  which is expected based on the status column
• The phone column has inconsistent formatting — US numbers use +1 prefix
  but UK numbers use +44. Consider standardizing to E.164 format
• quantity values range from 1-5, but total_amount suggests some bulk orders
  may be missing

Recommendations:
1. Add a not_null_when check: ship_date should be present when status != 'pending'
2. Add a phone format validation with matches() using E.164 pattern
3. Verify quantity * unit_price = subtotal for all rows (found 0 mismatches ✓)
```

### `duckguard suggest`

Auto-generate validation rules from your data patterns:

```bash
duckguard suggest orders.csv --output duckguard.yaml
```

```python
from duckguard import connect, suggest_rules

orders = connect("orders.csv")
rules = suggest_rules(orders)

# Returns YAML rules tailored to your actual data patterns
print(rules)
```

The AI analyzes column distributions, semantic types, relationships, and patterns to generate rules that match your data's actual structure — not generic boilerplate.

### `duckguard fix`

Get AI-suggested data cleaning steps:

```bash
duckguard fix orders.csv
```

```
🔧 Suggested Fixes for orders.csv

1. [MISSING DATA] ship_date is null for 2 rows
   → These are pending orders (status='pending'). No action needed,
     but add a conditional check: ship_date.not_null_when("status != 'pending'")

2. [FORMAT] phone has mixed formats (+12125551001 vs +442071234567)
   → Standardize to E.164: all numbers should start with + followed by country code
   → SQL: UPDATE orders SET phone = regexp_replace(phone, ...)

3. [POTENTIAL ISSUE] email column contains PII
   → 29/29 rows contain email addresses
   → Consider: masking in non-prod environments, adding to PII inventory
```

### Natural Language Rules

Define validation rules in plain English:

```python
from duckguard import connect
from duckguard.ai import natural_rules

orders = connect("orders.csv")

# Plain English → validation rules
results = natural_rules(orders, [
    "order IDs should never be null or duplicated",
    "quantities should be positive integers under 1000",
    "every shipped order must have a tracking number",
    "email addresses should be valid format",
])

for r in results:
    print(f"{'✓' if r.passed else '✗'} {r.message}")
```

## Architecture

```
User Data → AutoProfiler → AI Analysis → Actionable Output
                ↓                ↓
         Column stats      LLM interprets
         Patterns          patterns and
         Semantic types    generates rules
         Anomalies         in context
```

The AI layer is thin — it takes the rich profiling data DuckGuard already produces and uses an LLM to:
1. Interpret patterns in human terms
2. Generate contextual validation rules
3. Explain anomalies with domain awareness
4. Suggest fixes with actual SQL/code

## Supported LLMs

```python
from duckguard.ai import configure

# OpenAI
configure(provider="openai", api_key="sk-...")

# Anthropic
configure(provider="anthropic", api_key="sk-ant-...")

# Local (Ollama)
configure(provider="ollama", model="llama3")
```
