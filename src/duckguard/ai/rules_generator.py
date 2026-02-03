"""AI-powered validation rule generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from duckguard.ai.config import _get_client

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset

SYSTEM_PROMPT = """You are a data quality expert. Generate DuckGuard YAML validation rules 
based on dataset profiles. Rules should be practical, not overly strict.

Output format — valid YAML only, no markdown fences:

name: <dataset>_validation
description: Auto-generated quality checks

checks:
  column_name:
    - not_null
    - unique
    - between: [min, max]
    - allowed_values: [val1, val2]
    - pattern: "regex"

Rules to consider:
- not_null for columns with 0% nulls (they're probably required)
- unique for ID-like columns (>99% unique)
- between for numeric columns (use actual range with small buffer)
- allowed_values for low-cardinality columns (<20 distinct values)
- pattern for columns matching known patterns (email, phone, etc.)

Be conservative — generate rules that reflect the actual data, not hypothetical constraints.
Only output the YAML. No explanations."""


def suggest_rules(
    dataset: Dataset,
    strict: bool = False,
    include_comments: bool = True,
) -> str:
    """
    Generate validation rules using AI analysis.

    Combines DuckGuard's profiling with LLM intelligence to generate
    context-aware YAML rules that match your data's actual patterns.

    Args:
        dataset: Dataset to analyze
        strict: If True, generate stricter rules
        include_comments: If True, add explanatory comments

    Returns:
        YAML string with validation rules

    Example:
        from duckguard import connect
        from duckguard.ai import suggest_rules

        orders = connect("orders.csv")
        yaml_rules = suggest_rules(orders)
        print(yaml_rules)

        # Save to file
        with open("duckguard.yaml", "w") as f:
            f.write(yaml_rules)
    """
    from duckguard.profiler import AutoProfiler

    # Profile the dataset
    profiler = AutoProfiler()
    profile = profiler.profile(dataset)

    # Build context
    context_parts = [
        f"Dataset: {dataset.name}",
        f"Rows: {profile.row_count}",
        "",
        "Columns:",
    ]

    for col in profile.columns:
        col_info = f"  {col.name}:"
        col_info += f" type={col.dtype},"
        col_info += f" nulls={col.null_percent:.1f}%,"
        col_info += f" unique={col.unique_percent:.1f}%,"
        col_info += f" distinct={col.unique_count}"

        if col.min_value is not None:
            col_info += f", min={col.min_value}, max={col.max_value}"
        if col.detected_patterns:
            col_info += f", patterns={col.detected_patterns}"
        if hasattr(col, "sample_values") and col.sample_values:
            col_info += f", samples={col.sample_values[:5]}"

        context_parts.append(col_info)

    # Include auto-detected rules as baseline
    if profile.suggested_rules:
        context_parts.append("")
        context_parts.append("Auto-detected rules (baseline):")
        for rule in profile.suggested_rules:
            context_parts.append(f"  - {rule}")

    context = "\n".join(context_parts)

    strictness = "Generate strict rules — flag anything suspicious." if strict else \
        "Generate practical rules — match actual data patterns, allow reasonable variation."

    comment_instruction = "Add YAML comments explaining each rule." if include_comments else \
        "No comments, just rules."

    prompt = f"""{strictness}
{comment_instruction}

{context}"""

    client = _get_client()
    return client(prompt, system=SYSTEM_PROMPT)
