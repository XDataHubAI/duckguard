"""Data contract schema definitions.

Defines the structure of data contracts including schema, quality SLAs,
and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FieldType(Enum):
    """Supported data types for schema fields."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    TIME = "time"
    ARRAY = "array"
    OBJECT = "object"
    BINARY = "binary"
    UUID = "uuid"
    JSON = "json"
    ANY = "any"


@dataclass
class FieldConstraint:
    """Constraint on a schema field.

    Attributes:
        type: Constraint type (e.g., 'not_null', 'unique', 'range')
        value: Constraint value if applicable
        params: Additional constraint parameters
    """

    type: str
    value: Any = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaField:
    """Definition of a single field in the schema.

    Attributes:
        name: Field name
        type: Data type
        required: Whether field is required (not null)
        unique: Whether values must be unique
        description: Human-readable description
        semantic_type: Semantic type (e.g., 'email', 'phone')
        constraints: Additional constraints
        tags: Tags for categorization
        pii: Whether field contains PII
        deprecated: Whether field is deprecated
    """

    name: str
    type: FieldType | str = FieldType.STRING
    required: bool = False
    unique: bool = False
    description: str | None = None
    semantic_type: str | None = None
    constraints: list[FieldConstraint] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    pii: bool = False
    deprecated: bool = False
    default: Any = None

    def __post_init__(self):
        if isinstance(self.type, str):
            try:
                self.type = FieldType(self.type.lower())
            except ValueError:
                # Keep as string for custom types
                pass


@dataclass
class QualitySLA:
    """Quality Service Level Agreement.

    Defines the quality expectations for the data.

    Attributes:
        completeness: Minimum completeness percentage (100 - null%)
        freshness: Maximum age of data (e.g., "1h", "24h", "7d")
        uniqueness: Minimum uniqueness percentage for specified columns
        row_count_min: Minimum expected row count
        row_count_max: Maximum expected row count
        custom: Custom SLA metrics
    """

    completeness: float | None = None  # e.g., 99.5 means <= 0.5% nulls
    freshness: str | None = None       # e.g., "24h", "7d"
    uniqueness: dict[str, float] = field(default_factory=dict)  # column -> min unique %
    row_count_min: int | None = None
    row_count_max: int | None = None
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractMetadata:
    """Metadata about the data contract.

    Attributes:
        owner: Team or person responsible
        description: Human-readable description
        source_system: Origin system for the data
        consumers: List of consuming teams/systems
        schedule: Data refresh schedule (e.g., "daily", "hourly")
        tags: Tags for categorization
        links: Related documentation links
    """

    owner: str | None = None
    description: str | None = None
    source_system: str | None = None
    consumers: list[str] = field(default_factory=list)
    schedule: str | None = None
    tags: list[str] = field(default_factory=list)
    links: dict[str, str] = field(default_factory=dict)


@dataclass
class DataContract:
    """A complete data contract definition.

    Data contracts define the expected schema, quality requirements,
    and ownership for a data source.

    Attributes:
        name: Contract name (usually matches table/file name)
        version: Semantic version (e.g., "1.0.0")
        schema: List of field definitions
        quality: Quality SLA requirements
        metadata: Contract metadata
        created_at: When contract was created
        updated_at: When contract was last updated
    """

    name: str
    version: str = "1.0.0"
    schema: list[SchemaField] = field(default_factory=list)
    quality: QualitySLA = field(default_factory=QualitySLA)
    metadata: ContractMetadata = field(default_factory=ContractMetadata)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def get_field(self, name: str) -> SchemaField | None:
        """Get a field by name."""
        for f in self.schema:
            if f.name == name:
                return f
        return None

    @property
    def field_names(self) -> list[str]:
        """Get list of field names."""
        return [f.name for f in self.schema]

    @property
    def required_fields(self) -> list[SchemaField]:
        """Get list of required fields."""
        return [f for f in self.schema if f.required]

    @property
    def unique_fields(self) -> list[SchemaField]:
        """Get list of fields that must be unique."""
        return [f for f in self.schema if f.unique]

    @property
    def pii_fields(self) -> list[SchemaField]:
        """Get list of PII fields."""
        return [f for f in self.schema if f.pii]

    def add_field(
        self,
        name: str,
        type: FieldType | str = FieldType.STRING,
        required: bool = False,
        unique: bool = False,
        **kwargs
    ) -> SchemaField:
        """Add a field to the schema."""
        field_obj = SchemaField(
            name=name,
            type=type,
            required=required,
            unique=unique,
            **kwargs
        )
        self.schema.append(field_obj)
        return field_obj

    def validate_version(self, new_version: str) -> bool:
        """Check if new version is valid upgrade from current."""
        from packaging import version
        try:
            current = version.parse(self.version)
            new = version.parse(new_version)
            return new > current
        except Exception:
            return False

    def bump_version(self, bump_type: str = "patch") -> str:
        """Bump the contract version.

        Args:
            bump_type: One of 'major', 'minor', 'patch'

        Returns:
            New version string
        """
        parts = self.version.split(".")
        if len(parts) != 3:
            parts = ["1", "0", "0"]

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        self.version = f"{major}.{minor}.{patch}"
        self.updated_at = datetime.now()
        return self.version
