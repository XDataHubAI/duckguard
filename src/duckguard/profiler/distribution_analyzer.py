"""
Distribution analysis for enhanced profiling in DuckGuard 3.0.

This module provides comprehensive distribution analysis including:
- Distribution fitting (normal, uniform, exponential, etc.)
- Histogram generation
- Statistical moments (kurtosis, skewness)
- Best-fit distribution identification

Requirements:
- scipy>=1.11.0 for distribution fitting and tests

Example:
    >>> from duckguard.profiler.distribution_analyzer import DistributionAnalyzer
    >>> analyzer = DistributionAnalyzer()
    >>> analysis = analyzer.analyze(column_values)
    >>> print(f"Best fit: {analysis.best_fit_distribution}")
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class DistributionAnalysis:
    """Results of distribution analysis."""

    # Basic statistics
    mean: float
    std: float
    min: float
    max: float
    median: float

    # Distribution shape
    kurtosis: float
    skewness: float

    # Histogram
    histogram_bins: list[tuple[float, float, int]]  # (lower, upper, count)

    # Distribution tests
    is_normal: bool
    is_uniform: bool
    normality_pvalue: float
    uniformity_pvalue: float

    # Best fit
    best_fit_distribution: str
    best_fit_params: dict
    best_fit_score: float

    # Sample info
    sample_count: int
    null_count: int


class DistributionAnalyzer:
    """
    Analyzes the distribution of numerical data.

    Provides comprehensive statistical analysis including distribution fitting,
    moment calculation, and hypothesis testing.
    """

    MIN_SAMPLES = 30
    SUPPORTED_DISTRIBUTIONS = [
        'norm',      # Normal/Gaussian
        'uniform',   # Uniform
        'expon',     # Exponential
        'gamma',     # Gamma
        'lognorm',   # Log-normal
        'beta',      # Beta
    ]

    def __init__(self):
        """Initialize the distribution analyzer."""
        self._scipy_available = self._check_scipy()

    def _check_scipy(self) -> bool:
        """Check if scipy is available."""
        try:
            import scipy.stats
            return True
        except ImportError:
            return False

    def analyze(self, values: np.ndarray, num_bins: int = 20) -> DistributionAnalysis:
        """
        Perform comprehensive distribution analysis.

        Args:
            values: Array of numeric values (may contain NaN)
            num_bins: Number of histogram bins (default 20)

        Returns:
            DistributionAnalysis with complete statistical analysis

        Raises:
            ImportError: If scipy is not available
            ValueError: If insufficient valid samples
        """
        if not self._scipy_available:
            raise ImportError(
                "scipy is required for distribution analysis. "
                "Install with: pip install 'duckguard[statistics]'"
            )

        import scipy.stats as stats

        # Separate nulls from valid values
        null_count = np.sum(np.isnan(values))
        valid_values = values[~np.isnan(values)]

        if len(valid_values) < self.MIN_SAMPLES:
            raise ValueError(
                f"Insufficient samples for distribution analysis: {len(valid_values)} "
                f"(minimum {self.MIN_SAMPLES})"
            )

        # Calculate basic statistics
        mean = np.mean(valid_values)
        std = np.std(valid_values, ddof=1)
        min_val = np.min(valid_values)
        max_val = np.max(valid_values)
        median = np.median(valid_values)

        # Calculate moments
        kurtosis = stats.kurtosis(valid_values)
        skewness = stats.skew(valid_values)

        # Generate histogram
        hist, bin_edges = np.histogram(valid_values, bins=num_bins)
        histogram_bins = [
            (float(bin_edges[i]), float(bin_edges[i+1]), int(hist[i]))
            for i in range(len(hist))
        ]

        # Test for normality
        is_normal, normality_pvalue = self._test_normality(valid_values)

        # Test for uniformity
        is_uniform, uniformity_pvalue = self._test_uniformity(valid_values)

        # Find best fit distribution
        best_fit_dist, best_fit_params, best_fit_score = self._find_best_fit(valid_values)

        return DistributionAnalysis(
            mean=mean,
            std=std,
            min=min_val,
            max=max_val,
            median=median,
            kurtosis=kurtosis,
            skewness=skewness,
            histogram_bins=histogram_bins,
            is_normal=is_normal,
            is_uniform=is_uniform,
            normality_pvalue=normality_pvalue,
            uniformity_pvalue=uniformity_pvalue,
            best_fit_distribution=best_fit_dist,
            best_fit_params=best_fit_params,
            best_fit_score=best_fit_score,
            sample_count=len(valid_values),
            null_count=null_count,
        )

    def _test_normality(self, values: np.ndarray, alpha: float = 0.05) -> tuple[bool, float]:
        """
        Test if data follows normal distribution using Kolmogorov-Smirnov test.

        Args:
            values: Array of values to test
            alpha: Significance level (default 0.05)

        Returns:
            Tuple of (is_normal, p_value)
        """
        import scipy.stats as stats

        # Normalize values
        if np.std(values) > 0:
            normalized = (values - np.mean(values)) / np.std(values)
            statistic, pvalue = stats.kstest(normalized, 'norm')
            is_normal = pvalue > alpha
            return is_normal, pvalue
        else:
            # Zero variance - not normal
            return False, 0.0

    def _test_uniformity(self, values: np.ndarray, alpha: float = 0.05) -> tuple[bool, float]:
        """
        Test if data follows uniform distribution using Kolmogorov-Smirnov test.

        Args:
            values: Array of values to test
            alpha: Significance level (default 0.05)

        Returns:
            Tuple of (is_uniform, p_value)
        """
        import scipy.stats as stats

        # Scale to [0, 1]
        min_val = np.min(values)
        max_val = np.max(values)

        if min_val != max_val:
            scaled = (values - min_val) / (max_val - min_val)
            statistic, pvalue = stats.kstest(scaled, 'uniform')
            is_uniform = pvalue > alpha
            return is_uniform, pvalue
        else:
            # Constant values - not uniform
            return False, 0.0

    def _find_best_fit(self, values: np.ndarray) -> tuple[str, dict, float]:
        """
        Find the best-fitting distribution from supported distributions.

        Uses Kolmogorov-Smirnov test to measure goodness of fit.

        Args:
            values: Array of values to fit

        Returns:
            Tuple of (distribution_name, parameters, ks_statistic)
        """
        import scipy.stats as stats

        best_dist = None
        best_params = {}
        best_score = float('inf')  # Lower KS statistic is better

        for dist_name in self.SUPPORTED_DISTRIBUTIONS:
            try:
                # Get distribution
                dist = getattr(stats, dist_name)

                # Fit distribution to data
                if dist_name == 'norm':
                    # For normal, just use mean and std
                    params = (np.mean(values), np.std(values, ddof=1))
                    fitted_values = (values - params[0]) / params[1]
                    ks_stat, _ = stats.kstest(fitted_values, 'norm')
                    param_dict = {'loc': params[0], 'scale': params[1]}

                elif dist_name == 'uniform':
                    # For uniform, use min and max
                    params = (np.min(values), np.max(values) - np.min(values))
                    scaled = (values - params[0]) / params[1]
                    ks_stat, _ = stats.kstest(scaled, 'uniform')
                    param_dict = {'loc': params[0], 'scale': params[1]}

                elif dist_name == 'expon':
                    # For exponential, fit using MLE
                    params = dist.fit(values, floc=0)  # Force loc=0 for exponential
                    ks_stat, _ = stats.kstest(values, dist_name, args=params)
                    param_dict = {'loc': params[0], 'scale': params[1]}

                else:
                    # For other distributions, use MLE fitting
                    params = dist.fit(values)
                    ks_stat, _ = stats.kstest(values, dist_name, args=params)

                    # Extract param names
                    if len(params) == 2:
                        param_dict = {'loc': params[0], 'scale': params[1]}
                    elif len(params) == 3:
                        param_dict = {'shape': params[0], 'loc': params[1], 'scale': params[2]}
                    else:
                        param_dict = {f'param_{i}': p for i, p in enumerate(params)}

                # Update best if this is better
                if ks_stat < best_score:
                    best_score = ks_stat
                    best_dist = dist_name
                    best_params = param_dict

            except Exception:
                # Skip distributions that fail to fit
                continue

        # Default to normal if no fit found
        if best_dist is None:
            best_dist = 'norm'
            best_params = {'loc': np.mean(values), 'scale': np.std(values, ddof=1)}
            best_score = 1.0

        return best_dist, best_params, best_score

    def interpret_skewness(self, skewness: float) -> str:
        """
        Interpret skewness value.

        Args:
            skewness: Skewness value

        Returns:
            Human-readable interpretation
        """
        if abs(skewness) < 0.5:
            return "approximately symmetric"
        elif skewness > 0.5:
            return "right-skewed (positive skew)"
        else:
            return "left-skewed (negative skew)"

    def interpret_kurtosis(self, kurtosis: float) -> str:
        """
        Interpret kurtosis value (excess kurtosis).

        Args:
            kurtosis: Excess kurtosis value

        Returns:
            Human-readable interpretation
        """
        if abs(kurtosis) < 1:
            return "mesokurtic (normal-like tails)"
        elif kurtosis > 1:
            return "leptokurtic (heavy tails)"
        else:
            return "platykurtic (light tails)"

    def suggest_checks(self, analysis: DistributionAnalysis) -> list[dict]:
        """
        Suggest validation checks based on distribution analysis.

        Args:
            analysis: Distribution analysis results

        Returns:
            List of suggested check dictionaries
        """
        suggestions = []

        # Suggest range check based on distribution
        if analysis.best_fit_distribution == 'norm':
            # For normal, suggest mean ± 3*std
            lower = analysis.mean - 3 * analysis.std
            upper = analysis.mean + 3 * analysis.std
            suggestions.append({
                'check': 'between',
                'min_value': lower,
                'max_value': upper,
                'reason': 'Normal distribution: ~99.7% within 3 standard deviations'
            })

        elif analysis.best_fit_distribution == 'uniform':
            # For uniform, use observed min/max
            suggestions.append({
                'check': 'between',
                'min_value': analysis.min,
                'max_value': analysis.max,
                'reason': 'Uniform distribution: values bounded by observed range'
            })

        # Suggest normality check if data is normal
        if analysis.is_normal and analysis.normality_pvalue > 0.1:
            suggestions.append({
                'check': 'expect_distribution_normal',
                'significance_level': 0.05,
                'reason': f'Data follows normal distribution (p={analysis.normality_pvalue:.3f})'
            })

        # Suggest uniformity check if data is uniform
        if analysis.is_uniform and analysis.uniformity_pvalue > 0.1:
            suggestions.append({
                'check': 'expect_distribution_uniform',
                'significance_level': 0.05,
                'reason': f'Data follows uniform distribution (p={analysis.uniformity_pvalue:.3f})'
            })

        # Check for outliers based on IQR
        if abs(analysis.kurtosis) > 3:
            suggestions.append({
                'check': 'outlier_detection',
                'method': 'iqr',
                'reason': f'High kurtosis ({analysis.kurtosis:.2f}) suggests potential outliers'
            })

        return suggestions
