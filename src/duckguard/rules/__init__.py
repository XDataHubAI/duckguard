"""YAML-based rule system for DuckGuard.

This module provides a declarative YAML syntax for defining data quality rules,
making DuckGuard accessible to users who prefer configuration over code.

Example:
    from duckguard.rules import load_rules, execute_rules

    rules = load_rules("duckguard.yaml")
    results = execute_rules(rules, "data.csv")
"""

from duckguard.rules.executor import RuleExecutor, execute_rules
from duckguard.rules.generator import generate_rules
from duckguard.rules.loader import load_rules, load_rules_from_string
from duckguard.rules.schema import Check, ColumnRules, RuleSet, SimpleCheck

__all__ = [
    "load_rules",
    "load_rules_from_string",
    "execute_rules",
    "RuleExecutor",
    "RuleSet",
    "ColumnRules",
    "Check",
    "SimpleCheck",
    "generate_rules",
]
