# Airflow Integration

Add data quality gates to Airflow DAGs using DuckGuard.

## Quick Start

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def validate_orders():
    from duckguard import connect

    data = connect("s3://datalake/orders/orders.parquet")
    assert data.row_count > 0
    assert data.order_id.null_percent == 0
    assert data.amount.between(0, 100000)

    score = data.score()
    if score.overall < 80:
        raise ValueError(f"Quality score {score.overall:.0f} below threshold")

with DAG("orders_quality", start_date=datetime(2024, 1, 1), schedule="@daily"):
    validate = PythonOperator(
        task_id="validate_orders",
        python_callable=validate_orders,
    )
```

## Quality Gate Pattern

Use DuckGuard as a gate between pipeline stages:

```python
def extract():
    """Extract data from source."""
    ...

def validate():
    """Quality gate — fails the DAG if data is bad."""
    from duckguard import connect, load_rules, execute_rules

    data = connect("s3://staging/orders.parquet")
    rules = load_rules("/opt/airflow/duckguard.yaml")
    result = execute_rules(rules, dataset=data)

    if not result.passed:
        raise ValueError(
            f"Quality check failed: {result.failed_count}/{result.total_checks} "
            f"checks failed (score: {result.quality_score:.0f}%)"
        )

def transform():
    """Transform data — only runs if validation passes."""
    ...

with DAG("etl_pipeline", schedule="@daily", start_date=datetime(2024, 1, 1)):
    extract_task = PythonOperator(task_id="extract", python_callable=extract)
    validate_task = PythonOperator(task_id="validate", python_callable=validate)
    transform_task = PythonOperator(task_id="transform", python_callable=transform)

    extract_task >> validate_task >> transform_task
```

## Contract Validation

```python
def validate_contract():
    from duckguard import load_contract, validate_contract

    contract = load_contract("/opt/airflow/contracts/orders.contract.yaml")
    result = validate_contract(contract, "s3://datalake/orders.parquet")

    if not result.passed:
        raise ValueError(result.summary())
```

## Freshness Checks

```python
def check_freshness():
    from duckguard import connect
    from datetime import timedelta

    data = connect("s3://datalake/orders.parquet")
    if not data.is_fresh(timedelta(hours=6)):
        raise ValueError(f"Data is stale: {data.freshness.age_human}")
```

## Anomaly Detection

```python
def check_anomalies():
    from duckguard import connect
    from duckguard.anomaly import detect_anomalies

    data = connect("s3://datalake/metrics.parquet")
    report = detect_anomalies(data, method="zscore")

    if report.has_anomalies:
        raise ValueError(f"Anomalies detected: {report.anomaly_count}")
```

## Generate Reports

```python
def generate_report():
    from duckguard import connect
    from duckguard.rules import load_rules, execute_rules
    from duckguard.reports import HTMLReporter

    data = connect("s3://datalake/orders.parquet")
    rules = load_rules("/opt/airflow/duckguard.yaml")
    result = execute_rules(rules, dataset=data)

    reporter = HTMLReporter()
    reporter.generate(result, "/opt/airflow/reports/quality.html")
```

## BashOperator Alternative

```python
validate = BashOperator(
    task_id="validate",
    bash_command="duckguard check s3://datalake/orders.parquet --config duckguard.yaml",
)
```

The CLI exits with code 1 on failure, which fails the Airflow task.

## Tips

- Install DuckGuard in your Airflow worker image: `pip install duckguard`
- Store YAML rules and contracts alongside your DAGs
- Use `PythonOperator` for flexibility, `BashOperator` for simplicity
- Set `retries=0` on quality gate tasks — don't retry bad data
