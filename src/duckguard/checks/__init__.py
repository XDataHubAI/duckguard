"""Advanced check implementations for DuckGuard 3.0.

This package contains specialized check handlers for:
- Conditional checks (when clause)
- Multi-column checks (cross-column validation)
- Query-based checks (custom SQL)
- Distributional checks (statistical tests)
"""

from __future__ import annotations

__all__ = [
    "ConditionalCheckHandler",
    "QueryValidator",
]

# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    """Lazy import check modules."""
    if name == "ConditionalCheckHandler":
        from duckguard.checks.conditional import ConditionalCheckHandler
        return ConditionalCheckHandler
    elif name == "QueryValidator":
        from duckguard.checks.conditional import QueryValidator
        return QueryValidator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
