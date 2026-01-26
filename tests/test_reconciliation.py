"""Tests for Reconciliation feature."""


from duckguard import connect


class TestReconciliation:
    """Tests for Dataset.reconcile() method."""

    def test_matching_datasets_pass(self, source_orders_csv, target_orders_matching_csv):
        """Test that matching datasets pass reconciliation."""
        source = connect(source_orders_csv)
        target = connect(target_orders_matching_csv)

        result = source.reconcile(
            target,
            key_columns=["order_id"],
            compare_columns=["customer_id", "amount", "status"],
        )

        assert result.passed is True
        assert result.missing_in_target == 0
        assert result.extra_in_target == 0
        assert len(result.value_mismatches) == 0
        assert result.match_percentage == 100.0

    def test_missing_rows_detected(self, source_orders_csv, target_orders_mismatched_csv):
        """Test that missing rows in target are detected."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        result = source.reconcile(target, key_columns=["order_id"])

        assert result.passed is False
        assert result.missing_in_target == 2  # ORD-004, ORD-005 missing
        assert result.extra_in_target == 1  # ORD-006 extra

    def test_value_mismatches_detected(self, source_orders_csv, target_orders_mismatched_csv):
        """Test that value mismatches are detected."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        result = source.reconcile(
            target,
            key_columns=["order_id"],
            compare_columns=["amount"],
        )

        assert "amount" in result.value_mismatches
        assert result.value_mismatches["amount"] >= 1

    def test_reconciliation_with_tolerance(self, source_orders_csv, target_orders_mismatched_csv):
        """Test reconciliation with numeric tolerance."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        # With 10.0 tolerance, 205.00 vs 200.00 should pass (diff is 5)
        result = source.reconcile(
            target,
            key_columns=["order_id"],
            compare_columns=["amount"],
            tolerance=10.0,
        )

        # Amount mismatch should be tolerated
        assert result.value_mismatches.get("amount", 0) == 0

    def test_reconciliation_summary(self, source_orders_csv, target_orders_mismatched_csv):
        """Test that reconciliation summary is readable."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        result = source.reconcile(target, key_columns=["order_id"])
        summary = result.summary()

        assert "Missing in target" in summary
        assert "Extra in target" in summary

    def test_reconciliation_sample_mismatches(
        self, source_orders_csv, target_orders_mismatched_csv
    ):
        """Test that sample mismatches are captured."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        result = source.reconcile(
            target, key_columns=["order_id"], sample_mismatches=10
        )

        assert len(result.mismatches) > 0
        # Check mismatch structure
        mismatch = result.mismatches[0]
        assert "order_id" in mismatch.key_values

    def test_reconciliation_boolean_context(self, source_orders_csv, target_orders_matching_csv):
        """Test that reconciliation result works in boolean context."""
        source = connect(source_orders_csv)
        target = connect(target_orders_matching_csv)

        result = source.reconcile(target, key_columns=["order_id"])

        assert bool(result) is True
        assert result.passed is True

    def test_reconciliation_total_mismatches_property(
        self, source_orders_csv, target_orders_mismatched_csv
    ):
        """Test the total_mismatches property."""
        source = connect(source_orders_csv)
        target = connect(target_orders_mismatched_csv)

        result = source.reconcile(
            target,
            key_columns=["order_id"],
            compare_columns=["amount"],
        )

        # Should include missing + extra + value mismatches
        expected_total = (
            result.missing_in_target
            + result.extra_in_target
            + sum(result.value_mismatches.values())
        )
        assert result.total_mismatches == expected_total

    def test_reconciliation_with_multiple_key_columns(self):
        """Test reconciliation with composite keys."""
        import gc
        import os
        import tempfile

        source_content = """order_id,line_id,amount
ORD-001,1,100.00
ORD-001,2,50.00
ORD-002,1,200.00
"""
        target_content = """order_id,line_id,amount
ORD-001,1,100.00
ORD-001,2,50.00
ORD-002,1,200.00
"""
        source_path = None
        target_path = None

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                f.write(source_content)
                source_path = f.name

            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
                f.write(target_content)
                target_path = f.name

            source = connect(source_path)
            target = connect(target_path)

            result = source.reconcile(
                target,
                key_columns=["order_id", "line_id"],
                compare_columns=["amount"],
            )

            assert result.passed is True
            assert result.match_percentage == 100.0

        finally:
            gc.collect()
            for path in [source_path, target_path]:
                if path:
                    try:
                        os.unlink(path)
                    except PermissionError:
                        pass
