"""YAML rule loader for DuckGuard.

Parses YAML configuration files into RuleSet objects.
Supports a simple, readable syntax without complex DSL.

Example YAML:
    source: data/orders.csv

    checks:
      customer_id:
        - not_null
        - unique

      amount:
        - positive
        - range: [0, 10000]

      email:
        - pattern: email
        - null_percent: < 5%

      status:
        - allowed_values: [pending, shipped, delivered]

    table:
      - row_count: "> 0"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from duckguard.rules.schema import (
    BUILTIN_PATTERNS,
    Check,
    CheckType,
    ColumnRules,
    RuleSet,
    Severity,
    TableRules,
)


class RuleParseError(Exception):
    """Raised when YAML rule parsing fails."""

    def __init__(self, message: str, location: str | None = None):
        self.location = location
        full_message = f"{message}" if not location else f"{message} (at {location})"
        super().__init__(full_message)


def load_rules(path: str | Path) -> RuleSet:
    """Load rules from a YAML file.

    Args:
        path: Path to the YAML file

    Returns:
        Parsed RuleSet

    Raises:
        FileNotFoundError: If the file doesn't exist
        RuleParseError: If the YAML is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    return load_rules_from_string(content, source_file=str(path))


def load_rules_from_string(content: str, source_file: str | None = None) -> RuleSet:
    """Load rules from a YAML string.

    Args:
        content: YAML content as string
        source_file: Optional source file path for error messages

    Returns:
        Parsed RuleSet
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise RuleParseError(f"Invalid YAML: {e}", source_file)

    if not data:
        return RuleSet()

    if not isinstance(data, dict):
        raise RuleParseError("YAML root must be a mapping", source_file)

    return _parse_ruleset(data, source_file)


def _parse_ruleset(data: dict[str, Any], source_file: str | None = None) -> RuleSet:
    """Parse a dictionary into a RuleSet."""
    # Support both "name:" and "dataset:" for the ruleset name
    name = data.get("name") or data.get("dataset")

    ruleset = RuleSet(
        source=data.get("source"),
        name=name,
        version=str(data.get("version", "1.0")),
        description=data.get("description"),
        settings=data.get("settings", {}),
    )

    # Check for simple "rules:" list format (like Soda-style)
    rules_data = data.get("rules", [])
    if rules_data and isinstance(rules_data, list):
        for rule_expr in rules_data:
            if isinstance(rule_expr, str):
                ruleset.add_simple_check(rule_expr)
                # Also parse into structured format for execution
                _parse_simple_rule_expression(ruleset, rule_expr, source_file)

    # Parse column checks (structured format)
    checks_data = data.get("checks", {})
    if isinstance(checks_data, dict):
        for col_name, col_checks in checks_data.items():
            column_rules = _parse_column_rules(col_name, col_checks, source_file)
            ruleset.columns[col_name] = column_rules

    # Parse table-level checks
    table_data = data.get("table", [])
    if table_data:
        ruleset.table = _parse_table_rules(table_data, source_file)

    return ruleset


def _parse_simple_rule_expression(
    ruleset: RuleSet,
    expr: str,
    source_file: str | None = None
) -> None:
    """Parse a simple rule expression like 'order_id is not null' into structured checks."""
    expr = expr.strip()

    # Table-level rules
    if expr.startswith("row_count"):
        # Parse: "row_count > 0", "row_count < 1000000"
        match = re.match(r"row_count\s*([<>=!]+)\s*(\d+)", expr)
        if match:
            operator = match.group(1)
            value = int(match.group(2))
            ruleset.add_table_check(CheckType.ROW_COUNT, value=value, operator=operator)
        return

    # Column-level rules - parse various patterns
    # Pattern: "column_name is not null"
    match = re.match(r"(\w+)\s+is\s+not\s+null", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        ruleset.add_column_check(col_name, CheckType.NOT_NULL)
        return

    # Pattern: "column_name is unique"
    match = re.match(r"(\w+)\s+is\s+unique", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        ruleset.add_column_check(col_name, CheckType.UNIQUE)
        return

    # Pattern: "column_name >= value" or "column_name > value"
    match = re.match(r"(\w+)\s*([<>=!]+)\s*(-?[\d.]+)", expr)
    if match:
        col_name = match.group(1)
        operator = match.group(2)
        value = float(match.group(3)) if "." in match.group(3) else int(match.group(3))

        if operator == ">=":
            ruleset.add_column_check(col_name, CheckType.MIN, value=value)
        elif operator == ">":
            ruleset.add_column_check(col_name, CheckType.MIN, value=value, operator=">")
        elif operator == "<=":
            ruleset.add_column_check(col_name, CheckType.MAX, value=value)
        elif operator == "<":
            ruleset.add_column_check(col_name, CheckType.MAX, value=value, operator="<")
        return

    # Pattern: "column_name in ['a', 'b', 'c']"
    match = re.match(r"(\w+)\s+in\s+\[(.+)\]", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        values_str = match.group(2)
        # Parse the values list
        values = [v.strip().strip("'\"") for v in values_str.split(",")]
        ruleset.add_column_check(col_name, CheckType.ALLOWED_VALUES, value=values)
        return

    # Pattern: "column_name matches 'pattern'"
    match = re.match(r"(\w+)\s+matches\s+['\"](.+)['\"]", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        pattern = match.group(2)
        ruleset.add_column_check(col_name, CheckType.PATTERN, value=pattern)
        return

    # Pattern: "column_name between min and max"
    match = re.match(r"(\w+)\s+between\s+(-?[\d.]+)\s+and\s+(-?[\d.]+)", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        min_val = float(match.group(2)) if "." in match.group(2) else int(match.group(2))
        max_val = float(match.group(3)) if "." in match.group(3) else int(match.group(3))
        ruleset.add_column_check(col_name, CheckType.BETWEEN, value=[min_val, max_val])
        return

    # Pattern: "column_name null_percent < 5"
    match = re.match(r"(\w+)\s+null_percent\s*([<>=!]+)\s*(\d+)", expr, re.IGNORECASE)
    if match:
        col_name = match.group(1)
        operator = match.group(2)
        value = int(match.group(3))
        ruleset.add_column_check(col_name, CheckType.NULL_PERCENT, value=value, operator=operator)
        return


def _parse_column_rules(
    col_name: str,
    checks: list[Any],
    source_file: str | None = None
) -> ColumnRules:
    """Parse column-level rules."""
    column_rules = ColumnRules(name=col_name)

    if not checks:
        return column_rules

    if not isinstance(checks, list):
        checks = [checks]

    for check_item in checks:
        check = _parse_check(check_item, f"checks.{col_name}", source_file)
        if check:
            column_rules.checks.append(check)

    return column_rules


def _parse_table_rules(
    checks: list[Any],
    source_file: str | None = None
) -> TableRules:
    """Parse table-level rules."""
    table_rules = TableRules()

    if not isinstance(checks, list):
        checks = [checks]

    for check_item in checks:
        check = _parse_check(check_item, "table", source_file)
        if check:
            table_rules.checks.append(check)

    return table_rules


def _parse_check(
    check_item: Any,
    location: str,
    source_file: str | None = None
) -> Check | None:
    """Parse a single check from various formats.

    Supports:
        - Simple string: "not_null"
        - Dict with value: {"range": [0, 100]}
        - Dict with operator: {"null_percent": "< 5"}
        - Dict with params: {"pattern": {"value": "email", "severity": "warning"}}
    """
    if check_item is None:
        return None

    # Simple string format: "not_null"
    if isinstance(check_item, str):
        return _parse_simple_check(check_item)

    # Dictionary format
    if isinstance(check_item, dict):
        return _parse_dict_check(check_item, location, source_file)

    raise RuleParseError(
        f"Invalid check format: {check_item}",
        f"{source_file}:{location}" if source_file else location
    )


def _parse_simple_check(check_str: str) -> Check:
    """Parse a simple string check like 'not_null' or 'unique'."""
    check_str = check_str.lower().strip()

    # Handle simple check types
    simple_checks = {
        "not_null": CheckType.NOT_NULL,
        "notnull": CheckType.NOT_NULL,
        "required": CheckType.NOT_NULL,
        "unique": CheckType.UNIQUE,
        "no_duplicates": CheckType.NO_DUPLICATES,
        "positive": CheckType.POSITIVE,
        "negative": CheckType.NEGATIVE,
        "non_negative": CheckType.NON_NEGATIVE,
        "nonnegative": CheckType.NON_NEGATIVE,
    }

    if check_str in simple_checks:
        return Check(type=simple_checks[check_str])

    # Try to parse as CheckType
    try:
        check_type = CheckType(check_str)
        return Check(type=check_type)
    except ValueError:
        raise RuleParseError(f"Unknown check type: {check_str}")


def _parse_dict_check(
    check_dict: dict[str, Any],
    location: str,
    source_file: str | None = None
) -> Check:
    """Parse a dictionary check."""
    if len(check_dict) == 0:
        raise RuleParseError("Empty check definition", location)

    # Get the check type (first key)
    check_type_str = list(check_dict.keys())[0]
    check_value = check_dict[check_type_str]

    # Normalize check type
    check_type_str_normalized = check_type_str.lower().replace("-", "_")

    # Map common aliases
    type_aliases = {
        "not_null": "not_null",
        "notnull": "not_null",
        "required": "not_null",
        "unique": "unique",
        "range": "between",
        "between": "between",
        "min": "min",
        "max": "max",
        "pattern": "pattern",
        "regex": "pattern",
        "allowed_values": "allowed_values",
        "isin": "allowed_values",
        "in": "allowed_values",
        "values": "allowed_values",
        "length": "length",
        "min_length": "min_length",
        "max_length": "max_length",
        "type": "type",
        "semantic_type": "semantic_type",
        "null_percent": "null_percent",
        "unique_percent": "unique_percent",
        "row_count": "row_count",
        "positive": "positive",
        "negative": "negative",
        "non_negative": "non_negative",
        "anomaly": "anomaly",
        "custom_sql": "custom_sql",
        "sql": "custom_sql",
    }

    if check_type_str_normalized in type_aliases:
        check_type_str_normalized = type_aliases[check_type_str_normalized]

    try:
        check_type = CheckType(check_type_str_normalized)
    except ValueError:
        raise RuleParseError(f"Unknown check type: {check_type_str}", location)

    # Parse the value and extract operator if present
    value, operator, params = _parse_check_value(check_type, check_value)

    # Extract severity if specified
    severity = Severity.ERROR
    message = None

    if isinstance(check_value, dict):
        if "severity" in check_value:
            severity = Severity(check_value["severity"].lower())
        if "message" in check_value:
            message = check_value["message"]
        if "params" in check_value:
            params.update(check_value["params"])

    return Check(
        type=check_type,
        value=value,
        operator=operator,
        severity=severity,
        message=message,
        params=params,
    )


def _parse_check_value(
    check_type: CheckType,
    raw_value: Any
) -> tuple[Any, str, dict[str, Any]]:
    """Parse the value portion of a check, extracting operators if present.

    Returns:
        Tuple of (value, operator, extra_params)
    """
    operator = "="
    params: dict[str, Any] = {}

    # Handle None
    if raw_value is None:
        return None, operator, params

    # Handle dict with explicit value
    if isinstance(raw_value, dict):
        if "value" in raw_value:
            raw_value = raw_value["value"]
        elif "min" in raw_value and "max" in raw_value:
            # Range specified as {min: 0, max: 100}
            return [raw_value["min"], raw_value["max"]], operator, params
        elif "method" in raw_value:
            # Anomaly detection params
            params = raw_value.copy()
            return None, operator, params
        else:
            # Pass entire dict as params
            return None, operator, raw_value

    # Handle list (for range, allowed_values)
    if isinstance(raw_value, list):
        return raw_value, operator, params

    # Handle string with operator: "< 5", "> 0", "<= 10%"
    if isinstance(raw_value, str):
        value_str = raw_value.strip()

        # Check for percentage
        is_percent = value_str.endswith("%")
        if is_percent:
            value_str = value_str[:-1].strip()

        # Extract operator
        operator_match = re.match(r"^([<>=!]+)\s*(.+)$", value_str)
        if operator_match:
            operator = operator_match.group(1)
            value_str = operator_match.group(2).strip()

        # Handle built-in patterns
        if check_type == CheckType.PATTERN and value_str.lower() in BUILTIN_PATTERNS:
            return BUILTIN_PATTERNS[value_str.lower()], operator, {"pattern_name": value_str.lower()}

        # Try to parse as number
        try:
            if "." in value_str:
                value = float(value_str)
            else:
                value = int(value_str)
        except ValueError:
            value = value_str

        if is_percent:
            params["is_percent"] = True

        return value, operator, params

    # Handle boolean
    if isinstance(raw_value, bool):
        return raw_value, operator, params

    # Handle numbers directly
    if isinstance(raw_value, (int, float)):
        return raw_value, operator, params

    return raw_value, operator, params
