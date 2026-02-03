"""dbt Integration for DuckGuard.

Export DuckGuard validation rules as dbt tests and schema.yml configurations.

Usage:
    from duckguard import load_rules
    from duckguard.integrations import dbt

    # Load existing DuckGuard rules
    rules = load_rules("duckguard.yaml")

    # Export to dbt schema.yml format
    dbt.export_to_schema(rules, "models/schema.yml")

    # Generate dbt singular tests
    dbt.generate_singular_tests(rules, "tests/")

    # Convert rules to dbt test format
    tests = dbt.rules_to_dbt_tests(rules)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from duckguard.rules.loader import load_rules
from duckguard.rules.schema import Check, CheckType, RuleSet

# Mapping from DuckGuard check types to dbt generic tests
DBT_TEST_MAPPING = {
    CheckType.NOT_NULL: "not_null",
    CheckType.UNIQUE: "unique",
    CheckType.NO_DUPLICATES: "unique",
    CheckType.ALLOWED_VALUES: "accepted_values",
    CheckType.ISIN: "accepted_values",
}

# dbt test configurations for different check types
DBT_TEST_CONFIGS = {
    "not_null": lambda check: {},
    "unique": lambda check: {},
    "accepted_values": lambda check: {"values": check.value if isinstance(check.value, list) else [check.value]},
}


def rules_to_dbt_tests(ruleset: RuleSet) -> dict[str, Any]:
    """Convert a DuckGuard RuleSet to dbt test format.

    Args:
        ruleset: DuckGuard RuleSet

    Returns:
        Dictionary in dbt schema.yml format
    """
    columns = []

    for col_name, col_rules in ruleset.columns.items():
        column_tests = []

        for check in col_rules.checks:
            if not check.enabled:
                continue

            dbt_test = _check_to_dbt_test(check)
            if dbt_test:
                column_tests.append(dbt_test)

        if column_tests:
            columns.append({
                "name": col_name,
                "description": col_rules.description or "",
                "tests": column_tests,
            })

    # Build model configuration
    model = {
        "name": ruleset.name or "validated_model",
        "description": ruleset.description or "Model validated by DuckGuard",
        "columns": columns,
    }

    # Add table-level tests if any
    model_tests = []
    for check in ruleset.table.checks:
        if not check.enabled:
            continue

        if check.type == CheckType.ROW_COUNT:
            # dbt-utils row_count test
            model_tests.append({
                "dbt_utils.expression_is_true": {
                    "expression": f"count(*) {check.operator} {check.value}"
                }
            })

    if model_tests:
        model["tests"] = model_tests

    return {"models": [model]}


def _check_to_dbt_test(check) -> dict[str, Any] | str | None:
    """Convert a single DuckGuard check to a dbt test.

    Args:
        check: DuckGuard Check object

    Returns:
        dbt test configuration (string for simple tests, dict for configured)
    """
    # Simple mapping for basic tests
    if check.type in DBT_TEST_MAPPING:
        test_name = DBT_TEST_MAPPING[check.type]
        config_fn = DBT_TEST_CONFIGS.get(test_name)

        if config_fn:
            config = config_fn(check)
            if config:
                return {test_name: config}
            return test_name

    # Handle range/between checks
    if check.type in (CheckType.BETWEEN, CheckType.RANGE):
        if isinstance(check.value, (list, tuple)) and len(check.value) == 2:
            min_val, max_val = check.value
            return {
                "dbt_utils.expression_is_true": {
                    "expression": f"{{{{ column_name }}}} >= {min_val} and {{{{ column_name }}}} <= {max_val}"
                }
            }

    # Handle min/max checks
    if check.type == CheckType.MIN:
        return {
            "dbt_utils.expression_is_true": {
                "expression": f"{{{{ column_name }}}} >= {check.value}"
            }
        }

    if check.type == CheckType.MAX:
        return {
            "dbt_utils.expression_is_true": {
                "expression": f"{{{{ column_name }}}} <= {check.value}"
            }
        }

    # Handle positive/negative/non_negative
    if check.type == CheckType.POSITIVE:
        return {
            "dbt_utils.expression_is_true": {
                "expression": "{{ column_name }} > 0"
            }
        }

    if check.type == CheckType.NON_NEGATIVE:
        return {
            "dbt_utils.expression_is_true": {
                "expression": "{{ column_name }} >= 0"
            }
        }

    if check.type == CheckType.NEGATIVE:
        return {
            "dbt_utils.expression_is_true": {
                "expression": "{{ column_name }} < 0"
            }
        }

    # Handle pattern/regex checks
    if check.type == CheckType.PATTERN:
        return {
            "dbt_utils.expression_is_true": {
                "expression": f"REGEXP_MATCHES({{{{ column_name }}}}, '{check.value}')"
            }
        }

    # Handle length checks
    if check.type == CheckType.LENGTH:
        if isinstance(check.value, (list, tuple)) and len(check.value) == 2:
            min_len, max_len = check.value
            return {
                "dbt_utils.expression_is_true": {
                    "expression": f"LENGTH({{{{ column_name }}}}) >= {min_len} AND LENGTH({{{{ column_name }}}}) <= {max_len}"
                }
            }

    if check.type == CheckType.MIN_LENGTH:
        return {
            "dbt_utils.expression_is_true": {
                "expression": f"LENGTH({{{{ column_name }}}}) >= {check.value}"
            }
        }

    if check.type == CheckType.MAX_LENGTH:
        return {
            "dbt_utils.expression_is_true": {
                "expression": f"LENGTH({{{{ column_name }}}}) <= {check.value}"
            }
        }

    # Handle null percentage checks
    if check.type == CheckType.NULL_PERCENT:
        # This requires a singular test
        return None

    return None


def export_to_schema(
    rules: RuleSet | str,
    output_path: str | Path,
    merge: bool = True
) -> Path:
    """Export DuckGuard rules to a dbt schema.yml file.

    Args:
        rules: RuleSet or path to duckguard.yaml file
        output_path: Path to output schema.yml file
        merge: If True, merge with existing file (default: True)

    Returns:
        Path to created schema.yml file
    """
    if isinstance(rules, str):
        rules = load_rules(rules)

    output_path = Path(output_path)
    dbt_config = rules_to_dbt_tests(rules)

    # Merge with existing file if it exists
    if merge and output_path.exists():
        with open(output_path) as f:
            existing = yaml.safe_load(f) or {}

        if "models" in existing:
            # Merge models by name
            existing_models = {m["name"]: m for m in existing.get("models", [])}
            for model in dbt_config["models"]:
                if model["name"] in existing_models:
                    # Merge columns
                    existing_cols = {c["name"]: c for c in existing_models[model["name"]].get("columns", [])}
                    for col in model.get("columns", []):
                        if col["name"] in existing_cols:
                            # Merge tests
                            existing_tests = existing_cols[col["name"]].get("tests", [])
                            new_tests = col.get("tests", [])
                            merged_tests = _merge_tests(existing_tests, new_tests)
                            existing_cols[col["name"]]["tests"] = merged_tests
                        else:
                            existing_cols[col["name"]] = col
                    existing_models[model["name"]]["columns"] = list(existing_cols.values())
                else:
                    existing_models[model["name"]] = model
            dbt_config["models"] = list(existing_models.values())

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(dbt_config, f, default_flow_style=False, sort_keys=False)

    return output_path


def _merge_tests(existing: list, new: list) -> list:
    """Merge test lists, avoiding duplicates."""
    result = list(existing)
    existing_names = set()

    for test in existing:
        if isinstance(test, str):
            existing_names.add(test)
        elif isinstance(test, dict):
            existing_names.update(test.keys())

    for test in new:
        if isinstance(test, str):
            if test not in existing_names:
                result.append(test)
        elif isinstance(test, dict):
            test_name = list(test.keys())[0]
            if test_name not in existing_names:
                result.append(test)

    return result


def generate_singular_tests(
    rules: RuleSet | str,
    output_dir: str | Path,
    table_name: str | None = None
) -> list[Path]:
    """Generate dbt singular test files from DuckGuard rules.

    Singular tests are good for complex validations that can't be expressed
    as generic tests.

    Args:
        rules: RuleSet or path to duckguard.yaml file
        output_dir: Directory to write test files
        table_name: Table name to use in tests (defaults to rules.name)

    Returns:
        List of created test file paths
    """
    if isinstance(rules, str):
        rules = load_rules(rules)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table = table_name or rules.name or "source_table"
    created_files = []

    # Generate tests for checks that can't be generic tests
    for col_name, col_rules in rules.columns.items():
        for check in col_rules.checks:
            if not check.enabled:
                continue

            # Generate singular test for complex checks
            if check.type == CheckType.NULL_PERCENT:
                test_sql = _generate_null_percent_test(table, col_name, check)
                if test_sql:
                    filename = f"test_{table}_{col_name}_null_percent.sql"
                    test_path = output_dir / filename
                    with open(test_path, "w") as f:
                        f.write(test_sql)
                    created_files.append(test_path)

            if check.type == CheckType.UNIQUE_PERCENT:
                test_sql = _generate_unique_percent_test(table, col_name, check)
                if test_sql:
                    filename = f"test_{table}_{col_name}_unique_percent.sql"
                    test_path = output_dir / filename
                    with open(test_path, "w") as f:
                        f.write(test_sql)
                    created_files.append(test_path)

    return created_files


def _generate_null_percent_test(table: str, column: str, check) -> str:
    """Generate SQL for null percentage test."""
    operator = check.operator or "<="
    threshold = check.value

    return f"""-- Test that {column} null percentage is {operator} {threshold}%
-- Generated by DuckGuard

SELECT
    COUNT(*) FILTER (WHERE "{column}" IS NULL) * 100.0 / COUNT(*) as null_pct
FROM {{{{ ref('{table}') }}}}
HAVING COUNT(*) FILTER (WHERE "{column}" IS NULL) * 100.0 / COUNT(*) {_invert_operator(operator)} {threshold}
"""


def _generate_unique_percent_test(table: str, column: str, check) -> str:
    """Generate SQL for unique percentage test."""
    operator = check.operator or ">="
    threshold = check.value

    return f"""-- Test that {column} unique percentage is {operator} {threshold}%
-- Generated by DuckGuard

SELECT
    COUNT(DISTINCT "{column}") * 100.0 / COUNT(*) as unique_pct
FROM {{{{ ref('{table}') }}}}
WHERE "{column}" IS NOT NULL
HAVING COUNT(DISTINCT "{column}") * 100.0 / COUNT(*) {_invert_operator(operator)} {threshold}
"""


def _invert_operator(op: str) -> str:
    """Invert comparison operator for failure condition."""
    inversions = {
        ">=": "<",
        ">": "<=",
        "<=": ">",
        "<": ">=",
        "=": "!=",
        "==": "!=",
        "!=": "=",
    }
    return inversions.get(op, op)


def import_from_dbt(schema_path: str | Path) -> RuleSet:
    """Import dbt schema.yml tests as DuckGuard rules.

    Args:
        schema_path: Path to dbt schema.yml file

    Returns:
        DuckGuard RuleSet
    """
    from duckguard.rules.schema import ColumnRules, RuleSet, TableRules

    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    models = schema.get("models", [])
    if not models:
        raise ValueError("No models found in schema.yml")

    # Use first model
    model = models[0]

    columns = {}
    for col_def in model.get("columns", []):
        col_name = col_def["name"]
        checks = []

        for test in col_def.get("tests", []):
            check = _dbt_test_to_check(test)
            if check:
                checks.append(check)

        if checks:
            columns[col_name] = ColumnRules(
                name=col_name,
                description=col_def.get("description", ""),
                checks=checks,
            )

    return RuleSet(
        name=model.get("name", "imported_rules"),
        description=model.get("description", "Imported from dbt"),
        table=TableRules(),
        columns=columns,
    )


def _dbt_test_to_check(test) -> Check | None:
    """Convert a dbt test to a DuckGuard Check."""

    if isinstance(test, str):
        if test == "not_null":
            return Check(type=CheckType.NOT_NULL)
        if test == "unique":
            return Check(type=CheckType.UNIQUE)
        return None

    if isinstance(test, dict):
        test_name = list(test.keys())[0]
        config = test[test_name]

        if test_name == "not_null":
            return Check(type=CheckType.NOT_NULL)
        if test_name == "unique":
            return Check(type=CheckType.UNIQUE)
        if test_name == "accepted_values":
            values = config.get("values", [])
            return Check(type=CheckType.ALLOWED_VALUES, value=values)

    return None
