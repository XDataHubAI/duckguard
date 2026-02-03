"""
Comprehensive tests for distributional checks in DuckGuard 3.0.

Tests cover:
- Normal distribution tests (KS test)
- Uniform distribution tests
- Chi-square goodness-of-fit tests
- Edge cases (insufficient samples, zero variance)
- scipy availability handling

Target Coverage: 95%+
Note: Requires scipy for execution
"""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from duckguard import connect
from duckguard.checks.distributional import DistributionalCheckHandler
from duckguard.core.result import ValidationResult

# Check if scipy is available
try:
    import scipy.stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Skip all tests if scipy not available
pytestmark = pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy required for distributional checks")


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def normal_distribution_data():
    """Generate normally distributed data."""
    np.random.seed(42)
    df = pd.DataFrame({
        "normal_values": np.random.normal(loc=100, scale=15, size=500),
        "id": range(500)
    })

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


@pytest.fixture
def uniform_distribution_data():
    """Generate uniformly distributed data."""
    np.random.seed(42)
    df = pd.DataFrame({
        "uniform_values": np.random.uniform(low=0, high=100, size=500),
        "id": range(500)
    })

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


@pytest.fixture
def categorical_data():
    """Generate categorical data."""
    np.random.seed(42)
    # Create fair dice rolls (uniform)
    df = pd.DataFrame({
        "dice_roll": np.random.choice([1, 2, 3, 4, 5, 6], size=600),
        "biased_roll": np.random.choice([1, 2, 3, 4, 5, 6], size=600, p=[0.3, 0.2, 0.15, 0.15, 0.1, 0.1]),
        "id": range(600)
    })

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


@pytest.fixture
def small_sample_data():
    """Generate data with insufficient samples."""
    df = pd.DataFrame({
        "values": [1, 2, 3, 4, 5],  # Only 5 samples
        "id": range(5)
    })

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


@pytest.fixture
def constant_data():
    """Generate constant data (zero variance)."""
    df = pd.DataFrame({
        "constant": [42.0] * 100,
        "id": range(100)
    })

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
# NORMAL DISTRIBUTION TESTS
# =============================================================================


class TestNormalDistribution:
    """Tests for normal distribution checks."""

    def test_normal_distribution_passes(self, normal_distribution_data):
        """Test that normally distributed data passes normality test."""
        dataset = connect(normal_distribution_data)
        result = dataset.normal_values.expect_distribution_normal()

        assert result.passed
        assert result.actual_value > 0.05  # p-value should be > significance level
        assert "normal distribution" in result.message.lower()

    def test_uniform_fails_normal_test(self, uniform_distribution_data):
        """Test that uniform data fails normality test."""
        dataset = connect(uniform_distribution_data)
        result = dataset.uniform_values.expect_distribution_normal()

        # Uniform data should NOT pass normal distribution test
        assert not result.passed
        assert result.actual_value < 0.05

    def test_normal_with_custom_significance(self, normal_distribution_data):
        """Test normal distribution with custom significance level."""
        dataset = connect(normal_distribution_data)

        # Stricter significance level
        result = dataset.normal_values.expect_distribution_normal(
            significance_level=0.01
        )

        # Should still pass with stricter level (for good normal data)
        assert isinstance(result, ValidationResult)
        assert result.details["significance_level"] == 0.01

    def test_normal_distribution_details(self, normal_distribution_data):
        """Test that result contains detailed statistics."""
        dataset = connect(normal_distribution_data)
        result = dataset.normal_values.expect_distribution_normal()

        assert "test" in result.details
        assert result.details["test"] == "Kolmogorov-Smirnov"
        assert "statistic" in result.details
        assert "pvalue" in result.details
        assert "mean" in result.details
        assert "std" in result.details
        assert "sample_count" in result.details


# =============================================================================
# UNIFORM DISTRIBUTION TESTS
# =============================================================================


class TestUniformDistribution:
    """Tests for uniform distribution checks."""

    def test_uniform_distribution_passes(self, uniform_distribution_data):
        """Test that uniformly distributed data passes uniformity test."""
        dataset = connect(uniform_distribution_data)
        result = dataset.uniform_values.expect_distribution_uniform()

        assert result.passed
        assert result.actual_value > 0.05

    def test_normal_fails_uniform_test(self, normal_distribution_data):
        """Test that normal data fails uniformity test."""
        dataset = connect(normal_distribution_data)
        result = dataset.normal_values.expect_distribution_uniform()

        # Normal data should NOT pass uniform distribution test
        assert not result.passed
        assert result.actual_value < 0.05

    def test_uniform_with_custom_significance(self, uniform_distribution_data):
        """Test uniform distribution with custom significance level."""
        dataset = connect(uniform_distribution_data)

        result = dataset.uniform_values.expect_distribution_uniform(
            significance_level=0.01
        )

        assert isinstance(result, ValidationResult)
        assert result.details["significance_level"] == 0.01

    def test_uniform_distribution_details(self, uniform_distribution_data):
        """Test that result contains detailed statistics."""
        dataset = connect(uniform_distribution_data)
        result = dataset.uniform_values.expect_distribution_uniform()

        assert result.details["test"] == "Kolmogorov-Smirnov"
        assert result.details["distribution"] == "uniform"
        assert "min" in result.details
        assert "max" in result.details


# =============================================================================
# KS TEST - GENERAL
# =============================================================================


class TestKSTest:
    """Tests for general Kolmogorov-Smirnov test."""

    def test_ks_test_normal(self, normal_distribution_data):
        """Test KS test for normal distribution."""
        dataset = connect(normal_distribution_data)
        result = dataset.normal_values.expect_ks_test(distribution='norm')

        assert result.passed
        assert result.details["distribution"] == "norm"

    def test_ks_test_uniform(self, uniform_distribution_data):
        """Test KS test for uniform distribution."""
        dataset = connect(uniform_distribution_data)
        result = dataset.uniform_values.expect_ks_test(distribution='uniform')

        assert result.passed
        assert result.details["distribution"] == "uniform"

    def test_ks_test_exponential(self):
        """Test KS test for exponential distribution."""
        np.random.seed(42)
        df = pd.DataFrame({
            "exponential": np.random.exponential(scale=2.0, size=500)
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.exponential.expect_ks_test(distribution='expon')

            # Should pass (data is exponentially distributed)
            assert isinstance(result, ValidationResult)
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_ks_test_wrong_distribution(self, normal_distribution_data):
        """Test KS test fails when testing wrong distribution."""
        dataset = connect(normal_distribution_data)
        result = dataset.normal_values.expect_ks_test(distribution='uniform')

        # Normal data should fail uniform test
        assert not result.passed


# =============================================================================
# CHI-SQUARE TEST
# =============================================================================


class TestChiSquareTest:
    """Tests for chi-square goodness-of-fit test."""

    def test_chi_square_fair_dice(self, categorical_data):
        """Test chi-square for fair dice (uniform)."""
        dataset = connect(categorical_data)
        result = dataset.dice_roll.expect_chi_square_test()

        # Fair dice should pass uniform distribution test
        assert result.passed
        assert result.actual_value > 0.05

    def test_chi_square_biased_dice_fails_uniform(self, categorical_data):
        """Test chi-square for biased dice fails uniform test."""
        dataset = connect(categorical_data)
        result = dataset.biased_roll.expect_chi_square_test()

        # Biased dice should NOT pass uniform distribution test
        assert not result.passed
        assert result.actual_value < 0.05

    def test_chi_square_with_expected_frequencies(self, categorical_data):
        """Test chi-square with specified expected frequencies."""
        dataset = connect(categorical_data)

        # Test biased dice against its actual distribution
        expected = {1: 0.3, 2: 0.2, 3: 0.15, 4: 0.15, 5: 0.1, 6: 0.1}
        result = dataset.biased_roll.expect_chi_square_test(
            expected_frequencies=expected
        )

        # Should pass when testing against correct distribution
        assert result.passed

    def test_chi_square_details(self, categorical_data):
        """Test that chi-square result contains detailed statistics."""
        dataset = connect(categorical_data)
        result = dataset.dice_roll.expect_chi_square_test()

        assert result.details["test"] == "chi-square"
        assert "statistic" in result.details
        assert "pvalue" in result.details
        assert "degrees_of_freedom" in result.details
        assert "categories" in result.details
        assert "observed" in result.details
        assert "expected" in result.details


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in distributional checks."""

    def test_insufficient_samples_normal(self, small_sample_data):
        """Test normal distribution with insufficient samples."""
        dataset = connect(small_sample_data)
        result = dataset.values.expect_distribution_normal()

        assert not result.passed
        assert "insufficient samples" in result.message.lower()
        assert result.actual_value == 5  # Sample count
        assert result.details["min_required"] == 30

    def test_insufficient_samples_uniform(self, small_sample_data):
        """Test uniform distribution with insufficient samples."""
        dataset = connect(small_sample_data)
        result = dataset.values.expect_distribution_uniform()

        assert not result.passed
        assert "insufficient samples" in result.message.lower()

    def test_insufficient_samples_chi_square(self):
        """Test chi-square with insufficient samples."""
        df = pd.DataFrame({
            "category": ["A", "B", "C", "A", "B"]  # Only 5 samples
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.category.expect_chi_square_test()

            assert not result.passed
            assert "insufficient samples" in result.message.lower()
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_zero_variance_normal(self, constant_data):
        """Test normal distribution with zero variance."""
        dataset = connect(constant_data)
        result = dataset.constant.expect_distribution_normal()

        assert not result.passed
        assert "zero standard deviation" in result.message.lower()
        assert result.details["std"] == 0.0

    def test_constant_values_uniform(self, constant_data):
        """Test uniform distribution with constant values."""
        dataset = connect(constant_data)
        result = dataset.constant.expect_distribution_uniform()

        assert not result.passed
        assert "identical" in result.message.lower()

    def test_single_category_chi_square(self):
        """Test chi-square with single category."""
        df = pd.DataFrame({
            "category": ["A"] * 100
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.category.expect_chi_square_test()

            assert not result.passed
            assert "insufficient categories" in result.message.lower()
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows


# =============================================================================
# SCIPY AVAILABILITY TESTS
# =============================================================================


class TestScipyAvailability:
    """Tests for scipy availability handling."""

    def test_scipy_import_check(self):
        """Test that scipy availability is checked."""
        handler = DistributionalCheckHandler()
        assert handler._scipy_available == SCIPY_AVAILABLE

    def test_methods_require_scipy(self, normal_distribution_data):
        """Test that methods work when scipy is available."""
        dataset = connect(normal_distribution_data)

        # Should work since we have scipy
        result = dataset.normal_values.expect_distribution_normal()
        assert isinstance(result, ValidationResult)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestDistributionalIntegration:
    """Integration tests for distributional checks."""

    def test_multiple_distribution_tests(self, normal_distribution_data):
        """Test running multiple distribution tests on same data."""
        dataset = connect(normal_distribution_data)

        # Run multiple tests
        result1 = dataset.normal_values.expect_distribution_normal()
        result2 = dataset.normal_values.expect_distribution_uniform()
        result3 = dataset.normal_values.expect_ks_test(distribution='norm')

        assert result1.passed  # Should pass normal test
        assert not result2.passed  # Should fail uniform test
        assert result3.passed  # Should pass KS test for normal

    def test_combining_with_regular_checks(self, normal_distribution_data):
        """Test combining distributional checks with regular checks."""
        dataset = connect(normal_distribution_data)

        # Regular check
        result1 = dataset.normal_values.is_not_null()

        # Distributional check
        result2 = dataset.normal_values.expect_distribution_normal()

        assert result1.passed
        assert result2.passed


# =============================================================================
# REAL-WORLD SCENARIOS
# =============================================================================


class TestRealWorldScenarios:
    """Tests for real-world usage scenarios."""

    def test_quality_control_measurements(self):
        """Test manufacturing quality control scenario."""
        np.random.seed(42)
        # Simulate manufacturing measurements (should be normal)
        df = pd.DataFrame({
            "part_diameter": np.random.normal(loc=10.0, scale=0.1, size=1000)
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.part_diameter.expect_distribution_normal()

            assert result.passed
            assert result.details["mean"] == pytest.approx(10.0, abs=0.1)
            assert result.details["std"] == pytest.approx(0.1, abs=0.02)
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_random_number_generator_validation(self):
        """Test random number generator produces uniform distribution."""
        np.random.seed(42)
        df = pd.DataFrame({
            "random_number": np.random.random(size=1000)  # Should be uniform [0, 1)
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)
            result = dataset.random_number.expect_distribution_uniform()

            assert result.passed
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows

    def test_survey_response_distribution(self):
        """Test survey responses match expected distribution."""
        np.random.seed(42)
        # Simulate survey responses (1-5 scale)
        # Expected: 10% 1, 20% 2, 40% 3, 20% 4, 10% 5
        df = pd.DataFrame({
            "rating": np.random.choice(
                [1, 2, 3, 4, 5],
                size=1000,
                p=[0.1, 0.2, 0.4, 0.2, 0.1]
            )
        })

        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()

        try:
            dataset = connect(temp_file.name)

            # Test against expected distribution
            expected = {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.2, 5: 0.1}
            result = dataset.rating.expect_chi_square_test(
                expected_frequencies=expected
            )

            assert result.passed
        finally:
            # Clean up with garbage collection to release file handles (Windows)
            import gc
            gc.collect()
            try:
                os.unlink(temp_file.name)
            except (PermissionError, FileNotFoundError):
                pass  # Ignore cleanup errors on Windows
