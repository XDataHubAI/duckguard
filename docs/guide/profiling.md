# Profiling

Auto-profile datasets to discover statistics, patterns, and quality scores — then generate validation rules automatically.

## Quick Start

```python
from duckguard import connect, profile

data = connect("orders.csv")
result = profile(data)

print(f"Rows: {result.row_count}, Columns: {result.column_count}")
print(f"Quality: {result.overall_quality_score:.0f}/100 ({result.overall_quality_grade})")

# Print suggested rules
for rule in result.suggested_rules:
    print(rule)
```

```bash
# CLI
duckguard profile data.csv
duckguard profile data.csv --deep
duckguard profile data.csv --format json -o profile.json
```

## Column Profiles

Each column gets a full statistical profile:

```python
for col in result.columns:
    print(f"{col.name}: {col.dtype}")
    print(f"  Nulls: {col.null_percent:.1f}%")
    print(f"  Unique: {col.unique_percent:.1f}%")
    print(f"  Min: {col.min_value}, Max: {col.max_value}")
    print(f"  Mean: {col.mean_value}, Median: {col.median_value}")
    print(f"  Stddev: {col.stddev_value}")
    print(f"  P25: {col.p25_value}, P75: {col.p75_value}")
    print(f"  Quality: {col.quality_score:.0f}/100 ({col.quality_grade})")
    print(f"  Rules: {len(col.suggested_rules)}")
```

## Deep Profiling

Enable distribution analysis and outlier detection with `deep=True`:

```python
result = profile(data, deep=True)

for col in result.columns:
    if col.distribution_type:
        print(f"{col.name}: {col.distribution_type}")
        print(f"  Skewness: {col.skewness:.2f}")
        print(f"  Kurtosis: {col.kurtosis:.2f}")
        print(f"  Normal: {col.is_normal}")
        print(f"  Outliers: {col.outlier_count} ({col.outlier_percentage:.1f}%)")
```

Deep profiling uses:

- **DistributionAnalyzer** — fits distributions, tests normality (requires scipy)
- **OutlierDetector** — IQR-based outlier detection (works without scipy)

## Rule Suggestions

The profiler generates Python assertions automatically:

```python
# Suggested rules look like:
# assert data.order_id.null_percent == 0
# assert data.order_id.has_no_duplicates()
# assert data.amount.between(0, 10000)
# assert data.status.isin(['pending', 'shipped', 'delivered'])
```

Rules are generated based on:

| Pattern | Rule |
|---------|------|
| 0% nulls | `null_percent == 0` |
| <1% nulls | `null_percent < N` (with buffer) |
| 100% unique | `has_no_duplicates()` |
| Numeric range | `between(min, max)` (with 10% buffer) |
| Non-negative | `min >= 0` |
| Low cardinality (≤20 values) | `isin([...])` |
| Pattern match (email, UUID, etc.) | `matches(r"...")` |

## Generate Test Files

```python
from duckguard.profiler import AutoProfiler

profiler = AutoProfiler()
test_code = profiler.generate_test_file(data, output_var="orders")
print(test_code)
```

Output:

```python
"""Auto-generated data quality tests by DuckGuard."""

from duckguard import connect

def test_orders():
    orders = connect("orders.csv")

    # Basic dataset checks
    assert orders.row_count > 0

    # order_id validations
    assert orders.order_id.null_percent == 0
    assert orders.order_id.has_no_duplicates()

    # amount validations
    assert orders.amount.between(0, 11000)
    assert orders.amount.min >= 0
```

## Configurable Thresholds

```python
from duckguard.profiler import AutoProfiler

profiler = AutoProfiler(
    null_threshold=1.0,           # Suggest not_null below 1% nulls
    unique_threshold=99.0,        # Suggest unique above 99%
    enum_max_values=20,           # Max distinct values for enum suggestion
    pattern_sample_size=1000,     # Samples for pattern detection
    pattern_min_confidence=90.0,  # Min confidence for pattern match
)
result = profiler.profile(data)
```
