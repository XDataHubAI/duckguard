"""Natural language validation rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from duckguard.ai.config import _get_client
from duckguard.core.result import ValidationResult

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset

SYSTEM_PROMPT = """You are a data quality expert. Convert natural language rules into
DuckGuard Python code.

Available DuckGuard methods:
- dataset.column_name.is_not_null()
- dataset.column_name.is_unique()
- dataset.column_name.between(min, max)
- dataset.column_name.greater_than(value)
- dataset.column_name.less_than(value)
- dataset.column_name.isin(values_list)
- dataset.column_name.matches(regex_pattern)
- dataset.column_name.value_lengths_between(min, max)
- dataset.column_name.not_null_when(sql_condition)
- dataset.column_name.between_when(min, max, sql_condition)
- dataset.column_name.exists_in(other_dataset.column)
- dataset.expect_columns_unique(column_list)

Dataset columns: {columns}

For each natural language rule, output ONLY a Python expression that calls the appropriate
DuckGuard method. One expression per line. No explanations, no imports.

Example input: "order IDs should never be null"
Example output: dataset.order_id.is_not_null()

Example input: "quantities between 1 and 1000"
Example output: dataset.quantity.between(1, 1000)"""


def natural_rules(
    dataset: Dataset,
    rules: list[str],
) -> list[ValidationResult]:
    """
    Validate data using natural language rules.

    Converts plain English rules into DuckGuard validations and executes them.

    Args:
        dataset: Dataset to validate
        rules: List of natural language rule descriptions

    Returns:
        List of ValidationResult objects

    Example:
        from duckguard import connect
        from duckguard.ai import natural_rules

        orders = connect("orders.csv")
        results = natural_rules(orders, [
            "order IDs should never be null or duplicated",
            "quantities should be positive integers under 1000",
            "status must be pending, shipped, or delivered",
        ])

        for r in results:
            print(f"{'✓' if r.passed else '✗'} {r.message}")
    """
    columns = dataset.columns

    # Build prompt with all rules
    rules_text = "\n".join(f"Rule {i+1}: {rule}" for i, rule in enumerate(rules))

    system = SYSTEM_PROMPT.format(columns=columns)
    prompt = f"""Convert these natural language rules to DuckGuard expressions:

{rules_text}

Output one DuckGuard expression per rule, numbered to match. Use 'dataset' as the variable name."""

    client = _get_client()
    response = client(prompt, system=system)

    # Parse and execute the generated expressions
    results = []
    expressions = [line.strip() for line in response.strip().split("\n") if line.strip()]

    for i, expr in enumerate(expressions):
        # Clean up the expression
        expr = expr.lstrip("0123456789.:)-— ")
        if not expr.startswith("dataset."):
            continue

        try:
            # Execute the expression safely
            result = eval(expr, {"dataset": dataset, "__builtins__": {}})  # noqa: S307
            if isinstance(result, ValidationResult):
                results.append(result)
            elif isinstance(result, bool):
                rule_desc = rules[i] if i < len(rules) else expr
                results.append(ValidationResult(
                    passed=result,
                    actual_value=result,
                    expected_value=True,
                    message=f"Natural rule: {rule_desc}",
                ))
        except Exception as e:
            rule_desc = rules[i] if i < len(rules) else expr
            results.append(ValidationResult(
                passed=False,
                actual_value=str(e),
                expected_value="valid expression",
                message=f"Failed to evaluate rule '{rule_desc}': {e}",
            ))

    return results
