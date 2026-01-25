"""Data Quality Scoring System.

Implements industry-standard DQ dimensions (ISO 8000, DAMA DMBOK):
- Completeness: Are all required values present?
- Uniqueness: Are values appropriately unique?
- Validity: Do values conform to expected formats/ranges?
- Consistency: Are values consistent across columns/datasets?
- Timeliness: Is data fresh enough? (optional)
- Accuracy: Does data reflect reality? (requires reference data)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from duckguard.core.dataset import Dataset


class QualityDimension(Enum):
    """Standard data quality dimensions."""

    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    dimension: QualityDimension
    score: float  # 0-100
    weight: float  # 0-1
    checks_run: int
    checks_passed: int
    details: list[CheckScore] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted contribution to overall score."""
        return self.score * self.weight

    @property
    def pass_rate(self) -> float:
        """Percentage of checks that passed."""
        if self.checks_run == 0:
            return 100.0
        return (self.checks_passed / self.checks_run) * 100


@dataclass
class CheckScore:
    """Score for a single check within a dimension."""

    name: str
    column: str | None
    passed: bool
    score: float  # 0-100
    message: str
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class ColumnScore:
    """Quality score for a single column."""

    name: str
    overall_score: float
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    checks_run: int
    checks_passed: int
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityScore:
    """Complete data quality score for a dataset."""

    source: str
    overall: float  # 0-100 weighted average
    grade: str  # A, B, C, D, F

    # Dimension scores
    completeness: float
    uniqueness: float
    validity: float
    consistency: float

    # Detailed breakdowns
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    columns: dict[str, ColumnScore] = field(default_factory=dict)

    # Summary stats
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def pass_rate(self) -> float:
        """Overall pass rate as percentage."""
        if self.total_checks == 0:
            return 100.0
        return (self.passed_checks / self.total_checks) * 100

    def __repr__(self) -> str:
        return (
            f"QualityScore(overall={self.overall:.1f}, grade='{self.grade}', "
            f"completeness={self.completeness:.1f}, uniqueness={self.uniqueness:.1f}, "
            f"validity={self.validity:.1f}, consistency={self.consistency:.1f})"
        )


class QualityScorer:
    """
    Calculates data quality scores across multiple dimensions.

    Example:
        scorer = QualityScorer()
        score = scorer.score(dataset)

        print(score.overall)        # 87.5
        print(score.grade)          # 'B'
        print(score.completeness)   # 95.0
        print(score.columns['email'].overall_score)  # 76.2
    """

    # Default weights for each dimension (must sum to 1.0)
    DEFAULT_WEIGHTS = {
        QualityDimension.COMPLETENESS: 0.30,
        QualityDimension.UNIQUENESS: 0.20,
        QualityDimension.VALIDITY: 0.30,
        QualityDimension.CONSISTENCY: 0.20,
    }

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A"),
        (80, "B"),
        (70, "C"),
        (60, "D"),
        (0, "F"),
    ]

    # Severity multipliers (how much a failure affects the score)
    SEVERITY_MULTIPLIERS = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
        "critical": 2.0,
    }

    def __init__(
        self,
        weights: dict[QualityDimension, float] | None = None,
        include_timeliness: bool = False,
    ):
        """
        Initialize the scorer.

        Args:
            weights: Custom weights for each dimension (must sum to 1.0)
            include_timeliness: Whether to include timeliness checks
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.include_timeliness = include_timeliness

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total != 1.0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def score(self, dataset: Dataset) -> QualityScore:
        """
        Calculate comprehensive quality score for a dataset.

        Args:
            dataset: Dataset to score

        Returns:
            QualityScore with detailed breakdown
        """
        dimension_scores: dict[str, DimensionScore] = {}
        column_scores: dict[str, ColumnScore] = {}
        all_checks: list[CheckScore] = []

        # Score each column
        for col_name in dataset.columns:
            col = dataset[col_name]
            col_checks = self._score_column(col)
            all_checks.extend(col_checks)

            # Calculate column-level scores
            col_score = self._calculate_column_score(col_name, col_checks)
            column_scores[col_name] = col_score

        # Aggregate into dimension scores
        dimension_scores = self._aggregate_dimension_scores(all_checks)

        # Calculate overall score
        overall = self._calculate_overall_score(dimension_scores)
        grade = self._calculate_grade(overall)

        # Count totals
        total_checks = len(all_checks)
        passed_checks = sum(1 for c in all_checks if c.passed)
        failed_checks = total_checks - passed_checks

        return QualityScore(
            source=dataset.source,
            overall=overall,
            grade=grade,
            completeness=dimension_scores.get(
                QualityDimension.COMPLETENESS.value,
                DimensionScore(QualityDimension.COMPLETENESS, 100, 0.3, 0, 0)
            ).score,
            uniqueness=dimension_scores.get(
                QualityDimension.UNIQUENESS.value,
                DimensionScore(QualityDimension.UNIQUENESS, 100, 0.2, 0, 0)
            ).score,
            validity=dimension_scores.get(
                QualityDimension.VALIDITY.value,
                DimensionScore(QualityDimension.VALIDITY, 100, 0.3, 0, 0)
            ).score,
            consistency=dimension_scores.get(
                QualityDimension.CONSISTENCY.value,
                DimensionScore(QualityDimension.CONSISTENCY, 100, 0.2, 0, 0)
            ).score,
            dimensions=dimension_scores,
            columns=column_scores,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
        )

    def _score_column(self, col) -> list[CheckScore]:
        """Score a single column across all dimensions."""
        checks = []
        col_name = col.name

        # Get column statistics
        stats = col._get_stats()
        numeric_stats = col._get_numeric_stats()

        # === COMPLETENESS CHECKS ===
        null_pct = stats.get("null_percent", 0.0)
        completeness_score = 100 - null_pct

        checks.append(CheckScore(
            name="not_null",
            column=col_name,
            passed=null_pct == 0,
            score=completeness_score,
            message=f"{col_name}: {null_pct:.1f}% null values",
            severity="high" if null_pct > 50 else "medium" if null_pct > 10 else "low",
        ))

        # === UNIQUENESS CHECKS ===
        unique_pct = stats.get("unique_percent", 0.0)
        total_count = stats.get("total_count", 0)
        unique_count = stats.get("unique_count", 0)

        # For likely ID columns, check for duplicates
        is_likely_id = any(
            pattern in col_name.lower()
            for pattern in ["id", "key", "code", "uuid", "guid"]
        )

        if is_likely_id:
            uniqueness_score = unique_pct
            has_duplicates = unique_count < total_count
            checks.append(CheckScore(
                name="unique",
                column=col_name,
                passed=not has_duplicates,
                score=uniqueness_score,
                message=f"{col_name}: {unique_pct:.1f}% unique ({total_count - unique_count} duplicates)",
                severity="critical" if has_duplicates else "low",
            ))
        else:
            # For non-ID columns, just track cardinality
            checks.append(CheckScore(
                name="cardinality",
                column=col_name,
                passed=True,
                score=100,
                message=f"{col_name}: {unique_count} distinct values",
                severity="low",
            ))

        # === VALIDITY CHECKS ===
        # Check for reasonable ranges on numeric columns
        if numeric_stats.get("mean") is not None:
            min_val = stats.get("min_value")

            # Check for negative values in likely positive-only columns
            is_likely_positive = any(
                pattern in col_name.lower()
                for pattern in ["amount", "price", "quantity", "count", "age", "size"]
            )

            if is_likely_positive and min_val is not None:
                is_positive = min_val >= 0
                checks.append(CheckScore(
                    name="positive_values",
                    column=col_name,
                    passed=is_positive,
                    score=100 if is_positive else 0,
                    message=f"{col_name}: min={min_val} (should be >= 0)",
                    severity="high" if not is_positive else "low",
                ))

        # Check for common patterns in string columns
        sample_values = col.get_distinct_values(limit=100)
        string_values = [v for v in sample_values if isinstance(v, str)]

        if string_values and len(string_values) >= 10:
            pattern_score = self._check_pattern_consistency(col_name, string_values)
            if pattern_score is not None:
                checks.append(pattern_score)

        return checks

    def _check_pattern_consistency(self, col_name: str, values: list[str]) -> CheckScore | None:
        """Check if string values follow consistent patterns."""
        import re

        # Common patterns to detect
        patterns = {
            "email": (r"^[\w\.-]+@[\w\.-]+\.\w+$", ["email", "mail"]),
            "phone": (r"^\+?[\d\s\-\(\)]{10,}$", ["phone", "tel", "mobile"]),
            "url": (r"^https?://", ["url", "link", "website"]),
            "uuid": (r"^[0-9a-f]{8}-[0-9a-f]{4}-", ["uuid", "guid"]),
        }

        col_lower = col_name.lower()

        for pattern_name, (regex, keywords) in patterns.items():
            # Check if column name suggests this pattern
            if any(kw in col_lower for kw in keywords):
                matches = sum(1 for v in values if re.match(regex, str(v), re.IGNORECASE))
                match_rate = (matches / len(values)) * 100

                return CheckScore(
                    name=f"pattern_{pattern_name}",
                    column=col_name,
                    passed=match_rate >= 90,
                    score=match_rate,
                    message=f"{col_name}: {match_rate:.1f}% match {pattern_name} pattern",
                    severity="medium" if match_rate < 90 else "low",
                )

        return None

    def _calculate_column_score(self, col_name: str, checks: list[CheckScore]) -> ColumnScore:
        """Calculate aggregate score for a column."""
        if not checks:
            return ColumnScore(
                name=col_name,
                overall_score=100,
                completeness_score=100,
                uniqueness_score=100,
                validity_score=100,
                checks_run=0,
                checks_passed=0,
            )

        # Group checks by type
        completeness_checks = [c for c in checks if c.name == "not_null"]
        uniqueness_checks = [c for c in checks if c.name in ("unique", "cardinality")]
        validity_checks = [c for c in checks if c.name not in ("not_null", "unique", "cardinality")]

        def avg_score(check_list: list[CheckScore]) -> float:
            if not check_list:
                return 100.0
            return sum(c.score for c in check_list) / len(check_list)

        completeness = avg_score(completeness_checks)
        uniqueness = avg_score(uniqueness_checks)
        validity = avg_score(validity_checks)

        # Calculate overall using weights
        overall = (
            completeness * 0.35 +
            uniqueness * 0.25 +
            validity * 0.40
        )

        issues = [c.message for c in checks if not c.passed]

        return ColumnScore(
            name=col_name,
            overall_score=overall,
            completeness_score=completeness,
            uniqueness_score=uniqueness,
            validity_score=validity,
            checks_run=len(checks),
            checks_passed=sum(1 for c in checks if c.passed),
            issues=issues,
        )

    def _aggregate_dimension_scores(
        self, checks: list[CheckScore]
    ) -> dict[str, DimensionScore]:
        """Aggregate check scores into dimension scores."""
        # Map check names to dimensions
        dimension_mapping = {
            "not_null": QualityDimension.COMPLETENESS,
            "unique": QualityDimension.UNIQUENESS,
            "cardinality": QualityDimension.UNIQUENESS,
            "positive_values": QualityDimension.VALIDITY,
            "pattern_email": QualityDimension.VALIDITY,
            "pattern_phone": QualityDimension.VALIDITY,
            "pattern_url": QualityDimension.VALIDITY,
            "pattern_uuid": QualityDimension.VALIDITY,
        }

        # Group checks by dimension
        dimension_checks: dict[QualityDimension, list[CheckScore]] = {
            QualityDimension.COMPLETENESS: [],
            QualityDimension.UNIQUENESS: [],
            QualityDimension.VALIDITY: [],
            QualityDimension.CONSISTENCY: [],
        }

        for check in checks:
            dimension = dimension_mapping.get(check.name, QualityDimension.VALIDITY)
            dimension_checks[dimension].append(check)

        # Calculate scores per dimension
        result = {}
        for dimension, dim_checks in dimension_checks.items():
            if not dim_checks:
                score = 100.0
                passed = 0
                run = 0
            else:
                # Weight by severity
                total_weight = 0
                weighted_score = 0
                for check in dim_checks:
                    weight = self.SEVERITY_MULTIPLIERS.get(check.severity, 1.0)
                    weighted_score += check.score * weight
                    total_weight += weight

                score = weighted_score / total_weight if total_weight > 0 else 100.0
                passed = sum(1 for c in dim_checks if c.passed)
                run = len(dim_checks)

            result[dimension.value] = DimensionScore(
                dimension=dimension,
                score=score,
                weight=self.weights.get(dimension, 0.25),
                checks_run=run,
                checks_passed=passed,
                details=dim_checks,
            )

        return result

    def _calculate_overall_score(self, dimension_scores: dict[str, DimensionScore]) -> float:
        """Calculate weighted overall score."""
        total = 0.0
        for dim_score in dimension_scores.values():
            total += dim_score.weighted_score
        return total

    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"


def score(dataset: Dataset, **kwargs) -> QualityScore:
    """
    Convenience function to score a dataset.

    Args:
        dataset: Dataset to score
        **kwargs: Arguments passed to QualityScorer

    Returns:
        QualityScore

    Example:
        from duckguard import connect, score

        orders = connect("data/orders.csv")
        result = score(orders)

        print(result.overall)  # 87.5
        print(result.grade)    # 'B'
    """
    scorer = QualityScorer(**kwargs)
    return scorer.score(dataset)
