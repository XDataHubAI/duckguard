# Modern Formats

Connect to Delta Lake and Apache Iceberg tables.

## Delta Lake

DuckGuard reads Delta Lake tables through DuckDB's Delta extension.

### Quick Start

```python
from duckguard import connect

# Local Delta table
data = connect("path/to/delta_table/")

# Delta on S3
data = connect("s3://bucket/delta_table/")
```

### Time Travel

DuckDB's Delta support enables reading specific versions:

```python
# Read Delta table at a specific version via DuckDB SQL
data = connect("delta_table/")
rows = data.execute_sql(
    "SELECT * FROM delta_scan('{source}', version=5)"
)
```

### Requirements

Delta Lake support requires the DuckDB `delta` extension, which loads automatically on first use.

### Validation

```python
data = connect("s3://datalake/orders_delta/")

# Same API as any other source
assert data.row_count > 0
assert data.order_id.null_percent == 0

score = data.score()
print(f"Quality: {score.grade}")
```

## Apache Iceberg

DuckGuard reads Iceberg tables through DuckDB's Iceberg extension.

### Quick Start

```python
from duckguard import connect

# Local Iceberg table
data = connect("path/to/iceberg_table/")

# Iceberg on S3
data = connect("s3://bucket/iceberg_table/")
```

### Requirements

Iceberg support requires the DuckDB `iceberg` extension.

### Validation

```python
data = connect("s3://warehouse/orders_iceberg/")

assert data.row_count > 0
result = data.amount.between(0, 100000)
assert result.passed
```

## Comparison

| Feature | Delta Lake | Iceberg |
|---------|-----------|---------|
| ACID transactions | ✅ | ✅ |
| Time travel | ✅ | ✅ |
| Schema evolution | ✅ | ✅ |
| Partition pruning | ✅ | ✅ |
| DuckDB extension | `delta` | `iceberg` |
| Cloud support | S3, GCS, Azure | S3, GCS, Azure |

## Practical Patterns

### Quality gate for lakehouse

```python
from duckguard import connect, load_rules, execute_rules

data = connect("s3://datalake/orders/")
rules = load_rules("duckguard.yaml")
result = execute_rules(rules, dataset=data)

if not result.passed:
    raise RuntimeError(f"Quality gate failed: {result.failed_count} checks")
```

### Compare Delta versions

```python
current = connect("s3://lake/orders/")
backup = connect("s3://lake/orders_backup/")

result = current.row_count_matches(backup, tolerance=100)
assert result.passed
```

### Profile a Delta table

```python
from duckguard import connect, profile

data = connect("s3://lake/events/")
result = profile(data, deep=True)

for col in result.columns:
    print(f"{col.name}: {col.quality_grade} ({col.null_percent:.1f}% nulls)")
```
