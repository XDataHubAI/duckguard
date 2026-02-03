"""Anomaly detection for DuckGuard.

Provides statistical and ML-based anomaly detection for data quality monitoring.

Example:
    from duckguard.anomaly import detect_anomalies, AnomalyDetector

    detector = AnomalyDetector()
    anomalies = detector.detect(dataset, column="amount")
"""

from duckguard.anomaly.baselines import (
    BaselineStorage,
    ColumnBaseline,
    StoredBaseline,
)
from duckguard.anomaly.detector import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
    detect_anomalies,
    detect_column_anomalies,
)
from duckguard.anomaly.methods import (
    IQRMethod,
    ModifiedZScoreMethod,
    PercentChangeMethod,
    ZScoreMethod,
    create_method,
)
from duckguard.anomaly.ml_methods import (
    BaselineComparison,
    BaselineMethod,
    DistributionComparison,
    KSTestMethod,
    SeasonalMethod,
)

__all__ = [
    # Detector
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalyType",
    "detect_anomalies",
    "detect_column_anomalies",
    # Standard methods
    "ZScoreMethod",
    "IQRMethod",
    "PercentChangeMethod",
    "ModifiedZScoreMethod",
    "create_method",
    # ML methods
    "BaselineMethod",
    "KSTestMethod",
    "SeasonalMethod",
    "BaselineComparison",
    "DistributionComparison",
    # Baselines
    "BaselineStorage",
    "StoredBaseline",
    "ColumnBaseline",
]
