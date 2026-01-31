"""
DuckGuard - Data quality that just works.

A Python-native data quality tool built on DuckDB for speed.
Features YAML-based rules, semantic type detection, data contracts,
anomaly detection, notifications, and dbt integration.

Quick Start:
    # Python API
    from duckguard import connect
    orders = connect("data/orders.csv")
    assert orders.row_count > 0
    assert orders.customer_id.null_percent == 0

    # With row-level error capture
    result = orders.quantity.between(1, 100)
    if not result:
        print(result.summary())  # See which rows failed

    # Notifications
    from duckguard.notifications import SlackNotifier
    slack = SlackNotifier(webhook_url="...")
    slack.send_failure_alert(result)

    # CLI
    $ duckguard check data.csv
    $ duckguard discover data.csv --output duckguard.yaml
    $ duckguard contract generate data.csv

Documentation: https://github.com/XDataHubAI/duckguard
"""

# Core classes
# Anomaly detection
from duckguard.anomaly import (
    AnomalyDetector,
    AnomalyResult,
    detect_anomalies,
)

# Connectors
from duckguard.connectors import connect

# Data contracts
from duckguard.contracts import (
    DataContract,
    diff_contracts,
    generate_contract,
    load_contract,
    validate_contract,
)
from duckguard.core.column import Column
from duckguard.core.dataset import Dataset
from duckguard.core.engine import DuckGuardEngine
from duckguard.core.result import CheckResult, FailedRow, ValidationResult
from duckguard.core.scoring import QualityScore, QualityScorer, score

# Error classes
from duckguard.errors import (
    ColumnNotFoundError,
    ContractViolationError,
    DuckGuardError,
    RuleParseError,
    UnsupportedConnectorError,
    ValidationError,
)

# Profiling
from duckguard.profiler import AutoProfiler, profile

# Rules (YAML-based)
from duckguard.rules import (
    RuleSet,
    execute_rules,
    generate_rules,
    load_rules,
    load_rules_from_string,
)

# Semantic type detection
from duckguard.semantic import (
    SemanticAnalyzer,
    SemanticType,
    detect_type,
    detect_types_for_dataset,
)

__version__ = "3.1.0"

__all__ = [
    # Core classes
    "Dataset",
    "Column",
    "DuckGuardEngine",
    "ValidationResult",
    "CheckResult",
    "FailedRow",
    # Scoring
    "QualityScore",
    "QualityScorer",
    "score",
    # Connectors
    "connect",
    # Profiling
    "profile",
    "AutoProfiler",
    # Rules
    "load_rules",
    "load_rules_from_string",
    "execute_rules",
    "generate_rules",
    "RuleSet",
    # Semantic
    "SemanticType",
    "SemanticAnalyzer",
    "detect_type",
    "detect_types_for_dataset",
    # Contracts
    "DataContract",
    "load_contract",
    "validate_contract",
    "generate_contract",
    "diff_contracts",
    # Anomaly
    "AnomalyDetector",
    "AnomalyResult",
    "detect_anomalies",
    # Errors
    "DuckGuardError",
    "ColumnNotFoundError",
    "ContractViolationError",
    "RuleParseError",
    "UnsupportedConnectorError",
    "ValidationError",
    # Version
    "__version__",
]
