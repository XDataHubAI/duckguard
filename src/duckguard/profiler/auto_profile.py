"""Auto-profiling and rule suggestion engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from duckguard.core.dataset import Dataset
from duckguard.core.result import ColumnProfile, ProfileResult

# Grade thresholds (shared with QualityScorer for consistency)
_GRADE_THRESHOLDS = {"A": 90.0, "B": 80.0, "C": 70.0, "D": 60.0}

# Mapping from inferred dtype to QualityScorer expected_type
_DTYPE_TO_EXPECTED_TYPE: dict[str, str] = {
    "integer": "int",
    "float": "float",
    "string": "string",
}


def _score_to_grade(score: float) -> str:
    """Convert a numeric score (0-100) to a letter grade."""
    for grade, threshold in _GRADE_THRESHOLDS.items():
        if score >= threshold:
            return grade
    return "F"


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

    Args:
        dataset_var_name: Variable name to use in generated rules.
        deep: Enable deep profiling (distribution analysis, outlier detection).
            Requires scipy for distribution fitting. Default is False.
        null_threshold: Suggest not_null rule if null percentage is below this value.
        unique_threshold: Suggest unique rule if unique percentage is above this value.
        enum_max_values: Maximum distinct values for enum check suggestion.
        pattern_sample_size: Number of sample values for pattern detection.
        pattern_min_confidence: Minimum confidence (0-100) for pattern match reporting.
    """

    def __init__(
        self,
        dataset_var_name: str = "data",
        deep: bool = False,
        null_threshold: float = 1.0,
        unique_threshold: float = 99.0,
        enum_max_values: int = 20,
        pattern_sample_size: int = 1000,
        pattern_min_confidence: float = 90.0,
    ) -> None:
        self.dataset_var_name = dataset_var_name
        self.deep = deep
        self.null_threshold = null_threshold
        self.unique_threshold = unique_threshold
        self.enum_max_values = enum_max_values
        self.pattern_sample_size = pattern_sample_size
        self.pattern_min_confidence = pattern_min_confidence

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

        # Compute aggregate quality score
        scored_columns = [c for c in column_profiles if c.quality_score is not None]
        overall_score: float | None = None
        overall_grade: str | None = None
        if scored_columns:
            overall_score = sum(c.quality_score for c in scored_columns) / len(scored_columns)  # type: ignore[misc]
            overall_grade = _score_to_grade(overall_score)

        return ProfileResult(
            source=dataset.source,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
            columns=column_profiles,
            suggested_rules=all_suggestions,
            overall_quality_score=overall_score,
            overall_quality_grade=overall_grade,
        )

    def _profile_column(self, col: Any) -> ColumnProfile:
        """Profile a single column."""
        # Get basic stats
        stats = col._get_stats()
        numeric_stats = col._get_numeric_stats()

        # Get sample values for pattern detection
        sample_values = col.get_distinct_values(limit=self.pattern_sample_size)

        # Generate suggestions
        suggestions = self._generate_suggestions(col, stats, numeric_stats, sample_values)

        # Infer data type
        inferred_dtype = self._infer_dtype(stats, sample_values)

        # Quality scoring (requires numpy)
        quality_score, quality_grade = self._compute_quality(sample_values, inferred_dtype)

        # Deep profiling: distribution + outlier analysis (numeric columns only)
        distribution_type = None
        skewness = None
        kurtosis = None
        is_normal = None
        outlier_count = None
        outlier_percentage = None

        if self.deep and numeric_stats.get("mean") is not None:
            deep_results = self._deep_profile_numeric(col)
            distribution_type = deep_results.get("distribution_type")
            skewness = deep_results.get("skewness")
            kurtosis = deep_results.get("kurtosis")
            is_normal = deep_results.get("is_normal")
            outlier_count = deep_results.get("outlier_count")
            outlier_percentage = deep_results.get("outlier_percentage")

        return ColumnProfile(
            name=col.name,
            dtype=inferred_dtype,
            null_count=stats.get("null_count", 0),
            null_percent=stats.get("null_percent", 0.0),
            unique_count=stats.get("unique_count", 0),
            unique_percent=stats.get("unique_percent", 0.0),
            min_value=stats.get("min_value"),
            max_value=stats.get("max_value"),
            mean_value=numeric_stats.get("mean"),
            stddev_value=numeric_stats.get("stddev"),
            median_value=numeric_stats.get("median"),
            p25_value=numeric_stats.get("p25"),
            p75_value=numeric_stats.get("p75"),
            sample_values=sample_values[:10],
            suggested_rules=[s.rule for s in suggestions],
            quality_score=quality_score,
            quality_grade=quality_grade,
            distribution_type=distribution_type,
            skewness=skewness,
            kurtosis=kurtosis,
            is_normal=is_normal,
            outlier_count=outlier_count,
            outlier_percentage=outlier_percentage,
        )

    def _compute_quality(
        self, sample_values: list[Any], inferred_dtype: str
    ) -> tuple[float | None, str | None]:
        """Compute quality score and grade for a column using QualityScorer."""
        try:
            import numpy as np

            from duckguard.profiler.quality_scorer import QualityScorer

            if not sample_values:
                return None, None

            scorer = QualityScorer()
            values_array = np.array(sample_values, dtype=object)
            expected_type = _DTYPE_TO_EXPECTED_TYPE.get(inferred_dtype)
            dimensions = scorer.calculate(values_array, expected_type=expected_type)
            return dimensions.overall, dimensions.grade
        except ImportError:
            return None, None

    def _deep_profile_numeric(self, col: Any) -> dict[str, Any]:
        """Run deep profiling (distribution + outlier detection) on a numeric column."""
        results: dict[str, Any] = {}
        try:
            import numpy as np

            numeric_values = col._get_numeric_values(limit=10000)
            if len(numeric_values) < 30:
                return results

            values_array = np.array(numeric_values, dtype=float)

            # Distribution analysis (requires scipy)
            try:
                from duckguard.profiler.distribution_analyzer import DistributionAnalyzer

                analyzer = DistributionAnalyzer()
                analysis = analyzer.analyze(values_array)
                results["distribution_type"] = analysis.best_fit_distribution
                results["skewness"] = float(analysis.skewness)
                results["kurtosis"] = float(analysis.kurtosis)
                results["is_normal"] = analysis.is_normal
            except (ImportError, ValueError):
                pass

            # Outlier detection (IQR method — works without scipy)
            try:
                from duckguard.profiler.outlier_detector import OutlierDetector

                detector = OutlierDetector()
                outlier_analysis = detector.detect(values_array, method="iqr")
                results["outlier_count"] = outlier_analysis.outlier_count
                results["outlier_percentage"] = outlier_analysis.outlier_percentage
            except (ImportError, ValueError):
                pass

        except ImportError:
            pass  # numpy not available

        return results

    def _generate_suggestions(
        self,
        col: Any,
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
        elif null_pct < self.null_threshold:
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
        elif unique_pct > self.unique_threshold:
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

            if (
                min_val is not None
                and max_val is not None
                and isinstance(min_val, (int, float))
                and isinstance(max_val, (int, float))
            ):
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
            if min_val is not None and isinstance(min_val, (int, float)) and min_val >= 0:
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

        if 0 < unique_count <= self.enum_max_values and total_count > unique_count * 2:
            # Get all distinct values
            distinct_values = col.get_distinct_values(limit=self.enum_max_values + 1)
            if len(distinct_values) <= self.enum_max_values:
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

        # 5. Pattern suggestions for string columns (using PatternMatcher)
        string_values = [v for v in sample_values if isinstance(v, str)]
        if string_values:
            pattern_suggestion = self._detect_pattern_with_matcher(col_name, string_values)
            if pattern_suggestion:
                suggestions.append(pattern_suggestion)

        return suggestions

    def _detect_pattern_with_matcher(
        self, col_name: str, string_values: list[str]
    ) -> RuleSuggestion | None:
        """Detect patterns using the full PatternMatcher (25+ patterns)."""
        var = self.dataset_var_name
        try:
            import numpy as np

            from duckguard.profiler.pattern_matcher import PatternMatcher

            matcher = PatternMatcher()
            values_array = np.array(string_values, dtype=object)
            matches = matcher.detect_patterns(
                values_array, min_confidence=self.pattern_min_confidence
            )

            if not matches:
                return None

            best_match = matches[0]
            semantic_type = matcher.suggest_semantic_type(matches)
            label = semantic_type or best_match.pattern_type

            return RuleSuggestion(
                rule=f'assert {var}.{col_name}.matches(r"{best_match.pattern_regex}")',
                confidence=best_match.confidence / 100.0,
                reason=f"Values appear to be {label} ({best_match.confidence:.0f}% match)",
                category="pattern",
            )
        except ImportError:
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
        result = self.profile(dataset)

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
        for col_profile in result.columns:
            if col_profile.suggested_rules:
                lines.append(f"    # {col_profile.name} validations")
                for rule in col_profile.suggested_rules:
                    lines.append(f"    {rule}")
                lines.append("")

        return "\n".join(lines)


def profile(
    dataset: Dataset,
    dataset_var_name: str = "data",
    deep: bool = False,
    null_threshold: float = 1.0,
    unique_threshold: float = 99.0,
    pattern_min_confidence: float = 90.0,
) -> ProfileResult:
    """
    Convenience function to profile a dataset.

    Args:
        dataset: Dataset to profile
        dataset_var_name: Variable name for generated rules
        deep: Enable deep profiling (distribution, outlier detection)
        null_threshold: Suggest not_null rule if null percentage is below this
        unique_threshold: Suggest unique rule if unique percentage is above this
        pattern_min_confidence: Minimum confidence (0-100) for pattern matches

    Returns:
        ProfileResult
    """
    profiler = AutoProfiler(
        dataset_var_name=dataset_var_name,
        deep=deep,
        null_threshold=null_threshold,
        unique_threshold=unique_threshold,
        pattern_min_confidence=pattern_min_confidence,
    )
    return profiler.profile(dataset)
