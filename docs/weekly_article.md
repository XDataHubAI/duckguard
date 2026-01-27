# Data Quality Testing Shouldn't Require 50 Lines of Boilerplate

Every data engineer knows the pain.

You need to validate that a CSV doesn't have null customer IDs. Simple requirement. But with traditional tools, you're writing something like this:

```python
from great_expectations.data_context import DataContext

context = DataContext()
datasource = context.sources.add_pandas("my_datasource")
data_asset = datasource.add_csv_asset("orders", filepath="orders.csv")
batch_request = data_asset.build_batch_request()
validator = context.get_validator(batch_request=batch_request)
validator.expect_column_values_to_not_be_null("customer_id")
# ... and 40 more lines of ceremony
```

**Why is data quality testing so much harder than unit testing?**

When we test Python code, we just write:

```python
assert result == expected  # Done.
```

I wanted the same simplicity for data. So I built DuckGuard.

---

## 3 Lines. That's It.

```python
from duckguard import connect

orders = connect("orders.csv")
assert orders.customer_id.null_percent == 0
```

No contexts. No datasources. No expectation suites. Just Python assertions you already know.

Need more checks? Keep asserting:

```python
assert orders.amount.between(0, 10000)
assert orders.status.isin(['pending', 'shipped', 'delivered'])
assert orders.email.matches(r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

---

## But Simple Doesn't Mean Limited

DuckGuard packs serious features under that simple API:

**Row-level errors** — See exactly which rows failed:

```python
result = orders.validate()
print(result.failed_rows)  # DataFrame of problematic records
```

**Quality scoring** — ISO 8000-based grades:

```python
score = orders.quality_score()
# {'grade': 'B+', 'completeness': 0.98, 'validity': 0.95, ...}
```

**PII detection** — Auto-find sensitive data:

```python
pii = orders.detect_pii()
# {'email': 'email', 'phone': 'phone_number', 'ssn': 'ssn'}
```

**Anomaly detection** — Catch outliers automatically:

```python
anomalies = orders.amount.detect_anomalies(method='zscore')
```

**Cross-dataset validation** — FK checks, reconciliation:

```python
assert orders.customer_id.references(customers.id)
```

---

## Why It's Fast: DuckDB Under the Hood

Traditional tools load everything into pandas. DuckGuard uses DuckDB's columnar engine:

| Metric | DuckGuard | Great Expectations |
|--------|-----------|-------------------|
| 1GB CSV validation | 4 sec | 45 sec |
| Memory usage | 200 MB | 4 GB |
| Dependencies | 7 | 20+ |

10x faster. 20x less memory. That matters when you're validating data in CI/CD or running hourly checks.

---

## Works Where You Work

```python
# Local files
orders = connect("orders.csv")
orders = connect("data/*.parquet")

# Cloud storage
orders = connect("s3://bucket/orders.csv")

# Databases
orders = connect("snowflake://user:pass@account/db/schema/orders")
orders = connect("bigquery://project/dataset/orders")
```

Plus: Airflow operator, dbt integration, GitHub Actions support, Slack/Teams alerts.

---

## YAML Rules for Teams

Define validation rules declaratively:

```yaml
dataset: orders.csv
checks:
  - column: customer_id
    not_null: true
    unique: true
  - column: amount
    min: 0
    max: 10000
  - column: status
    allowed: [pending, shipped, delivered]
```

```python
from duckguard import validate_yaml
result = validate_yaml("duckguard.yaml")
```

---

## Try It Now

```bash
pip install duckguard
```

```python
from duckguard import connect

data = connect("your_data.csv")
assert data.id.is_unique
assert data.created_at.no_nulls
print(data.quality_score())
```

**Data quality testing should be as simple as pytest. Now it is.**

---

*GitHub: [your-repo-link]*
