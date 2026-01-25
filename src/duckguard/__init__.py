"""
DuckGuard - Data quality that just works.

A Python-native data quality tool built on DuckDB for speed.
Features YAML-based rules, semantic type detection, data contracts,
and anomaly detection.

Quick Start:
    # Python API
    from duckguard import connect
    orders = connect("data/orders.csv")
    assert orders.row_count > 0
    assert orders.customer_id.null_percent == 0

    # CLI
    $ duckguard check data.csv
    $ duckguard discover data.csv --output duckguard.yaml
    $ duckguard contract generate data.csv

Documentation: https://github.com/duckguard/duckguard
"""

# Core classes
from duckguard.core.dataset import Dataset
from duckguard.core.column import Column
from duckguard.core.engine import DuckGuardEngine
from duckguard.core.result import ValidationResult, CheckResult
from duckguard.core.scoring import QualityScore, QualityScorer, score

# Connectors
from duckguard.connectors import connect

# Profiling
from duckguard.profiler import profile, AutoProfiler

# Rules (YAML-based)
from duckguard.rules import (
    load_rules,
    load_rules_from_string,
    execute_rules,
    generate_rules,
    RuleSet,
)

# Semantic type detection
from duckguard.semantic import (
    SemanticType,
    SemanticAnalyzer,
    detect_type,
    detect_types_for_dataset,
)

# Data contracts
from duckguard.contracts import (
    DataContract,
    load_contract,
    validate_contract,
    generate_contract,
    diff_contracts,
)

# Anomaly detection
from duckguard.anomaly import (
    AnomalyDetector,
    AnomalyResult,
    detect_anomalies,
)

__version__ = "2.0.0"

__all__ = [
    # Core classes
    "Dataset",
    "Column",
    "DuckGuardEngine",
    "ValidationResult",
    "CheckResult",
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
    # Version
    "__version__",
]
