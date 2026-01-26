# Changelog

All notable changes to DuckGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2025-01-25

### Added

#### Cross-Dataset Validation (Reference/FK Checks)
Validate foreign key relationships and compare data across multiple datasets.

- **`column.exists_in(reference_column)`** - Check that all non-null values exist in a reference column
- **`column.references(reference_column, allow_nulls=True)`** - Validate FK relationships with configurable null handling
- **`column.find_orphans(reference_column, limit=100)`** - Get orphan values that don't exist in the reference
- **`column.matches_values(other_column)`** - Compare distinct value sets between columns
- **`dataset.row_count_matches(other_dataset, tolerance=0)`** - Compare row counts between datasets

```python
from duckguard import connect

orders = connect("orders.parquet")
customers = connect("customers.parquet")

# Validate all customer_ids exist in customers table
result = orders["customer_id"].exists_in(customers["id"])
print(f"Valid: {result.passed}, Orphans: {result.actual_value}")

# Find orphan values
orphans = orders["customer_id"].find_orphans(customers["id"])
print(f"Invalid customer_ids: {orphans}")
```

#### Dataset Reconciliation
Compare two datasets row-by-row with key-based matching.

- **`dataset.reconcile(target, key_columns, compare_columns, tolerance)`** - Full reconciliation between datasets
- Detects missing rows, extra rows, and value mismatches
- Supports numeric tolerance for approximate matching
- Sample mismatch capture for debugging

```python
source = connect("source_orders.csv")
target = connect("target_orders.csv")

result = source.reconcile(
    target,
    key_columns=["order_id"],
    compare_columns=["amount", "status"],
    tolerance=0.01
)

print(f"Match rate: {result.match_percentage}%")
print(f"Missing in target: {result.missing_in_target}")
print(f"Extra in target: {result.extra_in_target}")
```

#### Distribution Drift Detection
Detect statistical drift between baseline and current data using the Kolmogorov-Smirnov test.

- **`column.detect_drift(reference_column, threshold=0.05)`** - Detect distribution drift
- Returns p-value, test statistic, and drift status
- Configurable significance threshold

```python
baseline = connect("baseline_data.csv")
current = connect("current_data.csv")

result = baseline["amount"].detect_drift(current["amount"])

if result.is_drifted:
    print(f"DRIFT DETECTED: p-value={result.p_value:.4f}")
else:
    print(f"No drift: p-value={result.p_value:.4f}")
```

#### Group By Checks
Perform validation checks on grouped data for per-group quality assertions.

- **`dataset.group_by(columns)`** - Group dataset by one or more columns
- **`grouped.row_count_greater_than(n)`** - Validate minimum rows per group
- **`grouped.stats()`** - Get statistics for each group
- **`grouped.groups`** - Access group information
- Pass rate and failed group tracking

```python
orders = connect("orders.csv")

# Check each region has at least 10 orders
result = orders.group_by("region").row_count_greater_than(10)

print(f"Pass rate: {result.pass_rate}%")
print(f"Failed groups: {result.failed_groups}")

# Get failed group details
for group in result.get_failed_groups():
    print(f"Region {group['region']}: only {group['row_count']} rows")
```

### Changed

- Improved test organization: split monolithic test file into feature-specific test modules
- Enhanced test coverage with 31 tests for new features

### Fixed

- Fixed version sync between `pyproject.toml` and `__init__.py`

## [2.2.1] - 2025-01-24

### Fixed

- Resolved lint errors
- Minor bug fixes

## [2.2.0] - 2025-01-23

### Added

- Initial public release with core features:
  - Data profiling and quality scoring
  - YAML-based validation rules
  - Semantic type detection
  - Data contracts
  - Anomaly detection
  - CLI interface
  - pytest plugin
  - Multiple database connectors
