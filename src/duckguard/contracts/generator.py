"""Data contract generator for DuckGuard.

Auto-generates data contracts from existing data sources.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from duckguard.connectors import connect
from duckguard.contracts.loader import contract_to_yaml
from duckguard.contracts.schema import (
    ContractMetadata,
    DataContract,
    FieldConstraint,
    FieldType,
    QualitySLA,
    SchemaField,
)
from duckguard.core.dataset import Dataset
from duckguard.semantic import SemanticAnalyzer, SemanticType


class ContractGenerator:
    """Generates data contracts from data analysis."""

    # Type mapping from Python/DB types to FieldType
    TYPE_MAPPING = {
        "int": FieldType.INTEGER,
        "int64": FieldType.INTEGER,
        "int32": FieldType.INTEGER,
        "integer": FieldType.INTEGER,
        "bigint": FieldType.INTEGER,
        "float": FieldType.FLOAT,
        "float64": FieldType.FLOAT,
        "double": FieldType.FLOAT,
        "decimal": FieldType.DECIMAL,
        "numeric": FieldType.DECIMAL,
        "bool": FieldType.BOOLEAN,
        "boolean": FieldType.BOOLEAN,
        "str": FieldType.STRING,
        "string": FieldType.STRING,
        "varchar": FieldType.STRING,
        "text": FieldType.STRING,
        "date": FieldType.DATE,
        "datetime": FieldType.DATETIME,
        "timestamp": FieldType.TIMESTAMP,
        "time": FieldType.TIME,
    }

    # Semantic type to field type mapping
    SEMANTIC_TYPE_MAPPING = {
        SemanticType.EMAIL: FieldType.STRING,
        SemanticType.PHONE: FieldType.STRING,
        SemanticType.URL: FieldType.STRING,
        SemanticType.UUID: FieldType.UUID,
        SemanticType.DATE: FieldType.DATE,
        SemanticType.DATETIME: FieldType.DATETIME,
        SemanticType.TIMESTAMP: FieldType.TIMESTAMP,
        SemanticType.TIME: FieldType.TIME,
        SemanticType.CURRENCY: FieldType.DECIMAL,
        SemanticType.PERCENTAGE: FieldType.FLOAT,
        SemanticType.BOOLEAN: FieldType.BOOLEAN,
        SemanticType.LATITUDE: FieldType.FLOAT,
        SemanticType.LONGITUDE: FieldType.FLOAT,
        SemanticType.AGE: FieldType.INTEGER,
        SemanticType.YEAR: FieldType.INTEGER,
    }

    def __init__(self):
        self._analyzer = SemanticAnalyzer()

    def generate(
        self,
        source: str | Dataset,
        name: str | None = None,
        owner: str | None = None,
        include_constraints: bool = True,
        include_quality_sla: bool = True,
    ) -> DataContract:
        """Generate a contract from a data source.

        Args:
            source: Data source path or Dataset
            name: Contract name (defaults to source name)
            owner: Contract owner
            include_constraints: Include inferred constraints
            include_quality_sla: Include quality SLA

        Returns:
            Generated DataContract
        """
        if isinstance(source, str):
            dataset = connect(source)
            source_path = source
        else:
            dataset = source
            source_path = dataset.source

        # Determine name
        if not name:
            name = Path(source_path).stem if source_path else "dataset"

        contract = DataContract(
            name=name,
            version="1.0.0",
            created_at=datetime.now(),
            metadata=ContractMetadata(
                owner=owner,
                source_system=source_path,
            ),
        )

        # Analyze dataset semantically
        analysis = self._analyzer.analyze(dataset)

        # Generate schema fields
        for col_analysis in analysis.columns:
            field_def = self._generate_field(
                col_analysis,
                dataset,
                include_constraints
            )
            contract.schema.append(field_def)

        # Generate quality SLA
        if include_quality_sla:
            contract.quality = self._generate_quality_sla(dataset, analysis)

        # Add warnings to metadata
        if analysis.warnings:
            contract.metadata.tags.append("has_pii")

        return contract

    def _generate_field(
        self,
        col_analysis,
        dataset: Dataset,
        include_constraints: bool
    ) -> SchemaField:
        """Generate a schema field from column analysis."""
        col = dataset[col_analysis.name]

        # Determine field type
        field_type = self._infer_type(col_analysis)

        # Determine if required
        required = col.null_count == 0

        # Determine if unique
        unique = col.unique_percent == 100 and col.null_count == 0

        field_def = SchemaField(
            name=col_analysis.name,
            type=field_type,
            required=required,
            unique=unique,
            semantic_type=col_analysis.semantic_type.value if col_analysis.semantic_type != SemanticType.UNKNOWN else None,
            pii=col_analysis.is_pii,
        )

        # Add constraints
        if include_constraints:
            constraints = self._generate_constraints(col_analysis, col)
            field_def.constraints = constraints

        return field_def

    def _infer_type(self, col_analysis) -> FieldType:
        """Infer field type from analysis."""
        # Try semantic type first
        if col_analysis.semantic_type in self.SEMANTIC_TYPE_MAPPING:
            return self.SEMANTIC_TYPE_MAPPING[col_analysis.semantic_type]

        # Fall back to statistics-based inference
        stats = col_analysis.statistics
        if "mean" in stats and stats.get("mean") is not None:
            # Numeric type
            min_val = stats.get("min")
            max_val = stats.get("max")

            # Check if integer
            if min_val is not None and max_val is not None:
                if isinstance(min_val, int) and isinstance(max_val, int):
                    return FieldType.INTEGER

            return FieldType.FLOAT

        # Default to string
        return FieldType.STRING

    def _generate_constraints(self, col_analysis, col) -> list[FieldConstraint]:
        """Generate constraints for a field."""
        constraints = []
        stats = col_analysis.statistics

        # Range constraint for numeric fields
        if "mean" in stats and stats.get("mean") is not None:
            min_val = stats.get("min")
            max_val = stats.get("max")

            if min_val is not None and max_val is not None:
                # Add buffer
                range_size = max_val - min_val
                buffer = range_size * 0.1 if range_size > 0 else abs(max_val) * 0.1 or 1

                constraints.append(FieldConstraint(
                    type="range",
                    value=[
                        self._round_nice(min_val - buffer),
                        self._round_nice(max_val + buffer)
                    ]
                ))

            # Non-negative constraint
            if min_val is not None and min_val >= 0:
                constraints.append(FieldConstraint(type="non_negative"))

        # Pattern constraint for semantic types
        if col_analysis.semantic_type in (
            SemanticType.EMAIL,
            SemanticType.PHONE,
            SemanticType.URL,
            SemanticType.UUID,
            SemanticType.IP_ADDRESS,
        ):
            constraints.append(FieldConstraint(
                type="pattern",
                value=col_analysis.semantic_type.value,
            ))

        # Enum constraint for low cardinality
        unique_count = stats.get("unique_count", 0)
        unique_pct = stats.get("unique_percent", 100)

        if 0 < unique_count <= 20 and unique_pct < 5:
            try:
                distinct_values = col.get_distinct_values(limit=25)
                if len(distinct_values) <= 20:
                    allowed = [v for v in distinct_values if v is not None]
                    if allowed:
                        constraints.append(FieldConstraint(
                            type="allowed_values",
                            value=allowed,
                        ))
            except Exception:
                pass

        return constraints

    def _generate_quality_sla(self, dataset: Dataset, analysis) -> QualitySLA:
        """Generate quality SLA from dataset analysis."""
        # Calculate overall completeness
        total_cells = dataset.row_count * dataset.column_count
        total_nulls = sum(
            col.statistics.get("null_count", 0)
            for col in analysis.columns
        )
        actual_completeness = 100 - (total_nulls / total_cells * 100) if total_cells > 0 else 100

        # Set completeness SLA slightly below actual
        completeness_sla = max(95.0, round(actual_completeness - 1, 1))

        # Uniqueness SLAs for unique columns
        uniqueness = {}
        for col in analysis.columns:
            unique_pct = col.statistics.get("unique_percent", 0)
            if unique_pct == 100:
                uniqueness[col.name] = 100.0

        # Row count minimum (80% of current)
        row_count_min = int(dataset.row_count * 0.8) if dataset.row_count > 100 else None

        return QualitySLA(
            completeness=completeness_sla,
            uniqueness=uniqueness,
            row_count_min=row_count_min,
        )

    def _round_nice(self, value: float) -> int | float:
        """Round to a nice human-readable number."""
        if value is None:
            return 0
        if abs(value) < 1:
            return round(value, 2)
        if abs(value) < 100:
            return round(value)
        if abs(value) < 1000:
            return round(value / 10) * 10
        return round(value / 100) * 100


def generate_contract(
    source: str | Dataset,
    output: str | Path | None = None,
    name: str | None = None,
    owner: str | None = None,
    dataset_name: str | None = None,
    as_yaml: bool = False,
) -> DataContract | str:
    """Generate a data contract from a data source.

    Args:
        source: Data source path or Dataset
        output: Optional output file path (.yaml)
        name: Contract name (can also use dataset_name)
        owner: Contract owner
        dataset_name: Alias for name parameter
        as_yaml: If True and output is None, return YAML string instead of DataContract

    Returns:
        DataContract if as_yaml=False, YAML string if as_yaml=True,
        or file path if output is specified
    """
    # Support both name and dataset_name
    contract_name = name or dataset_name

    generator = ContractGenerator()
    contract = generator.generate(source, name=contract_name, owner=owner)

    if output is not None:
        # Write to file
        yaml_content = contract_to_yaml(contract)
        output_path = Path(output)
        output_path.write_text(yaml_content, encoding="utf-8")
        return str(output_path)

    if as_yaml:
        return contract_to_yaml(contract)

    return contract
