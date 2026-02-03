"""Tests for the auto-profiler."""

from __future__ import annotations

import os
import tempfile

from duckguard.profiler import AutoProfiler, profile


class TestAutoProfiler:
    """Tests for AutoProfiler class."""

    def test_profile_dataset(self, orders_dataset):
        """Test profiling a dataset."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert result.row_count == 30
        assert result.column_count == 15
        assert len(result.columns) == 15

    def test_profile_column_stats(self, orders_dataset):
        """Test column statistics in profile."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        # Find order_id column
        order_id_col = next(c for c in result.columns if c.name == "order_id")
        assert order_id_col.null_percent == 0
        assert order_id_col.unique_percent == 100

    def test_suggested_rules_generated(self, orders_dataset):
        """Test that rules are suggested."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert len(result.suggested_rules) > 0

    def test_unique_column_rule_suggested(self, orders_dataset):
        """Test that unique columns get uniqueness rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        # Should suggest uniqueness rule for order_id
        order_id_col = next(c for c in result.columns if c.name == "order_id")
        assert any("has_no_duplicates" in r for r in order_id_col.suggested_rules)

    def test_enum_column_rule_suggested(self, orders_dataset):
        """Test that low-cardinality columns get enum rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        # Should suggest isin rule for status
        status_col = next(c for c in result.columns if c.name == "status")
        assert any("isin" in r for r in status_col.suggested_rules)

    def test_generate_test_file(self, orders_dataset):
        """Test generating a test file."""
        profiler = AutoProfiler()
        code = profiler.generate_test_file(orders_dataset, output_var="orders")

        assert "from duckguard import connect" in code
        assert "def test_" in code
        assert "assert orders.row_count > 0" in code

    def test_profile_convenience_function(self, orders_dataset):
        """Test the profile() convenience function."""
        result = profile(orders_dataset)
        assert result.row_count == 30


class TestPatternDetection:
    """Tests for pattern detection in profiler."""

    def test_email_pattern_detection(self, orders_dataset):
        """Test that email pattern is detected."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        email_col = next(c for c in result.columns if c.name == "email")
        # Should have a pattern suggestion for email
        assert any("matches" in r for r in email_col.suggested_rules)

    def test_date_column_has_rules(self, orders_dataset):
        """Test that date columns get validation rules."""
        profiler = AutoProfiler(dataset_var_name="data")
        result = profiler.profile(orders_dataset)

        date_col = next(c for c in result.columns if c.name == "created_at")
        # Date column should have at least some suggested rules
        # (e.g., null checks, uniqueness checks)
        assert len(date_col.suggested_rules) > 0

    def test_pattern_matcher_detects_ssn_format(self):
        """Test that PatternMatcher detects SSN patterns (not in old 7-pattern set)."""
        from duckguard import connect

        content = "ssn\n123-45-6789\n234-56-7890\n345-67-8901\n456-78-9012\n567-89-0123\n"
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        try:
            tmp.write(content)
            tmp.close()

            dataset = connect(tmp.name)
            profiler = AutoProfiler(dataset_var_name="data")
            result = profiler.profile(dataset)

            ssn_col = next(c for c in result.columns if c.name == "ssn")
            assert any("matches" in r for r in ssn_col.suggested_rules)
        finally:
            try:
                os.unlink(tmp.name)
            except PermissionError:
                pass


class TestPercentiles:
    """Tests for percentile values in profile results."""

    def test_numeric_columns_have_percentiles(self, orders_dataset):
        """Test that numeric columns include median, p25, and p75 values."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        amount_col = next(c for c in result.columns if c.name == "total_amount")
        assert amount_col.median_value is not None
        assert amount_col.p25_value is not None
        assert amount_col.p75_value is not None
        assert amount_col.p25_value <= amount_col.median_value <= amount_col.p75_value

    def test_non_numeric_columns_have_none_percentiles(self, orders_dataset):
        """Test that string columns have None for percentile values."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        status_col = next(c for c in result.columns if c.name == "status")
        assert status_col.median_value is None
        assert status_col.p25_value is None
        assert status_col.p75_value is None


class TestQualityScoring:
    """Tests for quality scoring integration in profiler."""

    def test_columns_have_quality_score(self, orders_dataset):
        """Test that profiling produces quality scores per column."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        order_id_col = next(c for c in result.columns if c.name == "order_id")
        assert order_id_col.quality_score is not None
        assert 0 <= order_id_col.quality_score <= 100
        assert order_id_col.quality_grade in ("A", "B", "C", "D", "F")

    def test_profile_has_overall_quality_score(self, orders_dataset):
        """Test that ProfileResult has an aggregate quality score."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert result.overall_quality_score is not None
        assert 0 <= result.overall_quality_score <= 100
        assert result.overall_quality_grade in ("A", "B", "C", "D", "F")


class TestDeepProfiling:
    """Tests for deep profiling (distribution + outlier detection)."""

    def test_deep_profile_includes_distribution_info(self, orders_dataset):
        """Test that deep profiling includes distribution analysis for numeric columns."""
        profiler = AutoProfiler(deep=True)
        result = profiler.profile(orders_dataset)

        amount_col = next(c for c in result.columns if c.name == "total_amount")
        assert amount_col.distribution_type is not None
        assert amount_col.skewness is not None
        assert amount_col.kurtosis is not None
        assert amount_col.is_normal is not None

    def test_deep_profile_includes_outlier_info(self, orders_dataset):
        """Test that deep profiling includes outlier detection for numeric columns."""
        profiler = AutoProfiler(deep=True)
        result = profiler.profile(orders_dataset)

        amount_col = next(c for c in result.columns if c.name == "total_amount")
        assert amount_col.outlier_count is not None
        assert amount_col.outlier_percentage is not None
        assert amount_col.outlier_percentage >= 0

    def test_shallow_profile_skips_distribution_info(self, orders_dataset):
        """Test that default (shallow) profiling skips distribution analysis."""
        profiler = AutoProfiler(deep=False)
        result = profiler.profile(orders_dataset)

        amount_col = next(c for c in result.columns if c.name == "total_amount")
        assert amount_col.distribution_type is None
        assert amount_col.skewness is None
        assert amount_col.outlier_count is None

    def test_string_columns_skip_deep_profiling(self, orders_dataset):
        """Test that string columns do not get distribution or outlier info even with deep=True."""
        profiler = AutoProfiler(deep=True)
        result = profiler.profile(orders_dataset)

        status_col = next(c for c in result.columns if c.name == "status")
        assert status_col.distribution_type is None
        assert status_col.outlier_count is None


class TestConfigurableThresholds:
    """Tests for configurable profiling thresholds."""

    def test_default_thresholds_backward_compatible(self, orders_dataset):
        """Test that default parameters produce consistent results."""
        profiler = AutoProfiler()
        result = profiler.profile(orders_dataset)

        assert result.row_count == 30
        assert result.column_count == 15
        assert len(result.suggested_rules) > 0

    def test_strict_null_threshold_reduces_suggestions(self, orders_dataset):
        """Test that setting null_threshold=0 only suggests for zero-null columns."""
        profiler_strict = AutoProfiler(null_threshold=0.0)
        result_strict = profiler_strict.profile(orders_dataset)

        profiler_default = AutoProfiler()
        result_default = profiler_default.profile(orders_dataset)

        # Strict threshold should produce fewer or equal null-related rules
        strict_null_rules = [r for r in result_strict.suggested_rules if "null_percent" in r]
        default_null_rules = [r for r in result_default.suggested_rules if "null_percent" in r]
        assert len(strict_null_rules) <= len(default_null_rules)

    def test_custom_unique_threshold(self, orders_dataset):
        """Test that unique_threshold=100 only suggests for 100% unique columns."""
        profiler = AutoProfiler(unique_threshold=100.0)
        result = profiler.profile(orders_dataset)

        # With threshold=100, only truly 100% unique columns should get
        # uniqueness suggestions (not columns with 99.x% unique)
        for col in result.columns:
            unique_rules = [r for r in col.suggested_rules if "unique_percent" in r]
            assert len(unique_rules) == 0
