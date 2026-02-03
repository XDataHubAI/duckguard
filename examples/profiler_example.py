"""Example of using DuckGuard's auto-profiler to generate validation rules."""

from duckguard import connect
from duckguard.profiler import AutoProfiler

# Connect to data
orders = connect("examples/sample_data/orders.csv")

# Create profiler
profiler = AutoProfiler(dataset_var_name="orders")

# Profile the dataset
profile = profiler.profile(orders)

# Display profile summary with quality score
print("=" * 60)
print("DuckGuard Auto-Profiler Results")
print("=" * 60)
print(f"Source: {profile.source}")
print(f"Rows: {profile.row_count:,}")
print(f"Columns: {profile.column_count}")
print(f"Overall Quality: {profile.overall_quality_grade} ({profile.overall_quality_score:.1f}/100)")
print()

# Display column profiles with quality grades and percentiles
print("Column Profiles:")
print("-" * 60)
for col in profile.columns:
    print(f"\n{col.name}:")
    print(f"  Type: {col.dtype}")
    print(f"  Nulls: {col.null_count} ({col.null_percent:.1f}%)")
    print(f"  Unique: {col.unique_count} ({col.unique_percent:.1f}%)")
    print(f"  Quality: {col.quality_grade} ({col.quality_score:.0f}/100)")
    if col.min_value is not None:
        print(f"  Range: {col.min_value} - {col.max_value}")
    if col.median_value is not None:
        print(f"  Percentiles: p25={col.p25_value}, median={col.median_value}, p75={col.p75_value}")
    if col.sample_values:
        print(f"  Samples: {col.sample_values[:5]}")

# Display suggested rules (25+ pattern types)
print("\n" + "=" * 60)
print("Suggested Validation Rules:")
print("=" * 60)
for rule in profile.suggested_rules:
    print(f"  {rule}")

# Deep profiling: distribution analysis + outlier detection
print("\n" + "=" * 60)
print("Deep Profiling (distribution + outliers):")
print("=" * 60)
try:
    deep_profiler = AutoProfiler(dataset_var_name="orders", deep=True)
    deep_profile = deep_profiler.profile(orders)
    for col in deep_profile.columns:
        if col.distribution_type:
            print(f"\n{col.name}:")
            print(f"  Distribution: {col.distribution_type}")
            print(f"  Skewness: {col.skewness:.2f}, Kurtosis: {col.kurtosis:.2f}")
            print(f"  Normal: {col.is_normal}")
        if col.outlier_count is not None:
            print(f"  Outliers: {col.outlier_count} ({col.outlier_percentage:.1f}%)")
except ImportError:
    print("  [SKIP] Deep profiling requires scipy: pip install 'duckguard[profiling]'")

# Configurable thresholds
print("\n" + "=" * 60)
print("Configurable Thresholds:")
print("=" * 60)
strict = AutoProfiler(
    dataset_var_name="orders",
    null_threshold=0.0,  # Only suggest not_null for zero-null columns
    unique_threshold=100.0,  # Only suggest unique for 100% unique columns
    pattern_min_confidence=95.0,  # Higher confidence for pattern matches
)
strict_profile = strict.profile(orders)
print(f"Default rules: {len(profile.suggested_rules)}")
print(f"Strict rules:  {len(strict_profile.suggested_rules)}")

# Generate a test file
print("\n" + "=" * 60)
print("Generated Test File:")
print("=" * 60)
test_code = profiler.generate_test_file(orders, output_var="orders")
print(test_code)

# CLI usage
print("\n" + "=" * 60)
print("CLI Usage:")
print("=" * 60)
print("  duckguard profile data.csv                  # Rich table output")
print("  duckguard profile data.csv --format json    # JSON output")
print("  duckguard profile data.csv --deep           # Deep profiling")
print("  duckguard profile data.csv -o profile.json  # Save to file")
