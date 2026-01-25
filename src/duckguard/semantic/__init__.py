"""Semantic type detection for DuckGuard.

This module automatically detects the semantic meaning of data columns,
such as email addresses, phone numbers, dates, currencies, and PII.

Example:
    from duckguard.semantic import detect_type, SemanticAnalyzer

    analyzer = SemanticAnalyzer()
    result = analyzer.analyze_column(column)
    print(result.semantic_type)  # "email"
    print(result.confidence)     # 0.95
"""

from duckguard.semantic.analyzer import SemanticAnalyzer
from duckguard.semantic.detector import (
    SemanticType,
    SemanticTypeResult,
    detect_type,
    detect_types_for_dataset,
)
from duckguard.semantic.validators import get_validator_for_type

__all__ = [
    "SemanticType",
    "SemanticTypeResult",
    "detect_type",
    "detect_types_for_dataset",
    "SemanticAnalyzer",
    "get_validator_for_type",
]
