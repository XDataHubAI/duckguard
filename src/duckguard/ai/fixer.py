"""AI-powered data fix suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from duckguard.ai.config import _get_client

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset

SYSTEM_PROMPT = """You are a data quality expert. Given a dataset profile with quality issues,
suggest specific fixes. For each issue:

1. Describe the problem clearly
2. Assess severity (critical / warning / info)
3. Suggest a concrete fix (SQL, Python code, or process change)
4. Note if no action is needed (e.g., nulls are expected for pending orders)

Be practical. Not every null is a bug. Use context to determine what's actually wrong.
Format with emoji and clear sections."""


def suggest_fixes(
    dataset: Dataset,
    rules_result=None,
) -> str:
    """
    Get AI-suggested fixes for data quality issues.

    Args:
        dataset: Dataset to analyze
        rules_result: Optional RuleExecutionResult from a previous validation run

    Returns:
        Human-readable fix suggestions

    Example:
        from duckguard import connect
        from duckguard.ai import suggest_fixes

        orders = connect("orders.csv")
        print(suggest_fixes(orders))
    """
    from duckguard.profiler import AutoProfiler

    # Profile the dataset
    profiler = AutoProfiler(deep=True)
    profile = profiler.profile(dataset)

    # Build context
    context_parts = [
        f"Dataset: {dataset.name} ({profile.row_count} rows, {profile.column_count} columns)",
        f"Quality: {profile.overall_quality_grade} ({profile.overall_quality_score:.1f}/100)",
        "",
        "Issues detected:",
    ]

    has_issues = False

    for col in profile.columns:
        issues = []

        if col.null_percent > 0:
            issues.append(f"nulls: {col.null_percent:.1f}% ({col.null_count} rows)")

        if col.quality_grade in ("D", "F"):
            issues.append(f"low quality grade: {col.quality_grade}")

        if col.outlier_count and col.outlier_count > 0:
            issues.append(f"outliers: {col.outlier_count} ({col.outlier_percentage:.1f}%)")

        if issues:
            has_issues = True
            context_parts.append(f"  {col.name} ({col.dtype}): {'; '.join(issues)}")

            # Add sample values for context
            if col.min_value is not None:
                context_parts.append(f"    range: [{col.min_value}, {col.max_value}]")

    if not has_issues:
        return "✅ No data quality issues detected. Your data looks clean!"

    # Add validation results if provided
    if rules_result:
        context_parts.append("")
        context_parts.append("Failed validation checks:")
        for r in getattr(rules_result, "results", []):
            if not r.passed:
                context_parts.append(f"  ✗ {r.message}")

    context = "\n".join(context_parts)

    prompt = f"""Analyze these data quality issues and suggest specific fixes.

{context}

For each issue, provide:
1. What's wrong (brief)
2. Severity (🔴 critical / 🟡 warning / 🔵 info)
3. Suggested fix (code or process)
4. Whether it actually needs fixing (sometimes nulls are expected)"""

    client = _get_client()
    return client(prompt, system=SYSTEM_PROMPT)
