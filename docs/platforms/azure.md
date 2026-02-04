---
title: DuckGuard for Azure
description: Integrate data quality into your entire Azure data stack — ADF, Purview, Synapse, Functions, DevOps, Power BI, and Monitor.
---

# DuckGuard for Azure

## One Quality Layer Across Your Entire Azure Stack

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Azure Data │     │  Microsoft  │     │   Azure     │
│   Factory   │────▶│   Fabric    │────▶│   Purview   │
│  (Orchestr) │     │  (Compute)  │     │ (Governance)│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────┬───────┘                   │
                   ▼                           ▼
           ┌──────────────┐          ┌──────────────┐
           │  🦆 DuckGuard │─────────▶│ Quality      │
           │  (Validate)   │          │ Metadata     │
           └──────────────┘          └──────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐
   │ Azure  │ │Power BI│ │ Azure  │
   │Monitor │ │Dashboard│ │DevOps │
   │(Alert) │ │(Report)│ │ (CI)  │
   └────────┘ └────────┘ └────────┘
```

---

## Azure Data Factory Integration

Run DuckGuard as a validation step in your ADF pipelines.

### Option 1: Notebook Activity (Fabric / Synapse)

```python
# ADF Notebook Activity — runs in Fabric or Synapse Spark
%pip install duckguard -q

from duckguard import connect, load_rules, execute_rules

# Load the table that was just written by the previous pipeline step
df = spark.sql("SELECT * FROM staging.orders").toPandas()
data = connect(df)

# Validate
rules = load_rules("/lakehouse/default/Files/duckguard.yaml")
result = execute_rules(rules, data)

# Quality gate — fail the pipeline if quality is below threshold
score = data.score()
if score.grade in ("D", "F"):
    raise Exception(
        f"Data quality gate FAILED: grade={score.grade} ({score.overall:.1f}/100)\n"
        f"Failed checks: {result.failed_count}/{result.total_checks}\n"
        f"{result.summary()}"
    )

print(f"✅ Quality gate passed: {score.grade} ({score.overall:.1f}/100)")
```

### Option 2: Azure Function Activity

Trigger a lightweight Azure Function for validation — no Spark needed:

```python
# Azure Function (HTTP trigger)
import azure.functions as func
import json
from duckguard import connect

def main(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    source = body["source"]  # e.g., "fabric+sql://..."
    table = body["table"]
    token = body["token"]

    data = connect(source, table=table, token=token)
    score = data.score()

    return func.HttpResponse(
        json.dumps({
            "grade": score.grade,
            "overall": score.overall,
            "completeness": score.completeness,
            "uniqueness": score.uniqueness,
            "validity": score.validity,
            "passed": score.grade not in ("D", "F"),
        }),
        mimetype="application/json"
    )
```

ADF calls this via a **Web Activity** — zero compute overhead, scales to zero.

### Option 3: Custom Activity (Azure Batch)

For large-scale validation on dedicated compute:

```python
# custom_activity.py — runs on Azure Batch via ADF Custom Activity
import sys
from duckguard import connect

source = sys.argv[1]  # Connection string
table = sys.argv[2]   # Table name

data = connect(source, table=table, token=os.environ["FABRIC_TOKEN"])
score = data.score()

# Write results for ADF to pick up
with open("output.json", "w") as f:
    json.dump({"grade": score.grade, "overall": score.overall}, f)

if score.grade in ("D", "F"):
    sys.exit(1)  # Non-zero exit = ADF marks activity as failed
```

---

## Microsoft Purview Integration

Push quality scores into Purview for governance and lineage tracking.

```python
import requests
from duckguard import connect

# Validate data
data = connect("fabric://workspace/lakehouse/Tables/orders", token=token)
score = data.score()
profile = AutoProfiler().profile(data)

# Push quality metadata to Purview via REST API
purview_url = "https://your-purview.purview.azure.com"
headers = {
    "Authorization": f"Bearer {purview_token}",
    "Content-Type": "application/json",
}

# Update asset with quality annotations
quality_metadata = {
    "typeName": "DataSet",
    "attributes": {
        "qualifiedName": "fabric://workspace/lakehouse/Tables/orders",
        "duckguard_quality_grade": score.grade,
        "duckguard_quality_score": score.overall,
        "duckguard_completeness": score.completeness,
        "duckguard_uniqueness": score.uniqueness,
        "duckguard_validity": score.validity,
        "duckguard_last_checked": datetime.utcnow().isoformat(),
        "duckguard_row_count": data.row_count,
        "duckguard_pii_columns": str(analysis.pii_columns),
    }
}

requests.put(
    f"{purview_url}/catalog/api/atlas/v2/entity",
    headers=headers,
    json={"entity": quality_metadata}
)
```

!!! tip "Governance Dashboard"
    Once quality scores are in Purview, you can build a governance dashboard showing quality trends across all your data assets.

---

## Azure Monitor & Alerting

Push quality metrics to Azure Monitor for dashboards and alerts.

```python
from opencensus.ext.azure import metrics_exporter
from duckguard import connect

# Set up Azure Monitor exporter
exporter = metrics_exporter.new_metrics_exporter(
    connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
)

# Validate
data = connect("fabric://workspace/lakehouse/Tables/orders", token=token)
score = data.score()

# Push custom metrics
exporter.export_metrics([
    {"name": "duckguard/quality_score", "value": score.overall,
     "dimensions": {"table": "orders", "grade": score.grade}},
    {"name": "duckguard/completeness", "value": score.completeness,
     "dimensions": {"table": "orders"}},
])
```

### Alert Rules

Set up Azure Monitor alerts:
- **Quality drop**: Alert when `duckguard/quality_score` drops below 70
- **PII exposure**: Alert when new PII columns are detected
- **Freshness**: Alert when data is stale (via DuckGuard freshness monitor)

---

## Power BI Integration

### Python Visual

Add a DuckGuard quality scorecard directly in Power BI:

```python
# Power BI Python visual script
# Dataset is automatically available as 'dataset'
from duckguard import connect

data = connect(dataset)  # Power BI passes the DataFrame
score = data.score()

import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 4, figsize=(12, 3))
dims = [
    ("Completeness", score.completeness),
    ("Uniqueness", score.uniqueness),
    ("Validity", score.validity),
    ("Consistency", score.consistency),
]
colors = ["#2ecc71" if v >= 80 else "#f39c12" if v >= 60 else "#e74c3c" for _, v in dims]

for ax, (name, value), color in zip(axes, dims, colors):
    ax.barh([name], [value], color=color)
    ax.set_xlim(0, 100)
    ax.text(value + 2, 0, f"{value:.0f}%", va="center", fontweight="bold")
    ax.set_title(name, fontsize=10)

plt.suptitle(f"Quality Grade: {score.grade} ({score.overall:.0f}/100)", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.show()
```

### Dataflow Integration

Run DuckGuard in a Power BI Dataflow (Gen2) Python step to validate before loading into the semantic model.

---

## Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'

  - script: pip install duckguard[fabric]
    displayName: 'Install DuckGuard'

  - script: |
      python -c "
      import os
      from duckguard import connect

      data = connect(
          'fabric+sql://$(FABRIC_SERVER)',
          table='orders',
          database='$(FABRIC_DATABASE)',
          token=os.environ['FABRIC_TOKEN'],
      )
      score = data.score()
      print(f'Quality: {score.grade} ({score.overall:.1f}/100)')
      assert score.grade not in ('D', 'F'), f'Quality gate failed: {score.grade}'
      "
    displayName: 'Data Quality Gate'
    env:
      FABRIC_TOKEN: $(FABRIC_TOKEN)
```

---

## ADLS Gen2 / Blob Storage

DuckGuard reads Parquet and Delta files directly from Azure storage:

```python
from duckguard import connect

# ADLS Gen2
data = connect("abfss://container@account.dfs.core.windows.net/path/orders.parquet")

# Azure Blob Storage
data = connect("az://container/orders.parquet")

# With SAS token
data = connect(
    "az://container/orders.parquet",
    azure_storage_connection_string="DefaultEndpointsProtocol=https;..."
)
```

!!! info "Authentication"
    DuckDB supports Azure auth via:

    - `AZURE_STORAGE_CONNECTION_STRING` environment variable
    - `AZURE_STORAGE_ACCOUNT_NAME` + `AZURE_STORAGE_ACCOUNT_KEY`
    - SAS tokens
    - Azure AD (via `azure-identity`)

---

## Synapse Analytics

```python
# Synapse Dedicated SQL Pool
data = connect(
    "mssql://your-synapse.sql.azuresynapse.net",
    table="orders",
    database="your_pool",
    token="<azure-ad-token>"
)

# Synapse Serverless SQL Pool
data = connect(
    "mssql://your-synapse-ondemand.sql.azuresynapse.net",
    table="orders",
    database="your_db",
    token="<azure-ad-token>"
)
```

---

## Full Azure Architecture Example

A production-grade data quality pipeline:

```
1. ADF Pipeline triggers on schedule or event
2. Data lands in Fabric Lakehouse (Bronze layer)
3. Notebook Activity runs DuckGuard validation
4. Quality scores pushed to Purview (governance)
5. Metrics pushed to Azure Monitor (alerting)
6. If grade >= B: promote to Silver layer
7. If grade < B: quarantine + notify via Teams webhook
8. Power BI dashboard shows quality trends
```

```python
# Step 3-7 in a single notebook:
from duckguard import connect, load_rules, execute_rules
from duckguard.notifications import TeamsNotifier

# Validate
data = connect(df)
score = data.score()
rules = load_rules("duckguard.yaml")
result = execute_rules(rules, data)

# Push to Purview (step 4)
push_to_purview(score, table_name="orders")

# Push to Monitor (step 5)
push_to_monitor(score, table_name="orders")

# Quality gate (steps 6-7)
if score.grade in ("A", "B", "C"):
    spark.sql("INSERT INTO silver.orders SELECT * FROM bronze.orders")
    print(f"✅ Promoted to Silver: {score.grade}")
else:
    spark.sql("INSERT INTO quarantine.orders SELECT * FROM bronze.orders")
    teams = TeamsNotifier(webhook_url=os.environ["TEAMS_WEBHOOK"])
    teams.send(f"⚠️ Quality gate failed for orders: {score.grade} ({score.overall:.0f}/100)")
```

---

## Install

```bash
# Fabric SQL endpoint
pip install duckguard[fabric]

# Full Azure stack (Fabric + ADLS + SQL Server)
pip install duckguard[fabric,sqlserver]

# Everything
pip install duckguard[all]
```
