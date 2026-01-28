"""
Distributional checks for DuckGuard 3.0.

This module provides statistical distribution validation using standard
statistical tests like Kolmogorov-Smirnov (KS) test and chi-square test.

Requirements:
- scipy>=1.11.0 for statistical tests

Example:
    >>> from duckguard import connect
    >>> data = connect("measurements.csv")
    >>> # Test if column follows normal distribution
    >>> result = data.temperature.expect_distribution_normal(significance_level=0.05)
    >>> assert result.passed
"""

from dataclasses import dataclass

from duckguard.core.result import ValidationResult


@dataclass
class DistributionTestResult:
    """Result of a distribution test."""

    test_name: str
    statistic: float
    pvalue: float
    is_significant: bool
    significance_level: float
    distribution_type: str


class DistributionalCheckHandler:
    """
    Executes distributional validation checks using statistical tests.

    This handler provides methods to test if data follows specific distributions
    (normal, uniform) or to perform goodness-of-fit tests.
    """

    MIN_SAMPLES = 30  # Minimum samples required for reliable tests

    def __init__(self):
        """Initialize the distributional check handler."""
        self._scipy_available = self._check_scipy_availability()

    def _check_scipy_availability(self) -> bool:
        """Check if scipy is available."""
        try:
            import scipy.stats
            return True
        except ImportError:
            return False

    def _ensure_scipy(self):
        """Ensure scipy is available, raise if not."""
        if not self._scipy_available:
            raise ImportError(
                "scipy is required for distributional checks. "
                "Install with: pip install 'duckguard[statistics]'"
            )

    def execute_distribution_normal(
        self,
        dataset,
        column: str,
        significance_level: float = 0.05
    ) -> ValidationResult:
        """
        Test if column data follows a normal distribution.

        Uses Kolmogorov-Smirnov test comparing data to fitted normal distribution.

        Args:
            dataset: Dataset to test
            column: Column name
            significance_level: Significance level (default 0.05)

        Returns:
            ValidationResult (passed if p-value > significance_level)

        Example:
            >>> data = connect("measurements.csv")
            >>> result = data.temperature.expect_distribution_normal()
            >>> assert result.passed  # Temperature follows normal distribution
        """
        self._ensure_scipy()
        import numpy as np
        import scipy.stats as stats

        # Get column values
        values = self._get_numeric_values(dataset, column)

        # Check minimum samples
        if len(values) < self.MIN_SAMPLES:
            return ValidationResult(
                passed=False,
                actual_value=len(values),
                expected_value=f">= {self.MIN_SAMPLES} samples",
                message=f"Insufficient samples for distribution test: {len(values)} (minimum {self.MIN_SAMPLES})",
                details={
                    "column": column,
                    "sample_count": len(values),
                    "min_required": self.MIN_SAMPLES
                }
            )

        # Normalize values (subtract mean, divide by std)
        mean = np.mean(values)
        std = np.std(values, ddof=1)

        if std == 0:
            return ValidationResult(
                passed=False,
                actual_value=0.0,
                expected_value="> 0",
                message="Zero standard deviation - cannot test distribution",
                details={
                    "column": column,
                    "mean": mean,
                    "std": std
                }
            )

        normalized_values = (values - mean) / std

        # Perform KS test against standard normal
        statistic, pvalue = stats.kstest(normalized_values, 'norm')

        # Test passes if p-value > significance level
        # (null hypothesis: data follows normal distribution)
        passed = bool(pvalue > significance_level)

        if passed:
            message = f"Column '{column}' follows normal distribution (p={pvalue:.4f}, alpha={significance_level})"
        else:
            message = f"Column '{column}' does not follow normal distribution (p={pvalue:.4f}, alpha={significance_level})"

        return ValidationResult(
            passed=passed,
            actual_value=pvalue,
            expected_value=f"> {significance_level}",
            message=message,
            details={
                "test": "Kolmogorov-Smirnov",
                "distribution": "normal",
                "statistic": statistic,
                "pvalue": pvalue,
                "significance_level": significance_level,
                "sample_count": len(values),
                "mean": mean,
                "std": std,
            }
        )

    def execute_distribution_uniform(
        self,
        dataset,
        column: str,
        significance_level: float = 0.05
    ) -> ValidationResult:
        """
        Test if column data follows a uniform distribution.

        Uses Kolmogorov-Smirnov test comparing data to uniform distribution.

        Args:
            dataset: Dataset to test
            column: Column name
            significance_level: Significance level (default 0.05)

        Returns:
            ValidationResult (passed if p-value > significance_level)

        Example:
            >>> data = connect("random_numbers.csv")
            >>> result = data.random_value.expect_distribution_uniform()
            >>> assert result.passed  # Random values are uniformly distributed
        """
        self._ensure_scipy()
        import numpy as np
        import scipy.stats as stats

        # Get column values
        values = self._get_numeric_values(dataset, column)

        # Check minimum samples
        if len(values) < self.MIN_SAMPLES:
            return ValidationResult(
                passed=False,
                actual_value=len(values),
                expected_value=f">= {self.MIN_SAMPLES} samples",
                message=f"Insufficient samples for distribution test: {len(values)} (minimum {self.MIN_SAMPLES})",
                details={
                    "column": column,
                    "sample_count": len(values),
                    "min_required": self.MIN_SAMPLES
                }
            )

        # Scale values to [0, 1] range
        min_val = np.min(values)
        max_val = np.max(values)

        if min_val == max_val:
            return ValidationResult(
                passed=False,
                actual_value="constant",
                expected_value="varying values",
                message="All values are identical - cannot test distribution",
                details={
                    "column": column,
                    "value": min_val,
                }
            )

        scaled_values = (values - min_val) / (max_val - min_val)

        # Perform KS test against uniform distribution [0, 1]
        statistic, pvalue = stats.kstest(scaled_values, 'uniform')

        # Test passes if p-value > significance level
        passed = bool(pvalue > significance_level)

        if passed:
            message = f"Column '{column}' follows uniform distribution (p={pvalue:.4f}, alpha={significance_level})"
        else:
            message = f"Column '{column}' does not follow uniform distribution (p={pvalue:.4f}, alpha={significance_level})"

        return ValidationResult(
            passed=passed,
            actual_value=pvalue,
            expected_value=f"> {significance_level}",
            message=message,
            details={
                "test": "Kolmogorov-Smirnov",
                "distribution": "uniform",
                "statistic": statistic,
                "pvalue": pvalue,
                "significance_level": significance_level,
                "sample_count": len(values),
                "min": min_val,
                "max": max_val,
            }
        )

    def execute_ks_test(
        self,
        dataset,
        column: str,
        distribution: str = "norm",
        significance_level: float = 0.05
    ) -> ValidationResult:
        """
        Perform Kolmogorov-Smirnov test for specified distribution.

        Args:
            dataset: Dataset to test
            column: Column name
            distribution: Distribution name ('norm', 'uniform', 'expon', etc.)
            significance_level: Significance level (default 0.05)

        Returns:
            ValidationResult (passed if p-value > significance_level)

        Example:
            >>> data = connect("data.csv")
            >>> result = data.values.expect_ks_test(distribution='norm')
            >>> assert result.passed
        """
        self._ensure_scipy()
        import numpy as np
        import scipy.stats as stats

        # Get column values
        values = self._get_numeric_values(dataset, column)

        # Check minimum samples
        if len(values) < self.MIN_SAMPLES:
            return ValidationResult(
                passed=False,
                actual_value=len(values),
                expected_value=f">= {self.MIN_SAMPLES} samples",
                message=f"Insufficient samples for KS test: {len(values)} (minimum {self.MIN_SAMPLES})",
                details={
                    "column": column,
                    "sample_count": len(values),
                    "min_required": self.MIN_SAMPLES
                }
            )

        # Normalize values based on distribution
        if distribution == "norm":
            # Normalize to standard normal
            mean = np.mean(values)
            std = np.std(values, ddof=1)
            if std > 0:
                values = (values - mean) / std
        elif distribution == "uniform":
            # Scale to [0, 1] range for uniform distribution
            min_val = np.min(values)
            max_val = np.max(values)
            if max_val > min_val:
                values = (values - min_val) / (max_val - min_val)

        # Perform KS test
        try:
            statistic, pvalue = stats.kstest(values, distribution)

            passed = bool(pvalue > significance_level)

            if passed:
                message = f"Column '{column}' follows '{distribution}' distribution (p={pvalue:.4f}, alpha={significance_level})"
            else:
                message = f"Column '{column}' does not follow '{distribution}' distribution (p={pvalue:.4f}, alpha={significance_level})"

            return ValidationResult(
                passed=passed,
                actual_value=pvalue,
                expected_value=f"> {significance_level}",
                message=message,
                details={
                    "test": "Kolmogorov-Smirnov",
                    "distribution": distribution,
                    "statistic": statistic,
                    "pvalue": pvalue,
                    "significance_level": significance_level,
                    "sample_count": len(values),
                }
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value=f"{distribution} distribution",
                message=f"KS test failed: {str(e)}",
                details={
                    "column": column,
                    "distribution": distribution,
                    "error": str(e)
                }
            )

    def execute_chi_square_test(
        self,
        dataset,
        column: str,
        expected_frequencies: dict | None = None,
        significance_level: float = 0.05
    ) -> ValidationResult:
        """
        Perform chi-square goodness-of-fit test for categorical data.

        Tests if observed frequencies match expected frequencies.

        Args:
            dataset: Dataset to test
            column: Column name (categorical)
            expected_frequencies: Dict mapping categories to expected frequencies
                                  If None, assumes uniform distribution
            significance_level: Significance level (default 0.05)

        Returns:
            ValidationResult (passed if p-value > significance_level)

        Example:
            >>> data = connect("dice_rolls.csv")
            >>> # Test if dice is fair (uniform distribution)
            >>> result = data.roll.expect_chi_square_test(
            ...     expected_frequencies={1: 1/6, 2: 1/6, 3: 1/6, 4: 1/6, 5: 1/6, 6: 1/6}
            ... )
            >>> assert result.passed
        """
        self._ensure_scipy()
        import numpy as np
        import scipy.stats as stats

        # Get value counts
        value_counts = self._get_value_counts(dataset, column)

        if len(value_counts) < 2:
            return ValidationResult(
                passed=False,
                actual_value=len(value_counts),
                expected_value=">= 2 categories",
                message=f"Insufficient categories for chi-square test: {len(value_counts)}",
                details={
                    "column": column,
                    "categories": len(value_counts)
                }
            )

        # Total observations
        total = sum(value_counts.values())

        if total < self.MIN_SAMPLES:
            return ValidationResult(
                passed=False,
                actual_value=total,
                expected_value=f">= {self.MIN_SAMPLES} samples",
                message=f"Insufficient samples for chi-square test: {total}",
                details={
                    "column": column,
                    "sample_count": total,
                    "min_required": self.MIN_SAMPLES
                }
            )

        # Build observed and expected frequencies
        categories = sorted(value_counts.keys())
        observed = np.array([value_counts[cat] for cat in categories])

        if expected_frequencies is None:
            # Assume uniform distribution
            expected = np.array([total / len(categories)] * len(categories))
        else:
            # Use provided expected frequencies
            expected = np.array([
                expected_frequencies.get(cat, 0) * total
                for cat in categories
            ])

        # Check for zero expected frequencies
        if np.any(expected == 0):
            return ValidationResult(
                passed=False,
                actual_value="zero expected frequencies",
                expected_value="non-zero expected frequencies",
                message="Chi-square test requires non-zero expected frequencies",
                details={
                    "column": column,
                    "categories_with_zero_expected": [
                        cat for cat, exp in zip(categories, expected) if exp == 0
                    ]
                }
            )

        # Perform chi-square test
        try:
            statistic, pvalue = stats.chisquare(observed, expected)

            passed = bool(pvalue > significance_level)

            if passed:
                message = f"Column '{column}' matches expected distribution (p={pvalue:.4f}, alpha={significance_level})"
            else:
                message = f"Column '{column}' does not match expected distribution (p={pvalue:.4f}, alpha={significance_level})"

            return ValidationResult(
                passed=passed,
                actual_value=pvalue,
                expected_value=f"> {significance_level}",
                message=message,
                details={
                    "test": "chi-square",
                    "statistic": statistic,
                    "pvalue": pvalue,
                    "significance_level": significance_level,
                    "degrees_of_freedom": len(categories) - 1,
                    "categories": len(categories),
                    "sample_count": total,
                    "observed": dict(zip(categories, observed.tolist())),
                    "expected": dict(zip(categories, expected.tolist())),
                }
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                actual_value=None,
                expected_value="valid chi-square test",
                message=f"Chi-square test failed: {str(e)}",
                details={
                    "column": column,
                    "error": str(e)
                }
            )

    def _get_numeric_values(self, dataset, column: str):
        """Get numeric values from column, excluding nulls."""
        import numpy as np

        engine = dataset._engine
        # Normalize path for DuckDB (forward slashes work on all platforms)
        table_name = dataset._source.replace('\\', '/')

        # Query to get non-null numeric values
        query = f"""
            SELECT "{column}"
            FROM '{table_name}'
            WHERE "{column}" IS NOT NULL
        """

        try:
            result = engine.fetch_all(query)
            values = np.array([row[0] for row in result], dtype=float)
            return values
        except Exception as e:
            raise ValueError(f"Failed to get numeric values from column '{column}': {str(e)}")

    def _get_value_counts(self, dataset, column: str) -> dict:
        """Get value counts for categorical column."""
        engine = dataset._engine
        # Normalize path for DuckDB (forward slashes work on all platforms)
        table_name = dataset._source.replace('\\', '/')

        # Query to get value counts
        query = f"""
            SELECT "{column}", COUNT(*) as count
            FROM '{table_name}'
            WHERE "{column}" IS NOT NULL
            GROUP BY "{column}"
            ORDER BY "{column}"
        """

        try:
            result = engine.fetch_all(query)
            value_counts = {row[0]: row[1] for row in result}
            return value_counts
        except Exception as e:
            raise ValueError(f"Failed to get value counts from column '{column}': {str(e)}")
