"""Contract diff for DuckGuard.

Detects and categorizes changes between contract versions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from duckguard.contracts.schema import DataContract, FieldType, SchemaField


class ChangeType(Enum):
    """Types of schema changes."""

    # Field changes
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_TYPE_CHANGED = "field_type_changed"
    FIELD_REQUIRED_CHANGED = "field_required_changed"
    FIELD_UNIQUE_CHANGED = "field_unique_changed"
    FIELD_CONSTRAINT_ADDED = "field_constraint_added"
    FIELD_CONSTRAINT_REMOVED = "field_constraint_removed"
    FIELD_CONSTRAINT_CHANGED = "field_constraint_changed"

    # Metadata changes
    FIELD_DESCRIPTION_CHANGED = "field_description_changed"
    FIELD_DEPRECATED = "field_deprecated"

    # Quality changes
    QUALITY_SLA_CHANGED = "quality_sla_changed"


class BreakingChangeLevel(Enum):
    """Level of breaking change."""

    NONE = "none"           # Non-breaking
    MINOR = "minor"         # Potentially breaking for some consumers
    MAJOR = "major"         # Breaking change


@dataclass
class SchemaChange:
    """A single schema change.

    Attributes:
        type: Type of change
        field: Field name (if applicable)
        breaking_level: How breaking this change is
        old_value: Previous value
        new_value: New value
        message: Human-readable description
    """

    type: ChangeType
    field: str | None
    breaking_level: BreakingChangeLevel
    old_value: Any
    new_value: Any
    message: str


@dataclass
class SchemaDiff:
    """Difference between two contract versions.

    Attributes:
        old_contract: Original contract
        new_contract: New contract
        changes: List of changes
    """

    old_contract: DataContract
    new_contract: DataContract
    changes: list[SchemaChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    @property
    def has_breaking_changes(self) -> bool:
        return any(c.breaking_level == BreakingChangeLevel.MAJOR for c in self.changes)

    @property
    def breaking_changes(self) -> list[SchemaChange]:
        return [c for c in self.changes if c.breaking_level == BreakingChangeLevel.MAJOR]

    @property
    def minor_changes(self) -> list[SchemaChange]:
        return [c for c in self.changes if c.breaking_level == BreakingChangeLevel.MINOR]

    @property
    def non_breaking_changes(self) -> list[SchemaChange]:
        return [c for c in self.changes if c.breaking_level == BreakingChangeLevel.NONE]

    def summary(self) -> str:
        """Generate a summary of changes."""
        if not self.has_changes:
            return "No changes detected."

        lines = [
            f"Changes from v{self.old_contract.version} to v{self.new_contract.version}:",
            f"  Total: {len(self.changes)} changes",
            f"  Breaking: {len(self.breaking_changes)}",
            f"  Minor: {len(self.minor_changes)}",
            f"  Non-breaking: {len(self.non_breaking_changes)}",
        ]

        if self.breaking_changes:
            lines.append("\nBreaking changes:")
            for change in self.breaking_changes:
                lines.append(f"  ❌ {change.message}")

        return "\n".join(lines)

    def suggest_version_bump(self) -> str:
        """Suggest the appropriate version bump type."""
        if self.has_breaking_changes:
            return "major"
        if self.minor_changes:
            return "minor"
        return "patch"


class ContractDiffer:
    """Compares two contract versions and detects changes."""

    # Breaking change classification
    BREAKING_CHANGES = {
        ChangeType.FIELD_REMOVED,
        ChangeType.FIELD_TYPE_CHANGED,
        ChangeType.FIELD_CONSTRAINT_ADDED,  # New constraint can break existing data
    }

    MINOR_CHANGES = {
        ChangeType.FIELD_REQUIRED_CHANGED,  # Made required
        ChangeType.FIELD_UNIQUE_CHANGED,    # Made unique
    }

    def diff(
        self,
        old_contract: DataContract,
        new_contract: DataContract
    ) -> SchemaDiff:
        """Compare two contracts and return differences.

        Args:
            old_contract: Original contract version
            new_contract: New contract version

        Returns:
            SchemaDiff with all changes
        """
        changes: list[SchemaChange] = []

        # Compare schema fields
        old_fields = {f.name: f for f in old_contract.schema}
        new_fields = {f.name: f for f in new_contract.schema}

        # Find removed fields
        for name in old_fields:
            if name not in new_fields:
                changes.append(SchemaChange(
                    type=ChangeType.FIELD_REMOVED,
                    field=name,
                    breaking_level=BreakingChangeLevel.MAJOR,
                    old_value=old_fields[name],
                    new_value=None,
                    message=f"Field '{name}' was removed",
                ))

        # Find added fields
        for name in new_fields:
            if name not in old_fields:
                new_field = new_fields[name]
                # Adding a required field is breaking
                breaking = BreakingChangeLevel.MAJOR if new_field.required else BreakingChangeLevel.NONE

                changes.append(SchemaChange(
                    type=ChangeType.FIELD_ADDED,
                    field=name,
                    breaking_level=breaking,
                    old_value=None,
                    new_value=new_field,
                    message=f"Field '{name}' was added" + (" (required)" if new_field.required else ""),
                ))

        # Find modified fields
        for name in old_fields:
            if name in new_fields:
                field_changes = self._compare_fields(old_fields[name], new_fields[name])
                changes.extend(field_changes)

        # Compare quality SLA
        quality_changes = self._compare_quality(
            old_contract.quality,
            new_contract.quality
        )
        changes.extend(quality_changes)

        return SchemaDiff(
            old_contract=old_contract,
            new_contract=new_contract,
            changes=changes,
        )

    def _compare_fields(
        self,
        old_field: SchemaField,
        new_field: SchemaField
    ) -> list[SchemaChange]:
        """Compare two field definitions."""
        changes = []
        name = old_field.name

        # Type change
        old_type = old_field.type.value if isinstance(old_field.type, FieldType) else str(old_field.type)
        new_type = new_field.type.value if isinstance(new_field.type, FieldType) else str(new_field.type)

        if old_type != new_type:
            changes.append(SchemaChange(
                type=ChangeType.FIELD_TYPE_CHANGED,
                field=name,
                breaking_level=BreakingChangeLevel.MAJOR,
                old_value=old_type,
                new_value=new_type,
                message=f"Field '{name}' type changed from '{old_type}' to '{new_type}'",
            ))

        # Required change
        if old_field.required != new_field.required:
            # Making field required is potentially breaking
            breaking = BreakingChangeLevel.MINOR if new_field.required else BreakingChangeLevel.NONE

            changes.append(SchemaChange(
                type=ChangeType.FIELD_REQUIRED_CHANGED,
                field=name,
                breaking_level=breaking,
                old_value=old_field.required,
                new_value=new_field.required,
                message=f"Field '{name}' required changed from {old_field.required} to {new_field.required}",
            ))

        # Unique change
        if old_field.unique != new_field.unique:
            # Making field unique is potentially breaking
            breaking = BreakingChangeLevel.MINOR if new_field.unique else BreakingChangeLevel.NONE

            changes.append(SchemaChange(
                type=ChangeType.FIELD_UNIQUE_CHANGED,
                field=name,
                breaking_level=breaking,
                old_value=old_field.unique,
                new_value=new_field.unique,
                message=f"Field '{name}' unique changed from {old_field.unique} to {new_field.unique}",
            ))

        # Deprecated change
        if not old_field.deprecated and new_field.deprecated:
            changes.append(SchemaChange(
                type=ChangeType.FIELD_DEPRECATED,
                field=name,
                breaking_level=BreakingChangeLevel.MINOR,
                old_value=False,
                new_value=True,
                message=f"Field '{name}' was deprecated",
            ))

        # Constraint changes
        constraint_changes = self._compare_constraints(name, old_field, new_field)
        changes.extend(constraint_changes)

        return changes

    def _compare_constraints(
        self,
        field_name: str,
        old_field: SchemaField,
        new_field: SchemaField
    ) -> list[SchemaChange]:
        """Compare constraints between field versions."""
        changes = []

        old_constraints = {c.type: c for c in old_field.constraints}
        new_constraints = {c.type: c for c in new_field.constraints}

        # Find removed constraints
        for ctype in old_constraints:
            if ctype not in new_constraints:
                changes.append(SchemaChange(
                    type=ChangeType.FIELD_CONSTRAINT_REMOVED,
                    field=field_name,
                    breaking_level=BreakingChangeLevel.NONE,  # Removing constraint is usually safe
                    old_value=old_constraints[ctype],
                    new_value=None,
                    message=f"Field '{field_name}' constraint '{ctype}' was removed",
                ))

        # Find added constraints
        for ctype in new_constraints:
            if ctype not in old_constraints:
                changes.append(SchemaChange(
                    type=ChangeType.FIELD_CONSTRAINT_ADDED,
                    field=field_name,
                    breaking_level=BreakingChangeLevel.MAJOR,  # Adding constraint can break existing data
                    old_value=None,
                    new_value=new_constraints[ctype],
                    message=f"Field '{field_name}' constraint '{ctype}' was added",
                ))

        # Find changed constraints
        for ctype in old_constraints:
            if ctype in new_constraints:
                old_c = old_constraints[ctype]
                new_c = new_constraints[ctype]

                if old_c.value != new_c.value:
                    # Determine if change is breaking
                    # Making constraints more strict is breaking
                    breaking = self._is_constraint_more_strict(ctype, old_c.value, new_c.value)

                    changes.append(SchemaChange(
                        type=ChangeType.FIELD_CONSTRAINT_CHANGED,
                        field=field_name,
                        breaking_level=breaking,
                        old_value=old_c.value,
                        new_value=new_c.value,
                        message=f"Field '{field_name}' constraint '{ctype}' changed from {old_c.value} to {new_c.value}",
                    ))

        return changes

    def _is_constraint_more_strict(
        self,
        constraint_type: str,
        old_value: Any,
        new_value: Any
    ) -> BreakingChangeLevel:
        """Determine if a constraint change makes it more strict."""
        try:
            if constraint_type == "range":
                # Smaller range is more strict
                if isinstance(old_value, list) and isinstance(new_value, list):
                    old_min, old_max = old_value
                    new_min, new_max = new_value

                    if new_min > old_min or new_max < old_max:
                        return BreakingChangeLevel.MAJOR

            elif constraint_type in ("min", "min_length"):
                # Higher min is more strict
                if new_value > old_value:
                    return BreakingChangeLevel.MAJOR

            elif constraint_type in ("max", "max_length"):
                # Lower max is more strict
                if new_value < old_value:
                    return BreakingChangeLevel.MAJOR

            elif constraint_type in ("allowed_values", "enum"):
                # Fewer allowed values is more strict
                if isinstance(old_value, list) and isinstance(new_value, list):
                    if not set(new_value).issuperset(set(old_value)):
                        return BreakingChangeLevel.MAJOR

        except Exception:
            pass

        return BreakingChangeLevel.NONE

    def _compare_quality(self, old_quality, new_quality) -> list[SchemaChange]:
        """Compare quality SLA changes."""
        changes = []

        # Completeness
        if old_quality.completeness != new_quality.completeness:
            # Higher completeness requirement is more strict
            breaking = BreakingChangeLevel.NONE
            if new_quality.completeness and (
                old_quality.completeness is None or
                new_quality.completeness > old_quality.completeness
            ):
                breaking = BreakingChangeLevel.MINOR

            changes.append(SchemaChange(
                type=ChangeType.QUALITY_SLA_CHANGED,
                field=None,
                breaking_level=breaking,
                old_value=old_quality.completeness,
                new_value=new_quality.completeness,
                message=f"Completeness SLA changed from {old_quality.completeness}% to {new_quality.completeness}%",
            ))

        # Row count min
        if old_quality.row_count_min != new_quality.row_count_min:
            breaking = BreakingChangeLevel.NONE
            if new_quality.row_count_min and (
                old_quality.row_count_min is None or
                new_quality.row_count_min > old_quality.row_count_min
            ):
                breaking = BreakingChangeLevel.MINOR

            changes.append(SchemaChange(
                type=ChangeType.QUALITY_SLA_CHANGED,
                field=None,
                breaking_level=breaking,
                old_value=old_quality.row_count_min,
                new_value=new_quality.row_count_min,
                message=f"Row count minimum changed from {old_quality.row_count_min} to {new_quality.row_count_min}",
            ))

        return changes


def diff_contracts(
    old_contract: DataContract,
    new_contract: DataContract
) -> SchemaDiff:
    """Compare two contract versions.

    Args:
        old_contract: Original contract
        new_contract: New contract

    Returns:
        SchemaDiff with all changes
    """
    differ = ContractDiffer()
    return differ.diff(old_contract, new_contract)
