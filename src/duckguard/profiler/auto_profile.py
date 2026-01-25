"""Auto-profiling and rule suggestion engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from duckguard.core.dataset import Dataset
from duckguard.core.result import ColumnProfile, ProfileResult


@dataclass
class RuleSuggestion:
    """A suggested validation rule."""

    rule: str
    confidence: float  # 0-1
    reason: str
    category: str  # null, unique, range, pattern, enum


class AutoProfiler:
    """
    Automatically profiles datasets and suggests validation rules.

    The profiler analyzes data patterns and generates Python assertions
    that can be used directly in test files.
    """

    # Thresholds for rule generation
    NULL_THRESHOLD_SUGGEST = 1.0  # Suggest not_null if nulls < 1%
    UNIQUE_THRESHOLD_SUGGEST = 99.0  # Suggest unique if > 99% unique
    ENUM_MAX_VALUES = 20  # Max distinct values to suggest enum check
    PATTERN_SAMPLE_SIZE = 1000  # Sample size for pattern detection

    # Common patterns to detect
    PATTERNS = {
        "email": r"^[\w\.-]+@[\w\.-]+\.\w+$",
        "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "phone": r"^\+?[\d\s\-\(\)]{10,}$",
        "url": r"^https?://[\w\.-]+",
        "ip_address": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
        "date_iso": r"^\d{4}-\d{2}-\d{2}$",
        "datetime_iso": r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    }

    def __init__(self, dataset_var_name: str = "data"):
        """
        Initialize the profiler.

        Args:
            dataset_var_name: Variable name to use in generated rules
        """
        self.dataset_var_name = dataset_var_name

    def profile(self, dataset: Dataset) -> ProfileResult:
        """
        Generate a comprehensive profile of the dataset.

        Args:
            dataset: Dataset to profile

        Returns:
            ProfileResult with statistics and suggested rules
        """
        column_profiles = []
        all_suggestions: list[str] = []

        for col_name in dataset.columns:
            col = dataset[col_name]
            col_profile = self._profile_column(col)
            column_profiles.append(col_profile)
            all_suggestions.extend(col_profile.suggested_rules)

        return ProfileResult(
            source=dataset.source,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            columns=column_profiles,
            suggested_rules=all_suggestions,
        )

    def _profile_column(self, col) -> ColumnProfile:
        """Profile a single column."""
        # Get basic stats
        stats = col._get_stats()
        numeric_stats = col._get_numeric_stats()

        # Get sample values for pattern detection
        sample_values = col.get_distinct_values(limit=self.PATTERN_SAMPLE_SIZE)

        # Generate suggestions
        suggestions = self._generate_suggestions(col, stats, numeric_stats, sample_values)

        return ColumnProfile(
            name=col.name,
            dtype=self._infer_dtype(stats, sample_values),
            null_count=stats.get("null_count", 0),
            null_percent=stats.get("null_percent", 0.0),
            unique_count=stats.get("unique_count", 0),
            unique_percent=stats.get("unique_percent", 0.0),
            min_value=stats.get("min_value"),
            max_value=stats.get("max_value"),
            mean_value=numeric_stats.get("mean"),
            stddev_value=numeric_stats.get("stddev"),
            sample_values=sample_values[:10],
            suggested_rules=[s.rule for s in suggestions],
        )

    def _generate_suggestions(
        self,
        col,
        stats: dict[str, Any],
        numeric_stats: dict[str, Any],
        sample_values: list[Any],
    ) -> list[RuleSuggestion]:
        """Generate rule suggestions for a column."""
        suggestions = []
        col_name = col.name
        var = self.dataset_var_name

        # 1. Null check suggestions
        null_pct = stats.get("null_percent", 0.0)
        if null_pct == 0:
            suggestions.append(
                RuleSuggestion(
                    rule=f"assert {var}.{col_name}.null_percent == 0",
                    confidence=1.0,
                    reason="Column has no null values",
                    category="null",
                )
            )
        elif null_pct < self.NULL_THRESHOLD_SUGGEST:
            threshold = max(1, round(null_pct * 2))  # 2x buffer
            suggestions.append(
                RuleSuggestion(
                    rule=f"assert {var}.{col_name}.null_percent < {threshold}",
                    confidence=0.9,
                    reason=f"Column has only {null_pct:.2f}% nulls",
                    category="null",
                )
            )

        # 2. Uniqueness suggestions
        unique_pct = stats.get("unique_percent", 0.0)
        if unique_pct == 100:
            suggestions.append(
                RuleSuggestion(
                    rule=f"assert {var}.{col_name}.has_no_duplicates()",
                    confidence=1.0,
                    reason="All values are unique",
                    category="unique",
                )
            )
        elif unique_pct > self.UNIQUE_THRESHOLD_SUGGEST:
            suggestions.append(
                RuleSuggestion(
                    rule=f"assert {var}.{col_name}.unique_percent > 99",
                    confidence=0.8,
                    reason=f"Column has {unique_pct:.2f}% unique values",
                    category="unique",
                )
            )

        # 3. Range suggestions for numeric columns
        if numeric_stats.get("mean") is not None:
            min_val = stats.get("min_value")
            max_val = stats.get("max_value")

            if min_val is not None and max_val is not None:
                # Add buffer for range
                range_size = max_val - min_val
                buffer = range_size * 0.1 if range_size > 0 else 1

                suggested_min = self._round_nice(min_val - buffer)
                suggested_max = self._round_nice(max_val + buffer)

                suggestions.append(
                    RuleSuggestion(
                        rule=f"assert {var}.{col_name}.between({suggested_min}, {suggested_max})",
                        confidence=0.7,
                        reason=f"Values range from {min_val} to {max_val}",
                        category="range",
                    )
                )

            # Non-negative check
            if min_val is not None and min_val >= 0:
                suggestions.append(
                    RuleSuggestion(
                        rule=f"assert {var}.{col_name}.min >= 0",
                        confidence=0.9,
                        reason="All values are non-negative",
                        category="range",
                    )
                )

        # 4. Enum suggestions for low-cardinality columns
        unique_count = stats.get("unique_count", 0)
        total_count = stats.get("total_count", 0)

        if 0 < unique_count <= self.ENUM_MAX_VALUES and total_count > unique_count * 2:
            # Get all distinct values
            distinct_values = col.get_distinct_values(limit=self.ENUM_MAX_VALUES + 1)
            if len(distinct_values) <= self.ENUM_MAX_VALUES:
                # Format values for Python code
                formatted_values = self._format_values(distinct_values)
                suggestions.append(
                    RuleSuggestion(
                        rule=f"assert {var}.{col_name}.isin({formatted_values})",
                        confidence=0.85,
                        reason=f"Column has only {unique_count} distinct values",
                        category="enum",
                    )
                )

        # 5. Pattern suggestions for string columns
        string_values = [v for v in sample_values if isinstance(v, str)]
        if string_values:
            detected_pattern = self._detect_pattern(string_values)
            if detected_pattern:
                pattern_name, pattern = detected_pattern
                suggestions.append(
                    RuleSuggestion(
                        rule=f'assert {var}.{col_name}.matches(r"{pattern}")',
                        confidence=0.75,
                        reason=f"Values appear to be {pattern_name}",
                        category="pattern",
                    )
                )

        return suggestions

    def _detect_pattern(self, values: list[str]) -> tuple[str, str] | None:
        """Detect common patterns in string values."""
        if not values:
            return None

        # Sample for pattern detection
        sample = values[: min(100, len(values))]

        for pattern_name, pattern in self.PATTERNS.items():
            matches = sum(1 for v in sample if re.match(pattern, str(v), re.IGNORECASE))
            match_rate = matches / len(sample)

            if match_rate > 0.9:  # 90% match threshold
                return pattern_name, pattern

        return None

    def _infer_dtype(self, stats: dict[str, Any], sample_values: list[Any]) -> str:
        """Infer the data type from statistics and samples."""
        if not sample_values:
            return "unknown"

        # Get first non-null value
        first_val = next((v for v in sample_values if v is not None), None)

        if first_val is None:
            return "unknown"

        if isinstance(first_val, bool):
            return "boolean"
        if isinstance(first_val, int):
            return "integer"
        if isinstance(first_val, float):
            return "float"
        if isinstance(first_val, str):
            return "string"

        return type(first_val).__name__

    def _round_nice(self, value: float) -> int | float:
        """Round to a nice human-readable number."""
        if abs(value) < 1:
            return round(value, 2)
        if abs(value) < 100:
            return round(value)
        if abs(value) < 1000:
            return round(value / 10) * 10
        return round(value / 100) * 100

    def _format_values(self, values: list[Any]) -> str:
        """Format a list of values for Python code."""
        formatted = []
        for v in values:
            if v is None:
                continue
            if isinstance(v, str):
                # Escape quotes
                escaped = v.replace("'", "\\'")
                formatted.append(f"'{escaped}'")
            else:
                formatted.append(str(v))

        return "[" + ", ".join(formatted) + "]"

    def generate_test_file(self, dataset: Dataset, output_var: str = "data") -> str:
        """
        Generate a complete test file from profiling results.

        Args:
            dataset: Dataset to profile
            output_var: Variable name to use for the dataset

        Returns:
            Python code string for a test file
        """
        self.dataset_var_name = output_var
        profile = self.profile(dataset)

        lines = [
            '"""Auto-generated data quality tests by DuckGuard."""',
            "",
            "from duckguard import connect",
            "",
            "",
            f'def test_{dataset.name.replace("-", "_").replace(".", "_")}():',
            f'    {output_var} = connect("{dataset.source}")',
            "",
            "    # Basic dataset checks",
            f"    assert {output_var}.row_count > 0",
            "",
        ]

        # Group suggestions by column
        for col_profile in profile.columns:
            if col_profile.suggested_rules:
                lines.append(f"    # {col_profile.name} validations")
                for rule in col_profile.suggested_rules:
                    lines.append(f"    {rule}")
                lines.append("")

        return "\n".join(lines)


def profile(dataset: Dataset, dataset_var_name: str = "data") -> ProfileResult:
    """
    Convenience function to profile a dataset.

    Args:
        dataset: Dataset to profile
        dataset_var_name: Variable name for generated rules

    Returns:
        ProfileResult
    """
    profiler = AutoProfiler(dataset_var_name=dataset_var_name)
    return profiler.profile(dataset)
