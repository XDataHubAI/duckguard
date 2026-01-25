"""YAML rule generator for DuckGuard.

Auto-generates validation rules from data analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from duckguard.connectors import connect
from duckguard.core.dataset import Dataset
from duckguard.rules.schema import (
    BUILTIN_PATTERNS,
    CASE_SENSITIVE_PATTERNS,
    Check,
    CheckType,
    ColumnRules,
    RuleSet,
)


class RuleGenerator:
    """Generates validation rules from data analysis."""

    # Thresholds for rule generation
    NULL_THRESHOLD = 1.0      # Suggest not_null if nulls < 1%
    UNIQUE_THRESHOLD = 99.0   # Suggest unique if > 99%
    ENUM_MAX_VALUES = 20      # Max distinct values for enum
    PATTERN_MIN_MATCH = 0.9   # Min match rate for pattern detection

    def __init__(self):
        self._patterns = BUILTIN_PATTERNS.copy()

    def generate(
        self,
        source: str | Dataset,
        include_suggestions: bool = True
    ) -> RuleSet:
        """Generate rules for a data source.

        Args:
            source: Data source path or Dataset
            include_suggestions: Include suggested rules based on analysis

        Returns:
            RuleSet with generated rules
        """
        if isinstance(source, str):
            dataset = connect(source)
            source_path = source
        else:
            dataset = source
            source_path = dataset.source

        ruleset = RuleSet(
            source=source_path,
            name=Path(source_path).stem if source_path else "dataset",
            description=f"Auto-generated rules for {source_path}",
        )

        # Add row count check
        ruleset.add_table_check(
            CheckType.ROW_COUNT,
            value=0,
            operator=">"
        )

        # Analyze each column
        for col_name in dataset.columns:
            col_rules = self._analyze_column(dataset, col_name, include_suggestions)
            if col_rules.checks:
                ruleset.columns[col_name] = col_rules

        return ruleset

    def _analyze_column(
        self,
        dataset: Dataset,
        col_name: str,
        include_suggestions: bool
    ) -> ColumnRules:
        """Analyze a column and generate rules."""
        col = dataset[col_name]
        rules = ColumnRules(name=col_name)

        # Get statistics
        null_pct = col.null_percent
        unique_pct = col.unique_percent
        unique_count = col.unique_count
        total_count = col.total_count

        # Get sample values for pattern detection
        try:
            sample_values = col.get_distinct_values(limit=100)
        except Exception:
            sample_values = []

        # 1. Null check
        if null_pct == 0:
            rules.checks.append(Check(
                type=CheckType.NOT_NULL,
                params={"confidence": 1.0, "reason": "No null values found"}
            ))
        elif null_pct < self.NULL_THRESHOLD and include_suggestions:
            threshold = max(1, round(null_pct * 2))
            rules.checks.append(Check(
                type=CheckType.NULL_PERCENT,
                value=threshold,
                operator="<",
                params={"confidence": 0.9, "reason": f"Only {null_pct:.2f}% nulls"}
            ))

        # 2. Uniqueness check
        if unique_pct == 100:
            rules.checks.append(Check(
                type=CheckType.UNIQUE,
                params={"confidence": 1.0, "reason": "All values unique"}
            ))
        elif unique_pct > self.UNIQUE_THRESHOLD and include_suggestions:
            rules.checks.append(Check(
                type=CheckType.UNIQUE_PERCENT,
                value=99,
                operator=">",
                params={"confidence": 0.8, "reason": f"{unique_pct:.2f}% unique"}
            ))

        # 3. Numeric range check
        try:
            mean = col.mean
            if mean is not None:
                min_val = col.min
                max_val = col.max

                if min_val is not None and max_val is not None:
                    # Add range with buffer
                    range_size = max_val - min_val
                    buffer = range_size * 0.1 if range_size > 0 else abs(max_val) * 0.1 or 1

                    suggested_min = self._round_nice(min_val - buffer)
                    suggested_max = self._round_nice(max_val + buffer)

                    rules.checks.append(Check(
                        type=CheckType.BETWEEN,
                        value=[suggested_min, suggested_max],
                        params={
                            "confidence": 0.7,
                            "reason": f"Values range from {min_val} to {max_val}"
                        }
                    ))

                # Non-negative check
                if min_val is not None and min_val >= 0:
                    rules.checks.append(Check(
                        type=CheckType.NON_NEGATIVE,
                        params={"confidence": 0.9, "reason": "All values non-negative"}
                    ))
        except Exception:
            pass

        # 4. Enum check for low cardinality
        if 0 < unique_count <= self.ENUM_MAX_VALUES and total_count > unique_count * 2:
            try:
                distinct_values = col.get_distinct_values(limit=self.ENUM_MAX_VALUES + 1)
                if len(distinct_values) <= self.ENUM_MAX_VALUES:
                    # Filter out None values
                    allowed = [v for v in distinct_values if v is not None]
                    if allowed:
                        rules.checks.append(Check(
                            type=CheckType.ALLOWED_VALUES,
                            value=allowed,
                            params={
                                "confidence": 0.85,
                                "reason": f"Only {len(allowed)} distinct values"
                            }
                        ))
            except Exception:
                pass

        # 5. Pattern detection
        string_values = [v for v in sample_values if isinstance(v, str) and v]
        if string_values:
            detected = self._detect_pattern(string_values)
            if detected:
                pattern_name, pattern, match_rate = detected
                rules.checks.append(Check(
                    type=CheckType.PATTERN,
                    value=pattern_name,  # Use pattern name for readability
                    params={
                        "confidence": match_rate,
                        "reason": f"Values appear to be {pattern_name}",
                        "pattern_name": pattern_name,
                    }
                ))
                rules.semantic_type = pattern_name

        return rules

    def _detect_pattern(
        self,
        values: list[str]
    ) -> tuple[str, str, float] | None:
        """Detect common patterns in string values.

        Returns:
            Tuple of (pattern_name, pattern, match_rate) or None
        """
        import re

        if not values:
            return None

        sample = values[:100]

        for pattern_name, pattern in self._patterns.items():
            try:
                # Use case-sensitive matching for certain patterns (slug, identifier)
                flags = 0 if pattern_name in CASE_SENSITIVE_PATTERNS else re.IGNORECASE
                matches = sum(
                    1 for v in sample
                    if re.match(pattern, str(v), flags)
                )
                match_rate = matches / len(sample)

                if match_rate >= self.PATTERN_MIN_MATCH:
                    return pattern_name, pattern, match_rate
            except Exception:
                continue

        return None

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


def generate_rules(
    source: str | Dataset,
    output: str | Path | None = None,
    include_suggestions: bool = True,
    dataset_name: str | None = None,
    as_yaml: bool = True,
) -> RuleSet | str:
    """Generate validation rules for a data source.

    Args:
        source: Data source path or Dataset
        output: Optional output file path (.yaml)
        include_suggestions: Include suggested rules
        dataset_name: Override the dataset name in generated rules
        as_yaml: If True and output is None, return YAML string instead of RuleSet

    Returns:
        YAML string if as_yaml=True, RuleSet object if as_yaml=False,
        or file path if output is specified
    """
    generator = RuleGenerator()
    ruleset = generator.generate(source, include_suggestions)

    # Override name if specified
    if dataset_name:
        ruleset.name = dataset_name

    if output is not None:
        # Write to file
        yaml_content = ruleset_to_yaml(ruleset)
        output_path = Path(output)
        output_path.write_text(yaml_content, encoding="utf-8")
        return str(output_path)

    if as_yaml:
        return ruleset_to_yaml(ruleset)

    return ruleset


def ruleset_to_yaml(ruleset: RuleSet) -> str:
    """Convert a RuleSet to YAML string."""
    data: dict[str, Any] = {}

    if ruleset.source:
        data["source"] = ruleset.source

    if ruleset.name:
        data["name"] = ruleset.name

    if ruleset.version and ruleset.version != "1.0":
        data["version"] = ruleset.version

    if ruleset.description:
        data["description"] = ruleset.description

    # Table-level checks
    if ruleset.table.checks:
        data["table"] = []
        for check in ruleset.table.checks:
            data["table"].append(_check_to_dict(check))

    # Column checks
    if ruleset.columns:
        data["checks"] = {}
        for col_name, col_rules in ruleset.columns.items():
            if col_rules.checks:
                data["checks"][col_name] = []
                for check in col_rules.checks:
                    data["checks"][col_name].append(_check_to_dict(check))

    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _check_to_dict(check: Check) -> dict[str, Any] | str:
    """Convert a Check to YAML-friendly dict or string."""
    # Simple checks without values
    simple_types = {
        CheckType.NOT_NULL: "not_null",
        CheckType.UNIQUE: "unique",
        CheckType.NO_DUPLICATES: "no_duplicates",
        CheckType.POSITIVE: "positive",
        CheckType.NEGATIVE: "negative",
        CheckType.NON_NEGATIVE: "non_negative",
    }

    if check.type in simple_types and check.value is None:
        return simple_types[check.type]

    # Checks with values
    type_name = check.type.value

    if check.value is not None:
        if check.operator and check.operator != "=":
            return {type_name: f"{check.operator} {check.value}"}
        return {type_name: check.value}

    return type_name
