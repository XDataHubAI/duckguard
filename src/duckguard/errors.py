"""Enhanced error classes for DuckGuard with helpful suggestions.

Provides user-friendly error messages with:
- Clear descriptions of what went wrong
- Suggestions for how to fix the issue
- Links to relevant documentation
- Context about the data being validated
"""

from __future__ import annotations

from typing import Any

# Documentation base URL
DOCS_BASE_URL = "https://github.com/XDataHubAI/duckguard"


class DuckGuardError(Exception):
    """Base exception for all DuckGuard errors.

    Attributes:
        message: Human-readable error description
        suggestion: Helpful suggestion for fixing the issue
        docs_url: Link to relevant documentation
        context: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        docs_url: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        self.message = message
        self.suggestion = suggestion
        self.docs_url = docs_url
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the full error message with suggestions."""
        parts = [self.message]

        if self.suggestion:
            parts.append(f"\n\nSuggestion: {self.suggestion}")

        if self.docs_url:
            parts.append(f"\n\nDocs: {self.docs_url}")

        if self.context:
            context_str = "\n".join(f"  {k}: {v}" for k, v in self.context.items())
            parts.append(f"\n\nContext:\n{context_str}")

        return "".join(parts)


class ConnectionError(DuckGuardError):
    """Error connecting to a data source."""

    def __init__(
        self,
        source: str,
        original_error: Exception | None = None,
        **context: Any,
    ):
        super().__init__(
            message=f"Failed to connect to data source: {source}",
            suggestion=self._get_suggestion(source, original_error),
            docs_url=f"{DOCS_BASE_URL}#connectors",
            context={"source": source, **context},
        )
        self.source = source
        self.original_error = original_error

    def _get_suggestion(self, source: str, error: Exception | None) -> str:
        """Get a helpful suggestion based on the source type."""
        suggestions = []

        if source.endswith(".csv"):
            suggestions.append("Verify the CSV file exists and is readable")
            suggestions.append("Check file permissions")
        elif source.endswith(".parquet"):
            suggestions.append("Verify the Parquet file exists and is not corrupted")
            suggestions.append("Try: pip install pyarrow")
        elif "postgres" in source or "postgresql" in source:
            suggestions.append("Verify PostgreSQL connection string format: postgresql://user:pass@host:port/db")
            suggestions.append("Check if the database server is running")
        elif "mysql" in source:
            suggestions.append("Verify MySQL connection string format: mysql://user:pass@host:port/db")
        elif "s3://" in source:
            suggestions.append("Verify AWS credentials are configured")
            suggestions.append("Check S3 bucket permissions")
        else:
            suggestions.append("Verify the data source path or connection string")

        if error:
            suggestions.append(f"Original error: {error}")

        return "\n  - ".join([""] + suggestions).strip()


class FileNotFoundError(DuckGuardError):
    """File not found error with helpful context."""

    def __init__(self, path: str, **context: Any):
        import os

        cwd = os.getcwd()
        super().__init__(
            message=f"File not found: {path}",
            suggestion=f"Check if the file exists. Current directory: {cwd}",
            docs_url=f"{DOCS_BASE_URL}#file-connectors",
            context={"path": path, "cwd": cwd, **context},
        )


class ColumnNotFoundError(DuckGuardError):
    """Column not found in dataset."""

    def __init__(self, column: str, available_columns: list[str], **context: Any):
        # Find similar column names
        similar = self._find_similar(column, available_columns)

        suggestion = "Available columns: " + ", ".join(available_columns[:10])
        if len(available_columns) > 10:
            suggestion += f" (and {len(available_columns) - 10} more)"

        if similar:
            suggestion = f"Did you mean: {similar}?\n\n{suggestion}"

        super().__init__(
            message=f"Column '{column}' not found in dataset",
            suggestion=suggestion,
            docs_url=f"{DOCS_BASE_URL}#working-with-columns",
            context={"column": column, "similar": similar, **context},
        )

    def _find_similar(self, target: str, candidates: list[str]) -> str | None:
        """Find a similar column name using simple string matching."""
        target_lower = target.lower()

        # Exact match ignoring case
        for c in candidates:
            if c.lower() == target_lower:
                return c

        # Prefix match
        for c in candidates:
            if c.lower().startswith(target_lower) or target_lower.startswith(c.lower()):
                return c

        # Contains match
        for c in candidates:
            if target_lower in c.lower() or c.lower() in target_lower:
                return c

        return None


class ValidationError(DuckGuardError):
    """Validation check failed with detailed information."""

    def __init__(
        self,
        check_name: str,
        column: str | None = None,
        actual_value: Any = None,
        expected_value: Any = None,
        failed_rows: list | None = None,
        **context: Any,
    ):
        col_str = f" for column '{column}'" if column else ""
        message = f"Validation check '{check_name}' failed{col_str}"

        suggestion_parts = []
        if actual_value is not None and expected_value is not None:
            suggestion_parts.append(f"Expected: {expected_value}, Got: {actual_value}")

        if failed_rows:
            sample = failed_rows[:3]
            suggestion_parts.append(f"Sample failing values: {sample}")
            if len(failed_rows) > 3:
                suggestion_parts.append(f"({len(failed_rows)} total failures)")

        suggestion = "\n".join(suggestion_parts) if suggestion_parts else None

        super().__init__(
            message=message,
            suggestion=suggestion,
            docs_url=f"{DOCS_BASE_URL}#validation-methods",
            context={
                "check_name": check_name,
                "column": column,
                "actual_value": actual_value,
                "expected_value": expected_value,
                **context,
            },
        )


class RuleParseError(DuckGuardError):
    """Error parsing validation rules."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
        **context: Any,
    ):
        location = ""
        if file_path:
            location = f" in {file_path}"
            if line_number:
                location += f" at line {line_number}"

        suggestion = "Check your YAML syntax and rule format.\n"
        suggestion += "Example valid rule:\n"
        suggestion += """
columns:
  order_id:
    checks:
      - type: not_null
      - type: unique
  amount:
    checks:
      - type: between
        value: [0, 10000]
"""

        super().__init__(
            message=f"Failed to parse rules{location}: {message}",
            suggestion=suggestion,
            docs_url=f"{DOCS_BASE_URL}#yaml-rules",
            context={"file_path": file_path, "line_number": line_number, **context},
        )


class ContractViolationError(DuckGuardError):
    """Data contract was violated."""

    def __init__(
        self,
        violations: list[str],
        contract_path: str | None = None,
        **context: Any,
    ):
        message = f"Data contract violated with {len(violations)} issue(s)"
        if contract_path:
            message += f" (contract: {contract_path})"

        suggestion = "Violations:\n  - " + "\n  - ".join(violations[:5])
        if len(violations) > 5:
            suggestion += f"\n  ... and {len(violations) - 5} more"

        suggestion += "\n\nConsider updating the contract or fixing the data issues."

        super().__init__(
            message=message,
            suggestion=suggestion,
            docs_url=f"{DOCS_BASE_URL}#data-contracts",
            context={"violations": violations, "contract_path": contract_path, **context},
        )


class UnsupportedConnectorError(DuckGuardError):
    """No connector available for the data source."""

    def __init__(self, source: str, **context: Any):
        supported = [
            "CSV (.csv)",
            "Parquet (.parquet, .pq)",
            "JSON (.json, .jsonl, .ndjson)",
            "PostgreSQL (postgres://, postgresql://)",
            "MySQL (mysql://)",
            "SQLite (sqlite://)",
            "S3 (s3://)",
            "Snowflake (snowflake://)",
            "BigQuery (bigquery://)",
        ]

        suggestion = "Supported formats:\n  - " + "\n  - ".join(supported)

        super().__init__(
            message=f"No connector found for: {source}",
            suggestion=suggestion,
            docs_url=f"{DOCS_BASE_URL}#supported-connectors",
            context={"source": source, **context},
        )


# Error formatting utilities

def format_validation_failure(
    check_name: str,
    column: str | None,
    actual: Any,
    expected: Any,
    failed_rows: list | None = None,
) -> str:
    """Format a validation failure message with context.

    Args:
        check_name: Name of the failed check
        column: Column name (if column-level)
        actual: Actual value found
        expected: Expected value
        failed_rows: Sample of failing rows

    Returns:
        Formatted error message
    """
    parts = []

    if column:
        parts.append(f"Check '{check_name}' failed for column '{column}'")
    else:
        parts.append(f"Check '{check_name}' failed")

    parts.append(f"  Expected: {expected}")
    parts.append(f"  Actual: {actual}")

    if failed_rows:
        parts.append("")
        parts.append("  Sample failing rows:")
        for row in failed_rows[:5]:
            if hasattr(row, "value"):
                parts.append(f"    Row {row.row_index}: {row.value}")
            else:
                parts.append(f"    {row}")

        if len(failed_rows) > 5:
            parts.append(f"    ... and {len(failed_rows) - 5} more")

    return "\n".join(parts)


def format_multiple_failures(failures: list) -> str:
    """Format multiple validation failures into a summary.

    Args:
        failures: List of failure objects

    Returns:
        Formatted summary string
    """
    if not failures:
        return "All checks passed!"

    parts = [f"{len(failures)} validation check(s) failed:"]
    parts.append("")

    for i, failure in enumerate(failures[:10], 1):
        col = f"[{failure.column}]" if hasattr(failure, "column") and failure.column else "[table]"
        msg = failure.message if hasattr(failure, "message") else str(failure)
        parts.append(f"  {i}. {col} {msg}")

    if len(failures) > 10:
        parts.append(f"  ... and {len(failures) - 10} more failures")

    return "\n".join(parts)
