# Freshness & Schema Tracking

Monitor data staleness and track schema evolution over time.

## Freshness Quick Start

```python
from duckguard import connect
from datetime import timedelta

data = connect("orders.csv")

# Simple freshness check
print(data.freshness.age_human)  # "2 hours ago"
print(data.freshness.is_fresh)   # True

# Custom threshold
if not data.is_fresh(timedelta(hours=6)):
    print("Data is stale!")
```

## Freshness Methods

DuckGuard checks freshness via file modification time or timestamp columns:

### File Modification Time

```python
from duckguard.freshness import FreshnessMonitor

monitor = FreshnessMonitor(threshold=timedelta(hours=6))
result = monitor.check_file_mtime("data.csv")

print(result.last_modified)      # datetime
print(result.age_human)          # "3 hours ago"
print(result.is_fresh)           # True/False
print(result.method)             # FreshnessMethod.FILE_MTIME
```

### Column Timestamp

```python
result = monitor.check_column_timestamp(data, "updated_at")
# Uses MAX(updated_at) to determine freshness

# Use MIN instead (oldest record)
result = monitor.check_column_timestamp(data, "created_at", use_max=False)
```

### Auto-Detection

`monitor.check()` picks the best method automatically:

1. Local file → uses file mtime
2. Dataset with timestamp column → auto-detects columns like `updated_at`, `created_at`, `timestamp`

## FreshnessResult

```python
result = monitor.check(data)

result.source             # Data source path
result.last_modified      # datetime or None
result.age_seconds        # Float or None
result.age_human          # "2 hours ago"
result.is_fresh           # True/False
result.threshold_seconds  # Configured threshold
result.method             # FILE_MTIME, COLUMN_MAX, etc.
result.to_dict()          # JSON-serializable dict
```

## CLI

```bash
duckguard freshness data.csv
duckguard freshness data.csv --max-age 6h
duckguard freshness data.csv --column updated_at
duckguard freshness data.csv --format json
```

---

## Schema Tracking

Capture schema snapshots over time and detect changes.

### Capture a Snapshot

```python
from duckguard import connect
from duckguard.schema_history import SchemaTracker

tracker = SchemaTracker()
data = connect("data.csv")

snapshot = tracker.capture(data)
print(f"Captured {snapshot.column_count} columns, {snapshot.row_count} rows")
```

### View History

```python
history = tracker.get_history(data.source, limit=10)
for snap in history:
    print(f"{snap.captured_at}: {snap.column_count} columns")
```

### Get Latest Snapshot

```python
latest = tracker.get_latest(data.source)
if latest:
    for col in latest.columns:
        print(f"{col.name}: {col.dtype} (nullable: {col.nullable})")
```

### Detect Changes

```python
from duckguard.schema_history import SchemaChangeAnalyzer

analyzer = SchemaChangeAnalyzer()
# Compare current schema against the last snapshot
# (uses tracker internally)
```

### CLI

```bash
duckguard schema data.csv                    # Show current schema
duckguard schema data.csv --action capture   # Capture snapshot
duckguard schema data.csv --action history   # View history
duckguard schema data.csv --action changes   # Detect changes
```

## Schema Snapshot Structure

Each snapshot captures:

- **Column name** and **data type**
- **Nullable** flag
- **Column position** (ordering)
- **Row count** at capture time
- **Timestamp** of capture

Snapshots are stored in a local SQLite database and compared for drift detection.
