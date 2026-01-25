"""Anomaly detection for DuckGuard.

Provides statistical and ML-based anomaly detection for data quality monitoring.

Example:
    from duckguard.anomaly import detect_anomalies, AnomalyDetector

    detector = AnomalyDetector()
    anomalies = detector.detect(dataset, column="amount")
"""

from duckguard.anomaly.detector import (
    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
    detect_anomalies,
    detect_column_anomalies,
)
from duckguard.anomaly.methods import (
    IQRMethod,
    PercentChangeMethod,
    ZScoreMethod,
)

__all__ = [
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalyType",
    "detect_anomalies",
    "detect_column_anomalies",
    "ZScoreMethod",
    "IQRMethod",
    "PercentChangeMethod",
]
