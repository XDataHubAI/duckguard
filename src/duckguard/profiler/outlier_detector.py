"""
Outlier detection for enhanced profiling in DuckGuard 3.0.

This module provides multiple outlier detection methods:
- Z-score method (parametric)
- IQR (Interquartile Range) method (non-parametric)
- Isolation Forest (machine learning)
- Local Outlier Factor (density-based)
- Consensus outlier detection (combining multiple methods)

Requirements:
- scipy>=1.11.0 for statistical methods
- scikit-learn>=1.3.0 for ML methods (Isolation Forest, LOF)

Example:
    >>> from duckguard.profiler.outlier_detector import OutlierDetector
    >>> detector = OutlierDetector()
    >>> result = detector.detect(column_values, method='consensus')
    >>> print(f"Found {result.outlier_count} outliers")
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class OutlierAnalysis:
    """Results of outlier detection."""

    # Overall results
    outlier_count: int
    outlier_percentage: float
    outlier_indices: list[int]

    # Method-specific results
    method_results: dict[str, int]  # method -> outlier count
    method_indices: dict[str, list[int]]  # method -> indices

    # Consensus results (if applicable)
    consensus_outliers: list[int]  # Indices detected by multiple methods
    consensus_threshold: int  # Minimum methods agreeing

    # Sample info
    sample_count: int
    methods_used: list[str]


class OutlierDetector:
    """
    Detects outliers using multiple statistical and ML methods.

    Provides both individual method results and consensus detection
    where outliers must be flagged by multiple methods.
    """

    MIN_SAMPLES = 30

    def __init__(self):
        """Initialize the outlier detector."""
        self._scipy_available = self._check_scipy()
        self._sklearn_available = self._check_sklearn()

    def _check_scipy(self) -> bool:
        """Check if scipy is available."""
        try:
            import scipy.stats
            return True
        except ImportError:
            return False

    def _check_sklearn(self) -> bool:
        """Check if scikit-learn is available."""
        try:
            import sklearn
            return True
        except ImportError:
            return False

    def detect(
        self,
        values: np.ndarray,
        method: str = 'consensus',
        contamination: float = 0.05,
        consensus_threshold: int = 2
    ) -> OutlierAnalysis:
        """
        Detect outliers using specified method(s).

        Args:
            values: Array of numeric values (may contain NaN)
            method: Detection method - 'zscore', 'iqr', 'isolation_forest',
                   'lof', 'consensus' (default)
            contamination: Expected proportion of outliers (0.01-0.5)
            consensus_threshold: Min methods agreeing for consensus (default 2)

        Returns:
            OutlierAnalysis with detection results

        Raises:
            ValueError: If insufficient samples or invalid method
        """
        # Remove NaN values
        valid_values = values[~np.isnan(values)]
        original_indices = np.where(~np.isnan(values))[0]

        if len(valid_values) < self.MIN_SAMPLES:
            raise ValueError(
                f"Insufficient samples for outlier detection: {len(valid_values)} "
                f"(minimum {self.MIN_SAMPLES})"
            )

        # Detect based on method
        if method == 'zscore':
            return self._detect_zscore(valid_values, original_indices)

        elif method == 'iqr':
            return self._detect_iqr(valid_values, original_indices)

        elif method == 'isolation_forest':
            if not self._sklearn_available:
                raise ImportError(
                    "scikit-learn required for Isolation Forest. "
                    "Install with: pip install scikit-learn"
                )
            return self._detect_isolation_forest(valid_values, original_indices, contamination)

        elif method == 'lof':
            if not self._sklearn_available:
                raise ImportError(
                    "scikit-learn required for Local Outlier Factor. "
                    "Install with: pip install scikit-learn"
                )
            return self._detect_lof(valid_values, original_indices, contamination)

        elif method == 'consensus':
            return self._detect_consensus(
                valid_values,
                original_indices,
                contamination,
                consensus_threshold
            )

        else:
            raise ValueError(
                f"Unknown method: {method}. "
                f"Valid methods: zscore, iqr, isolation_forest, lof, consensus"
            )

    def _detect_zscore(
        self,
        values: np.ndarray,
        original_indices: np.ndarray,
        threshold: float = 3.0
    ) -> OutlierAnalysis:
        """
        Detect outliers using Z-score method.

        Points with |z-score| > threshold are considered outliers.

        Args:
            values: Array of values
            original_indices: Original indices in the dataset
            threshold: Z-score threshold (default 3.0)

        Returns:
            OutlierAnalysis
        """
        if not self._scipy_available:
            raise ImportError("scipy required for Z-score method")

        import scipy.stats as stats

        # Calculate z-scores
        z_scores = np.abs(stats.zscore(values))

        # Find outliers
        outlier_mask = z_scores > threshold
        outlier_indices = original_indices[outlier_mask].tolist()
        outlier_count = len(outlier_indices)

        return OutlierAnalysis(
            outlier_count=outlier_count,
            outlier_percentage=(outlier_count / len(values)) * 100,
            outlier_indices=outlier_indices,
            method_results={'zscore': outlier_count},
            method_indices={'zscore': outlier_indices},
            consensus_outliers=[],
            consensus_threshold=1,
            sample_count=len(values),
            methods_used=['zscore']
        )

    def _detect_iqr(
        self,
        values: np.ndarray,
        original_indices: np.ndarray,
        multiplier: float = 1.5
    ) -> OutlierAnalysis:
        """
        Detect outliers using IQR (Interquartile Range) method.

        Points outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR] are outliers.

        Args:
            values: Array of values
            original_indices: Original indices in the dataset
            multiplier: IQR multiplier (default 1.5)

        Returns:
            OutlierAnalysis
        """
        # Calculate quartiles
        Q1 = np.percentile(values, 25)
        Q3 = np.percentile(values, 75)
        IQR = Q3 - Q1

        # Calculate bounds
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        # Find outliers
        outlier_mask = (values < lower_bound) | (values > upper_bound)
        outlier_indices = original_indices[outlier_mask].tolist()
        outlier_count = len(outlier_indices)

        return OutlierAnalysis(
            outlier_count=outlier_count,
            outlier_percentage=(outlier_count / len(values)) * 100,
            outlier_indices=outlier_indices,
            method_results={'iqr': outlier_count},
            method_indices={'iqr': outlier_indices},
            consensus_outliers=[],
            consensus_threshold=1,
            sample_count=len(values),
            methods_used=['iqr']
        )

    def _detect_isolation_forest(
        self,
        values: np.ndarray,
        original_indices: np.ndarray,
        contamination: float
    ) -> OutlierAnalysis:
        """
        Detect outliers using Isolation Forest algorithm.

        Args:
            values: Array of values
            original_indices: Original indices in the dataset
            contamination: Expected proportion of outliers

        Returns:
            OutlierAnalysis
        """
        from sklearn.ensemble import IsolationForest

        # Reshape for sklearn
        X = values.reshape(-1, 1)

        # Fit Isolation Forest
        iso = IsolationForest(contamination=contamination, random_state=42)
        predictions = iso.fit_predict(X)

        # Find outliers (predictions == -1)
        outlier_mask = predictions == -1
        outlier_indices = original_indices[outlier_mask].tolist()
        outlier_count = len(outlier_indices)

        return OutlierAnalysis(
            outlier_count=outlier_count,
            outlier_percentage=(outlier_count / len(values)) * 100,
            outlier_indices=outlier_indices,
            method_results={'isolation_forest': outlier_count},
            method_indices={'isolation_forest': outlier_indices},
            consensus_outliers=[],
            consensus_threshold=1,
            sample_count=len(values),
            methods_used=['isolation_forest']
        )

    def _detect_lof(
        self,
        values: np.ndarray,
        original_indices: np.ndarray,
        contamination: float
    ) -> OutlierAnalysis:
        """
        Detect outliers using Local Outlier Factor.

        Args:
            values: Array of values
            original_indices: Original indices in the dataset
            contamination: Expected proportion of outliers

        Returns:
            OutlierAnalysis
        """
        from sklearn.neighbors import LocalOutlierFactor

        # Reshape for sklearn
        X = values.reshape(-1, 1)

        # Fit LOF
        lof = LocalOutlierFactor(contamination=contamination, n_neighbors=20)
        predictions = lof.fit_predict(X)

        # Find outliers (predictions == -1)
        outlier_mask = predictions == -1
        outlier_indices = original_indices[outlier_mask].tolist()
        outlier_count = len(outlier_indices)

        return OutlierAnalysis(
            outlier_count=outlier_count,
            outlier_percentage=(outlier_count / len(values)) * 100,
            outlier_indices=outlier_indices,
            method_results={'lof': outlier_count},
            method_indices={'lof': outlier_indices},
            consensus_outliers=[],
            consensus_threshold=1,
            sample_count=len(values),
            methods_used=['lof']
        )

    def _detect_consensus(
        self,
        values: np.ndarray,
        original_indices: np.ndarray,
        contamination: float,
        threshold: int
    ) -> OutlierAnalysis:
        """
        Detect outliers using consensus of multiple methods.

        An outlier must be flagged by at least 'threshold' methods.

        Args:
            values: Array of values
            original_indices: Original indices in the dataset
            contamination: Expected proportion of outliers
            threshold: Minimum methods agreeing

        Returns:
            OutlierAnalysis with consensus results
        """
        methods_used = []
        method_results = {}
        method_indices = {}

        # Run Z-score method
        if self._scipy_available:
            try:
                result = self._detect_zscore(values, original_indices)
                method_results['zscore'] = result.outlier_count
                method_indices['zscore'] = result.outlier_indices
                methods_used.append('zscore')
            except Exception:
                pass

        # Run IQR method
        try:
            result = self._detect_iqr(values, original_indices)
            method_results['iqr'] = result.outlier_count
            method_indices['iqr'] = result.outlier_indices
            methods_used.append('iqr')
        except Exception:
            pass

        # Run Isolation Forest (if available)
        if self._sklearn_available:
            try:
                result = self._detect_isolation_forest(values, original_indices, contamination)
                method_results['isolation_forest'] = result.outlier_count
                method_indices['isolation_forest'] = result.outlier_indices
                methods_used.append('isolation_forest')
            except Exception:
                pass

        # Run LOF (if available)
        if self._sklearn_available:
            try:
                result = self._detect_lof(values, original_indices, contamination)
                method_results['lof'] = result.outlier_count
                method_indices['lof'] = result.outlier_indices
                methods_used.append('lof')
            except Exception:
                pass

        # Find consensus outliers
        # Count how many methods flagged each index
        index_counts = {}
        for method, indices in method_indices.items():
            for idx in indices:
                index_counts[idx] = index_counts.get(idx, 0) + 1

        # Filter by threshold
        consensus_outliers = [
            idx for idx, count in index_counts.items()
            if count >= threshold
        ]

        # Calculate overall outlier set (union of all methods)
        all_outliers = set()
        for indices in method_indices.values():
            all_outliers.update(indices)

        return OutlierAnalysis(
            outlier_count=len(all_outliers),
            outlier_percentage=(len(all_outliers) / len(values)) * 100,
            outlier_indices=sorted(list(all_outliers)),
            method_results=method_results,
            method_indices=method_indices,
            consensus_outliers=sorted(consensus_outliers),
            consensus_threshold=threshold,
            sample_count=len(values),
            methods_used=methods_used
        )

    def get_outlier_stats(
        self,
        values: np.ndarray,
        outlier_indices: list[int]
    ) -> dict:
        """
        Get statistics about outliers.

        Args:
            values: Original array of values
            outlier_indices: Indices of outliers

        Returns:
            Dictionary with outlier statistics
        """
        if len(outlier_indices) == 0:
            return {
                'count': 0,
                'percentage': 0.0,
                'min': None,
                'max': None,
                'mean': None,
            }

        outlier_values = values[outlier_indices]
        valid_outliers = outlier_values[~np.isnan(outlier_values)]

        if len(valid_outliers) == 0:
            return {
                'count': 0,
                'percentage': 0.0,
                'min': None,
                'max': None,
                'mean': None,
            }

        return {
            'count': len(valid_outliers),
            'percentage': (len(valid_outliers) / len(values)) * 100,
            'min': float(np.min(valid_outliers)),
            'max': float(np.max(valid_outliers)),
            'mean': float(np.mean(valid_outliers)),
        }

    def suggest_handling(self, analysis: OutlierAnalysis) -> list[str]:
        """
        Suggest how to handle detected outliers.

        Args:
            analysis: Outlier analysis results

        Returns:
            List of suggestions
        """
        suggestions = []

        if analysis.outlier_percentage < 1:
            suggestions.append(
                "Low outlier rate (<1%): Consider investigating and removing "
                "if confirmed as errors"
            )
        elif analysis.outlier_percentage < 5:
            suggestions.append(
                "Moderate outlier rate (1-5%): Review outliers, consider "
                "robust statistical methods"
            )
        else:
            suggestions.append(
                "High outlier rate (>5%): Data may not follow expected distribution, "
                "review data collection process"
            )

        if len(analysis.consensus_outliers) > 0:
            suggestions.append(
                f"{len(analysis.consensus_outliers)} outliers flagged by multiple methods - "
                "strong evidence of anomalies"
            )

        return suggestions
