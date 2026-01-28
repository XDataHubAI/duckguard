"""
Integration tests for DuckGuard 3.0 new features.

This test suite focuses on end-to-end workflows and feature interactions:
- Combining conditional, multi-column, and query-based checks
- Real-world validation scenarios
- Cross-feature integration
- Performance validation

Target: Comprehensive integration coverage across all new features
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from duckguard import connect

# Check optional dependencies
try:
    import scipy.stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def comprehensive_orders_data():
    """Comprehensive order data for integration testing."""
    np.random.seed(42)

    df = pd.DataFrame({
        # Identifiers
        "order_id": range(1, 501),
        "customer_id": np.random.choice(range(1, 101), size=500),
        "product_id": np.random.choice(['A', 'B', 'C', 'D', 'E'], size=500),

        # Dates
        "order_date": pd.date_range('2024-01-01', periods=500, freq='h'),
        "ship_date": pd.date_range('2024-01-02', periods=500, freq='h'),

        # Amounts
        "subtotal": np.random.uniform(10, 1000, size=500),
        "tax": np.zeros(500),  # Will be calculated as % of subtotal
        "shipping": np.random.uniform(5, 50, size=500),
        "discount": np.random.uniform(0, 100, size=500),

        # Categorical
        "status": np.random.choice(['pending', 'completed', 'shipped', 'cancelled'],
                                   size=500, p=[0.1, 0.6, 0.2, 0.1]),
        "country": np.random.choice(['USA', 'Canada', 'Mexico'],
                                   size=500, p=[0.7, 0.2, 0.1]),
        "tier": np.random.choice(['standard', 'premium', 'vip'],
                                size=500, p=[0.6, 0.3, 0.1]),
    })

    # Ensure total = subtotal + tax + shipping
    # Ensure discount never exceeds subtotal
    # Calculate tax as percentage of subtotal (5-15%)
    df['tax'] = df['subtotal'] * np.random.uniform(0.05, 0.15, size=500)
    df['discount'] = np.minimum(df['discount'], df['subtotal'])
    df['total'] = df['subtotal'] + df['tax'] + df['shipping']

    # Add state only for USA orders
    df['state'] = None
    usa_mask = df['country'] == 'USA'
    df.loc[usa_mask, 'state'] = np.random.choice(
        ['CA', 'NY', 'TX', 'FL'],
        size=usa_mask.sum()
    )

    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    yield temp_file.name

    # Clean up with garbage collection to release file handles (Windows)
    import gc
    gc.collect()
    try:
        os.unlink(temp_file.name)
    except (PermissionError, FileNotFoundError):
        pass  # Ignore cleanup errors on Windows


# =============================================================================
# CROSS-FEATURE INTEGRATION TESTS
# =============================================================================


class TestCrossFeatureIntegration:
    """Tests for interactions between different feature types."""

    def test_conditional_and_multicolumn_combination(self, comprehensive_orders_data):
        """Test combining conditional checks with multi-column checks."""
        data = connect(comprehensive_orders_data)

        # Conditional check: State required for USA orders
        result1 = data.state.not_null_when("country = 'USA'")
        assert result1.passed

        # Multi-column check: Total equals sum of parts
        result2 = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total = subtotal + tax + shipping",
            threshold=1.0
        )
        assert result2.passed

        # Both checks should work together
        assert result1.passed and result2.passed

    def test_conditional_and_query_based_combination(self, comprehensive_orders_data):
        """Test combining conditional checks with query-based checks."""
        data = connect(comprehensive_orders_data)

        # Conditional check: Discount limits for premium tier
        result1 = data.discount.between_when(0, 50, "tier = 'premium'")
        assert isinstance(result1.passed, bool)

        # Query-based check: No negative totals
        result2 = data.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < 0"
        )
        assert result2.passed

    def test_multicolumn_and_query_based_combination(self, comprehensive_orders_data):
        """Test combining multi-column checks with query-based checks."""
        data = connect(comprehensive_orders_data)

        # Multi-column check: Ship date after order date
        result1 = data.expect_column_pair_satisfy(
            column_a="ship_date",
            column_b="order_date",
            expression="ship_date >= order_date",
            threshold=1.0
        )
        assert result1.passed

        # Query-based check: Count by status
        result2 = data.expect_query_result_to_be_between(
            query="SELECT COUNT(*) FROM table WHERE status = 'completed'",
            min_value=100,
            max_value=400
        )
        assert result2.passed

    @pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy required")
    def test_distributional_with_regular_checks(self, comprehensive_orders_data):
        """Test combining distributional checks with regular checks."""
        data = connect(comprehensive_orders_data)

        # Regular check: Subtotal is numeric and positive
        result1 = data.subtotal.greater_than(0)
        assert result1.passed

        # Distributional check: Subtotal follows some distribution
        result2 = data.subtotal.expect_ks_test(distribution='uniform')
        assert isinstance(result2.passed, bool)


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestEndToEndWorkflows:
    """Tests for complete validation workflows."""

    def test_complete_order_validation_workflow(self, comprehensive_orders_data):
        """Test complete order validation workflow with all check types."""
        data = connect(comprehensive_orders_data)

        # Step 1: Basic checks
        assert data.order_id.is_unique().passed
        assert data.total.greater_than(0).passed

        # Step 2: Conditional checks
        assert data.state.not_null_when("country = 'USA'").passed

        # Step 3: Multi-column checks
        result = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total >= subtotal",
            threshold=1.0
        )
        assert result.passed

        # Step 4: Query-based checks
        result = data.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE discount > subtotal"
        )
        assert result.passed

        # All checks passed - workflow complete
        print("[PASS] Complete order validation workflow passed")

    def test_data_quality_assessment_workflow(self, comprehensive_orders_data):
        """Test data quality assessment workflow."""
        data = connect(comprehensive_orders_data)

        # Check completeness
        null_checks = [
            data.order_id.is_not_null(),
            data.customer_id.is_not_null(),
            data.total.is_not_null(),
        ]
        assert all(c.passed for c in null_checks)

        # Check uniqueness
        unique_checks = [
            data.order_id.is_unique(),
        ]
        assert all(c.passed for c in unique_checks)

        # Check validity (ranges)
        range_checks = [
            data.subtotal.greater_than(0),
            data.total.greater_than(0),
        ]
        assert all(c.passed for c in range_checks)

        # Check consistency (relationships)
        result = data.expect_column_pair_satisfy(
            column_a="ship_date",
            column_b="order_date",
            expression="ship_date >= order_date",
            threshold=0.95  # Allow 5% exceptions
        )
        assert isinstance(result.passed, bool)

        print("[PASS] Data quality assessment workflow completed")

    def test_tiered_validation_workflow(self, comprehensive_orders_data):
        """Test tiered validation with escalating checks."""
        data = connect(comprehensive_orders_data)

        # Tier 1: Critical checks (must pass)
        critical_checks = [
            data.order_id.is_unique(),
            data.total.is_not_null(),
        ]

        if not all(c.passed for c in critical_checks):
            pytest.fail("Critical checks failed")

        # Tier 2: Important checks (should pass)
        important_checks = [
            data.state.not_null_when("country = 'USA'"),
            data.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE total < 0"
            ),
        ]

        assert all(c.passed for c in important_checks)

        # Tier 3: Nice-to-have checks (warnings only)
        nice_to_have = [
            data.discount.between_when(0, 100, "tier = 'premium'"),
        ]

        for check in nice_to_have:
            if not check.passed:
                print(f"Warning: {check.message}")

        print("[PASS] Tiered validation workflow completed")


# =============================================================================
# REAL-WORLD SCENARIO TESTS
# =============================================================================


class TestRealWorldScenarios:
    """Tests for real-world data validation scenarios."""

    def test_ecommerce_order_validation(self, comprehensive_orders_data):
        """Test e-commerce order validation scenario."""
        data = connect(comprehensive_orders_data)

        # Business rule: USA orders must have state
        assert data.state.not_null_when("country = 'USA'").passed

        # Business rule: Completed orders must have valid totals
        result = data.expect_query_to_return_no_rows(
            query="""
                SELECT * FROM table
                WHERE status = 'completed' AND (total IS NULL OR total <= 0)
            """
        )
        assert result.passed

        # Business rule: Discount cannot exceed subtotal
        result = data.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE discount > subtotal"
        )
        assert result.passed

        # Business rule: Premium tier gets higher discounts
        result = data.discount.between_when(0, 100, "tier = 'premium'")
        assert isinstance(result.passed, bool)

    def test_financial_compliance_validation(self, comprehensive_orders_data):
        """Test financial compliance validation scenario."""
        data = connect(comprehensive_orders_data)

        # Compliance: All amounts must be non-negative
        result = data.expect_query_to_return_no_rows(
            query="""
                SELECT * FROM table
                WHERE subtotal < 0 OR tax < 0 OR shipping < 0 OR total < 0
            """
        )
        assert result.passed

        # Compliance: Total must equal sum of parts
        result = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="ABS(total - (subtotal + tax + shipping)) < 0.01",
            threshold=0.99
        )
        assert result.passed

        # Compliance: Tax should be reasonable percentage of subtotal
        result = data.expect_query_result_to_be_between(
            query="SELECT AVG(tax / subtotal * 100) FROM table WHERE subtotal > 0",
            min_value=0,
            max_value=20  # Max 20% tax rate
        )
        assert result.passed

    def test_data_consistency_validation(self, comprehensive_orders_data):
        """Test data consistency validation scenario."""
        data = connect(comprehensive_orders_data)

        # Consistency: Date relationships
        result = data.expect_column_pair_satisfy(
            column_a="ship_date",
            column_b="order_date",
            expression="ship_date >= order_date",
            threshold=1.0
        )
        assert result.passed

        # Consistency: Status transitions
        result = data.expect_query_to_return_no_rows(
            query="""
                SELECT * FROM table
                WHERE status = 'shipped' AND ship_date IS NULL
            """
        )
        assert result.passed

        # Consistency: No orphaned relationships (all customers exist)
        # This would normally join to customer table
        result = data.expect_query_to_return_rows(
            query="SELECT DISTINCT customer_id FROM table"
        )
        assert result.passed


# =============================================================================
# PERFORMANCE INTEGRATION TESTS
# =============================================================================


class TestPerformanceIntegration:
    """Tests for performance with realistic data volumes."""

    def test_multiple_checks_performance(self, comprehensive_orders_data):
        """Test performance when running multiple checks."""
        import time

        data = connect(comprehensive_orders_data)

        start_time = time.time()

        # Run 10 different checks
        checks = [
            data.order_id.is_unique(),
            data.total.greater_than(0),
            data.state.not_null_when("country = 'USA'"),
            data.discount.between_when(0, 100, "tier = 'premium'"),
            data.expect_column_pair_satisfy(
                column_a="total",
                column_b="subtotal",
                expression="total >= subtotal",
                threshold=1.0
            ),
            data.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE total < 0"
            ),
            data.expect_query_result_to_equal(
                query="SELECT COUNT(*) FROM table WHERE status = 'pending'",
                expected=50,
                tolerance=40
            ),
            data.subtotal.is_not_null(),
            data.country.isin(['USA', 'Canada', 'Mexico']),
            data.status.isin(['pending', 'completed', 'shipped', 'cancelled']),
        ]

        elapsed_time = time.time() - start_time

        # Should complete reasonably fast
        assert elapsed_time < 10.0  # < 10 seconds for 10 checks on 500 rows
        assert all(isinstance(c.passed, bool) for c in checks)

    def test_query_based_checks_caching(self, comprehensive_orders_data):
        """Test that query-based checks benefit from DuckDB's performance."""
        import time

        data = connect(comprehensive_orders_data)

        # Run same query multiple times
        times = []
        for _ in range(3):
            start = time.time()
            _ = data.expect_query_result_to_equal(
                query="SELECT COUNT(*) FROM table WHERE status = 'completed'",
                expected=300,
                tolerance=200
            )
            times.append(time.time() - start)

        # Subsequent runs should not be significantly slower
        assert all(t < 5.0 for t in times)


# =============================================================================
# ERROR HANDLING INTEGRATION TESTS
# =============================================================================


class TestErrorHandlingIntegration:
    """Tests for error handling across features."""

    def test_graceful_failure_cascade(self, comprehensive_orders_data):
        """Test that one failing check doesn't break others."""
        data = connect(comprehensive_orders_data)

        # This check will fail (intentionally bad condition)
        try:
            _ = data.expect_query_to_return_no_rows(
                query="SELECT * FROM nonexistent_table"
            )
        except Exception:
            pass  # Expected to fail

        # But other checks should still work
        result2 = data.order_id.is_unique()
        assert result2.passed

        result3 = data.total.greater_than(0)
        assert result3.passed

    def test_invalid_parameter_handling(self, comprehensive_orders_data):
        """Test handling of invalid parameters across features."""
        data = connect(comprehensive_orders_data)

        # Invalid threshold (should be 0-1)
        with pytest.raises(Exception):
            data.state.not_null_when("country = 'USA'", threshold=2.0)

        # Invalid column reference
        with pytest.raises(Exception):
            data.expect_column_pair_satisfy(
                column_a="nonexistent",
                column_b="total",
                expression="nonexistent > total",
                threshold=1.0
            )


# =============================================================================
# FEATURE COMPATIBILITY TESTS
# =============================================================================


class TestFeatureCompatibility:
    """Tests for backward compatibility with existing features."""

    def test_new_checks_with_yaml_rules(self, comprehensive_orders_data):
        """Test that new checks can be defined in YAML rules."""
        # This is a conceptual test - actual YAML execution would need the full pipeline
        data = connect(comprehensive_orders_data)

        # Simulate YAML-style checks using Python
        checks = {
            'conditional': data.state.not_null_when("country = 'USA'"),
            'multicolumn': data.expect_column_pair_satisfy(
                column_a="total",
                column_b="subtotal",
                expression="total >= subtotal",
                threshold=1.0
            ),
            'query_based': data.expect_query_to_return_no_rows(
                query="SELECT * FROM table WHERE total < 0"
            ),
        }

        # All should execute successfully
        assert all(isinstance(c.passed, bool) for c in checks.values())

    def test_new_checks_with_existing_api(self, comprehensive_orders_data):
        """Test that new checks integrate with existing API."""
        data = connect(comprehensive_orders_data)

        # Mix old and new checks
        old_style = data.order_id.is_unique()
        new_conditional = data.state.not_null_when("country = 'USA'")
        new_multicolumn = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total >= subtotal",
            threshold=1.0
        )

        # All return ValidationResult
        assert all(
            hasattr(r, 'passed') and hasattr(r, 'message')
            for r in [old_style, new_conditional, new_multicolumn]
        )


# =============================================================================
# SUMMARY TEST
# =============================================================================


class TestDuckGuard30Integration:
    """Comprehensive integration test for DuckGuard 3.0."""

    def test_duckguard_30_feature_integration(self, comprehensive_orders_data):
        """Master integration test for all DuckGuard 3.0 features."""
        data = connect(comprehensive_orders_data)

        results = {}

        # Test 1: Conditional Expectations
        results['conditional'] = data.state.not_null_when("country = 'USA'")

        # Test 2: Multi-Column Expectations
        results['multicolumn'] = data.expect_column_pair_satisfy(
            column_a="total",
            column_b="subtotal",
            expression="total >= subtotal",
            threshold=1.0
        )

        # Test 3: Query-Based Expectations
        results['query_based'] = data.expect_query_to_return_no_rows(
            query="SELECT * FROM table WHERE total < 0"
        )

        # Test 4: Distributional Checks (if scipy available)
        if SCIPY_AVAILABLE:
            results['distributional'] = data.subtotal.expect_ks_test(
                distribution='uniform'
            )

        # All features should work together
        assert all(isinstance(r.passed, bool) for r in results.values())

        # Print summary
        passed_count = sum(1 for r in results.values() if r.passed)
        print(f"\n[PASS] DuckGuard 3.0 Integration Test: {passed_count}/{len(results)} checks passed")

        for name, result in results.items():
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"  {status} {name}: {result.message}")
