# Quality Scoring

DuckGuard scores data quality across four dimensions and assigns an A-F letter grade.

## Quick Score

```python
from duckguard import connect

orders = connect("orders.csv")
score = orders.score()

print(score.grade)          # A, B, C, D, or F
print(score.overall)        # 0-100 composite score
```

## Quality Dimensions

| Dimension | What it measures |
|-----------|-----------------|
| **Completeness** | % of non-null values across columns |
| **Uniqueness** | % of unique values in key columns |
| **Validity** | % of values passing type and range checks |
| **Consistency** | % of values with consistent formatting |

```python
score = orders.score()

print(score.completeness)   # 98.5
print(score.uniqueness)     # 100.0
print(score.validity)       # 95.2
print(score.consistency)    # 97.8
```

## Grade Scale

| Grade | Score Range | Meaning |
|:-----:|:----------:|---------|
| A | 90-100 | Excellent — production ready |
| B | 80-89 | Good — minor issues |
| C | 70-79 | Fair — needs attention |
| D | 60-69 | Poor — significant issues |
| F | <60 | Failing — not usable |

## Profiling for Deeper Insight

```python
from duckguard import AutoProfiler

profiler = AutoProfiler()
profile = profiler.profile(orders)

print(f"Columns: {profile.column_count}")
print(f"Rows: {profile.row_count}")
print(f"Quality: {profile.overall_quality_grade} ({profile.overall_quality_score:.1f}/100)")

# Per-column breakdown
for col in profile.columns:
    print(f"  {col.name}: grade={col.quality_grade}, nulls={col.null_percent:.1f}%")
```

### Deep Profiling

Enable distribution analysis and outlier detection for numeric columns:

```python
deep_profiler = AutoProfiler(deep=True)
profile = deep_profiler.profile(orders)

for col in profile.columns:
    if col.distribution_type:
        print(f"  {col.name}: {col.distribution_type}, skew={col.skewness:.2f}")
    if col.outlier_count is not None:
        print(f"    outliers: {col.outlier_count} ({col.outlier_percentage:.1f}%)")
```

### Custom Thresholds

```python
strict = AutoProfiler(
    null_threshold=0.0,            # Any nulls trigger not_null suggestion
    unique_threshold=100.0,        # Must be 100% unique
    pattern_min_confidence=95.0,   # Higher confidence for patterns
)
profile = strict.profile(orders)
```

## Auto-Generated Rules

DuckGuard can suggest validation rules based on your data:

```python
from duckguard import generate_rules

yaml_rules = generate_rules(orders, dataset_name="orders")
print(yaml_rules)  # Ready-to-use YAML
```

## CLI

```bash
# Quick profile
duckguard profile orders.csv

# Deep profile with JSON output
duckguard profile orders.csv --deep --format json

# Save to file
duckguard profile orders.csv -o profile.json
```
