"""Data contract validator for DuckGuard.

Validates datasets against data contracts to ensure compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from duckguard.connectors import connect
from duckguard.contracts.schema import DataContract, SchemaField
from duckguard.core.dataset import Dataset


class ViolationType(Enum):
    """Types of contract violations."""

    # Schema violations
    MISSING_FIELD = "missing_field"
    EXTRA_FIELD = "extra_field"
    TYPE_MISMATCH = "type_mismatch"
    REQUIRED_NULL = "required_null"
    UNIQUE_VIOLATION = "unique_violation"
    CONSTRAINT_VIOLATION = "constraint_violation"

    # Quality violations
    COMPLETENESS_VIOLATION = "completeness_violation"
    FRESHNESS_VIOLATION = "freshness_violation"
    ROW_COUNT_VIOLATION = "row_count_violation"
    UNIQUENESS_SLA_VIOLATION = "uniqueness_sla_violation"


class ViolationSeverity(Enum):
    """Severity levels for violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ContractViolation:
    """A single contract violation.

    Attributes:
        type: Type of violation
        severity: Severity level
        field: Field name (if applicable)
        message: Human-readable message
        expected: Expected value
        actual: Actual value
        details: Additional details
    """

    type: ViolationType
    severity: ViolationSeverity
    field: str | None
    message: str
    expected: Any = None
    actual: Any = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractValidationResult:
    """Result of validating a dataset against a contract.

    Attributes:
        contract: The contract that was validated
        source: The data source that was validated
        passed: Whether validation passed (no errors)
        violations: List of violations found
        validated_at: When validation was performed
        statistics: Validation statistics
    """

    contract: DataContract
    source: str
    passed: bool
    violations: list[ContractViolation] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)
    statistics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Alias for passed - True if no errors."""
        return self.passed

    @property
    def schema_valid(self) -> bool:
        """Check if schema validation passed."""
        schema_types = {ViolationType.MISSING_FIELD, ViolationType.TYPE_MISMATCH, ViolationType.EXTRA_FIELD}
        return not any(
            v.severity == ViolationSeverity.ERROR and v.type in schema_types
            for v in self.violations
        )

    @property
    def quality_valid(self) -> bool:
        """Check if quality SLA validation passed."""
        quality_types = {
            ViolationType.COMPLETENESS_VIOLATION,
            ViolationType.FRESHNESS_VIOLATION,
            ViolationType.ROW_COUNT_VIOLATION,
            ViolationType.UNIQUENESS_SLA_VIOLATION,
        }
        return not any(
            v.severity == ViolationSeverity.ERROR and v.type in quality_types
            for v in self.violations
        )

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.WARNING)

    @property
    def errors(self) -> list[str]:
        """Get error messages as strings."""
        return [v.message for v in self.violations if v.severity == ViolationSeverity.ERROR]

    @property
    def warnings(self) -> list[str]:
        """Get warning messages as strings."""
        return [v.message for v in self.violations if v.severity == ViolationSeverity.WARNING]

    def summary(self) -> str:
        """Generate a summary string."""
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"Contract '{self.contract.name}' v{self.contract.version}: {status}\n"
            f"  Errors: {self.error_count}, Warnings: {self.warning_count}"
        )


class ContractValidator:
    """Validates datasets against data contracts."""

    def __init__(self, strict_mode: bool = False):
        """Initialize validator.

        Args:
            strict_mode: If True, treat extra fields as errors
        """
        self.strict_mode = strict_mode

    def validate(
        self,
        contract: DataContract,
        source: str | Dataset
    ) -> ContractValidationResult:
        """Validate a data source against a contract.

        Args:
            contract: The contract to validate against
            source: Data source path or Dataset

        Returns:
            ContractValidationResult
        """
        if isinstance(source, str):
            dataset = connect(source)
            source_str = source
        else:
            dataset = source
            source_str = dataset.source

        violations: list[ContractViolation] = []
        statistics: dict[str, Any] = {
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
            "fields_checked": len(contract.schema),
        }

        # 1. Validate schema
        schema_violations = self._validate_schema(contract, dataset)
        violations.extend(schema_violations)

        # 2. Validate field constraints
        for field_def in contract.schema:
            if field_def.name in dataset.columns:
                field_violations = self._validate_field(field_def, dataset)
                violations.extend(field_violations)

        # 3. Validate quality SLAs
        quality_violations = self._validate_quality(contract, dataset)
        violations.extend(quality_violations)

        # Determine if passed (no errors)
        passed = not any(v.severity == ViolationSeverity.ERROR for v in violations)

        return ContractValidationResult(
            contract=contract,
            source=source_str,
            passed=passed,
            violations=violations,
            statistics=statistics,
        )

    def _validate_schema(
        self,
        contract: DataContract,
        dataset: Dataset
    ) -> list[ContractViolation]:
        """Validate schema structure."""
        violations = []

        contract_fields = set(f.name for f in contract.schema)
        dataset_fields = set(dataset.columns)

        # Check for missing fields
        missing = contract_fields - dataset_fields
        for field_name in missing:
            field_def = contract.get_field(field_name)
            severity = ViolationSeverity.ERROR if field_def and field_def.required else ViolationSeverity.WARNING

            violations.append(ContractViolation(
                type=ViolationType.MISSING_FIELD,
                severity=severity,
                field=field_name,
                message=f"Field '{field_name}' defined in contract but not found in data",
                expected="present",
                actual="missing",
            ))

        # Check for extra fields
        extra = dataset_fields - contract_fields
        for field_name in extra:
            severity = ViolationSeverity.ERROR if self.strict_mode else ViolationSeverity.INFO

            violations.append(ContractViolation(
                type=ViolationType.EXTRA_FIELD,
                severity=severity,
                field=field_name,
                message=f"Field '{field_name}' found in data but not defined in contract",
                expected="not present",
                actual="present",
            ))

        return violations

    def _validate_field(
        self,
        field_def: SchemaField,
        dataset: Dataset
    ) -> list[ContractViolation]:
        """Validate a single field against its definition."""
        violations = []
        col = dataset[field_def.name]

        # Check required (not null)
        if field_def.required:
            null_count = col.null_count
            if null_count > 0:
                violations.append(ContractViolation(
                    type=ViolationType.REQUIRED_NULL,
                    severity=ViolationSeverity.ERROR,
                    field=field_def.name,
                    message=f"Required field '{field_def.name}' has {null_count} null values",
                    expected=0,
                    actual=null_count,
                    details={"null_percent": col.null_percent},
                ))

        # Check unique
        if field_def.unique:
            unique_pct = col.unique_percent
            if unique_pct < 100:
                duplicate_count = col.total_count - col.unique_count
                violations.append(ContractViolation(
                    type=ViolationType.UNIQUE_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=field_def.name,
                    message=f"Field '{field_def.name}' must be unique but has {duplicate_count} duplicates",
                    expected=100,
                    actual=unique_pct,
                    details={"duplicate_count": duplicate_count},
                ))

        # Check constraints
        for constraint in field_def.constraints:
            constraint_violations = self._validate_constraint(
                field_def.name, col, constraint
            )
            violations.extend(constraint_violations)

        return violations

    def _validate_constraint(
        self,
        field_name: str,
        col,
        constraint
    ) -> list[ContractViolation]:
        """Validate a field constraint."""
        violations = []

        if constraint.type == "range":
            if isinstance(constraint.value, (list, tuple)) and len(constraint.value) == 2:
                min_val, max_val = constraint.value
                result = col.between(min_val, max_val)
                if not result.passed:
                    violations.append(ContractViolation(
                        type=ViolationType.CONSTRAINT_VIOLATION,
                        severity=ViolationSeverity.ERROR,
                        field=field_name,
                        message=f"Field '{field_name}' has {result.actual_value} values outside range [{min_val}, {max_val}]",
                        expected=f"[{min_val}, {max_val}]",
                        actual=result.actual_value,
                    ))

        elif constraint.type == "min":
            actual_min = col.min
            if actual_min is not None and actual_min < constraint.value:
                violations.append(ContractViolation(
                    type=ViolationType.CONSTRAINT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=field_name,
                    message=f"Field '{field_name}' min value {actual_min} is below constraint {constraint.value}",
                    expected=f">= {constraint.value}",
                    actual=actual_min,
                ))

        elif constraint.type == "max":
            actual_max = col.max
            if actual_max is not None and actual_max > constraint.value:
                violations.append(ContractViolation(
                    type=ViolationType.CONSTRAINT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=field_name,
                    message=f"Field '{field_name}' max value {actual_max} exceeds constraint {constraint.value}",
                    expected=f"<= {constraint.value}",
                    actual=actual_max,
                ))

        elif constraint.type == "pattern":
            result = col.matches(constraint.value)
            if not result.passed:
                violations.append(ContractViolation(
                    type=ViolationType.CONSTRAINT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=field_name,
                    message=f"Field '{field_name}' has {result.actual_value} values not matching pattern",
                    expected=f"matches '{constraint.value}'",
                    actual=result.actual_value,
                ))

        elif constraint.type in ("allowed_values", "enum"):
            result = col.isin(constraint.value)
            if not result.passed:
                violations.append(ContractViolation(
                    type=ViolationType.CONSTRAINT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=field_name,
                    message=f"Field '{field_name}' has {result.actual_value} values not in allowed set",
                    expected=f"in {constraint.value}",
                    actual=result.actual_value,
                ))

        return violations

    def _validate_quality(
        self,
        contract: DataContract,
        dataset: Dataset
    ) -> list[ContractViolation]:
        """Validate quality SLAs."""
        violations = []
        quality = contract.quality

        # Completeness check
        if quality.completeness is not None:
            # Calculate overall null percentage
            total_cells = dataset.row_count * dataset.column_count
            total_nulls = sum(dataset[col].null_count for col in dataset.columns)
            actual_completeness = 100 - (total_nulls / total_cells * 100) if total_cells > 0 else 100

            if actual_completeness < quality.completeness:
                violations.append(ContractViolation(
                    type=ViolationType.COMPLETENESS_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=None,
                    message=f"Data completeness {actual_completeness:.2f}% is below SLA of {quality.completeness}%",
                    expected=f">= {quality.completeness}%",
                    actual=f"{actual_completeness:.2f}%",
                ))

        # Row count checks
        if quality.row_count_min is not None:
            if dataset.row_count < quality.row_count_min:
                violations.append(ContractViolation(
                    type=ViolationType.ROW_COUNT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=None,
                    message=f"Row count {dataset.row_count:,} is below minimum of {quality.row_count_min:,}",
                    expected=f">= {quality.row_count_min:,}",
                    actual=dataset.row_count,
                ))

        if quality.row_count_max is not None:
            if dataset.row_count > quality.row_count_max:
                violations.append(ContractViolation(
                    type=ViolationType.ROW_COUNT_VIOLATION,
                    severity=ViolationSeverity.ERROR,
                    field=None,
                    message=f"Row count {dataset.row_count:,} exceeds maximum of {quality.row_count_max:,}",
                    expected=f"<= {quality.row_count_max:,}",
                    actual=dataset.row_count,
                ))

        # Uniqueness SLA checks
        for col_name, min_unique_pct in quality.uniqueness.items():
            if col_name in dataset.columns:
                col = dataset[col_name]
                actual_unique = col.unique_percent

                if actual_unique < min_unique_pct:
                    violations.append(ContractViolation(
                        type=ViolationType.UNIQUENESS_SLA_VIOLATION,
                        severity=ViolationSeverity.ERROR,
                        field=col_name,
                        message=f"Field '{col_name}' uniqueness {actual_unique:.2f}% is below SLA of {min_unique_pct}%",
                        expected=f">= {min_unique_pct}%",
                        actual=f"{actual_unique:.2f}%",
                    ))

        return violations


def validate_contract(
    contract: DataContract,
    source: str | Dataset,
    strict_mode: bool = False
) -> ContractValidationResult:
    """Validate a data source against a contract.

    Args:
        contract: The contract to validate against
        source: Data source path or Dataset
        strict_mode: Treat extra fields as errors

    Returns:
        ContractValidationResult
    """
    validator = ContractValidator(strict_mode=strict_mode)
    return validator.validate(contract, source)
