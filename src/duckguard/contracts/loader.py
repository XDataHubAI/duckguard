"""Data contract loader for DuckGuard.

Parses YAML contract files into DataContract objects.

Example contract YAML:
    contract:
      name: orders
      version: "1.2.0"

      schema:
        - name: order_id
          type: string
          required: true
          unique: true

        - name: amount
          type: decimal
          required: true
          constraints:
            - type: range
              value: [0, 100000]

        - name: email
          type: string
          semantic_type: email
          pii: true

      quality:
        completeness: 99.5
        freshness: "24h"
        row_count_min: 1000

      metadata:
        owner: platform-team
        description: Order transactions from checkout
        consumers:
          - analytics
          - finance
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from duckguard.contracts.schema import (
    ContractMetadata,
    DataContract,
    FieldConstraint,
    FieldType,
    QualitySLA,
    SchemaField,
)


class ContractParseError(Exception):
    """Raised when contract parsing fails."""

    def __init__(self, message: str, location: str | None = None):
        self.location = location
        full_message = f"{message}" if not location else f"{message} (at {location})"
        super().__init__(full_message)


def load_contract(path: str | Path) -> DataContract:
    """Load a data contract from a YAML file.

    Args:
        path: Path to the contract YAML file

    Returns:
        Parsed DataContract

    Raises:
        FileNotFoundError: If file doesn't exist
        ContractParseError: If YAML is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    return load_contract_from_string(content, source_file=str(path))


def load_contract_from_string(
    content: str,
    source_file: str | None = None
) -> DataContract:
    """Load a data contract from a YAML string.

    Args:
        content: YAML content
        source_file: Optional source file for error messages

    Returns:
        Parsed DataContract
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ContractParseError(f"Invalid YAML: {e}", source_file)

    if not data:
        raise ContractParseError("Empty contract file", source_file)

    # Support both root-level and nested 'contract' key
    if "contract" in data:
        data = data["contract"]

    return _parse_contract(data, source_file)


def _parse_contract(data: dict[str, Any], source_file: str | None = None) -> DataContract:
    """Parse dictionary into DataContract."""
    # Required: name
    name = data.get("name")
    if not name:
        raise ContractParseError("Contract must have a 'name'", source_file)

    contract = DataContract(
        name=name,
        version=str(data.get("version", "1.0.0")),
    )

    # Parse timestamps
    if "created_at" in data:
        contract.created_at = _parse_datetime(data["created_at"])
    if "updated_at" in data:
        contract.updated_at = _parse_datetime(data["updated_at"])

    # Parse schema
    schema_data = data.get("schema", [])
    if isinstance(schema_data, list):
        for i, field_data in enumerate(schema_data):
            try:
                field_obj = _parse_schema_field(field_data)
                contract.schema.append(field_obj)
            except Exception as e:
                raise ContractParseError(
                    f"Invalid schema field at index {i}: {e}",
                    source_file
                )

    # Parse quality SLA
    quality_data = data.get("quality", {})
    if quality_data:
        contract.quality = _parse_quality_sla(quality_data)

    # Parse metadata
    metadata_data = data.get("metadata", {})
    if metadata_data:
        contract.metadata = _parse_metadata(metadata_data)

    return contract


def _parse_schema_field(data: dict[str, Any] | str) -> SchemaField:
    """Parse a schema field definition."""
    # Handle simple string format: "field_name: type"
    if isinstance(data, str):
        parts = data.split(":")
        name = parts[0].strip()
        type_str = parts[1].strip() if len(parts) > 1 else "string"
        return SchemaField(name=name, type=type_str)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid field format: {data}")

    name = data.get("name")
    if not name:
        raise ValueError("Field must have a 'name'")

    # Parse type
    type_value = data.get("type", "string")
    try:
        if isinstance(type_value, str):
            field_type = FieldType(type_value.lower())
        else:
            field_type = type_value
    except ValueError:
        field_type = type_value  # Keep as string for custom types

    # Parse constraints
    constraints = []
    constraints_data = data.get("constraints", [])
    for c in constraints_data:
        if isinstance(c, dict):
            constraints.append(FieldConstraint(
                type=c.get("type", "custom"),
                value=c.get("value"),
                params=c.get("params", {}),
            ))
        elif isinstance(c, str):
            constraints.append(FieldConstraint(type=c))

    return SchemaField(
        name=name,
        type=field_type,
        required=data.get("required", False),
        unique=data.get("unique", False),
        description=data.get("description"),
        semantic_type=data.get("semantic_type"),
        constraints=constraints,
        tags=data.get("tags", []),
        pii=data.get("pii", False),
        deprecated=data.get("deprecated", False),
        default=data.get("default"),
    )


def _parse_quality_sla(data: dict[str, Any]) -> QualitySLA:
    """Parse quality SLA definition."""
    # Parse uniqueness dict
    uniqueness = {}
    uniqueness_data = data.get("uniqueness", {})
    if isinstance(uniqueness_data, dict):
        uniqueness = {k: float(v) for k, v in uniqueness_data.items()}
    elif isinstance(uniqueness_data, list):
        # Handle list format: ["col1", "col2"] means 100% unique
        uniqueness = {col: 100.0 for col in uniqueness_data}

    return QualitySLA(
        completeness=_parse_percentage(data.get("completeness")),
        freshness=data.get("freshness"),
        uniqueness=uniqueness,
        row_count_min=data.get("row_count_min") or data.get("min_rows"),
        row_count_max=data.get("row_count_max") or data.get("max_rows"),
        custom=data.get("custom", {}),
    )


def _parse_metadata(data: dict[str, Any]) -> ContractMetadata:
    """Parse contract metadata."""
    return ContractMetadata(
        owner=data.get("owner"),
        description=data.get("description"),
        source_system=data.get("source_system") or data.get("source"),
        consumers=data.get("consumers", []),
        schedule=data.get("schedule"),
        tags=data.get("tags", []),
        links=data.get("links", {}),
    )


def _parse_percentage(value: Any) -> float | None:
    """Parse a percentage value."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Handle "99.5%" format
        value = value.strip().rstrip("%")
        return float(value)

    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a datetime value."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

    return None


def contract_to_yaml(contract: DataContract) -> str:
    """Convert a DataContract to YAML string.

    Args:
        contract: Contract to convert

    Returns:
        YAML string
    """
    data: dict[str, Any] = {
        "contract": {
            "name": contract.name,
            "version": contract.version,
        }
    }

    # Add schema
    if contract.schema:
        data["contract"]["schema"] = []
        for field_obj in contract.schema:
            field_dict: dict[str, Any] = {
                "name": field_obj.name,
                "type": field_obj.type.value if isinstance(field_obj.type, FieldType) else str(field_obj.type),
            }
            if field_obj.required:
                field_dict["required"] = True
            if field_obj.unique:
                field_dict["unique"] = True
            if field_obj.description:
                field_dict["description"] = field_obj.description
            if field_obj.semantic_type:
                field_dict["semantic_type"] = field_obj.semantic_type
            if field_obj.pii:
                field_dict["pii"] = True
            if field_obj.constraints:
                field_dict["constraints"] = [
                    {"type": c.type, "value": c.value} if c.value else {"type": c.type}
                    for c in field_obj.constraints
                ]

            data["contract"]["schema"].append(field_dict)

    # Add quality
    quality_dict: dict[str, Any] = {}
    if contract.quality.completeness is not None:
        quality_dict["completeness"] = contract.quality.completeness
    if contract.quality.freshness:
        quality_dict["freshness"] = contract.quality.freshness
    if contract.quality.uniqueness:
        quality_dict["uniqueness"] = contract.quality.uniqueness
    if contract.quality.row_count_min is not None:
        quality_dict["row_count_min"] = contract.quality.row_count_min
    if contract.quality.row_count_max is not None:
        quality_dict["row_count_max"] = contract.quality.row_count_max

    if quality_dict:
        data["contract"]["quality"] = quality_dict

    # Add metadata
    meta_dict: dict[str, Any] = {}
    if contract.metadata.owner:
        meta_dict["owner"] = contract.metadata.owner
    if contract.metadata.description:
        meta_dict["description"] = contract.metadata.description
    if contract.metadata.source_system:
        meta_dict["source_system"] = contract.metadata.source_system
    if contract.metadata.consumers:
        meta_dict["consumers"] = contract.metadata.consumers
    if contract.metadata.schedule:
        meta_dict["schedule"] = contract.metadata.schedule
    if contract.metadata.tags:
        meta_dict["tags"] = contract.metadata.tags

    if meta_dict:
        data["contract"]["metadata"] = meta_dict

    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
