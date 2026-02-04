---
title: DuckGuard on Kaggle & Colab
description: Profile any dataset in 30 seconds. Data quality checks for notebooks — install, profile, validate, done.
---

# DuckGuard on Kaggle & Colab

## Profile any dataset in 30 seconds

```python
!pip install duckguard -q
from duckguard import profile
profile("orders.csv").show()
```

Three lines. Full data profile. Before you write a single model.

---

## Why This Matters

**Data quality is the #1 reason ML models fail in production.**

Not architecture. Not hyperparameters. Bad data.

- Null values your model silently treats as zero
- Duplicate rows inflating your training set
- PII leaking into features
- Outliers skewing distributions
- Categories that don't match between train and test

You find these problems after 4 hours of training. Or after deploying to production. Or you find them now, in 30 seconds, before you start.

---

## Quick Start

### Kaggle Notebook

```python
# Cell 1 — Install
!pip install duckguard -q
```

```python
# Cell 2 — Load and Profile
import pandas as pd
from duckguard import connect

df = pd.read_csv("/kaggle/input/ecommerce-data/orders.csv")
dg = connect(df)

profile = dg.profile()
profile.show()
```

### Google Colab

```python
# Cell 1 — Install
!pip install duckguard -q
```

```python
# Cell 2 — Load and Profile
import pandas as pd
from duckguard import connect

df = pd.read_csv("orders.csv")
dg = connect(df)

profile = dg.profile()
profile.show()
```

!!! tip "One-click Colab badge"
    Add this to your notebook's README or description to let others run your quality checks instantly:

    ```markdown
    [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USER/YOUR_REPO/blob/main/quality_check.ipynb)
    ```

    The badge links directly to your notebook in Colab — one click to reproduce your data quality analysis.

---

## The Full Workflow

Load → Profile → Validate → Fix → Model

### 1. Load Your Dataset

```python
import pandas as pd
from duckguard import connect

# From Kaggle dataset
df = pd.read_csv("/kaggle/input/ecommerce-data/orders.csv")
dg = connect(df)
```

### 2. Profile — Understand What You Have

```python
profile = dg.profile()
profile.show()
```

**Output:**

```
╭─────────────────────────────────────────────────╮
│ DuckGuard Profile: orders.csv                   │
│ Rows: 51,243  |  Columns: 8  |  Size: 4.2 MB   │
├──────────────┬──────────┬───────┬───────┬───────┤
│ Column       │ Type     │ Nulls │ Unique│ Issues│
├──────────────┼──────────┼───────┼───────┼───────┤
│ order_id     │ int64    │ 0%    │ 100%  │       │
│ customer_id  │ int64    │ 0%    │ 42%   │       │
│ order_date   │ object   │ 0.2%  │ 38%   │ ⚠     │
│ amount       │ float64  │ 1.1%  │ 89%   │ ⚠     │
│ quantity     │ int64    │ 0%    │ 0.4%  │       │
│ status       │ object   │ 0%    │ 0.01% │       │
│ email        │ object   │ 3.4%  │ 41%   │ 🔒 PII│
│ ship_country │ object   │ 0.8%  │ 0.5%  │       │
╰──────────────┴──────────┴───────┴───────┴───────╯

Quality Score: 72/100
Issues Found: 4
  ⚠ order_date: 102 null values, inconsistent date formats detected
  ⚠ amount: 563 null values, 3 extreme outliers (>$50,000)
  🔒 email: Contains PII (email addresses)
  ℹ quantity: Low cardinality (12 unique values)
```

### 3. Validate — Set Expectations

```python
result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "customer_id": {"not_null": True},
    "amount": {"not_null": True, "min": 0, "max": 10000},
    "quantity": {"not_null": True, "min": 1},
    "status": {"in": ["pending", "processing", "shipped", "delivered", "cancelled"]},
})

result.show()
```

**Output:**

```
╭─────────────────────────────────────────────────╮
│ DuckGuard Validation Results                    │
│ 5 checks  |  3 passed  |  2 failed             │
├──────────────────────────┬──────────┬───────────┤
│ Check                    │ Status   │ Details   │
├──────────────────────────┼──────────┼───────────┤
│ order_id not null        │ ✓ PASS   │           │
│ order_id unique          │ ✓ PASS   │           │
│ customer_id not null     │ ✓ PASS   │           │
│ amount not null          │ ✗ FAIL   │ 563 nulls │
│ amount max ≤ 10000       │ ✗ FAIL   │ max=87431 │
│ quantity not null        │ ✓ PASS   │           │
│ quantity min ≥ 1         │ ✓ PASS   │           │
│ status in set            │ ✓ PASS   │           │
╰──────────────────────────┴──────────┴───────────╯
```

### 4. Find Issues — Drill Down

```python
# Get the rows that failed
bad_amounts = dg.failures("amount")
print(f"Null amounts: {len(bad_amounts[bad_amounts['amount'].isna()])}")
print(f"Outliers: {len(bad_amounts[bad_amounts['amount'] > 10000])}")

# See the actual outlier values
print(bad_amounts[bad_amounts["amount"] > 10000][["order_id", "amount", "order_date"]])
```

### 5. Fix Before Modeling

```python
# Drop nulls in amount
df = df.dropna(subset=["amount"])

# Cap outliers
df.loc[df["amount"] > 10000, "amount"] = 10000

# Re-validate
dg = connect(df)
result = dg.expect({
    "amount": {"not_null": True, "min": 0, "max": 10000},
})
assert result.passed  # ✓ Now passes
```

---

## Key Features for Notebooks

### Quality Score

Every profile generates a 0-100 quality score:

```python
profile = dg.profile()
print(f"Quality Score: {profile.score}/100")
```

| Score   | Meaning                                        |
|---------|------------------------------------------------|
| 90-100  | Clean data. Minor issues at most.              |
| 70-89   | Usable, but check nulls and outliers.          |
| 50-69   | Significant issues. Clean before modeling.     |
| 0-49    | Major problems. Investigate data source.       |

### PII Detection

DuckGuard automatically flags columns that look like personal data:

```python
profile = dg.profile()
pii = profile.pii_columns()
print(pii)
# ['email', 'phone', 'ip_address']
```

!!! warning "PII in competition data"
    If you find PII in a Kaggle dataset, consider:

    - **Don't include PII as features** — it won't generalize
    - **Hash or drop PII columns** before training
    - **Report to dataset owner** if PII shouldn't be public

### Anomaly Detection

Spot statistical anomalies without manual investigation:

```python
anomalies = dg.detect_anomalies()
anomalies.show()
```

```
Anomalies Detected:
  amount: 3 values > 5σ from mean (likely data entry errors)
  order_date: 17 dates in the future (data collection issue)
  quantity: 1 negative value (should be ≥ 1)
```

---

## Competition Notebook Pattern

Add to your competition notebook in 3 lines:

```python
# Add this at the top of any competition notebook
!pip install duckguard -q
from duckguard import connect
connect(train_df).profile().show()
```

### Full Competition Template

```python
# ── Cell 1: Setup ──────────────────────────────
!pip install duckguard -q

import pandas as pd
from duckguard import connect

# ── Cell 2: Load ───────────────────────────────
train = pd.read_csv("/kaggle/input/competition/train.csv")
test = pd.read_csv("/kaggle/input/competition/test.csv")

# ── Cell 3: Profile Training Data ─────────────
train_dg = connect(train)
train_profile = train_dg.profile()
train_profile.show()

# ── Cell 4: Profile Test Data ─────────────────
test_dg = connect(test)
test_profile = test_dg.profile()
test_profile.show()

# ── Cell 5: Compare Train vs Test ─────────────
from duckguard import compare
diff = compare(train, test)
diff.show()
# Shows: distribution shifts, missing columns, type mismatches

# ── Cell 6: Validate & Clean ──────────────────
result = train_dg.expect({
    "target": {"not_null": True},
    "feature_1": {"not_null": True, "min": 0},
    # ... add checks per column
})

if not result.passed:
    print("Issues found — fix before training:")
    print(result.failures())

# ── Cell 7: Your model code goes here... ──────
```

---

## Working with Different File Formats

DuckGuard handles whatever Kaggle throws at you:

=== "CSV"

    ```python
    df = pd.read_csv("/kaggle/input/data/file.csv")
    dg = connect(df)
    ```

=== "Parquet"

    ```python
    # Direct — no pandas needed
    dg = connect("/kaggle/input/data/file.parquet")
    ```

=== "JSON"

    ```python
    df = pd.read_json("/kaggle/input/data/file.json")
    dg = connect(df)
    ```

=== "Excel"

    ```python
    df = pd.read_excel("/kaggle/input/data/file.xlsx")
    dg = connect(df)
    ```

=== "Multiple Files"

    ```python
    # Profile all CSVs in a directory
    dg = connect("/kaggle/input/data/*.csv")
    dg.profile().show()
    ```

---

## Example: E-Commerce Dataset Analysis

Full walkthrough with a realistic orders dataset:

```python
!pip install duckguard -q

import pandas as pd
from duckguard import connect

# Load
df = pd.read_csv("/kaggle/input/ecommerce/orders.csv")
print(f"Shape: {df.shape}")

# Profile
dg = connect(df)
profile = dg.profile()
profile.show()

# Check for modeling readiness
result = dg.expect({
    "order_id": {"not_null": True, "unique": True},
    "customer_id": {"not_null": True},
    "product_id": {"not_null": True},
    "amount": {"not_null": True, "min": 0},
    "quantity": {"not_null": True, "min": 1},
    "order_date": {"not_null": True},
})

print(f"\nQuality Score: {profile.score}/100")
print(f"Checks Passed: {result.stats['passed']}/{result.stats['total']}")

# Detailed column stats
for col in profile.columns:
    c = profile.columns[col]
    print(f"\n{col}:")
    print(f"  Type: {c.type}, Nulls: {c.null_pct}%, Unique: {c.unique_pct}%")
    if c.is_numeric:
        print(f"  Range: [{c.min}, {c.max}], Mean: {c.mean:.2f}, Std: {c.std:.2f}")

# Fix issues
if not result.passed:
    # Drop rows with null amounts
    df = df.dropna(subset=["amount", "quantity"])
    # Remove impossible values
    df = df[df["amount"] >= 0]
    df = df[df["quantity"] >= 1]

    # Verify fix
    dg = connect(df)
    assert dg.expect({
        "amount": {"not_null": True, "min": 0},
        "quantity": {"not_null": True, "min": 1},
    }).passed

    print(f"\n✓ Cleaned: {len(df)} rows ready for modeling")
```

---

## Tips

!!! tip "Profile before you model"
    Every minute spent on data quality saves an hour of debugging model performance. Profile first. Always.

!!! tip "Compare train and test"
    Distribution shift between train and test is the silent killer. Use `compare()` to catch it before your leaderboard score tanks.

!!! tip "Save your quality checks"
    Export expectations so teammates can reproduce your cleaning steps:

    ```python
    result = dg.expect({...})
    result.save("quality_checks.json")

    # Teammate loads and re-runs
    from duckguard import load_expectations
    result = dg.expect(load_expectations("quality_checks.json"))
    ```

!!! tip "Kaggle kernel resources"
    DuckGuard uses DuckDB under the hood. It's fast and memory-efficient. Profiling a 1M-row DataFrame takes ~2 seconds and ~50MB of RAM on a standard Kaggle kernel.
