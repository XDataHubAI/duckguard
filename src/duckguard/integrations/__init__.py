"""
DuckGuard Integrations - Connect with dbt, Airflow, and more.

Usage:
    from duckguard.integrations import dbt

    # Export DuckGuard rules to dbt tests
    dbt.export_to_schema("duckguard.yaml", "models/schema.yml")

    # Generate dbt generic tests from rules
    tests = dbt.rules_to_dbt_tests(rules)

    # Airflow integration (requires apache-airflow)
    from duckguard.integrations.airflow import DuckGuardOperator

    check_task = DuckGuardOperator(
        task_id="check_quality",
        source="s3://bucket/data.parquet",
        rules="rules.yaml",
    )
"""

from duckguard.integrations import dbt

# Airflow integration is optional - only import if available
try:
    from duckguard.integrations import airflow
except ImportError:
    airflow = None  # type: ignore[assignment]

__all__ = ["dbt", "airflow"]
