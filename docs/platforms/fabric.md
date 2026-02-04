---
title: DuckGuard for Microsoft Fabric
description: Validate Lakehouse and Warehouse data in 3 lines of Python. OneLake direct access, SQL endpoints, and Fabric notebook integration.
---

# DuckGuard for Microsoft Fabric

## Validate your Fabric data in 3 lines of Python

```python
from duckguard import connect

data = connect("fabric://workspace/lakehouse/Tables/orders", token="...")
assert data.customer_id.is_not_null()
assert data.total_amount.between(0, 10000)
```

No Spark cluster. No complex setup. Runs from a Fabric notebook, your laptop, or CI.

---

## The Problem

Data quality in Microsoft Fabric today means:

- **PySpark checks** — spin up a cluster, write SQL with extra steps, no reusable framework
- **Great Expectations** — 50+ lines of config before your first check, needs a running compute
- **Manual SQL** — write T-SQL queries against the SQL endpoint, no automation, no scoring

DuckGuard connects directly to your Lakehouse or Warehouse. One API, 3 lines, any table.

---

## Quick Start

```bash
pip install duckguard[fabric]
```

### Option 1: OneLake (Direct File Access)

Access Parquet and Delta tables in your Lakehouse without a SQL endpoint:

```python
from duckguard import connect

# Lakehouse table
data = connect(
    "fabric://my-workspace/my-lakehouse/Tables/orders",
    token="<azure-ad-token>"
)

# Full OneLake path
data = connect(
    "onelake://my-workspace/my-lakehouse.Lakehouse/Files/raw/orders.parquet",
    token="<azure-ad-token>"
)

# Validate
assert data.customer_id.is_not_null()
assert data.total_amount.between(0, 10000)
score = data.score()
print(f"Grade: {score.grade}")
```

### Option 2: SQL Endpoint

Query via T-SQL — works with both Lakehouse and Warehouse:

```python
data = connect(
    "fabric+sql://your-guid.datawarehouse.fabric.microsoft.com",
    table="orders",
    database="my_lakehouse",
    token="<azure-ad-token>"
)
```

### Option 3: Inside a Fabric Notebook

Load via Spark, validate via DuckGuard — no token needed:

```python
# Fabric notebook cell
%pip install duckguard -q

from duckguard import connect

# Load from Lakehouse via Spark
df = spark.sql("SELECT * FROM my_lakehouse.orders").toPandas()
data = connect(df)

# Full quality analysis
score = data.score()
print(f"Quality: {score.grade} ({score.overall:.1f}/100)")
```

---

## Authentication

### In a Fabric Notebook

```python
# Automatic — use mssparkutils
token = mssparkutils.credentials.getToken("pbi")
data = connect("fabric://workspace/lakehouse/Tables/orders", token=token)
```

### From External Environments

```python
# Azure Identity (recommended)
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token(
    "https://analysis.windows.net/powerbi/api/.default"
).token

data = connect("fabric://workspace/lakehouse/Tables/orders", token=token)
```

!!! tip "Environment Variables"
    Set `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_CLIENT_SECRET` for service principal auth, or use managed identity in Azure-hosted environments.

---

## Fabric Pipeline Integration

### Notebook Activity in Data Pipeline

Add a notebook activity that runs quality checks after data loads:

```python
from duckguard import connect, load_rules, execute_rules

# Load from Lakehouse
df = spark.sql("SELECT * FROM my_lakehouse.orders").toPandas()
data = connect(df)

# Validate
rules = load_rules("/lakehouse/default/Files/duckguard.yaml")
result = execute_rules(rules, data)

if not result.passed:
    # Fail the pipeline
    raise Exception(f"Quality check failed: {result.failed_count} failures")

# Log results
print(f"Quality: {data.score().grade}")
print(f"Checks: {result.passed_count}/{result.total_checks} passed")
```

### Auto-Generate Rules

Let DuckGuard analyze your table and generate validation rules:

```python
from duckguard import connect, generate_rules

data = connect(df)
yaml_rules = generate_rules(data, dataset_name="orders")

# Save to Lakehouse Files
with open("/lakehouse/default/Files/duckguard.yaml", "w") as f:
    f.write(yaml_rules)
```

---

## CI/CD Integration

### pytest with Fabric SQL Endpoint

```python
# tests/test_fabric_quality.py
import os
from duckguard import connect

def test_orders_quality():
    orders = connect(
        "fabric+sql://workspace.datawarehouse.fabric.microsoft.com",
        table="orders",
        database="my_lakehouse",
        token=os.environ["FABRIC_TOKEN"],
    )
    assert orders.row_count > 0
    assert orders.order_id.is_not_null()
    assert orders.order_id.is_unique()
    assert orders.total_amount.between(0, 50000)
```

### GitHub Actions

```yaml
name: Fabric Data Quality
on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 8 AM

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install duckguard[fabric]
      - run: pytest tests/test_fabric_quality.py
        env:
          FABRIC_TOKEN: ${{ secrets.FABRIC_TOKEN }}
```

---

## What DuckGuard Gives You on Fabric

| Feature | Raw SQL | PySpark | DuckGuard |
|---------|---------|---------|-----------|
| Lines of code | 10+ per check | 10+ per check | **3** |
| Quality scoring | Manual | Manual | **Built-in (A-F)** |
| PII detection | Manual | Manual | **Automatic** |
| Anomaly detection | Manual | Manual | **7 methods** |
| Data contracts | No | No | **Yes** |
| Schema tracking | No | No | **Yes** |
| Drift detection | No | No | **Yes** |
| Needs Spark cluster | No | **Yes** | **No** |
| pytest integration | No | No | **Yes** |

---

## Next Steps

- 📓 [Fabric Quickstart Notebook](https://github.com/XDataHubAI/duckguard/blob/main/examples/fabric_quickstart.ipynb)
- 📚 [Full Documentation](https://xdatahubai.github.io/duckguard/)
- 🔌 [All Connectors](../connectors/overview.md)
- 🤖 [AI Features](../guide/ai-features.md)
