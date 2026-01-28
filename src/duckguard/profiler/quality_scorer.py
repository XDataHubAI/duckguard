"""
Data quality scoring for enhanced profiling in DuckGuard 3.0.

This module provides comprehensive data quality assessment across multiple dimensions:
- Completeness: Percentage of non-null values
- Validity: Conformance to expected patterns/types
- Consistency: Internal consistency and duplicate detection
- Accuracy: Statistical measures of correctness
- Overall quality score: Weighted combination of dimensions

Example:
    >>> from duckguard.profiler.quality_scorer import QualityScorer
    >>> scorer = QualityScorer()
    >>> score = scorer.calculate(column_profile)
    >>> print(f"Overall quality: {score.overall_score}/100")
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class QualityDimensions:
    """Quality scores across different dimensions."""

    completeness: float  # 0-100
    validity: float  # 0-100
    consistency: float  # 0-100
    accuracy: float  # 0-100
    overall: float  # 0-100

    # Detailed breakdowns
    completeness_details: dict
    validity_details: dict
    consistency_details: dict
    accuracy_details: dict

    # Grade
    grade: str  # A, B, C, D, F


class QualityScorer:
    """
    Calculates data quality scores across multiple dimensions.

    Provides both overall scores and dimensional breakdowns with
    actionable insights for improvement.
    """

    # Dimension weights (must sum to 1.0)
    WEIGHTS = {
        'completeness': 0.30,
        'validity': 0.30,
        'consistency': 0.20,
        'accuracy': 0.20,
    }

    # Grade thresholds
    GRADE_THRESHOLDS = {
        'A': 90.0,
        'B': 80.0,
        'C': 70.0,
        'D': 60.0,
        'F': 0.0,
    }

    def calculate(
        self,
        values: np.ndarray,
        expected_type: str | None = None,
        expected_pattern: str | None = None,
        allow_nulls: bool = True
    ) -> QualityDimensions:
        """
        Calculate comprehensive quality scores for a column.

        Args:
            values: Array of values to score
            expected_type: Expected data type ('int', 'float', 'string', 'date')
            expected_pattern: Expected regex pattern for string values
            allow_nulls: Whether nulls are acceptable

        Returns:
            QualityDimensions with all scores and details
        """
        # Calculate individual dimensions
        completeness_score, completeness_details = self._calculate_completeness(
            values, allow_nulls
        )

        validity_score, validity_details = self._calculate_validity(
            values, expected_type, expected_pattern
        )

        consistency_score, consistency_details = self._calculate_consistency(
            values
        )

        accuracy_score, accuracy_details = self._calculate_accuracy(
            values
        )

        # Calculate weighted overall score
        overall_score = (
            completeness_score * self.WEIGHTS['completeness'] +
            validity_score * self.WEIGHTS['validity'] +
            consistency_score * self.WEIGHTS['consistency'] +
            accuracy_score * self.WEIGHTS['accuracy']
        )

        # Determine grade
        grade = self._calculate_grade(overall_score)

        return QualityDimensions(
            completeness=completeness_score,
            validity=validity_score,
            consistency=consistency_score,
            accuracy=accuracy_score,
            overall=overall_score,
            completeness_details=completeness_details,
            validity_details=validity_details,
            consistency_details=consistency_details,
            accuracy_details=accuracy_details,
            grade=grade
        )

    def _calculate_completeness(
        self,
        values: np.ndarray,
        allow_nulls: bool
    ) -> tuple[float, dict]:
        """
        Calculate completeness score.

        Completeness measures the percentage of non-null values.

        Args:
            values: Array of values
            allow_nulls: Whether nulls are acceptable

        Returns:
            Tuple of (score, details)
        """
        total_count = len(values)

        # Count nulls (NaN for numeric, None for others)
        null_count = 0
        for v in values:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                null_count += 1

        non_null_count = total_count - null_count
        null_percentage = (null_count / total_count) * 100 if total_count > 0 else 0

        if allow_nulls:
            # If nulls allowed, score based on percentage present
            # 100% = perfect, 0% = worst
            score = (non_null_count / total_count) * 100 if total_count > 0 else 0
        else:
            # If nulls not allowed, any null drops score significantly
            if null_count == 0:
                score = 100.0
            else:
                score = max(0, 100 - (null_percentage * 2))  # Double penalty

        details = {
            'total_count': total_count,
            'non_null_count': non_null_count,
            'null_count': null_count,
            'null_percentage': null_percentage,
            'nulls_allowed': allow_nulls,
        }

        return score, details

    def _calculate_validity(
        self,
        values: np.ndarray,
        expected_type: str | None,
        expected_pattern: str | None
    ) -> tuple[float, dict]:
        """
        Calculate validity score.

        Validity measures conformance to expected types and patterns.

        Args:
            values: Array of values
            expected_type: Expected data type
            expected_pattern: Expected regex pattern

        Returns:
            Tuple of (score, details)
        """
        if expected_type is None and expected_pattern is None:
            # No expectations defined, assume valid
            return 100.0, {'note': 'No expectations defined'}

        valid_values = values[~pd.isna(values)] if hasattr(values, 'isna') else values
        valid_count = len([v for v in valid_values if v is not None])

        if valid_count == 0:
            return 0.0, {'valid_count': 0, 'total_count': 0}

        conforming_count = 0

        # Check type conformance
        if expected_type:
            for v in valid_values:
                if self._check_type_conformance(v, expected_type):
                    conforming_count += 1

        # Check pattern conformance
        elif expected_pattern:
            import re
            pattern = re.compile(expected_pattern)
            for v in valid_values:
                if pattern.match(str(v)):
                    conforming_count += 1

        score = (conforming_count / valid_count) * 100 if valid_count > 0 else 0

        details = {
            'valid_count': valid_count,
            'conforming_count': conforming_count,
            'conformance_rate': score,
            'expected_type': expected_type,
            'expected_pattern': expected_pattern,
        }

        return score, details

    def _calculate_consistency(
        self,
        values: np.ndarray
    ) -> tuple[float, dict]:
        """
        Calculate consistency score.

        Consistency measures internal consistency and duplicate detection.

        Args:
            values: Array of values

        Returns:
            Tuple of (score, details)
        """
        # Remove nulls
        valid_values = []
        for v in values:
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                valid_values.append(v)

        if len(valid_values) == 0:
            return 0.0, {'note': 'No valid values'}

        # Calculate uniqueness rate
        unique_count = len(set(valid_values))
        total_count = len(valid_values)
        uniqueness_rate = (unique_count / total_count) * 100

        # Calculate duplicate rate
        duplicate_count = total_count - unique_count
        duplicate_rate = (duplicate_count / total_count) * 100

        # Score based on uniqueness (higher uniqueness = more consistent)
        # But also consider if low uniqueness is expected (categorical data)
        if unique_count <= 10:
            # Likely categorical - low uniqueness is ok
            score = 100.0 if duplicate_rate < 50 else 80.0
        else:
            # Continuous data - penalize excessive duplicates
            score = max(50, 100 - duplicate_rate)

        details = {
            'total_count': total_count,
            'unique_count': unique_count,
            'duplicate_count': duplicate_count,
            'uniqueness_rate': uniqueness_rate,
            'duplicate_rate': duplicate_rate,
        }

        return score, details

    def _calculate_accuracy(
        self,
        values: np.ndarray
    ) -> tuple[float, dict]:
        """
        Calculate accuracy score.

        Accuracy measures statistical validity and outlier detection.

        Args:
            values: Array of values

        Returns:
            Tuple of (score, details)
        """
        # Try to convert to numeric for statistical analysis
        numeric_values = []
        for v in values:
            try:
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    numeric_values.append(float(v))
            except (ValueError, TypeError):
                pass

        if len(numeric_values) < 3:
            # Not enough numeric data
            return 100.0, {'note': 'Insufficient numeric data for accuracy assessment'}

        numeric_array = np.array(numeric_values)

        # Check for outliers using IQR method
        Q1 = np.percentile(numeric_array, 25)
        Q3 = np.percentile(numeric_array, 75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = numeric_array[(numeric_array < lower_bound) | (numeric_array > upper_bound)]
        outlier_count = len(outliers)
        outlier_rate = (outlier_count / len(numeric_array)) * 100

        # Score based on outlier rate
        # < 5% outliers = excellent, > 20% = poor
        if outlier_rate < 5:
            score = 100.0
        elif outlier_rate < 10:
            score = 90.0
        elif outlier_rate < 15:
            score = 80.0
        elif outlier_rate < 20:
            score = 70.0
        else:
            score = max(50, 100 - outlier_rate * 2)

        details = {
            'numeric_count': len(numeric_array),
            'outlier_count': outlier_count,
            'outlier_rate': outlier_rate,
            'Q1': Q1,
            'Q3': Q3,
            'IQR': IQR,
        }

        return score, details

    def _check_type_conformance(self, value, expected_type: str) -> bool:
        """Check if value conforms to expected type."""
        if expected_type == 'int':
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False

        elif expected_type == 'float':
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        elif expected_type == 'string':
            return isinstance(value, str)

        elif expected_type == 'date':
            # Basic date check (would need proper parsing in production)
            import re
            date_pattern = r'\d{4}-\d{2}-\d{2}'
            return bool(re.match(date_pattern, str(value)))

        return False

    def _calculate_grade(self, overall_score: float) -> str:
        """Calculate letter grade from overall score."""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if overall_score >= threshold:
                return grade
        return 'F'

    def get_improvement_suggestions(self, dimensions: QualityDimensions) -> list[str]:
        """
        Get suggestions for improving data quality.

        Args:
            dimensions: Quality dimensions

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Completeness suggestions
        if dimensions.completeness < 80:
            null_pct = dimensions.completeness_details.get('null_percentage', 0)
            suggestions.append(
                f"Completeness: {null_pct:.1f}% null values detected. "
                "Review data collection process to reduce missing data."
            )

        # Validity suggestions
        if dimensions.validity < 80:
            conformance = dimensions.validity_details.get('conformance_rate', 0)
            suggestions.append(
                f"Validity: Only {conformance:.1f}% of values conform to expectations. "
                "Add validation checks at data ingestion."
            )

        # Consistency suggestions
        if dimensions.consistency < 80:
            duplicate_rate = dimensions.consistency_details.get('duplicate_rate', 0)
            if duplicate_rate > 20:
                suggestions.append(
                    f"Consistency: {duplicate_rate:.1f}% duplicate values. "
                    "Review for data entry errors or implement deduplication."
                )

        # Accuracy suggestions
        if dimensions.accuracy < 80:
            outlier_rate = dimensions.accuracy_details.get('outlier_rate', 0)
            if outlier_rate > 10:
                suggestions.append(
                    f"Accuracy: {outlier_rate:.1f}% outliers detected. "
                    "Investigate outliers and implement range checks."
                )

        if not suggestions:
            suggestions.append(
                f"Quality grade {dimensions.grade}: Data quality is acceptable. "
                "Continue monitoring for any degradation."
            )

        return suggestions


# Import pandas if available (gracefully handle if not)
try:
    import pandas as pd
except ImportError:
    pd = None
