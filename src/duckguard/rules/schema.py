"""Schema definitions for YAML-based rules.

Defines the data structures that represent validation rules loaded from YAML.
The schema is designed to be simple and readable, avoiding complex DSL syntax.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CheckType(Enum):
    """Types of validation checks."""

    # Null checks
    NOT_NULL = "not_null"
    NULL_PERCENT = "null_percent"

    # Uniqueness checks
    UNIQUE = "unique"
    UNIQUE_PERCENT = "unique_percent"
    NO_DUPLICATES = "no_duplicates"

    # Value checks
    RANGE = "range"
    BETWEEN = "between"
    MIN = "min"
    MAX = "max"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NON_NEGATIVE = "non_negative"

    # String checks
    PATTERN = "pattern"
    LENGTH = "length"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"

    # Enum/Set checks
    ALLOWED_VALUES = "allowed_values"
    ISIN = "isin"
    NOT_IN = "not_in"

    # Type checks
    TYPE = "type"
    SEMANTIC_TYPE = "semantic_type"

    # Statistical checks
    MEAN = "mean"
    STDDEV = "stddev"

    # Anomaly checks
    ANOMALY = "anomaly"

    # Row-level checks
    ROW_COUNT = "row_count"

    # Custom SQL
    CUSTOM_SQL = "custom_sql"

    # Cross-dataset / Reference checks
    EXISTS_IN = "exists_in"              # FK check: all values exist in reference
    REFERENCES = "references"            # FK check with options (allow_nulls, etc.)
    MATCHES_VALUES = "matches_values"    # Column values match between datasets
    ROW_COUNT_MATCHES = "row_count_matches"  # Row counts match between datasets

    # Conditional checks (DuckGuard 3.0)
    NOT_NULL_WHEN = "not_null_when"      # Not null when condition is true
    UNIQUE_WHEN = "unique_when"          # Unique when condition is true
    BETWEEN_WHEN = "between_when"        # Between min/max when condition is true
    ISIN_WHEN = "isin_when"              # In allowed values when condition is true
    PATTERN_WHEN = "pattern_when"        # Matches pattern when condition is true

    # Multi-column checks (DuckGuard 3.0)
    COLUMN_PAIR_SATISFY = "column_pair_satisfy"      # Column pair satisfies expression
    MULTICOLUMN_UNIQUE = "multicolumn_unique"        # Composite uniqueness
    MULTICOLUMN_SUM = "multicolumn_sum"              # Sum constraint
    COLUMN_A_GT_B = "column_a_gt_b"                  # A > B
    COLUMN_A_GTE_B = "column_a_gte_b"                # A >= B
    COLUMN_A_LT_B = "column_a_lt_b"                  # A < B
    COLUMN_A_LTE_B = "column_a_lte_b"                # A <= B
    COLUMN_A_EQ_B = "column_a_eq_b"                  # A = B

    # Query-based checks (DuckGuard 3.0)
    QUERY_NO_ROWS = "query_no_rows"                  # Query returns no rows
    QUERY_RETURNS_ROWS = "query_returns_rows"        # Query returns at least one row
    QUERY_RESULT_EQUALS = "query_result_equals"      # Query result equals expected value
    QUERY_RESULT_BETWEEN = "query_result_between"    # Query result in range
    QUERY_RESULT_GT = "query_result_gt"              # Query result > threshold
    QUERY_RESULT_LT = "query_result_lt"              # Query result < threshold

    # Distributional checks (DuckGuard 3.0)
    DISTRIBUTION_NORMAL = "distribution_normal"      # Test for normal distribution
    DISTRIBUTION_UNIFORM = "distribution_uniform"    # Test for uniform distribution
    DISTRIBUTION_KS_TEST = "distribution_ks_test"    # Kolmogorov-Smirnov test
    DISTRIBUTION_CHI_SQUARE = "distribution_chi_square"  # Chi-square goodness-of-fit test


class Severity(Enum):
    """Severity levels for rule violations."""

    ERROR = "error"      # Fails the check
    WARNING = "warning"  # Reports but doesn't fail
    INFO = "info"        # Informational only


@dataclass
class Check:
    """A single validation check.

    Attributes:
        type: The type of check to perform
        value: The expected value or threshold
        operator: Comparison operator (=, <, >, <=, >=, !=)
        severity: How severe a violation is
        message: Custom message on failure
        enabled: Whether the check is active
    """

    type: CheckType
    value: Any = None
    operator: str = "="
    severity: Severity = Severity.ERROR
    message: str | None = None
    enabled: bool = True

    # Additional parameters for complex checks
    params: dict[str, Any] = field(default_factory=dict)

    # Store the original column name for context
    _column: str | None = field(default=None, repr=False)

    def __post_init__(self):
        # Convert string type to enum if needed
        if isinstance(self.type, str):
            self.type = CheckType(self.type)
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)

    @property
    def expression(self) -> str:
        """Generate a human-readable expression for this check."""
        col = self._column or ""

        if self.type == CheckType.NOT_NULL:
            return f"{col} is not null" if col else "is not null"
        elif self.type == CheckType.UNIQUE:
            return f"{col} is unique" if col else "is unique"
        elif self.type == CheckType.NO_DUPLICATES:
            return f"{col} has no duplicates" if col else "has no duplicates"
        elif self.type == CheckType.ROW_COUNT:
            return f"row_count {self.operator} {self.value}"
        elif self.type == CheckType.NULL_PERCENT:
            return f"{col} null_percent {self.operator} {self.value}" if col else f"null_percent {self.operator} {self.value}"
        elif self.type == CheckType.UNIQUE_PERCENT:
            return f"{col} unique_percent {self.operator} {self.value}" if col else f"unique_percent {self.operator} {self.value}"
        elif self.type == CheckType.BETWEEN or self.type == CheckType.RANGE:
            if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                return f"{col} between {self.value[0]} and {self.value[1]}" if col else f"between {self.value[0]} and {self.value[1]}"
        elif self.type == CheckType.MIN:
            return f"{col} >= {self.value}" if col else f">= {self.value}"
        elif self.type == CheckType.MAX:
            return f"{col} <= {self.value}" if col else f"<= {self.value}"
        elif self.type == CheckType.POSITIVE:
            return f"{col} > 0" if col else "> 0"
        elif self.type == CheckType.NEGATIVE:
            return f"{col} < 0" if col else "< 0"
        elif self.type == CheckType.NON_NEGATIVE:
            return f"{col} >= 0" if col else ">= 0"
        elif self.type == CheckType.PATTERN:
            return f"{col} matches '{self.value}'" if col else f"matches '{self.value}'"
        elif self.type == CheckType.ALLOWED_VALUES or self.type == CheckType.ISIN:
            return f"{col} in {self.value}" if col else f"in {self.value}"
        elif self.type == CheckType.EXISTS_IN:
            ref = self.params.get("dataset", "?") + "." + self.params.get("column", "?")
            return f"{col} exists in {ref}" if col else f"exists in {ref}"
        elif self.type == CheckType.REFERENCES:
            ref = self.params.get("dataset", "?") + "." + self.params.get("column", "?")
            return f"{col} references {ref}" if col else f"references {ref}"
        elif self.type == CheckType.MATCHES_VALUES:
            ref = self.params.get("dataset", "?") + "." + self.params.get("column", "?")
            return f"{col} matches values in {ref}" if col else f"matches values in {ref}"
        elif self.type == CheckType.ROW_COUNT_MATCHES:
            ref = self.params.get("dataset", "?")
            tolerance = self.params.get("tolerance", 0)
            return f"row_count matches {ref} (tolerance: {tolerance})"

        # Fallback
        if col:
            return f"{col} {self.type.value} {self.value}" if self.value else f"{col} {self.type.value}"
        return f"{self.type.value} {self.value}" if self.value else self.type.value


@dataclass
class ColumnRules:
    """Rules for a specific column.

    Attributes:
        name: Column name
        checks: List of checks to apply
        semantic_type: Detected or specified semantic type
        description: Human-readable description
        tags: Tags for grouping/filtering
    """

    name: str
    checks: list[Check] = field(default_factory=list)
    semantic_type: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class TableRules:
    """Table-level rules (row count, freshness, etc).

    Attributes:
        checks: List of table-level checks
    """

    checks: list[Check] = field(default_factory=list)


@dataclass
class SimpleCheck:
    """A simple check with just an expression string.

    Used for the simplified YAML rule syntax.
    """
    expression: str
    column: str | None = None
    check_type: CheckType | None = None
    value: Any = None
    operator: str = "="


@dataclass
class RuleSet:
    """A complete set of validation rules for a data source.

    Attributes:
        source: Data source path or connection string
        name: Human-readable name for this rule set
        version: Version of the rule set
        description: Description of what this validates
        columns: Column-specific rules
        table: Table-level rules
        settings: Global settings for rule execution
    """

    source: str | None = None
    name: str | None = None
    version: str = "1.0"
    description: str | None = None
    columns: dict[str, ColumnRules] = field(default_factory=dict)
    table: TableRules = field(default_factory=TableRules)
    settings: dict[str, Any] = field(default_factory=dict)
    # Simple rules list for the simplified format
    _simple_checks: list[SimpleCheck] = field(default_factory=list)

    @property
    def dataset(self) -> str | None:
        """Alias for name (for compatibility with simple syntax)."""
        return self.name

    @property
    def checks(self) -> list[SimpleCheck]:
        """Get all checks as a simple list."""
        return self._simple_checks

    def get_column_rules(self, column_name: str) -> ColumnRules | None:
        """Get rules for a specific column."""
        return self.columns.get(column_name)

    def add_simple_check(self, expression: str) -> None:
        """Add a simple check by expression string."""
        self._simple_checks.append(SimpleCheck(expression=expression))

    def add_column_check(
        self,
        column_name: str,
        check_type: CheckType | str,
        value: Any = None,
        **kwargs
    ) -> None:
        """Add a check to a column."""
        if column_name not in self.columns:
            self.columns[column_name] = ColumnRules(name=column_name)

        check = Check(
            type=check_type if isinstance(check_type, CheckType) else CheckType(check_type),
            value=value,
            _column=column_name,
            **kwargs
        )
        self.columns[column_name].checks.append(check)

    def add_table_check(
        self,
        check_type: CheckType | str,
        value: Any = None,
        **kwargs
    ) -> None:
        """Add a table-level check."""
        check = Check(
            type=check_type if isinstance(check_type, CheckType) else CheckType(check_type),
            value=value,
            **kwargs
        )
        self.table.checks.append(check)

    @property
    def total_checks(self) -> int:
        """Total number of checks in this rule set."""
        column_checks = sum(len(col.checks) for col in self.columns.values())
        table_checks = len(self.table.checks)
        return column_checks + table_checks


# Built-in patterns for common validations
BUILTIN_PATTERNS = {
    "email": r"^[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}$",
    "phone": r"^\+?[\d\s\-\(\)]{10,}$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "url": r"^https?://[\w\.\-]+(/[\w\.\-\?=&%]*)?$",
    "ip_address": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
    "ipv6": r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$",
    "date_iso": r"^\d{4}-\d{2}-\d{2}$",
    "datetime_iso": r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
    "ssn": r"^\d{3}-\d{2}-\d{4}$",
    "zip_us": r"^\d{5}(-\d{4})?$",
    "credit_card": r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$",
    "identifier": r"^[A-Z][A-Z0-9]*[-_]?\d+$|^[A-Z]{2,}[-_][A-Z0-9]+$",
    "slug": r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    "alpha": r"^[a-zA-Z]+$",
    "alphanumeric": r"^[a-zA-Z0-9]+$",
    "numeric": r"^-?\d+\.?\d*$",
}

# Patterns that must be matched case-sensitively
CASE_SENSITIVE_PATTERNS = {"slug", "identifier"}
