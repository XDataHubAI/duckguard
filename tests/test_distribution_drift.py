"""Tests for Distribution Drift Detection feature."""


from duckguard import connect


class TestDistributionDrift:
    """Tests for Column.detect_drift() method."""

    def test_detects_significant_drift(self, baseline_data_csv, drifted_data_csv):
        """Test that significant drift is detected."""
        baseline = connect(baseline_data_csv)
        drifted = connect(drifted_data_csv)

        result = baseline["amount"].detect_drift(drifted["amount"])

        assert result.is_drifted is True
        assert result.p_value < 0.05
        assert "drift detected" in result.message.lower()

    def test_no_drift_with_similar_data(self, baseline_data_csv, similar_data_csv):
        """Test that similar distributions show no drift."""
        baseline = connect(baseline_data_csv)
        similar = connect(similar_data_csv)

        result = baseline["amount"].detect_drift(similar["amount"])

        assert result.is_drifted is False
        assert result.p_value >= 0.05

    def test_drift_result_has_statistics(self, baseline_data_csv, drifted_data_csv):
        """Test that drift result contains proper statistics."""
        baseline = connect(baseline_data_csv)
        drifted = connect(drifted_data_csv)

        result = baseline["amount"].detect_drift(drifted["amount"])

        assert result.statistic > 0
        assert 0 <= result.p_value <= 1
        assert result.method == "ks_test"
        assert result.threshold == 0.05

    def test_custom_threshold(self, baseline_data_csv, similar_data_csv):
        """Test drift detection with custom threshold."""
        baseline = connect(baseline_data_csv)
        similar = connect(similar_data_csv)

        # Use very strict threshold
        result = baseline["amount"].detect_drift(similar["amount"], threshold=0.99)

        # With a 0.99 threshold, even small differences won't be flagged as drift
        assert result.threshold == 0.99

    def test_drift_result_boolean_context(self, baseline_data_csv, drifted_data_csv):
        """Test that drift result works in boolean context."""
        baseline = connect(baseline_data_csv)
        drifted = connect(drifted_data_csv)

        result = baseline["amount"].detect_drift(drifted["amount"])

        # In boolean context, True means stable (no drift)
        assert bool(result) == (not result.is_drifted)

    def test_drift_result_summary(self, baseline_data_csv, drifted_data_csv):
        """Test that drift result summary is readable."""
        baseline = connect(baseline_data_csv)
        drifted = connect(drifted_data_csv)

        result = baseline["amount"].detect_drift(drifted["amount"])
        summary = result.summary()

        assert "DRIFT DETECTED" in summary or "No significant drift" in summary
        assert "p-value" in summary
        assert "threshold" in summary

    def test_drift_with_empty_data(self, baseline_data_csv):
        """Test drift detection handles edge cases gracefully."""
        import gc
        import os
        import tempfile

        # Create empty dataset
        content = """id,amount,score
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(content)
            empty_path = f.name

        try:
            baseline = connect(baseline_data_csv)
            empty = connect(empty_path)

            result = baseline["amount"].detect_drift(empty["amount"])

            # Should handle gracefully
            assert result.is_drifted is False
            assert "Insufficient data" in result.message
        finally:
            gc.collect()
            try:
                os.unlink(empty_path)
            except PermissionError:
                pass
