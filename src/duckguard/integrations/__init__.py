"""
DuckGuard Integrations - Connect with dbt, Great Expectations, and more.

Usage:
    from duckguard.integrations import dbt

    # Export DuckGuard rules to dbt tests
    dbt.export_to_schema("duckguard.yaml", "models/schema.yml")

    # Generate dbt generic tests from rules
    tests = dbt.rules_to_dbt_tests(rules)
"""

from duckguard.integrations import dbt

__all__ = ["dbt"]
