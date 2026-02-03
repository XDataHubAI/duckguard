# Anomaly Detection

DuckGuard includes 7 built-in anomaly detection methods, from simple statistical tests to ML-powered baselines.

## Quick Start

```python
from duckguard import detect_anomalies

report = detect_anomalies(orders, method="zscore", columns=["quantity", "amount"])

print(report.has_anomalies)    # True/False
print(report.anomaly_count)    # Number of anomalies

for a in report.anomalies:
    print(f"{a.column}: score={a.score:.2f}, anomaly={a.is_anomaly}")
```

## Methods

| Method | Best for | How it works |
|--------|----------|-------------|
| `zscore` | Normal distributions | Flags values >3σ from mean |
| `iqr` | Skewed data | Uses interquartile range (Q1-1.5·IQR, Q3+1.5·IQR) |
| `modified_zscore` | Robust to outliers | Uses median absolute deviation |
| `percent_change` | Time series | Flags sudden changes between periods |
| `baseline` | Historical comparison | Fit on historical data, score new values |
| `ks_test` | Distribution drift | Kolmogorov-Smirnov test between distributions |
| `seasonal` | Periodic patterns | Time-aware anomaly detection |

## Using AnomalyDetector

```python
from duckguard.anomaly import AnomalyDetector

# IQR method with custom threshold
detector = AnomalyDetector(method="iqr", threshold=1.5)
report = detector.detect(orders, columns=["quantity"])
```

## ML Baseline

Fit a baseline on historical data and score new values against it:

```python
from duckguard.anomaly import BaselineMethod

baseline = BaselineMethod(sensitivity=2.0)
baseline.fit([100, 102, 98, 105, 97, 103])

# Score a single value
score = baseline.score(250)
print(score.is_anomaly)  # True
print(score.score)       # deviation score

# Score an entire column
scores = baseline.score(orders.amount)
```

## KS Test (Distribution Drift)

```python
from duckguard.anomaly import KSTestMethod

ks = KSTestMethod(p_value_threshold=0.05)
ks.fit([1, 2, 3, 4, 5])

comparison = ks.compare_distributions([10, 11, 12, 13, 14])
print(comparison.is_drift)   # True
print(comparison.p_value)    # 0.008
print(comparison.message)    # "Significant distribution drift detected"
```

## Seasonal Detection

```python
from duckguard.anomaly import SeasonalMethod

seasonal = SeasonalMethod(period="daily", sensitivity=2.0)
seasonal.fit([10, 12, 11, 13, 9, 14])
```

## CLI

```bash
# Detect anomalies with Z-score
duckguard anomaly orders.csv --method zscore

# IQR method on specific columns
duckguard anomaly orders.csv --method iqr --columns quantity,amount
```
