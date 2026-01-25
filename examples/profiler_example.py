"""Example of using DuckGuard's auto-profiler to generate validation rules."""

from duckguard import connect
from duckguard.profiler import AutoProfiler

# Connect to data
orders = connect("examples/sample_data/orders.csv")

# Create profiler
profiler = AutoProfiler(dataset_var_name="orders")

# Profile the dataset
profile = profiler.profile(orders)

# Display profile summary
print("=" * 60)
print("DuckGuard Auto-Profiler Results")
print("=" * 60)
print(f"Source: {profile.source}")
print(f"Rows: {profile.row_count:,}")
print(f"Columns: {profile.column_count}")
print()

# Display column profiles
print("Column Profiles:")
print("-" * 60)
for col in profile.columns:
    print(f"\n{col.name}:")
    print(f"  Type: {col.dtype}")
    print(f"  Nulls: {col.null_count} ({col.null_percent:.1f}%)")
    print(f"  Unique: {col.unique_count} ({col.unique_percent:.1f}%)")
    if col.min_value is not None:
        print(f"  Range: {col.min_value} - {col.max_value}")
    if col.sample_values:
        print(f"  Samples: {col.sample_values[:5]}")

# Display suggested rules
print("\n" + "=" * 60)
print("Suggested Validation Rules:")
print("=" * 60)
for rule in profile.suggested_rules:
    print(f"  {rule}")

# Generate a test file
print("\n" + "=" * 60)
print("Generated Test File:")
print("=" * 60)
test_code = profiler.generate_test_file(orders, output_var="orders")
print(test_code)
