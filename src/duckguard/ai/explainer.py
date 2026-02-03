"""AI-powered data quality explanation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from duckguard.ai.config import _get_client, get_config

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset

SYSTEM_PROMPT = """You are a data quality expert. You analyze dataset profiles and explain 
data quality issues in clear, actionable language. Be specific about which columns and 
values are problematic. Suggest concrete validation rules using DuckGuard's API.

DuckGuard API methods:
- column.is_not_null() — check for nulls
- column.is_unique() — check uniqueness
- column.between(min, max) — range check
- column.isin(values) — enum check
- column.matches(pattern) — regex pattern
- column.not_null_when(condition) — conditional not-null
- column.between_when(min, max, condition) — conditional range
- dataset.score() — quality score (A-F)
- detect_anomalies(dataset) — anomaly detection

Keep explanations concise and actionable. Use emoji for visual clarity."""


def explain(
    dataset: Dataset,
    focus: str | None = None,
    detail: str = "medium",
) -> str:
    """
    Generate a natural language explanation of data quality.

    Args:
        dataset: Dataset to analyze
        focus: Optional column or aspect to focus on
        detail: Level of detail ("brief", "medium", "detailed")

    Returns:
        Human-readable data quality explanation

    Example:
        from duckguard import connect
        from duckguard.ai import explain

        orders = connect("orders.csv")
        print(explain(orders))
    """
    from duckguard.profiler import AutoProfiler

    # Profile the dataset
    profiler = AutoProfiler(deep=True)
    profile = profiler.profile(dataset)

    # Build context for the LLM
    context_parts = [
        f"Dataset: {dataset.name}",
        f"Rows: {profile.row_count}, Columns: {profile.column_count}",
        f"Overall Quality: {profile.overall_quality_grade} ({profile.overall_quality_score:.1f}/100)",
        "",
        "Column Profiles:",
    ]

    for col in profile.columns:
        col_info = f"  {col.name} ({col.dtype}): "
        col_info += f"nulls={col.null_percent:.1f}%, "
        col_info += f"unique={col.unique_percent:.1f}%, "
        col_info += f"grade={col.quality_grade}"

        if col.min_value is not None:
            col_info += f", range=[{col.min_value}, {col.max_value}]"
        if col.detected_patterns:
            col_info += f", patterns={col.detected_patterns}"
        if col.distribution_type:
            col_info += f", dist={col.distribution_type}"
        if col.outlier_count and col.outlier_count > 0:
            col_info += f", outliers={col.outlier_count}"

        context_parts.append(col_info)

    if profile.suggested_rules:
        context_parts.append("")
        context_parts.append(f"Auto-suggested rules ({len(profile.suggested_rules)}):")
        for rule in profile.suggested_rules[:10]:
            context_parts.append(f"  - {rule}")

    context = "\n".join(context_parts)

    # Build prompt
    detail_instruction = {
        "brief": "Give a 3-5 sentence summary.",
        "medium": "Give a comprehensive but concise analysis (10-15 lines).",
        "detailed": "Give a thorough analysis with specific recommendations.",
    }.get(detail, "Give a comprehensive but concise analysis.")

    focus_instruction = f"\nFocus specifically on: {focus}" if focus else ""

    prompt = f"""Analyze this dataset profile and explain the data quality status.
{detail_instruction}{focus_instruction}

{context}"""

    # Call LLM
    client = _get_client()
    return client(prompt, system=SYSTEM_PROMPT)
