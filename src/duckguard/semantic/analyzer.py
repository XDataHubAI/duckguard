"""High-level semantic analyzer for DuckGuard.

Provides comprehensive semantic analysis of datasets including
type detection, PII identification, and validation suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from duckguard.core.dataset import Dataset
from duckguard.semantic.detector import (
    SemanticType,
    SemanticTypeDetector,
)


@dataclass
class ColumnAnalysis:
    """Complete analysis of a single column.

    Attributes:
        name: Column name
        semantic_type: Detected semantic type
        confidence: Detection confidence
        is_pii: Whether column contains PII
        pii_warning: Warning message if PII detected
        suggested_validations: Recommended validations
        statistics: Column statistics
    """

    name: str
    semantic_type: SemanticType
    confidence: float
    is_pii: bool = False
    pii_warning: str | None = None
    suggested_validations: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class DatasetAnalysis:
    """Complete semantic analysis of a dataset.

    Attributes:
        source: Data source path
        row_count: Number of rows
        column_count: Number of columns
        columns: Analysis per column
        pii_columns: List of columns containing PII
        warnings: List of warnings
    """

    source: str
    row_count: int
    column_count: int
    columns: list[ColumnAnalysis] = field(default_factory=list)
    pii_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def get_column(self, name: str) -> ColumnAnalysis | None:
        """Get analysis for a specific column."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    @property
    def has_pii(self) -> bool:
        """Check if dataset contains any PII."""
        return len(self.pii_columns) > 0

    def get_validations_yaml(self) -> str:
        """Generate YAML validation rules from analysis."""
        lines = ["checks:"]

        for col in self.columns:
            if col.suggested_validations:
                lines.append(f"  {col.name}:")
                for validation in col.suggested_validations:
                    lines.append(f"    - {validation}")

        return "\n".join(lines)


class SemanticAnalyzer:
    """Analyzes datasets for semantic types and patterns."""

    def __init__(self):
        self._detector = SemanticTypeDetector()

    def analyze(self, dataset: Dataset) -> DatasetAnalysis:
        """Perform complete semantic analysis of a dataset.

        Args:
            dataset: Dataset to analyze

        Returns:
            DatasetAnalysis with all column analyses
        """
        analysis = DatasetAnalysis(
            source=dataset.source,
            row_count=dataset.row_count,
            column_count=dataset.column_count,
        )

        for col_name in dataset.columns:
            col_analysis = self.analyze_column(dataset, col_name)
            analysis.columns.append(col_analysis)

            if col_analysis.is_pii:
                analysis.pii_columns.append(col_name)
                analysis.warnings.append(
                    f"⚠️ PII detected in column '{col_name}' ({col_analysis.semantic_type.value})"
                )

        return analysis

    def analyze_column(self, dataset: Dataset, col_name: str) -> ColumnAnalysis:
        """Analyze a single column.

        Args:
            dataset: Parent dataset
            col_name: Column name to analyze

        Returns:
            ColumnAnalysis for the column
        """
        col = dataset[col_name]

        # Get sample values
        try:
            sample_values = col.get_distinct_values(limit=100)
        except Exception:
            sample_values = []

        # Detect semantic type
        result = self._detector.detect(
            col_name,
            sample_values,
            col.unique_percent,
            col.null_percent,
        )

        # Build statistics
        statistics = {
            "null_count": col.null_count,
            "null_percent": col.null_percent,
            "unique_count": col.unique_count,
            "unique_percent": col.unique_percent,
            "total_count": col.total_count,
        }

        # Add numeric stats if available
        try:
            if col.mean is not None:
                statistics["min"] = col.min
                statistics["max"] = col.max
                statistics["mean"] = col.mean
        except Exception:
            pass

        # Generate PII warning
        pii_warning = None
        if result.is_pii:
            pii_warning = self._generate_pii_warning(result.semantic_type)

        return ColumnAnalysis(
            name=col_name,
            semantic_type=result.semantic_type,
            confidence=result.confidence,
            is_pii=result.is_pii,
            pii_warning=pii_warning,
            suggested_validations=result.suggested_validations,
            statistics=statistics,
            reasons=result.reasons,
        )

    def _generate_pii_warning(self, sem_type: SemanticType) -> str:
        """Generate appropriate PII warning message."""
        warnings = {
            SemanticType.EMAIL: (
                "Email addresses are PII. Consider: encryption at rest, "
                "access controls, and GDPR compliance."
            ),
            SemanticType.PHONE: (
                "Phone numbers are PII. Consider: encryption, "
                "access controls, and regional privacy laws."
            ),
            SemanticType.SSN: (
                "⚠️ CRITICAL: SSN is highly sensitive PII. "
                "Requires encryption, strict access controls, "
                "and compliance with data protection regulations."
            ),
            SemanticType.CREDIT_CARD: (
                "⚠️ CRITICAL: Credit card numbers require PCI DSS compliance. "
                "Must be encrypted and tokenized."
            ),
            SemanticType.PERSON_NAME: (
                "Names are PII. Consider: purpose limitation, "
                "consent requirements, and anonymization."
            ),
            SemanticType.ADDRESS: (
                "Physical addresses are PII. Consider: "
                "data minimization and access controls."
            ),
        }
        return warnings.get(sem_type, "This column may contain personally identifiable information (PII).")

    def quick_scan(self, dataset: Dataset) -> dict[str, SemanticType]:
        """Quickly scan dataset and return type mapping.

        Args:
            dataset: Dataset to scan

        Returns:
            Dict mapping column names to semantic types
        """
        types = {}
        for col_name in dataset.columns:
            col = dataset[col_name]
            try:
                sample = col.get_distinct_values(limit=50)
            except Exception:
                sample = []

            result = self._detector.detect(
                col_name,
                sample,
                col.unique_percent,
                col.null_percent,
            )
            types[col_name] = result.semantic_type

        return types

    def find_pii_columns(self, dataset: Dataset) -> list[tuple[str, SemanticType, str]]:
        """Find all columns containing PII.

        Args:
            dataset: Dataset to scan

        Returns:
            List of (column_name, semantic_type, warning) tuples
        """
        pii_found = []

        for col_name in dataset.columns:
            col = dataset[col_name]
            try:
                sample = col.get_distinct_values(limit=50)
            except Exception:
                sample = []

            result = self._detector.detect(
                col_name,
                sample,
                col.unique_percent,
                col.null_percent,
            )

            if result.is_pii:
                warning = self._generate_pii_warning(result.semantic_type)
                pii_found.append((col_name, result.semantic_type, warning))

        return pii_found
